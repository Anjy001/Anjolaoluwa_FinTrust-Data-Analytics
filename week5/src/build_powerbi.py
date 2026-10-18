"""Build the portable Power BI report and import-mode semantic model."""
from pathlib import Path
import base64
import json
import uuid
import shutil
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'Dashboard'
R=D/'SwiftLog.Report'
S=D/'SwiftLog.SemanticModel'
if (R/'definition').exists():shutil.rmtree(R/'definition')

def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2))

def schema(kind,version):
    return f'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/{kind}/{version}/schema.json'

measures=[
 ('Total Orders','COUNTROWS(Orders)','#,0','Order volume within the selected order cohort.'),
 ('Total Customers','COUNTROWS(Customers)','#,0','Customer catalogue size.'),
 ('Active Customers','DISTINCTCOUNT(Orders[CustomerID])','#,0','Customers with selected orders.'),
 ('Total Products','COUNTROWS(Products)','#,0','Product catalogue size.'),
 ('Total Shipments','COUNTROWS(Shipments)','#,0','Shipments linked to selected orders.'),
 ('Total Revenue','SUM(OrderItems[DeliveredValue])','#,0.00','Delivered order value at supplied catalogue prices. Currency and revenue recognition are unspecified.'),
 ('All Order Value','SUM(OrderItems[LineValue])','#,0.00','Catalogue value across all order statuses.'),
 ('Delivered Orders','CALCULATE([Total Orders],KEEPFILTERS(Orders[Status]="Delivered"))','#,0','Delivered status order count.'),
 ('Priced Delivered Orders','CALCULATE([Total Orders],KEEPFILTERS(Orders[Status]="Delivered"),KEEPFILTERS(Orders[HasItems]=1))','#,0','Delivered orders represented in order items.'),
 ('Average Order Value','DIVIDE([Total Revenue],[Priced Delivered Orders])','#,0.00','Delivered catalogue value per priced delivered order.'),
 ('Orders Without Items','CALCULATE([Total Orders],KEEPFILTERS(Orders[HasItems]=0))','#,0','Source coverage exception count.'),
 ('Delivered Units','SUM(OrderItems[DeliveredUnits])','#,0','Units in delivered status orders.'),
 ('Recorded On-Time Shipments','SUM(Shipments[RecordedOnTime])','#,0','Source On Time status, consistently associated with delay of 0-2 days.'),
 ('On-Time Delivery Rate','DIVIDE([Recorded On-Time Shipments],[Total Shipments])','0.00%','Recorded status rate, not the zero-delay share.'),
 ('Delayed Shipments','[Total Shipments]-[Recorded On-Time Shipments]','#,0','Source Delayed status.'),
 ('Delayed Shipment Rate','DIVIDE([Delayed Shipments],[Total Shipments])','0.00%','Recorded delayed share.'),
 ('Average Delivery Delay','AVERAGE(Shipments[DelayDays])','0.00','Mean recorded delay in days.'),
 ('Average Delivery Time','BLANK()','0.00','Not estimable: dispatch and arrival timestamps are absent.'),
 ('Zero-Delay Share','DIVIDE(CALCULATE([Total Shipments],KEEPFILTERS(Shipments[DelayDays]=0)),[Total Shipments])','0.00%','Share with exactly zero recorded delay.'),
 ('Inventory Stock Level','SUM(Inventory[Stock])','#,0','Sum of all supplied stock movement quantities. Not a current on-hand balance.'),
 ('Inventory Turnover','BLANK()','0.00','Standard turnover cannot be estimated without dated inventory balances and a consistent cost or quantity basis.'),
 ('Throughput to Stock Proxy','DIVIDE([Delivered Units],[Inventory Stock Level])','0.0000','Period delivered units divided by undated aggregate stock. Does not estimate standard turnover.'),
 ('Return Events','COUNTROWS(Returns)','#,0','Return event count.'),
 ('Returned Orders','DISTINCTCOUNT(Returns[OrderID])','#,0','Distinct orders with a return record.'),
 ('Return Rate','DIVIDE([Returned Orders],[Total Orders])','0.00%','Order-level return association. Product-level returned items are not identified.'),
 ('Product Order Count','DISTINCTCOUNT(OrderItems[OrderID])','#,0','Distinct orders containing selected products.'),
 ('Product Return-Associated Orders','VAR P=VALUES(OrderItems[OrderID]) RETURN CALCULATE(DISTINCTCOUNT(Returns[OrderID]),TREATAS(P,Returns[OrderID]))','#,0','Orders containing a selected product and carrying any return event.'),
 ('Product Return Association Rate','DIVIDE([Product Return-Associated Orders],[Product Order Count])','0.00%','Association with a returned order, not the actual product return rate.'),
 ('Supplier Count','COUNTROWS(Suppliers)','#,0','Standalone supplier reference count.'),
 ('Supplier Performance Score','BLANK()','0.00','Not estimable: no supplier relationship or performance observations.'),
 ('Supplier Measurement Coverage','"Unavailable: no supplier-to-product relationship"','', 'Supplier measurement boundary.'),
 ('Warehouse Utilization','BLANK()','0.00%','Physical utilisation is not estimable without capacity.'),
 ('Warehouse Inventory Share Proxy','DIVIDE([Inventory Stock Level],CALCULATE([Inventory Stock Level],REMOVEFILTERS(Warehouses)))','0.00%','Share of aggregate stock held by selected warehouse. Not capacity utilisation.'),
 ('Warehouse Employees','COUNTROWS(Employees)','#,0','Employee count for selected warehouse.'),
 ('Shipments per Employee','DIVIDE([Total Shipments],[Warehouse Employees])','0.0','Shipment workload proxy, without employee hours or costs.'),
 ('Low Stock Threshold','SELECTEDVALUE(LowStockParameter[Threshold],100)','#,0','Illustrative planning threshold, adjustable from 0 to 500 units.'),
 ('Low Stock Pairs','COUNTROWS(FILTER(Inventory,Inventory[Stock]<[Low Stock Threshold]))','#,0','Observed warehouse-product aggregates below the selected threshold.'),
 ('Observed Inventory Pairs','COUNTROWS(Inventory)','#,0','Warehouse-product combinations present in the source.'),
 ('Repeat Customers','COUNTROWS(FILTER(VALUES(Orders[CustomerID]),CALCULATE(COUNTROWS(Orders))>1))','#,0','Customers with at least two selected orders.'),
 ('Repeat Customer Rate','DIVIDE([Repeat Customers],[Active Customers])','0.00%','Repeat purchasing indicator, not a longitudinal retention estimate.'),
 ('First Observed Customers','CALCULATE(DISTINCTCOUNT(Orders[CustomerID]),Orders[IsFirstObservedOrder]=1)','#,0','First observed order within the supplied history.'),
 ('Dynamic Report Title','"SwiftLog | "&COALESCE(SELECTEDVALUE(Dates[Month]),"All order months")&" | "&COALESCE(SELECTEDVALUE(Customers[City]),"All customer cities")','','Title follows date and customer-city selections.'),
 ('Selected Product Title','"Product "&COALESCE(SELECTEDVALUE(Products[ProductID]),"overview")','','Context-sensitive tooltip and drill-through title.'),
 ('Delivery Colour','IF([Delayed Shipment Rate]>=0.65,"#BF4A3C","#137D7B")','','Conditional colour at an illustrative 65% delayed-rate monitoring threshold.')
]
measures += [
 ('Top Customer Value','IF(RANKX(ALLSELECTED(Customers[CustomerID]),[Total Revenue],,DESC,DENSE)<=10,[Total Revenue],BLANK())','#,0.00','Delivered catalogue value for the ten highest ranked customers in the selection.'),
 ('Top Product Value','IF(RANKX(ALLSELECTED(Products[ProductID]),[Total Revenue],,DESC,DENSE)<=10,[Total Revenue],BLANK())','#,0.00','Delivered catalogue value for the ten highest ranked products in the selection.')
]
measures += [('Top Customer Orders','IF(RANKX(ALLSELECTED(Customers[CustomerID]),[Total Orders],,DESC,DENSE)<=10,[Total Orders],BLANK())','#,0','Highest observed customer order frequencies within the selection.')]

def m_type(column,series):
    if column in ['Date','OrderDate','FirstOrder','LastOrder']: return 'dateTime','type date','yyyy-mm-dd'
    if pd.api.types.is_integer_dtype(series): return 'int64','Int64.Type','#,0'
    if pd.api.types.is_numeric_dtype(series): return 'double','type number','#,0.00'
    return 'string','type text',None

def make_table(name,frame):
    columns=[];types=[];texts=[]
    for c in frame:
        dt,mt,fmt=m_type(c,frame[c])
        col={'name':c,'dataType':dt,'sourceColumn':c,'summarizeBy':'none'}
        if fmt: col['formatString']=fmt
        columns.append(col);types.append('{"'+c+'", '+mt+'}')
        if dt=='string':texts.append('{"'+c+'", Text.Trim, type text}')
    payload=base64.b64encode(frame.to_csv(index=False).encode()).decode()
    expression=['let','    Source = Csv.Document(Binary.FromText("'+payload+'", BinaryEncoding.Base64), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
        '    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',
        '    Typed = Table.TransformColumnTypes(Headers, {'+', '.join(types)+'}, "en-US"),',
        '    Trimmed = Table.TransformColumns(Typed, {'+', '.join(texts)+'})']
    last='Trimmed'
    if name=='Orders':
        expression[-1]+=','
        expression += ['    Base = Table.RemoveColumns(Trimmed, {"Month", "Quarter", "Year"}),',
          '    AddMonth = Table.AddColumn(Base, "Month", each Date.ToText([OrderDate], "yyyy-MM"), type text),',
          '    AddQuarter = Table.AddColumn(AddMonth, "Quarter", each "Q" & Text.From(Date.QuarterOfYear([OrderDate])), type text),',
          '    AddYear = Table.AddColumn(AddQuarter, "Year", each Date.Year([OrderDate]), Int64.Type)']
        last='AddYear'
    if name=='Inventory':
        expression[-1]+=','
        expression += ['    Base = Table.RemoveColumns(Trimmed, {"LowStock100"}),',
          '    AddConditional = Table.AddColumn(Base, "LowStock100", each if [Stock] < 100 then 1 else 0, Int64.Type)']
        last='AddConditional'
    expression += ['in','    '+last]
    table={'name':name,'columns':columns,'partitions':[{'name':name,'mode':'import','source':{'type':'m','expression':expression}}]}
    if name=='Orders':table['measures']=[{'name':n,'expression':e,'formatString':f,'description':d,'displayFolder':'Business KPIs'} for n,e,f,d in measures]
    return table

frames={p.stem:pd.read_csv(p) for p in (ROOT/'Data/Processed').glob('*.csv')}
frames['DeliveryPerformance']=pd.read_csv(ROOT/'Data/Original_Datasets/SwiftLog_Delivery_Performance.csv')
frames['LowStockParameter']=pd.DataFrame({'Threshold':range(0,501,25)})
tables=[make_table(n,f) for n,f in frames.items()]
expressions=[]
for source_path in sorted((ROOT/'Data/Original_Datasets').glob('SwiftLog_*.csv')):
    source_name='Source'+source_path.stem.replace('SwiftLog_','').replace('_','')
    source_frame=pd.read_csv(source_path)
    source_expression=make_table(source_name,source_frame)['partitions'][0]['source']['expression']
    expressions.append({'name':source_name,'kind':'m','expression':source_expression})
expressions.append({'name':'PricedOrderLines','kind':'m','expression':'''let
    Source = SourceOrderItems,
    JoinProducts = Table.NestedJoin(Source, {"ProductID"}, SourceProducts, {"ProductID"}, "Product", JoinKind.LeftOuter),
    ExpandProducts = Table.ExpandTableColumn(JoinProducts, "Product", {"Category", "UnitPrice"}),
    AddLineValue = Table.AddColumn(ExpandProducts, "LineValue", each Number.Round([Quantity] * [UnitPrice], 2), type number)
in
    AddLineValue'''.splitlines()})
queries={
 'Orders':'''let
    Source = SourceOrders,
    AddMonth = Table.AddColumn(Source, "Month", each Date.ToText([OrderDate], "yyyy-MM"), type text),
    AddQuarter = Table.AddColumn(AddMonth, "Quarter", each "Q" & Text.From(Date.QuarterOfYear([OrderDate])), type text),
    AddYear = Table.AddColumn(AddQuarter, "Year", each Date.Year([OrderDate]), Int64.Type),
    ItemTotals = Table.Group(PricedOrderLines, {"OrderID"}, {{"OrderValue", each List.Sum([LineValue]), type number}, {"Units", each List.Sum([Quantity]), Int64.Type}, {"ItemRows", each Table.RowCount(_), Int64.Type}}),
    JoinItems = Table.NestedJoin(AddYear, {"OrderID"}, ItemTotals, {"OrderID"}, "Items", JoinKind.LeftOuter),
    ExpandItems = Table.ExpandTableColumn(JoinItems, "Items", {"OrderValue", "Units", "ItemRows"}),
    AddCoverage = Table.AddColumn(ExpandItems, "HasItems", each if [ItemRows] = null then 0 else 1, Int64.Type),
    FillNumbers = Table.ReplaceValue(AddCoverage, null, 0, Replacer.ReplaceValue, {"OrderValue", "Units", "ItemRows"}),
    AddDeliveredValue = Table.AddColumn(FillNumbers, "DeliveredValue", each if [Status] = "Delivered" then [OrderValue] else 0, type number),
    ReturnCounts = Table.Group(SourceReturns, {"OrderID"}, {{"ReturnCount", each Table.RowCount(_), Int64.Type}}),
    JoinReturns = Table.NestedJoin(AddDeliveredValue, {"OrderID"}, ReturnCounts, {"OrderID"}, "Return", JoinKind.LeftOuter),
    ExpandReturns = Table.ExpandTableColumn(JoinReturns, "Return", {"ReturnCount"}),
    FillReturns = Table.ReplaceValue(ExpandReturns, null, 0, Replacer.ReplaceValue, {"ReturnCount"}),
    AddReturnFlag = Table.AddColumn(FillReturns, "HasReturn", each if [ReturnCount] > 0 then 1 else 0, Int64.Type),
    JoinCustomers = Table.NestedJoin(AddReturnFlag, {"CustomerID"}, SourceCustomers, {"CustomerID"}, "Customer", JoinKind.LeftOuter),
    ExpandCustomers = Table.ExpandTableColumn(JoinCustomers, "Customer", {"City"}),
    FirstOrders = Table.Group(Source, {"CustomerID"}, {{"FirstOrderID", each Table.First(Table.Sort(_, {{"OrderDate", Order.Ascending}, {"OrderID", Order.Ascending}}))[OrderID], type text}}),
    JoinFirstOrders = Table.NestedJoin(ExpandCustomers, {"CustomerID"}, FirstOrders, {"CustomerID"}, "First", JoinKind.LeftOuter),
    ExpandFirstOrders = Table.ExpandTableColumn(JoinFirstOrders, "First", {"FirstOrderID"}),
    AddFirstFlag = Table.AddColumn(ExpandFirstOrders, "IsFirstObservedOrder", each if [OrderID] = [FirstOrderID] then 1 else 0, Int64.Type),
    Result = Table.RemoveColumns(AddFirstFlag, {"FirstOrderID"})
in
    Result''',
 'OrderItems':'''let
    Source = PricedOrderLines,
    JoinOrders = Table.NestedJoin(Source, {"OrderID"}, Orders, {"OrderID"}, "Order", JoinKind.LeftOuter),
    ExpandOrders = Table.ExpandTableColumn(JoinOrders, "Order", {"CustomerID", "OrderDate", "Month", "Status", "City", "HasReturn"}),
    AddDeliveredValue = Table.AddColumn(ExpandOrders, "DeliveredValue", each if [Status] = "Delivered" then [LineValue] else 0, type number),
    AddDeliveredUnits = Table.AddColumn(AddDeliveredValue, "DeliveredUnits", each if [Status] = "Delivered" then [Quantity] else 0, Int64.Type)
in
    AddDeliveredUnits''',
 'Shipments':'''let
    Source = Table.RenameColumns(SourceShipments, {{"DelayDays", "ShipmentDelayDays"}}),
    JoinDelivery = Table.NestedJoin(Source, {"ShipmentID"}, SourceDeliveryPerformance, {"ShipmentID"}, "Delivery", JoinKind.LeftOuter),
    ExpandDelivery = Table.ExpandTableColumn(JoinDelivery, "Delivery", {"Status", "DelayDays"}, {"DeliveryStatus", "DelayDays"}),
    JoinOrders = Table.NestedJoin(ExpandDelivery, {"OrderID"}, Orders, {"OrderID"}, "Order", JoinKind.LeftOuter),
    ExpandOrders = Table.ExpandTableColumn(JoinOrders, "Order", {"CustomerID", "OrderDate", "Month", "Status", "City"}),
    AddOnTime = Table.AddColumn(ExpandOrders, "RecordedOnTime", each if [DeliveryStatus] = "On Time" then 1 else 0, Int64.Type),
    AddPositive = Table.AddColumn(AddOnTime, "PositiveDelay", each if [DelayDays] > 0 then 1 else 0, Int64.Type),
    AddBand = Table.AddColumn(AddPositive, "DelayBand", each if [DelayDays] = 0 then "0 days" else if [DelayDays] <= 2 then "1-2 days" else if [DelayDays] <= 4 then "3-4 days" else "5-7 days", type text),
    JoinWarehouses = Table.NestedJoin(AddBand, {"WarehouseID"}, SourceWarehouses, {"WarehouseID"}, "Warehouse", JoinKind.LeftOuter),
    Result = Table.ExpandTableColumn(JoinWarehouses, "Warehouse", {"Location"}, {"WarehouseLocation"})
in
    Result''',
 'InventoryMovements':'''let
    Source = SourceInventory,
    AddRow = Table.AddIndexColumn(Source, "SourceRow", 1, 1, Int64.Type),
    AddID = Table.AddColumn(AddRow, "InventoryRecordID", each "IM" & Text.PadStart(Text.From([SourceRow]), 5, "0"), type text),
    Result = Table.RemoveColumns(AddID, {"SourceRow"})
in
    Result''',
 'Inventory':'''let
    Source = InventoryMovements,
    Aggregate = Table.Group(Source, {"WarehouseID", "ProductID"}, {{"Stock", each List.Sum([Stock]), Int64.Type}, {"MovementRows", each Table.RowCount(_), Int64.Type}}),
    AddKey = Table.AddColumn(Aggregate, "WarehouseProductKey", each [WarehouseID] & "_" & [ProductID], type text),
    AddLowStock = Table.AddColumn(AddKey, "LowStock100", each if [Stock] < 100 then 1 else 0, Int64.Type)
in
    AddLowStock''',
 'Dates':'''let
    FirstDate = List.Min(Orders[OrderDate]),
    LastDate = List.Max(Orders[OrderDate]),
    Source = Table.FromList(List.Dates(FirstDate, Duration.Days(LastDate - FirstDate) + 1, #duration(1, 0, 0, 0)), Splitter.SplitByNothing(), {"Date"}),
    Typed = Table.TransformColumnTypes(Source, {{"Date", type date}}),
    AddYear = Table.AddColumn(Typed, "Year", each Date.Year([Date]), Int64.Type),
    AddQuarter = Table.AddColumn(AddYear, "Quarter", each "Q" & Text.From(Date.QuarterOfYear([Date])), type text),
    AddMonth = Table.AddColumn(AddQuarter, "Month", each Date.ToText([Date], "yyyy-MM"), type text),
    AddMonthName = Table.AddColumn(AddMonth, "MonthName", each Date.ToText([Date], "MMM", "en-US"), type text),
    AddMonthNumber = Table.AddColumn(AddMonthName, "MonthNumber", each Date.Month([Date]), Int64.Type)
in
    AddMonthNumber'''
}
for name in ['Customers','Products','Suppliers','Warehouses','Employees','Returns']:
    queries[name]='let\n    Source = Source'+name+'\nin\n    Source'
queries['DeliveryPerformance']='let\n    Source = SourceDeliveryPerformance\nin\n    Source'
for t in tables:
    if t['name'] in queries:t['partitions'][0]['source']['expression']=queries[t['name']].splitlines()
relations=[]
for child,foreign,parent,key,both in [
 ('Orders','CustomerID','Customers','CustomerID',False),('Orders','OrderDate','Dates','Date',False),
 ('OrderItems','OrderID','Orders','OrderID',True),('OrderItems','ProductID','Products','ProductID',False),
 ('Shipments','OrderID','Orders','OrderID',True),('Shipments','WarehouseID','Warehouses','WarehouseID',False),
 ('Inventory','WarehouseID','Warehouses','WarehouseID',False),('Inventory','ProductID','Products','ProductID',False),
 ('Employees','WarehouseID','Warehouses','WarehouseID',False),('Returns','OrderID','Orders','OrderID',False),
 ('InventoryMovements','WarehouseID','Warehouses','WarehouseID',False),('InventoryMovements','ProductID','Products','ProductID',False)]:
    relations.append({'name':str(uuid.uuid5(uuid.NAMESPACE_URL,child+foreign+parent)),
      'fromTable':child,'fromColumn':foreign,'toTable':parent,'toColumn':key,
      'crossFilteringBehavior':'bothDirections' if both else 'oneDirection'})
for t in tables:
    if t['name'] in ['DeliveryPerformance','InventoryMovements']:t['isHidden']=True
write(S/'model.bim',{'name':'SwiftLog_Analytics','compatibilityLevel':1567,'model':{'culture':'en-US','sourceQueryCulture':'en-US','defaultPowerBIDataSourceVersion':'powerBI_V3','tables':tables,'relationships':relations,'expressions':expressions}})
write(S/'definition.pbism',{'version':'1.0','settings':{}})
write(D/'SwiftLog_Analytics.pbip',{'version':'1.0','artifacts':[{'report':{'path':'SwiftLog.Report'}}],'settings':{'enableAutoRecovery':True}})
write(R/'definition.pbir',{'version':'4.0','datasetReference':{'byPath':{'path':'../SwiftLog.SemanticModel'}}})
write(R/'definition/version.json',{'$schema':schema('versionMetadata','1.0.0'),'version':'4.0.0'})
write(R/'definition/report.json',{'$schema':schema('report','3.1.0'),'themeCollection':{},'settings':{'useStylableVisualContainerHeader':True,'defaultDrillFilterOtherVisuals':True,'useEnhancedTooltips':True}})
(D/'Measures.dax').write_text('\n\n'.join('// '+d+'\n'+n+' = '+e for n,e,f,d in measures))
pd.DataFrame(measures,columns=['Measure','DAX','Format','BusinessDefinition']).to_csv(ROOT/'Analysis/KPI_Definitions.csv',index=False)
(D/'PowerQuery.m').write_text('\n\n'.join('// '+t['name']+'\n'+'\n'.join(t['expression']) for t in expressions)+'\n\n'+'\n\n'.join('// '+t['name']+'\n'+'\n'.join(t['partitions'][0]['source']['expression']) for t in tables))

def literal(value): return {'expr':{'Literal':{'Value':value}}}
def text(value): return literal("'"+str(value).replace("'","''")+"'")
def field(entity,column,measure=False):
    return {'Measure' if measure else 'Column':{'Expression':{'SourceRef':{'Entity':entity}},'Property':column}}
def projection(entity,column,measure=False):
    return {'field':field(entity,column,measure),'queryRef':entity+'.'+column,'nativeQueryRef':column}

visible=[('executive','Executive'),('customers','Customer Analytics'),('inventory','Inventory & Warehouse'),('delivery','Shipment & Delivery'),('products','Supplier & Product')]
all_pages=visible+[('product_detail','Product Detail'),('context_tooltip','Context Tooltip')]
write(R/'definition/pages/pages.json',{'$schema':schema('pagesMetadata','1.0.0'),'pageOrder':[n for n,t in all_pages],'activePageName':'executive'})

def visual(page,name,kind,x,y,w,h,roles=None,title=None,objects=None,link=None,tooltip=False):
    v={'$schema':schema('visualContainer','2.0.0'),'name':name,'position':{'x':x,'y':y,'width':w,'height':h,'z':0,'tabOrder':len(list(page.glob('visuals/*')))},'visual':{'visualType':kind,'drillFilterOtherVisuals':True}}
    q=v['visual'];q['visualContainerObjects']={}
    if roles:q['query']={'queryState':{r:{'projections':p} for r,p in roles.items()}}
    if title:q['visualContainerObjects']['title']=[{'properties':{'show':literal('true'),'text':text(title),'fontSize':literal('12D')}}]
    if objects:q['objects']=objects
    if kind=='card':
        font='14D' if name in ['dynamic_title','supplier_coverage'] else '28D'
        q['objects']={'labels':[{'properties':{'fontSize':literal(font)}}],
                      'categoryLabels':[{'properties':{'show':literal('false')}}]}
    if link:q['visualContainerObjects']['visualLink']=[{'properties':link}]
    if tooltip:q['visualContainerObjects']['visualTooltip']=[{'properties':{'show':literal('true'),'type':text('ReportPage'),'section':text('context_tooltip')}}]
    write(page/'visuals'/name/'visual.json',v)
    index=q['query']['queryState'] if 'query' in q else {}
    mobile_y=v['position']['tabOrder']*150;mobile_h=140
    if name.startswith('nav_'):mobile_y=[n for n,t in visible].index(name[4:])*42;mobile_h=38
    elif name.startswith('slicer_'):mobile_y=220+['Month','City','WarehouseID','Category','Status'].index(name[7:])*70;mobile_h=65
    elif name=='dynamic_title':mobile_y=580;mobile_h=55
    elif name.startswith('kpi_'):mobile_y=650+int(name[4:])*105+(90 if page.name=='inventory' else 0);mobile_h=100
    elif name.startswith('chart_'):mobile_y=1190+int(name[6:])*250+(90 if page.name=='inventory' else 0);mobile_h=240
    elif name=='stock_parameter':mobile_y=640;mobile_h=80
    elif name=='supplier_catalogue':mobile_y=1940;mobile_h=240
    elif name=='supplier_coverage':mobile_y=2200;mobile_h=90
    mobile={'$schema':schema('visualContainerMobileState','2.0.0'),'position':{'x':0,'y':mobile_y,'width':320,'height':mobile_h,'z':0,'tabOrder':v['position']['tabOrder']}}
    write(page/'visuals'/name/'mobile.json',mobile)
    return v

def save_visual(page,v):write(page/'visuals'/v['name']/'visual.json',v)
def measure_label(measure):
    return {'Total Revenue':'Delivered order value (catalogue)', 'Average Order Value':'Priced delivered AOV',
      'On-Time Delivery Rate':'Recorded on-time rate','Return Rate':'Orders with return records',
      'Inventory Stock Level':'Aggregate stock quantity (proxy)','Supplier Performance Score':'Supplier score (unavailable)',
      'Top Customer Value':'Top customer delivered value','Top Product Value':'Top product delivered value'}.get(measure,measure)
def card(page,key,measure,x,y=180,w=238):return visual(page,key,'card',x,y,w,110,{'Values':[projection('Orders',measure,True)]},measure_label(measure))
def chart(page,key,entity,column,measure,x,y,kind='clusteredBarChart',w=596,h=245):
    v=visual(page,key,kind,x,y,w,h,{'Category':[projection(entity,column)],'Y':[projection('Orders',measure,True)],'Tooltips':[projection('Orders','Total Orders',True)]},measure_label(measure)+' by '+column,tooltip=True)
    sort_field=field(entity,column) if column in ['Month','DelayDays'] else field('Orders',measure,True)
    v['visual']['query']['sortDefinition']={'sort':[{'field':sort_field,'direction':'Ascending' if column in ['Month','DelayDays'] else 'Descending'}]}
    save_visual(page,v)
    return v

for name,title in all_pages:
    page=R/'definition/pages'/name
    p={'$schema':schema('page','2.0.0'),'name':name,'displayName':title,'displayOption':'FitToPage','width':1280,'height':850}
    if name=='product_detail':
        p['visibility']='HiddenInViewMode';p['filterConfig']={'filters':[{'name':'ProductDrillFilter','field':field('Products','ProductID'),'type':'Categorical','howCreated':'Drillthrough'}]}
        p['pageBinding']={'name':'ProductDrillthrough','type':'Drillthrough','parameters':[{'name':'Product','boundFilter':'ProductDrillFilter','fieldExpr':field('Products','ProductID')}],'acceptsFilterContext':'Default'}
    if name=='context_tooltip':
        p.update({'width':440,'height':280,'visibility':'HiddenInViewMode','pageBinding':{'name':'ContextTooltip','type':'Tooltip','acceptsFilterContext':'Default'}})
    write(page/'page.json',p)
    if name=='context_tooltip':
        card(page,'product_title','Selected Product Title',10,10,420)
        card(page,'tooltip_value','Total Revenue',10,145,200)
        card(page,'tooltip_return','Product Return Association Rate',225,145,200)
        continue
    for j,(destination,label) in enumerate(visible):
        visual(page,'nav_'+destination,'actionButton',20+248*j,10,235,40,objects={'text':[{'properties':{'text':text(label),'fontSize':literal('11D')}}]},link={'show':literal('true'),'type':text('PageNavigation'),'navigationSection':text(destination)})
    if name=='product_detail':
        for j,m in enumerate(['Selected Product Title','Total Revenue','Delivered Units','Product Order Count','Product Return Association Rate']):card(page,'detail_'+str(j),m,20+j*250)
        chart(page,'detail_month','Dates','Month','Total Revenue',20,320,kind='lineChart')
        chart(page,'detail_orders','Orders','Status','Total Orders',650,320)
        continue
    for j,(entity,column) in enumerate([('Dates','Month'),('Customers','City'),('Warehouses','WarehouseID'),('Products','Category'),('Orders','Status')]):
        v=visual(page,'slicer_'+column,'slicer',20+j*250,65,238,85,{'Values':[projection(entity,column)]},column)
        v['visual']['syncGroup']={'groupName':'SwiftLog_'+entity+'_'+column,'fieldChanges':True,'filterChanges':True};save_visual(page,v)
    title_visual=card(page,'dynamic_title','Dynamic Report Title',20,155,1238)
    title_visual['position']['height']=40;save_visual(page,title_visual)
    metrics={
      'executive':['Total Orders','Total Revenue','Average Order Value','On-Time Delivery Rate','Return Rate'],
      'customers':['Active Customers','Total Revenue','Repeat Customer Rate','First Observed Customers','Total Customers'],
      'inventory':['Inventory Stock Level','Observed Inventory Pairs','Low Stock Pairs','Warehouse Employees','Throughput to Stock Proxy'],
      'delivery':['Total Shipments','Delayed Shipments','On-Time Delivery Rate','Average Delivery Delay','Zero-Delay Share'],
      'products':['Total Products','Total Revenue','Delivered Units','Supplier Count','Supplier Performance Score']}[name]
    for j,m in enumerate(metrics):card(page,'kpi_'+str(j),m,20+j*250,205)
    spec={
      'executive':[('Dates','Month','Total Revenue','lineChart'),('Dates','Month','Total Orders','clusteredColumnChart'),('Shipments','DeliveryStatus','Total Shipments','clusteredBarChart'),('Returns','Reason','Return Events','clusteredBarChart')],
      'customers':[('Customers','CustomerID','Top Customer Value','clusteredBarChart'),('Customers','City','Total Orders','clusteredColumnChart'),('Customers','CustomerID','Top Customer Orders','clusteredBarChart'),('Dates','Month','First Observed Customers','lineChart')],
      'inventory':[('Warehouses','WarehouseID','Inventory Stock Level','clusteredColumnChart'),('Warehouses','WarehouseID','Warehouse Inventory Share Proxy','clusteredBarChart'),('Warehouses','WarehouseID','Low Stock Pairs','clusteredBarChart'),('Warehouses','WarehouseID','Shipments per Employee','clusteredColumnChart')],
      'delivery':[('Customers','City','Delayed Shipment Rate','clusteredBarChart'),('Shipments','DelayDays','Total Shipments','clusteredColumnChart'),('Dates','Month','Total Shipments','lineChart'),('Warehouses','WarehouseID','On-Time Delivery Rate','clusteredBarChart')],
      'products':[('Products','ProductID','Top Product Value','clusteredBarChart'),('Products','Category','Total Revenue','clusteredColumnChart'),('Products','ProductID','Product Return Association Rate','clusteredBarChart'),('Suppliers','SupplierID','Supplier Count','clusteredBarChart')]}[name]
    for j,(entity,column,measure,kind) in enumerate(spec):
        if name=='products' and j==3:
            visual(page,'supplier_catalogue','tableEx',650,585,596,230,{'Values':[projection('Suppliers','SupplierID'),projection('Suppliers','SupplierName')]},'Standalone supplier reference catalogue')
            continue
        v=chart(page,'chart_'+str(j),entity,column,measure,20+(j%2)*630,335+(j//2)*250,kind=kind,h=230)
        if name=='delivery' and j==0:
            v['visual']['objects']={'dataPoint':[{'properties':{'defaultColor':{'solid':{'color':{'expr':field('Orders','Delivery Colour',True)}}}}}]};save_visual(page,v)
    if name=='inventory':
        v=visual(page,'stock_parameter','slicer',20,800,590,45,{'Values':[projection('LowStockParameter','Threshold')]},'Low-stock planning threshold',objects={'data':[{'properties':{'mode':text('Dropdown')}}],'selection':[{'properties':{'singleSelect':literal('true'),'selectAllCheckboxEnabled':literal('false')}}]})
    if name=='products':
        v=card(page,'supplier_coverage','Supplier Measurement Coverage',650,800,590);v['position']['height']=45;save_visual(page,v)
    visuals=['chart_0','chart_1','chart_2'] if name=='products' else ['chart_0','chart_1','chart_2','chart_3']
    p['visualInteractions']=[{'source':source,'target':target,'type':'DataFilter'} for source in visuals for target in visuals if source!=target]
    write(page/'page.json',p)

bookmarks=[]
for target,label in [('executive','Executive overview'),('delivery','Delivery review')]:
    name='bookmark_'+target;bookmarks.append({'name':name})
    state={n:{'visualContainers':{}} for n,t in visible}
    write(R/'definition/bookmarks'/(name+'.bookmark.json'),{'$schema':schema('bookmark','2.1.0'),'name':name,'displayName':label,'options':{'suppressData':True},'explorationState':{'version':'1.3','activeSection':target,'sections':state}})
write(R/'definition/bookmarks/bookmarks.json',{'$schema':schema('bookmarksMetadata','1.0.0'),'items':bookmarks})
print(json.dumps({'tables':len(tables),'relationships':len(relations),'measures':len(measures),'visible_pages':5,'support_pages':2,'visuals':len(list(R.glob('definition/pages/*/visuals/*/visual.json')))}))
