"""Create the healthcare business report and six analytical dashboard views."""
from pathlib import Path
import json
import textwrap
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.ticker import FuncFormatter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont("HCSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("HCSans-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
pdfmetrics.registerFontFamily("HCSans", normal="HCSans", bold="HCSans-Bold", italic="HCSans", boldItalic="HCSans-Bold")

ROOT=Path(__file__).resolve().parents[1]
P=json.loads((ROOT/"Analysis/Dashboard_Data.json").read_text())
S=P["summary"];D=P["data"]
INK="#173D4A";TEAL="#147D83";GOLD="#C58A42";RED="#AC493F";LIGHT="#E8F0F1";MUTED="#526774"
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":11,"axes.spines.top":False,
 "axes.spines.right":False,"axes.spines.left":False,"axes.edgecolor":"#C9D7DA","axes.labelcolor":INK,
 "xtick.color":MUTED,"ytick.color":MUTED,"text.color":INK,"axes.titleweight":"bold",
 "figure.facecolor":"white","axes.facecolor":"white","savefig.facecolor":"white"})

def frame(name):return pd.DataFrame(D[name])
def save(fig,name):
    fig.tight_layout(pad=1.5)
    fig.savefig(ROOT/"Images"/(name+".png"),dpi=160,bbox_inches="tight")
    plt.close(fig)
def bar(name,labels,values,title,xlabel,color=TEAL):
    fig,ax=plt.subplots(figsize=(8.6,4.5))
    pos=np.arange(len(labels));ax.barh(pos,values,color=color,height=.63)
    ax.set_yticks(pos,labels=[textwrap.fill(str(x),25) for x in labels]);ax.invert_yaxis()
    ax.set_title(title,loc="left",pad=16);ax.set_xlabel(xlabel);ax.grid(axis="x",alpha=.16);ax.set_axisbelow(True)
    maximum=max(values) if len(values) else 1
    for y,v in zip(pos,values):ax.text(v+maximum*.015,y,f"{v:.2f}%" if xlabel.endswith("(%)") else f"{v:,.0f}",va="center",fontsize=10)
    ax.set_xlim(0,maximum*1.20);save(fig,name)
def make_charts():
    (ROOT/"Images").mkdir(exist_ok=True)
    coverage=frame("Coverage")
    bar("Appointment_Link_Coverage",coverage.Source,100*coverage.LinkedRecords/coverage.Records,
        "Only a small share of clinical and billing records links to the appointment extract","Linked records (%)",RED)
    age=frame("AgeGender").pivot(index="AgeGroup",columns="Gender",values="Patients").reindex(["0-17","18-34","35-49","50-64","65+"])
    fig,ax=plt.subplots(figsize=(8.6,4.5));y=np.arange(len(age))
    ax.barh(y,-age.Male,color=TEAL,label="Male");ax.barh(y,age.Female,color=GOLD,label="Female")
    ax.set_yticks(y,age.index);ax.set_xlabel("Registered patient records");ax.set_title("Age and recorded gender",loc="left",pad=15)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x,p:f"{abs(x):,.0f}"));ax.legend(frameon=False,loc="lower right")
    ax.axvline(0,color="#CBD5D7",lw=1);save(fig,"Age_Pyramid")
    province=frame("PatientProvince")
    bar("Patient_Provinces",province.ProvinceName,province.Patients,"Patient register by province of residence","Registered patient records")
    geo=json.loads((ROOT/"References/Rwanda_Provinces.geojson").read_text())
    counts=dict(zip(province.ProvinceName,province.Patients))
    def norm(x):return str(x).lower().replace("province","").replace("city of","").replace("city","").strip()
    lookup={norm(k):v for k,v in counts.items()}
    fig,ax=plt.subplots(figsize=(8.6,5));lo=min(counts.values());hi=max(counts.values())
    for feature in geo["features"]:
        name=feature["properties"]["shapeName"];value=lookup[norm(name)]
        polygons=feature["geometry"]["coordinates"]
        if feature["geometry"]["type"]=="Polygon":polygons=[polygons]
        largest=max(polygons,key=lambda poly:len(poly[0]))[0]
        for poly in polygons:
            a=np.array(poly[0]);ax.add_patch(Polygon(a,facecolor=plt.cm.YlGnBu(.30+.55*(value-lo)/max(1,hi-lo)),edgecolor="white",lw=1.4))
        a=np.array(largest);cx,cy=a[:,0].mean(),a[:,1].mean()
        ax.text(cx,cy,name.replace(" Province","").replace("City of ","")+"\n"+f"{value:,}",ha="center",va="center",fontsize=10,color=INK,bbox={"facecolor":"white","edgecolor":"none","alpha":.82,"pad":2})
    ax.autoscale();ax.set_aspect(1);ax.axis("off");ax.set_title("Patient residence, not facility location",loc="left",pad=12)
    fig.text(.03,.02,"Boundaries: geoBoundaries / Rwanda Geo Portal (2020), CC BY 4.0",fontsize=8,color=MUTED)
    save(fig,"Patient_Province_Map")
    monthly=frame("MonthlyAppointments")
    fig,ax=plt.subplots(figsize=(8.6,4.4));ax.plot(monthly.Month.str[-2:],monthly.Appointments,marker="o",color=TEAL,lw=2.4)
    ax.set_title("Available appointment records across the supplied 2026 scenario",loc="left",pad=16)
    ax.set_xlabel("Month");ax.set_ylabel("Appointments");ax.grid(axis="y",alpha=.2);save(fig,"Monthly_Appointments")
    diagnoses=frame("Diagnoses").head(20)
    bar("Diagnosis_Distribution",diagnoses.Diagnosis,diagnoses.Records,"Diagnosis records in the full CSV extract","Diagnosis records")
    labs=frame("LaboratoryTests")
    bar("Laboratory_Volume",labs.Test,labs.Records,"Laboratory test mix","Test records")
    meds=frame("Medications")
    bar("Medication_Volume",meds.Medication,meds.Records,"Prescription records by medication","Prescription records")
    fig,ax=plt.subplots(figsize=(8.6,4.3));vals=[S["billed"]/1e9,S["payments"]/1e9,S["summary_revenue"]/1e9]
    ax.bar(["Billing","Payment records","Revenue Summary"],vals,color=[INK,TEAL,GOLD],width=.58)
    for x,v in enumerate(vals):ax.text(x,v+.12,f"{v:.3f}",ha="center",weight="bold",fontsize=12)
    ax.set_ylim(0,max(vals)*1.2);ax.set_ylabel("RWF billion");ax.set_title("Financial extracts have different totals",loc="left",pad=16)
    ax.grid(axis="y",alpha=.15);ax.set_axisbelow(True);save(fig,"Financial_Reconciliation")
    rev=frame("RevenueSummary")
    fig,ax=plt.subplots(figsize=(8.6,4.3));ax.plot(rev.Month.str[-2:],rev.RevenueRWF/1e6,color=GOLD,marker="o",lw=2.4)
    ax.set_title("Monthly Revenue Summary remains unreconciled",loc="left",pad=16)
    ax.set_xlabel("Month in supplied 2026 series");ax.set_ylabel("RWF million");ax.grid(axis="y",alpha=.18);save(fig,"Revenue_Summary_Trend")
    roles=frame("StaffDistribution").groupby("Role",as_index=False).Staff.sum().sort_values("Staff",ascending=False)
    bar("Staff_Roles",roles.Role,roles.Staff,"Staff register by role","Staff records")
    ratings=frame("FeedbackRatings")
    fig,ax=plt.subplots(figsize=(8.6,4.3));ax.bar(ratings.Rating.astype(str),ratings.Responses,color=[RED,RED,GOLD,TEAL,TEAL],width=.58)
    for x,v in enumerate(ratings.Responses):ax.text(x,v+35,f"{v:,}",ha="center",fontsize=10)
    ax.set_ylim(0,ratings.Responses.max()*1.18);ax.set_xlabel("Recorded rating (1-5)");ax.set_ylabel("Feedback responses")
    ax.set_title("Feedback ratings are spread across the full scale",loc="left",pad=16);save(fig,"Feedback_Ratings")
    facility=frame("FacilityFeedback").head(10)
    fig,ax=plt.subplots(figsize=(8.6,4.5));ax.barh(facility.FacilityID,facility.MeanRating,color=TEAL,height=.63);ax.invert_yaxis()
    for y,(v,n) in enumerate(zip(facility.MeanRating,facility.Responses)):ax.text(v+.03,y,f"{v:.2f}  (n={n})",va="center",fontsize=9)
    ax.set_xlim(0,5);ax.set_xlabel("Mean rating out of 5");ax.set_title("Facility ratings in appointment-linked feedback only",loc="left",pad=16)
    save(fig,"Linked_Facility_Ratings")
    quality=pd.read_csv(ROOT/"Analysis/Data_Quality_Findings.csv")
    P["presentation"]={"coverage":coverage.to_dict("records"),"roles":roles.to_dict("records"),
      "financial":[{"Source":"Billing","AmountRWF":S["billed"]},{"Source":"Payment records","AmountRWF":S["payments"]},
                   {"Source":"Revenue Summary","AmountRWF":S["summary_revenue"]}],
      "source_table_count":S["canonical_tables"],"quality":quality.fillna("").to_dict("records")}
    (ROOT/"Analysis/Presentation_Data.json").write_text(json.dumps(P["presentation"],indent=2))

ST=getSampleStyleSheet()
ST.add(ParagraphStyle(name="TitleHC",fontName="HCSans-Bold",fontSize=24,leading=28,textColor=colors.HexColor(INK),spaceAfter=12))
ST.add(ParagraphStyle(name="HeadHC",fontName="HCSans-Bold",fontSize=14,leading=18,textColor=colors.HexColor(INK),spaceBefore=10,spaceAfter=7))
ST.add(ParagraphStyle(name="BodyHC",fontName="HCSans",fontSize=10.5,leading=15,textColor=colors.HexColor(INK),spaceAfter=8))
ST.add(ParagraphStyle(name="SmallHC",fontName="HCSans",fontSize=8.5,leading=12,textColor=colors.HexColor(MUTED),spaceAfter=6))
def para(t,style="BodyHC"):return Paragraph(t,ST[style])
def image(name,width=490):
    from PIL import Image as PILImage
    p=ROOT/"Images"/(name+".png")
    with PILImage.open(p) as im:w,h=im.size
    return Image(str(p),width=width,height=width*h/w)
def table(headers,rows,widths,font=9.2):
    data=[[para(str(c),"SmallHC") for c in headers]]+[[para(str(c),"SmallHC") for c in row] for row in rows]
    t=Table(data,colWidths=widths,hAlign="LEFT",repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor(LIGHT)),("LINEBELOW",(0,0),(-1,0),.7,colors.HexColor(TEAL)),
        ("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("LINEBELOW",(0,1),(-1,-1),.25,colors.HexColor("#DDE5E7"))]))
    return t
def footer(c,doc):
    c.setStrokeColor(colors.HexColor("#CAD7DA"));c.line(42,37,553,37)
    c.setFont("HCSans",8);c.setFillColor(colors.HexColor(MUTED))
    c.drawString(42,25,"HealthConnect Rwanda | AnalystLab Africa | Iyiola Anjolaoluwa Emmanuel")
    c.drawRightString(553,25,str(doc.page))
def report():
    story=[]
    story += [para("HealthConnect Rwanda","TitleHC"),para("Healthcare operations and performance analytics","HeadHC"),
        para("Business insights report<br/>Iyiola Anjolaoluwa Emmanuel | AnalystLab Africa, Week 6","SmallHC"),
        para("The supplied 2026 scenario contains 20,000 registered patient records, 5,000 available appointments, 60,000 bills and 21,064 feedback responses. The principal constraint is incomplete encounter linkage: 55,000 bills have no matching appointment in the supplied extract. Full financial totals and linked facility comparisons therefore answer different questions."),
        table(["Measure","Result","Reporting basis"],[
          ["Registered patients","20,000","Patient master, all records"],
          ["Observed appointment patients","4,443","Distinct patients in 5,000 available appointments"],
          ["Recorded payment amounts",f"RWF {S['payments']:,.0f}","All 60,000 payment records; dates absent"],
          ["Positive bill balances",f"RWF {S['outstanding']:,.0f}","Billed less aggregated paid, bounded at zero"],
          ["Mean feedback rating",f"{S['satisfaction']:.2f} / 5","All 21,064 supplied responses"]],[145,132,218]),
        para("Coverage governs interpretation","HeadHC"),
        image("Appointment_Link_Coverage",470),
        para("Source: supplied HealthConnect files. The annual scenario extends to 28 December 2026; it includes 864 appointments dated after 25 October. These records are analysed as supplied scenario data, not verified completed clinical activity.","SmallHC"),
        PageBreak()]
    story += [para("Patient register and clinical activity","TitleHC"),
        para(f"The register is 50.45% Male and 49.55% Female, with a mean supplied age of {S['age']:.2f} years. Every record is labelled Active and carries an insurance code. These fields do not verify recent attendance or policy validity. Only 4,443 registered patients appear in the available appointments; 510 have at least two observed appointments."),
        image("Age_Pyramid",470),
        para(f"Recorded chronic conditions appear on {S['chronic']:,} patient records ({S['chronic']/S['patients']:.3%}). Asthma, hypertension and diabetes are descriptive register categories; no clinical diagnosis or treatment recommendation is inferred from these fields."),
        para("Clinical extracts use different reporting grains","HeadHC"),
        table(["Extract","Available records","Interpretation"],[
          ["Diagnoses","60,000","Full CSV selected; workbook's 5,000 rows are an identical subset"],
          ["Laboratory tests / prescriptions","5,000 / 5,000","Full event counts retained; only matched appointments support date/facility attribution"],
          ["Admissions","5,000",f"Supplied mean length of stay: {S['los']:.2f} days"],
          ["Referrals","4,708","Destination identifiers available; origin requires appointment linkage"]],[140,100,255]),
        para("New registration counts, cancellation rates and clinical readmission rates are unavailable. Registration dates, appointment statuses, and dated admission/discharge episodes are absent. An observed repeat-admission count is reported separately and is not a 30-day readmission rate.","SmallHC"),PageBreak()]
    story += [para("Financial position and reconciliation","TitleHC"),
        image("Financial_Reconciliation",480),
        para(f"Billing totals RWF {S['billed']:,.0f}; payment records total RWF {S['payments']:,.0f}. The difference is RWF {S['outstanding']:,.0f}, with no calculated credit balances. The recorded payment-to-bill ratio is {S['collection_ratio']:.2%}. No payment dates or recognition rules are supplied, so these figures do not establish dated cash collection performance or recognised accounting revenue."),
        table(["Source","Total","Limitation"],[
          ["Billing","RWF 9.309 billion","Invoice dates and ServiceID absent"],
          ["Payment records","RWF 8.389 billion","Receipt dates absent; amounts kept independent of billing status"],
          ["Revenue Summary","RWF 1.133 billion","Separate annual monthly series; not reconciled to transaction extracts"],
          ["Insurance claims",f"{S['claim_count']:,} records",f"{S['claim_pending']:,} Pending; {S['claim_approved']:.2%} Approved share of all claims"]],[125,140,230]),
        para("Attribution and trend boundaries","HeadHC"),
        para("Only the 5,000 appointment-linked bills support facility, department and patient-residence province comparisons. Revenue by service cannot be derived: neither billing nor appointments identifies ServiceID. Insurance claim providers identify claims and associated bills, not the patient master insurance-code dictionary. Monthly Revenue Summary values remain a separate unreconciled series; linked appointment-cohort amounts are not receipt-month cash flows."),
        PageBreak()]
    story += [para("Operations and patient experience","TitleHC"),
        para(f"The staff extracts contain {S['staff']:,} records, including 350 doctors and 700 nurses. Clinical staff amount to 58.5 records per 1,000 registered patients. This ratio does not establish staffing adequacy: working hours, staffed capacity, case mix and complete encounter demand are not supplied."),
        image("Staff_Roles",450),
        para("Facility and capacity interpretation","HeadHC"),
        para("Twenty facility identifiers appear across the files, but a facility master with names, types, ownership and geography is absent. Appointment FacilityID agrees with the referenced department's FacilityID in only 5.12% of rows. Activity uses the appointment's recorded facility; department IDs supply type labels without forcing a facility reassignment."),
        para("The inventory lists 2,000 beds, 400 rooms and 200 equipment items. All beds are labelled Available. Dated occupancy, bed assignments, room usage and equipment availability are absent; physical utilization and expansion requirements cannot be estimated."),
        para("Feedback findings","HeadHC"),
        para(f"The all-response mean is {S['satisfaction']:.2f}/5. Ratings 1-2 represent {S['poor_rating']:.2%} of responses; rating 5 represents {S['excellent_rating']:.2%}. Only {S['feedback_coverage']:.2%} of feedback links to an available appointment. Facility and department rankings show their linked response counts and are descriptive comparisons of that subset. Monthly low-rating views follow appointment cohorts, not feedback-submission dates."),
        PageBreak()]
    recs=[
      ["1","Recover complete appointment extracts","55,000 of 60,000 bills lack an appointment match; monitor linkage coverage."],
      ["2","Reconcile financial source definitions","Resolve RWF 9.309bn billed, 8.389bn recorded payments and 1.133bn summary revenue."],
      ["3","Correct facility and department reference mappings","94.88% of appointment-to-department facility references disagree."],
      ["4","Publish a verified facility directory","Names, geography, ownership and facility types cannot currently be reported."],
      ["5","Add invoice dates, receipt dates and service keys","Enable dated balances, receipt-month trends and service-level attribution."],
      ["6","Review pending insurance claims","21,028 claims are Pending; track ageing and eventual resolution separately."],
      ["7","Investigate low-rating service feedback","40.44% of recorded ratings are 1-2; retain response counts and coverage."],
      ["8","Collect dated bed assignments and occupancy","A uniform Available label does not establish occupancy or bed utilization."],
      ["9","Maintain room and equipment usage histories","Capacity and availability indicators require actual operating observations."],
      ["10","Use controlled access for identifiable extracts","Keep patient contacts and individual clinical records out of public portfolio files."]
    ]
    story += [para("Executive recommendations","TitleHC"),table(["Rank","Action","Evidence and monitoring basis"],recs,[42,180,273]),
        para("Methods and reproducibility","HeadHC"),
        para(f"Thirty canonical tables were prepared from 27 unchanged source files. Text was trimmed, numeric fields typed, and slash-form birth dates normalised to ISO dates. All supplied birth dates fall on 1 January; recorded Age is retained. Duplicate source copies were reconciled rather than appended. All 40 required SQL questions were executed in SQLite, which the programme team explicitly permitted. The pipeline passes {S['validation_checks']} checks and 12 independent SQL reconciliations; the SQL backup was restored and its principal totals checked.","SmallHC"),
        para("Sources: AnalystLab Africa Week 6 official brief and linked HealthConnect datasets; programme clarification permitting SQLite, 20 October 2026. Province boundaries: geoBoundaries / Rwanda Geo Portal, 2020, CC BY 4.0. Source links and field definitions accompany the project. No unavailable capacity, facility geography or clinical-outcome fields were invented.","SmallHC")]
    doc=SimpleDocTemplate(str(ROOT/"Report/Business_Insights_Report.pdf"),pagesize=A4,
        leftMargin=42,rightMargin=42,topMargin=40,bottomMargin=48,
        title="HealthConnect Rwanda - Business Insights Report",author="Iyiola Anjolaoluwa Emmanuel")
    doc.build(story,onFirstPage=footer,onLaterPages=footer)

def dashboard_pdf():
    path=ROOT/"Report/Executive_Dashboard.pdf";w,h=landscape(A4)
    c=canvas.Canvas(str(path),pagesize=(w,h));c.setTitle("HealthConnect Rwanda - Executive Dashboard")
    c.setAuthor("Iyiola Anjolaoluwa Emmanuel")
    pages=[
      ("Executive dashboard",[("Registered patients","20,000"),("Available appointments","5,000"),("Payment records","RWF 8.389bn"),("Mean feedback","2.99 / 5")],
       ["Monthly_Appointments","Appointment_Link_Coverage"],
       "Annual supplied 2026 scenario. Only 8.33% of bills link to the available appointments. Full financial totals and linked facility comparisons have different coverage."),
      ("Patient analytics",[("Patients with visits","4,443"),("Repeat-visit patients","510"),("Recorded mean age","45.03 years"),("Insurance code present","100%")],
       ["Age_Pyramid","Patient_Province_Map"],
       "The patient master contains 20,000 records. Maps show province of patient residence. Insurance-code presence does not verify coverage or policy validity."),
      ("Clinical analytics",[("Diagnosis records","60,000"),("Laboratory tests","5,000"),("Prescriptions","5,000"),("Mean admission stay","5.49 days")],
       ["Diagnosis_Distribution","Laboratory_Volume"],
       "Global counts retain unmatched clinical records. Facility and date comparisons require a valid appointment link. Clinical readmission rates and causal conclusions are not supported."),
      ("Financial dashboard",[("Billing amounts","RWF 9.309bn"),("Payment records","RWF 8.389bn"),("Positive balances","RWF 919.947m"),("Approved claim share","49.98%")],
       ["Financial_Reconciliation","Revenue_Summary_Trend"],
       "Payment dates and accounting recognition rules are absent. Revenue Summary is an unreconciled source series. Service-level revenue attribution is unavailable."),
      ("Operational dashboard",[("Observed facility IDs","20"),("Staff records","1,250"),("Bed register","2,000"),("Equipment items","200")],
       ["Staff_Roles","Appointment_Link_Coverage"],
       "All beds are labelled Available. Occupancy, room utilization and equipment availability are unmeasured. Facility names and facility-to-geography mappings are absent."),
      ("Patient experience dashboard",[("Feedback responses","21,064"),("Mean rating","2.99 / 5"),("Ratings 1-2","40.44%"),("Appointment-linked","8.34%")],
       ["Feedback_Ratings","Linked_Facility_Ratings"],
       "Facility rankings cover only appointment-linked feedback and display response counts. Appointment-cohort trends do not establish feedback-submission trends.")
    ]
    for i,(title,cards,charts,note) in enumerate(pages):
        c.setFillColor(colors.HexColor("#F4F7F8"));c.rect(0,0,w,h,fill=1,stroke=0)
        c.setFillColor(colors.HexColor(INK));c.rect(0,h-74,w,74,fill=1,stroke=0)
        c.setFillColor(colors.white);c.setFont("HCSans-Bold",23);c.drawString(32,h-37,title)
        c.setFont("HCSans",10);c.drawString(32,h-57,"HealthConnect Rwanda | Supplied 2026 scenario | AnalystLab Africa")
        for j,(label,value) in enumerate(cards):
            x=32+j*(w-64)/4
            c.setFillColor(colors.HexColor(MUTED));c.setFont("HCSans",9);c.drawString(x,h-103,label)
            c.setFillColor(colors.HexColor(INK));c.setFont("HCSans-Bold",19);c.drawString(x,h-130,value)
        for j,name in enumerate(charts):
            c.drawImage(str(ROOT/"Images"/(name+".png")),32+j*(w-56)/2,133,width=(w-80)/2,height=h-298,preserveAspectRatio=True,anchor="c",mask="auto")
        c.setFillColor(colors.HexColor(INK));c.setFont("HCSans",10)
        y=100
        for line in textwrap.wrap(note,140):c.drawString(32,y,line);y-=15
        c.setFont("HCSans",8);c.setFillColor(colors.HexColor(MUTED))
        c.drawString(32,31,"Analytical page views | Definitions and source coverage are documented in the business report")
        c.drawRightString(w-32,31,f"{i+1} / 6");c.showPage()
    c.save()

if __name__=="__main__":
    make_charts();report();dashboard_pdf()
    print(json.dumps({"report":"Report/Business_Insights_Report.pdf","dashboard":"Report/Executive_Dashboard.pdf","images":len(list((ROOT/"Images").glob("*.png")))}))
