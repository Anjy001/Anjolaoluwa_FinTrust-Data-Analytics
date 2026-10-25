"""Build the HealthConnect Power BI project from the executed SQLite model."""
from pathlib import Path
import base64
import json
import shutil
import sqlite3
import uuid
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'Dashboard'; R=D/'HealthConnect.Report'; S=D/'HealthConnect.SemanticModel'

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2),encoding='utf-8')
def schema(kind,version):return f'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/{kind}/{version}/schema.json'
def literal(value):return {'expr':{'Literal':{'Value':value}}}
def text(value):return literal("'"+str(value).replace("'","''")+"'")
def field(entity,column,measure=False):return {'Measure' if measure else 'Column':{'Expression':{'SourceRef':{'Entity':entity}},'Property':column}}
def projection(entity,column,measure=False):return {'field':field(entity,column,measure),'queryRef':entity+'.'+column,'nativeQueryRef':column}

MEASURES=[
('Registered Patients','COUNTROWS(Patients)','#,0','Supplied patient register; independent of encounter dates.'),
('Observed Patients','DISTINCTCOUNT(Appointments[PatientID])','#,0','Distinct patients represented in selected available appointments.'),
('Available Appointments','COUNTROWS(Appointments)','#,0','Available encounter extract; not the RevenueSummary annual count.'),
('Repeat Visit Patients','COUNTROWS(FILTER(VALUES(Appointments[PatientID]),CALCULATE(COUNTROWS(Appointments))>=2))','#,0','Patients with at least two appointments in the selected extract.'),
('First Observed Patients','CALCULATE(DISTINCTCOUNT(Appointments[PatientID]),Appointments[IsFirstObserved]=1)','#,0','First encounter in supplied history, not new registration.'),
('Mean Recorded Age','AVERAGE(Patients[Age])','0.00','Source age retained; not recalculated against the execution date.'),
('Insurance Code Presence','DIVIDE(COUNTROWS(FILTER(Patients,NOT(ISBLANK(Patients[InsuranceID])))),[Registered Patients])','0.00%','Nonblank insurance code, not verified insurance validity.'),
('Chronic Condition Share','DIVIDE(COUNTROWS(FILTER(Patients,Patients[ChronicCondition]<>"None")),[Registered Patients])','0.00%','Recorded register category prevalence.'),
('Emergency Share','DIVIDE(CALCULATE([Available Appointments],KEEPFILTERS(Appointments[VisitType]="Emergency")),[Available Appointments])','0.00%','Emergency-labelled available appointments.'),
('Diagnosis Records','COUNTROWS(Diagnoses)','#,0','Full 60,000-row CSV at diagnosis grain.'),
('Laboratory Tests','COUNTROWS(LaboratoryTests)','#,0','Test records; unmatched appointment IDs remain global.'),
('Prescriptions','COUNTROWS(Prescriptions)','#,0','Prescription records, not medication consumption.'),
('Admission Records','COUNTROWS(Admissions)','#,0','Admission records; episode dates absent.'),
('Mean Length of Stay','AVERAGE(Admissions[LengthOfStayDays])','0.00','Mean supplied length-of-stay field in days.'),
('Referral Records','COUNTROWS(Referrals)','#,0','Supplied referral rows.'),
('Admission Association','DIVIDE(CALCULATE(DISTINCTCOUNT(Admissions[AppointmentID]),KEEPFILTERS(Admissions[HasAppointment]=1)),[Available Appointments])','0.00%','Available appointments with at least one linked admission; not population incidence.'),
('Referral Association','DIVIDE(CALCULATE(DISTINCTCOUNT(Referrals[AppointmentID]),KEEPFILTERS(Referrals[HasAppointment]=1)),[Available Appointments])','0.00%','Available appointments with a linked referral.'),
('Bills','COUNTROWS(Billing)','#,0','One row per bill, preserving unlinked source records.'),
('Billed Amount','SUM(Billing[Amount])','"RWF "#,0','Supplied billed amounts; invoice dates absent.'),
('Recorded Payments','SUM(Billing[AmountPaid])','"RWF "#,0','Payments preaggregated by BillingID to avoid join multiplication; receipt dates absent.'),
('Positive Balances','SUM(Billing[Outstanding])','"RWF "#,0','SUM(MAX(0,billed-paid)) at bill grain.'),
('Credit Balances','SUM(Billing[Credit])','"RWF "#,0','SUM(MAX(0,paid-billed)) at bill grain.'),
('Payment to Bill Ratio','DIVIDE([Recorded Payments],[Billed Amount])','0.00%','Recorded amounts ratio; not dated collection performance.'),
('Average Bill','DIVIDE([Billed Amount],[Bills])','"RWF "#,0.00','Mean across supplied bills.'),
('Payment Records Amount','SUM(Payments[AmountPaid])','"RWF "#,0','Payment fact measure for payment-method segmentation.'),
('Claim Records','COUNTROWS(Claims)','#,0','Supplied claim records.'),
('Pending Claims','CALCULATE([Claim Records],KEEPFILTERS(Claims[Status]="Pending"))','#,0','Pending status; aging cannot be computed without dates.'),
('Approved Claim Share','DIVIDE(CALCULATE([Claim Records],KEEPFILTERS(Claims[Status]="Approved")),[Claim Records])','0.00%','Approved divided by all supplied claims, including pending.'),
('Claim Amount','SUM(Claims[ClaimAmount])','"RWF "#,0.00','Supplied claim amounts, not receipts.'),
('Summary Revenue','SUM(RevenueSummary[Revenue])','"RWF "#,0','Separate unreconciled RevenueSummary series.'),
('Staff Records','COUNTROWS(Staff)','#,0','Staff register count; no working-hour or shift denominator.'),
('Mean Staff Experience','AVERAGE(Staff[YearsExperience])','0.00','Recorded years of experience.'),
('Doctor Records','CALCULATE([Staff Records],KEEPFILTERS(Staff[Role]="Doctor"))','#,0','Registered doctor count.'),
('Nurse Records','CALCULATE([Staff Records],KEEPFILTERS(Staff[Role]="Nurse"))','#,0','Registered nurse count.'),
('Appointments per Doctor','DIVIDE([Available Appointments],[Doctor Records])','0.00','Available appointment workload per registered doctor; not productivity.'),
('Observed Facility IDs','COUNTROWS(Facilities)','#,0','Distinct identifiers observed across source tables, not a verified facility directory.'),
('Bed Register','COUNTROWS(Beds)','#,0','Inventory records; source status is not occupancy.'),
('Room Register','COUNTROWS(Rooms)','#,0','Room inventory records.'),
('Equipment Register','COUNTROWS(Equipment)','#,0','Equipment inventory records; no usage/availability observations.'),
('Feedback Responses','COUNTROWS(Feedback)','#,0','Response records; source submission dates absent.'),
('Mean Feedback Rating','AVERAGE(Feedback[Rating])','0.00','Mean rating on the supplied 1-5 scale.'),
('Low Rating Share','DIVIDE(CALCULATE([Feedback Responses],KEEPFILTERS(Feedback[Rating]<=2)),[Feedback Responses])','0.00%','Share rated 1-2; comment categories reported separately.'),
('Excellent Rating Share','DIVIDE(CALCULATE([Feedback Responses],KEEPFILTERS(Feedback[Rating]=5)),[Feedback Responses])','0.00%','Share rated 5.'),
('Linked Bills','CALCULATE([Bills],KEEPFILTERS(Billing[HasAppointment]=1))','#,0','Bills attributable to available appointments.'),
('Billing Link Coverage','DIVIDE([Linked Bills],[Bills])','0.00%','Linkage within selected bill context; unfiltered baseline 8.33%.'),
('Linked Feedback Responses','CALCULATE([Feedback Responses],KEEPFILTERS(Feedback[HasAppointment]=1))','#,0','Feedback with a matching available appointment.'),
('Feedback Link Coverage','DIVIDE([Linked Feedback Responses],[Feedback Responses])','0.00%','Linkage within selected feedback context; unfiltered baseline 8.34%.'),
('Previous Month Appointments','CALCULATE([Available Appointments],DATEADD(Dates[Date],-1,MONTH))','#,0','Prior calendar month in the supplied scenario.'),
('Appointment Month Growth','DIVIDE([Available Appointments]-[Previous Month Appointments],[Previous Month Appointments])','0.00%','Month-on-month change in available appointments, not full network demand.'),
('YTD Available Appointments','TOTALYTD([Available Appointments],Dates[Date])','#,0','Cumulative supplied scenario appointments.'),
('Dynamic Title','"HealthConnect | "&COALESCE(SELECTEDVALUE(Dates[Month]),"All scenario months")&" | "&COALESCE(SELECTEDVALUE(Facilities[FacilityID]),"All observed facilities")','','Selection-aware report heading.'),
('Financial Scope','IF(ISCROSSFILTERED(Appointments),"Appointment-linked financial subset","All supplied financial records; undated")','','Distinguishes full totals from linked attribution.'),
('Patient Residence Label','"Patient residence: "&COALESCE(SELECTEDVALUE(Patients[ProvinceName]),"All provinces")','','Province is patient residence, not facility geography.'),
('Rating Colour','IF(ISBLANK([Mean Feedback Rating]),"#526774",IF([Mean Feedback Rating]<3,"#AC493F","#147D83"))','','Rating midpoint used for descriptive conditional colour, not a clinical threshold.'),
('Bed Utilization','BLANK()','0.00%','Unavailable: dated occupancy and bed assignments absent.'),
('Room Utilization','BLANK()','0.00%','Unavailable: room usage and capacity logs absent.'),
('Equipment Availability','BLANK()','0.00%','Unavailable: operating/maintenance status absent.'),
('Clinical Readmission Rate','BLANK()','0.00%','Unavailable: dated admission and discharge episodes absent.'),
('New Registrations','BLANK()','#,0','Unavailable: registration dates absent.'),
('Cancellation Rate','BLANK()','0.00%','Unavailable: appointment status absent.'),
('Revenue by Service','BLANK()','"RWF "#,0','Unavailable: ServiceID absent from transactions.'),
]

def make_table(name,frame):
    cols=[];types=[]
    for c in frame:
        if c=='Date':dt,mt,fmt='dateTime','type date','yyyy-mm-dd'
        elif pd.api.types.is_integer_dtype(frame[c]):dt,mt,fmt='int64','Int64.Type','#,0'
        elif pd.api.types.is_numeric_dtype(frame[c]):dt,mt,fmt='double','type number','#,0.00'
        else:dt,mt,fmt='string','type text',None
        col={'name':c,'dataType':dt,'sourceColumn':c,'summarizeBy':'none'}
        if fmt:col['formatString']=fmt
        if c=='ProvinceName':col['dataCategory']='StateOrProvince'
        if c=='CountryName':col['dataCategory']='Country'
        if name=='Dates' and c=='Month':col['sortByColumn']='MonthNumber'
        if name=='Patients' and c=='AgeGroup':col['sortByColumn']='AgeSort'
        cols.append(col);types.append('{"'+c+'", '+mt+'}')
    payload=base64.b64encode(frame.to_csv(index=False,float_format='%.15g').encode()).decode()
    expression=['let','    Source = Csv.Document(Binary.FromText("'+payload+'", BinaryEncoding.Base64), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
      '    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',
      '    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),',
      '    Typed = Table.TransformColumnTypes(Nulls, {'+', '.join(types)+'}, "en-US")','in','    Typed']
    table={'name':name,'columns':cols,'partitions':[{'name':name,'mode':'import','source':{'type':'m','expression':expression}}]}
    if name=='Dates':
        next(c for c in cols if c['name']=='Date')['isKey']=True
        table['hierarchies']=[{'name':'Calendar','levels':[{'name':c,'ordinal':i,'column':c} for i,c in enumerate(['Year','Quarter','Month','Date'])]}]
    if name=='Patients':table['hierarchies']=[{'name':'Residence','levels':[{'name':c,'ordinal':i,'column':c} for i,c in enumerate(['ProvinceName','DistrictName','SectorID','VillageID'])]}]
    if name=='Appointments':table['measures']=[{'name':n,'expression':e,'formatString':f,'description':d,'displayFolder':'HealthConnect KPIs'} for n,e,f,d in MEASURES]
    return table

VISIBLE=[('executive','Executive'),('patients','Patient analytics'),('clinical','Clinical analytics'),('finance','Financial'),('operations','Operational'),('experience','Patient experience')]

def main():
    if (R/'definition').exists():shutil.rmtree(R/'definition')
    con=sqlite3.connect(ROOT/'SQL/HealthConnect.sqlite')
    read=lambda q:pd.read_sql_query(q,con)
    frames={n:read('SELECT * FROM "'+t+'"') for n,t in [('Appointments','AppointmentFact'),('Patients','PatientGeo'),('Billing','BillingFact'),('Staff','Staff'),('Facilities','ObservedFacilities')]}
    frames['Patients']=frames['Patients'].drop(columns=['FirstName','LastName','Phone','EmergencyContact','DateOfBirth'],errors='ignore')
    frames['Patients']['CountryName']='Rwanda';frames['Patients']['AgeSort']=frames['Patients'].AgeGroup.map({'0-17':0,'18-34':1,'35-49':2,'50-64':3,'65+':4})
    frames['Staff']=frames['Staff'].drop(columns=['FirstName','LastName'],errors='ignore')
    ap=frames['Appointments'];first=ap.groupby('PatientID').Date.min()
    ap['IsFirstObserved']=(ap.Date==ap.PatientID.map(first)).astype(int)
    for n in ['Diagnoses','LaboratoryTests','Prescriptions','Admissions','Referrals','Payments','Feedback','Departments','Beds','Rooms','Equipment','Services','RevenueSummary']:
        frames[n]=read('SELECT * FROM "'+n+'"')
    frames['Claims']=read('SELECT * FROM InsuranceClaims')
    for n in ['Diagnoses','LaboratoryTests','Prescriptions','Admissions','Referrals','Feedback']:
        frames[n]['HasAppointment']=frames[n].AppointmentID.isin(ap.AppointmentID).astype(int)
    frames['Billing']['BalanceFlag']=frames['Billing'].Outstanding.gt(0).map({True:'Positive balance',False:'No positive balance'})
    dates=pd.DataFrame({'Date':pd.date_range('2026-01-01','2026-12-31')});dates['Year']=dates.Date.dt.year
    dates['Quarter']='Q'+dates.Date.dt.quarter.astype(str);dates['Month']=dates.Date.dt.strftime('%Y-%m');dates['MonthNumber']=dates.Date.dt.month
    dates['Date']=dates.Date.dt.strftime('%Y-%m-%d');frames['Dates']=dates
    tables=[make_table(n,f) for n,f in frames.items()]
    relations=[]
    pairs=[('Appointments','PatientID','Patients','PatientID'),('Appointments','Date','Dates','Date'),('Appointments','FacilityID','Facilities','FacilityID'),('Appointments','DepartmentID','Departments','DepartmentID'),
     ('Billing','AppointmentID','Appointments','AppointmentID'),('Payments','BillingID','Billing','BillingID'),('Claims','BillingID','Billing','BillingID'),
     ('Staff','FacilityID','Facilities','FacilityID'),('Rooms','FacilityID','Facilities','FacilityID'),('Beds','RoomID','Rooms','RoomID'),('Equipment','FacilityID','Facilities','FacilityID')]
    pairs += [(n,'AppointmentID','Appointments','AppointmentID') for n in ['Diagnoses','LaboratoryTests','Prescriptions','Admissions','Referrals','Feedback']]
    for child,foreign,parent,key in pairs:
        assert frames[parent][key].is_unique,(parent,key)
        relations.append({'name':str(uuid.uuid5(uuid.NAMESPACE_URL,child+foreign+parent)), 'fromTable':child,'fromColumn':foreign,'toTable':parent,'toColumn':key,'crossFilteringBehavior':'oneDirection'})
    write(S/'model.bim',{'name':'HealthConnect_Analytics','compatibilityLevel':1567,'model':{'culture':'en-US','sourceQueryCulture':'en-US','defaultPowerBIDataSourceVersion':'powerBI_V3','tables':tables,'relationships':relations}})
    write(S/'definition.pbism',{'version':'1.0','settings':{}})
    write(D/'HealthConnect_Analytics.pbip',{'version':'1.0','artifacts':[{'report':{'path':'HealthConnect.Report'}}],'settings':{'enableAutoRecovery':True}})
    write(R/'definition.pbir',{'version':'4.0','datasetReference':{'byPath':{'path':'../HealthConnect.SemanticModel'}}})
    write(R/'definition/version.json',{'$schema':schema('versionMetadata','1.0.0'),'version':'4.0.0'})
    write(R/'definition/report.json',{'$schema':schema('report','3.1.0'),'themeCollection':{},'settings':{'useStylableVisualContainerHeader':True,'defaultDrillFilterOtherVisuals':True,'useEnhancedTooltips':True}})
    (D/'Measures.dax').write_text('\n\n'.join('// '+d+'\n'+n+' = '+e for n,e,f,d in MEASURES))
    pd.DataFrame(MEASURES,columns=['Measure','DAX','Format','Definition']).to_csv(D/'Measure_Definitions.csv',index=False)
    # External-table import definitions are safe to publish; embedded data remain private.
    external=[]
    for n,f in frames.items():
        f.to_csv(ROOT/'Data/Processed'/('Model_'+n+'.csv'),index=False,float_format='%.15g')
        types=make_table(n,f)['partitions'][0]['source']['expression'][4]
        external.append('// '+n+'\nlet\n    Source = Csv.Document(File.Contents(DataFolder & "/Model_'+n+'.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),\n    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),\n    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),\n'+types+'\nin\n    Typed')
    (D/'PowerQuery_External.m').write_text('// DataFolder is a text parameter containing the absolute Data/Processed path.\n\n'+'\n\n'.join(external))
    allpages=VISIBLE+[('facility_detail','Facility detail'),('context_tooltip','Context tooltip')]
    write(R/'definition/pages/pages.json',{'$schema':schema('pagesMetadata','1.0.0'),'pageOrder':[n for n,t in allpages],'activePageName':'executive'})
    counts={}
    def visual(page,name,kind,x,y,w,h,roles=None,title=None,objects=None,link=None,tooltip=False):
        index=counts.get(page.name,0);counts[page.name]=index+1
        v={'$schema':schema('visualContainer','2.0.0'),'name':name,'position':{'x':x,'y':y,'width':w,'height':h,'z':0,'tabOrder':index},'visual':{'visualType':kind,'drillFilterOtherVisuals':True,'visualContainerObjects':{}}}
        q=v['visual']
        if roles:q['query']={'queryState':{r:{'projections':p} for r,p in roles.items()}}
        if title:q['visualContainerObjects']['title']=[{'properties':{'show':literal('true'),'text':text(title),'fontSize':literal('12D')}}]
        if objects:q['objects']=objects
        if link:q['visualContainerObjects']['visualLink']=[{'properties':link}]
        if tooltip:q['visualContainerObjects']['visualTooltip']=[{'properties':{'show':literal('true'),'type':text('ReportPage'),'section':text('context_tooltip')}}]
        write(page/'visuals'/name/'visual.json',v)
        return v
    def card(page,name,measure,x,y,w=290,h=100):return visual(page,name,'card',x,y,w,h,{'Values':[projection('Appointments',measure,True)]},measure,{'labels':[{'properties':{'fontSize':literal('25D')}}]})
    def chart(page,name,entity,col,measure,x,y,kind='clusteredBarChart',w=600,h=245):
        return visual(page,name,kind,x,y,w,h,{'Category':[projection(entity,col)],'Y':[projection('Appointments',measure,True)],'Tooltips':[projection('Appointments','Available Appointments',True)]},measure+' by '+col,tooltip=True)
    for name,title in allpages:
        page=R/'definition/pages'/name
        p={'$schema':schema('page','2.0.0'),'name':name,'displayName':title,'displayOption':'FitToPage','width':1280,'height':930}
        if name=='context_tooltip':
            p.update({'width':470,'height':300,'visibility':'HiddenInViewMode','pageBinding':{'name':'ContextTooltip','type':'Tooltip','acceptsFilterContext':'Default'}})
            write(page/'page.json',p);card(page,'rating','Mean Feedback Rating',10,10,450);card(page,'responses','Feedback Responses',10,145,450);continue
        if name=='facility_detail':
            p['visibility']='HiddenInViewMode';p['filterConfig']={'filters':[{'name':'FacilityDrill','field':field('Facilities','FacilityID'),'type':'Categorical','howCreated':'Drillthrough'}]}
            p['pageBinding']={'name':'FacilityDrillthrough','type':'Drillthrough','parameters':[{'name':'Facility','boundFilter':'FacilityDrill','fieldExpr':field('Facilities','FacilityID')}],'acceptsFilterContext':'Default'}
        write(page/'page.json',p)
        for j,(destination,label) in enumerate(VISIBLE):
            visual(page,'nav_'+destination,'actionButton',20+j*207,10,195,38,objects={'text':[{'properties':{'text':text(label),'fontSize':literal('11D')}}]},link={'show':literal('true'),'type':text('PageNavigation'),'navigationSection':text(destination)})
        for j,(entity,col) in enumerate([('Dates','Month'),('Facilities','FacilityID'),('Patients','ProvinceName'),('Appointments','VisitType')]):
            v=visual(page,'slicer_'+col,'slicer',20+j*310,60,295,78,{'Values':[projection(entity,col)]},col)
            v['visual']['syncGroup']={'groupName':'HealthConnect_'+col,'fieldChanges':True,'filterChanges':True};write(page/'visuals'/v['name']/'visual.json',v)
        card(page,'dynamic_title','Dynamic Title',20,145,1230,55)
        metrics={'executive':['Registered Patients','Available Appointments','Recorded Payments','Mean Feedback Rating'],
         'patients':['Observed Patients','Repeat Visit Patients','Mean Recorded Age','Insurance Code Presence'],
         'clinical':['Diagnosis Records','Laboratory Tests','Prescriptions','Mean Length of Stay'],
         'finance':['Billed Amount','Recorded Payments','Positive Balances','Payment to Bill Ratio'],
         'operations':['Staff Records','Bed Register','Room Register','Equipment Register'],
         'experience':['Feedback Responses','Mean Feedback Rating','Low Rating Share','Feedback Link Coverage'],
         'facility_detail':['Available Appointments','Staff Records','Recorded Payments','Mean Feedback Rating']}[name]
        for j,m in enumerate(metrics):card(page,'kpi_'+str(j),m,20+j*310,210)
        specs={'executive':[('Dates','Month','Available Appointments','lineChart'),('Facilities','FacilityID','Available Appointments','clusteredBarChart'),('Appointments','VisitType','Available Appointments','clusteredColumnChart'),('Dates','Month','YTD Available Appointments','lineChart')],
         'patients':[('Patients','AgeGroup','Registered Patients','clusteredColumnChart'),('Patients','ProvinceName','Registered Patients','filledMap'),('Patients','ChronicCondition','Registered Patients','clusteredBarChart'),('Dates','Month','First Observed Patients','lineChart')],
         'clinical':[('Diagnoses','Diagnosis','Diagnosis Records','clusteredBarChart'),('LaboratoryTests','Test','Laboratory Tests','clusteredBarChart'),('Prescriptions','Medication','Prescriptions','clusteredBarChart'),('Admissions','LengthOfStayDays','Admission Records','clusteredColumnChart')],
         'finance':[('RevenueSummary','Month','Summary Revenue','lineChart'),('Payments','Method','Payment Records Amount','clusteredColumnChart'),('Claims','Provider','Claim Amount','clusteredBarChart'),('Facilities','FacilityID','Recorded Payments','clusteredBarChart')],
         'operations':[('Staff','Role','Staff Records','clusteredBarChart'),('Facilities','FacilityID','Staff Records','clusteredColumnChart'),('Facilities','FacilityID','Bed Register','clusteredBarChart'),('Facilities','FacilityID','Equipment Register','clusteredBarChart')],
         'experience':[('Feedback','Rating','Feedback Responses','clusteredColumnChart'),('Feedback','Comment','Feedback Responses','clusteredBarChart'),('Facilities','FacilityID','Mean Feedback Rating','clusteredBarChart'),('Dates','Month','Low Rating Share','lineChart')],
         'facility_detail':[('Dates','Month','Available Appointments','lineChart'),('Departments','DepartmentName','Available Appointments','clusteredBarChart'),('Staff','Role','Staff Records','clusteredBarChart'),('Departments','DepartmentName','Mean Feedback Rating','clusteredBarChart')]}[name]
        for j,(entity,col,measure,kind) in enumerate(specs):
            v=chart(page,'chart_'+str(j),entity,col,measure,20+(j%2)*620,325+(j//2)*255,kind)
            if kind=='filledMap':v['visual']['query']['queryState']={'Location':{'projections':[projection(entity,col)]},'Size':{'projections':[projection('Appointments',measure,True)]},'Tooltips':{'projections':[projection('Patients','CountryName')]}}
            if name=='experience' and j==2:v['visual']['objects']={'dataPoint':[{'properties':{'defaultColor':{'solid':{'color':{'expr':field('Appointments','Rating Colour',True)}}}}}]}
            write(page/'visuals'/v['name']/'visual.json',v)
        scope={'executive':'Patient register is independent of month/facility filters. Financial and feedback attribution requires appointment links.',
         'patients':'Province maps patient residence. First observed visits are not new registrations; insurance codes do not verify valid coverage.',
         'clinical':'Global clinical totals retain unmatched records. Date/facility selections retain linked appointments only; readmission is unavailable.',
         'finance':'RWF. RevenueSummary is separate and unreconciled. Facility/date comparisons use 5,000 linked bills; receipt dates are absent.',
         'operations':'Facility identifiers only. Staff and inventories are undated; physical utilization, adequacy and equipment availability are unavailable.',
         'experience':'Ratings use all responses when unfiltered. Facility/month views are linked subsets, not feedback-submission-month trends.',
         'facility_detail':'Observed identifier, not a verified facility master. Date/facility financial and clinical views use linked appointments.'}[name]
        visual(page,'scope','textbox',20,850,1230,65,objects={'general':[{'properties':{'paragraphs':[{'textRuns':[{'value':scope,'textStyle':{'fontSize':'12px'}}]}]}}]})
        p['visualInteractions']=[{'source':'chart_'+str(i),'target':'chart_'+str(j),'type':'DataFilter'} for i in range(4) for j in range(4) if i!=j]
        write(page/'page.json',p)
    # Additional financial exploration page keeps associations separate from clinical interpretation.
    page=R/'definition/pages/finance'
    # Standard matrix can be reached by bookmark without displacing the six main layouts.
    detail=R/'definition/pages/financial_exploration'
    write(detail/'page.json',{'$schema':schema('page','2.0.0'),'name':'financial_exploration','displayName':'Financial exploration','displayOption':'FitToPage','width':1280,'height':930,'visibility':'HiddenInViewMode'})
    visual(detail,'claim_matrix','pivotTable',20,30,600,350,{'Rows':[projection('Claims','Provider')],'Columns':[projection('Claims','Status')],'Values':[projection('Appointments','Claim Records',True),projection('Appointments','Claim Amount',True)]},'Claims by provider and status')
    visual(detail,'payment_decomposition','decompositionTreeVisual',650,30,600,350,{'Analyze':[projection('Appointments','Recorded Payments',True)],'ExplainBy':[projection('Facilities','FacilityID'),projection('Departments','DepartmentName'),projection('Appointments','VisitType')]},'Linked payment amount decomposition')
    visual(detail,'balance_associations','keyDriversVisual',20,410,1230,410,{'Target':[projection('Billing','BalanceFlag')],'ExplainBy':[projection('Billing','BillingStatus'),projection('Billing','Amount')]},'Positive-balance associations; descriptive financial exploration')
    allpages.append(('financial_exploration','Financial exploration'))
    write(R/'definition/pages/pages.json',{'$schema':schema('pagesMetadata','1.0.0'),'pageOrder':[n for n,t in allpages],'activePageName':'executive'})
    bookmarks=[]
    for target,label in [('executive','Executive overview'),('finance','Financial overview'),('financial_exploration','Financial exploration')]:
        n='bookmark_'+target;bookmarks.append({'name':n})
        write(R/'definition/bookmarks'/(n+'.bookmark.json'),{'$schema':schema('bookmark','2.1.0'),'name':n,'displayName':label,'options':{'suppressData':True},'explorationState':{'version':'1.3','activeSection':target,'sections':{n:{'visualContainers':{}} for n,t in allpages}}})
    write(R/'definition/bookmarks/bookmarks.json',{'$schema':schema('bookmarksMetadata','1.0.0'),'items':bookmarks})
    visual(page,'explore_button','actionButton',950,148,295,45,objects={'text':[{'properties':{'text':text('Financial exploration')}}]},link={'show':literal('true'),'type':text('PageNavigation'),'navigationSection':text('financial_exploration')})
    # Portable embedded snapshots are verified against the executed model before packaging.
    for t in tables:
        expr=t['partitions'][0]['source']['expression'][1]
        encoded=expr.split('Binary.FromText("',1)[1].split('"',1)[0]
        assert base64.b64decode(encoded)==frames[t['name']].to_csv(index=False,float_format='%.15g').encode()
    print(json.dumps({'tables':len(tables),'relationships':len(relations),'measures':len(MEASURES),'visible_pages':6,'support_pages':3,'visuals':sum(counts.values()),'snapshot_roundtrips':len(tables)}))

if __name__=='__main__':main()
