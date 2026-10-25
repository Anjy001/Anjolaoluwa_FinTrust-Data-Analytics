"""Prepare HealthConnect source tables, execute SQL, and export analytical outputs."""
from pathlib import Path
import hashlib
import io
import json
import re
import sqlite3
import sys
import contextlib
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "Countries": "HCCountries.csv", "Provinces": "HC_Provinces.csv",
    "Districts": "HC_Districts.csv", "Sectors": "HC_Sectors.csv",
    "Villages": "HC_Villages.csv", "OwnershipTypes": "HC_Ownership_Types.csv",
    "Departments": "HC_Departments.csv", "Specialties": "HC_Medical_Specialties.csv",
    "Services": "HC_Services.csv", "Equipment": "HC_Medical_Equipment.csv",
    "Rooms": "HC_Rooms.csv", "Beds": "HC_Beds.csv", "Doctors": "HC_Doctor.csv",
    "Nurses": "HC_Nurse.csv", "Pharmacists": "Pharmacist.csv",
    "LaboratoryScientists": "Laboratory_Scientist.csv",
    "Radiographers": "HC_Radiographer.csv",
    "AdministrativeStaff": "HC_Administrative_Staff.csv", "Patients": "HC_Patients.csv",
    "Diagnoses": "HC_Diagnoses.csv", "Billing": "HC_Billing.csv",
    "InsuranceClaims": "Insurance_Claims.csv", "Payments": "HC_Payments.csv",
    "Feedback": "HC_Patient_Feedback.csv", "RevenueSummary": "HC_Revenue_Summary.csv",
}
SHEETS = {"Appointments":"Appointments", "LaboratoryTests":"Laboratory_Tests",
          "Prescriptions":"Prescriptions", "Admissions":"Admissions", "Referrals":"Referrals"}
NUMERIC = {"Age", "HeightCm", "WeightKg", "BMI", "YearsExperience", "Amount",
           "AmountPaid", "ClaimAmount", "Rating", "LengthOfStayDays", "Revenue", "Appointments"}
PRIVATE_COLUMNS = {"FirstName","LastName","Phone","EmergencyContact","DateOfBirth"}

def load_tables():
    tables = {name: pd.read_csv(ROOT/"Data/Original"/file, dtype=str, keep_default_na=False)
              for name, file in FILES.items()}
    clinical = pd.read_excel(ROOT/"Data/Original/HC_Clinical_Transactions.xlsx",
                             sheet_name=None, dtype=str, keep_default_na=False)
    tables.update({name: clinical[sheet].copy() for name,sheet in SHEETS.items()})
    transformations = []
    for name, frame in tables.items():
        frame.columns = frame.columns.str.strip()
        changed = 0
        for col in frame:
            before = frame[col].copy()
            frame[col] = frame[col].astype(str).str.strip()
            changed += int((before != frame[col]).sum())
            if col in NUMERIC:
                frame[col] = pd.to_numeric(frame[col], errors="raise")
        normalized_dates = 0
        if name == "Patients":
            frame["DateOfBirth"] = pd.to_datetime(frame["DateOfBirth"], format="%m/%d/%Y", errors="raise").dt.strftime("%Y-%m-%d")
            normalized_dates = len(frame)
        transformations.append({"Table":name,"Rows":len(frame),"TrimmedCells":changed,"NormalizedDates":normalized_dates,
                                "DuplicateRowsRetained":int(frame.duplicated().sum())})
    pd.DataFrame(transformations).to_csv(ROOT/"Analysis/Transformations.csv",index=False)
    return tables, clinical

def write_csv(frame, path):
    frame.to_csv(path,index=False,float_format="%.15g")

def main():
    for d in ["Analysis","Data/Processed","SQL/Results","Dashboard"]:
        (ROOT/d).mkdir(parents=True,exist_ok=True)
    tables, clinical = load_tables()
    checks, findings = [], []
    def check(name, ok, observed, expected):
        checks.append({"Check":name,"Passed":bool(ok),"Observed":str(observed),"Expected":str(expected)})
    def finding(name, numerator, denominator=None, detail=""):
        findings.append({"Issue":name,"Records":int(numerator),"Denominator":denominator,
                         "Share":None if denominator is None else numerator/denominator,"Interpretation":detail})
    for name, frame in tables.items():
        key = frame.columns[0]
        check(name+" primary key", frame[key].is_unique and frame[key].ne("").all(),
              frame[key].nunique(),len(frame))
        check(name+" blank cells",int(frame.eq("").sum().sum())==0,int(frame.eq("").sum().sum()),0)
        for col in set(frame.columns)&NUMERIC:
            check(name+" "+col+" nonnegative",bool((frame[col]>=0).all()),int((frame[col]<0).sum()),0)
        write_csv(frame.drop(columns=list(PRIVATE_COLUMNS&set(frame)),errors="ignore"),
                  ROOT/"Data/Processed"/(name+".csv"))
    full_diag=tables["Diagnoses"]
    embedded=clinical["Diagnoses"].astype(str)
    embedded_match=embedded.merge(full_diag.astype(str),on=list(embedded.columns),how="inner").shape[0]
    check("Workbook diagnosis subset agrees with full CSV",embedded_match==len(embedded),embedded_match,len(embedded))
    master=pd.read_excel(ROOT/"Data/Original/HC_Facility_Master_Data.xlsx",sheet_name=None,dtype=str,keep_default_na=False)
    master_pairs={"Departments":"Departments","Medical_Specialties":"Specialties","Services":"Services",
                  "Medical_Equipment":"Equipment","Rooms":"Rooms","Beds":"Beds"}
    for sheet, name in master_pairs.items():
        left=master[sheet].astype(str).sort_values(master[sheet].columns.tolist()).reset_index(drop=True)
        right=tables[name].astype(str).sort_values(tables[name].columns.tolist()).reset_index(drop=True)
        check("Facility workbook mirrors "+name,left.equals(right),len(left),len(right))
    app=tables["Appointments"]
    for name in ["Appointments","Patients"]:
        col="Date" if name=="Appointments" else "DateOfBirth"
        parsed=pd.to_datetime(tables[name][col],format="%Y-%m-%d",errors="coerce")
        check(name+" dates parse",parsed.notna().all(),int(parsed.isna().sum()),0)
    check("Patient ages 0-120",tables["Patients"].Age.between(0,120).all(),
          int((~tables["Patients"].Age.between(0,120)).sum()),0)
    check("Feedback ratings 1-5",tables["Feedback"].Rating.between(1,5).all(),
          int((~tables["Feedback"].Rating.between(1,5)).sum()),0)
    links=[("Provinces","CountryID","Countries","CountryID"),("Districts","ProvinceID","Provinces","ProvinceID"),
           ("Sectors","DistrictID","Districts","DistrictID"),("Villages","SectorID","Sectors","SectorID"),
           ("Patients","VillageID","Villages","VillageID"),("Appointments","PatientID","Patients","PatientID"),
           ("Appointments","DoctorID","Doctors","StaffID"),("Appointments","DepartmentID","Departments","DepartmentID"),
           ("Beds","RoomID","Rooms","RoomID"),("Payments","BillingID","Billing","BillingID"),
           ("InsuranceClaims","BillingID","Billing","BillingID")]
    for child,ck,parent,pk in links:
        n=int((~tables[child][ck].isin(tables[parent][pk])).sum())
        check(child+"."+ck+" references "+parent,n==0,n,0)
    for name in ["Billing","Diagnoses","Feedback","LaboratoryTests","Prescriptions","Admissions","Referrals"]:
        n=int((~tables[name].AppointmentID.isin(app.AppointmentID)).sum())
        finding(name+" appointment references absent from extract",n,len(tables[name]),
                "Unmatched records retained in their own reporting grain; excluded from appointment-linked attribution.")
    dept=tables["Departments"].set_index("DepartmentID").FacilityID
    mism=int((app.FacilityID!=app.DepartmentID.map(dept)).sum())
    finding("Appointment versus department facility mismatch",mism,len(app),
            "Record FacilityID identifies appointment activity; department lookup supplies type only.")
    staff=pd.concat([tables[n] for n in ["Doctors","Nurses","Pharmacists","LaboratoryScientists","Radiographers","AdministrativeStaff"]],ignore_index=True)
    finding("Staff versus department facility mismatch",int((staff.FacilityID!=staff.DepartmentID.map(dept)).sum()),len(staff),
            "Staff distribution uses the staff record's facility and department label.")
    doctor_facility=tables["Doctors"].set_index("StaffID").FacilityID
    finding("Appointment versus doctor master facility mismatch",int((app.FacilityID!=app.DoctorID.map(doctor_facility)).sum()),len(app),
            "A master affiliation does not establish the location of each encounter.")
    db=ROOT/"SQL/HealthConnect.sqlite"
    if db.exists(): db.unlink()
    con=sqlite3.connect(db)
    for name,frame in tables.items():
        frame.to_sql(name,con,index=False,if_exists="replace",chunksize=1000)
        key=frame.columns[0]
        con.execute('CREATE UNIQUE INDEX "pk_'+name+'" ON "'+name+'" ("'+key+'")')
        for col in frame.columns:
            if col.endswith("ID") and col!=key:
                con.execute('CREATE INDEX "ix_'+name+'_'+col+'" ON "'+name+'" ("'+col+'")')
    con.executescript((ROOT/"SQL/model_views.sql").read_text())
    query_text=(ROOT/"SQL/healthcare_analysis.sql").read_text()
    parts=re.split(r"-- Q(\d{2}): ([^\n]+)\n",query_text)
    query_manifest=[]
    for i in range(1,len(parts),3):
        qid,title,sql=parts[i:i+3]
        sql=sql.strip()
        result=pd.read_sql_query(sql,con)
        filename="Q"+qid+".csv"
        write_csv(result,ROOT/"SQL/Results"/filename)
        query_manifest.append({"Question":int(qid),"BusinessQuestion":title,"Rows":len(result),"Output":filename})
    check("All required SQL queries executed",len(query_manifest)==40,len(query_manifest),40)
    write_csv(pd.DataFrame(query_manifest),ROOT/"SQL/Query_Index.csv")
    def q(sql):return pd.read_sql_query(sql,con)
    def scalar(sql):return con.execute(sql).fetchone()[0]
    patients=q("SELECT * FROM PatientGeo")
    af=q("SELECT * FROM AppointmentFact")
    bf=q("SELECT * FROM BillingFact")
    k=[]
    def metric(key,label,value,unit,definition):
        k.append({"Key":key,"Metric":label,"Value":value,"Unit":unit,"Definition":definition})
    n_pat=len(patients);n_app=len(app)
    counts=app.PatientID.value_counts()
    paid=float(tables["Payments"].AmountPaid.sum());billed=float(tables["Billing"].Amount.sum())
    outstanding=float(bf.Outstanding.sum());credit=float(bf.Credit.sum())
    feedback=tables["Feedback"]
    claim=tables["InsuranceClaims"]
    summary=tables["RevenueSummary"]
    linked_ad=tables["Admissions"].merge(app,on="AppointmentID",how="inner",validate="many_to_one")
    ref_distinct=app.AppointmentID.isin(tables["Referrals"].AppointmentID).sum()
    ad_distinct=app.AppointmentID.isin(tables["Admissions"].AppointmentID).sum()
    repeats=linked_ad.groupby("PatientID").size()
    first_dates=af.groupby("PatientID").Date.min()
    metric("patients","Registered patient records",n_pat,"patients","All supplied patient master records.")
    metric("active_patients","Patients labelled Active",int(patients.Status.eq("Active").sum()),"patients","Source status, distinct from observed visit activity.")
    metric("observed_patients","Patients with observed appointments",len(counts),"patients","Distinct PatientID in the available appointment extract.")
    metric("first_observed","First observed patients",len(first_dates),"patients","First encounter within the supplied extract; registration dates are absent.")
    metric("returning","Patients with repeat observed appointments",int(counts.ge(2).sum()),"patients","At least two available appointments; not a longitudinal retention rate.")
    metric("single_visit","Patients with one observed appointment",int(counts.eq(1).sum()),"patients","Exactly one encounter in the available appointment extract.")
    metric("male","Male patient records",int(patients.Gender.eq("Male").sum()),"patients","Recorded Gender.")
    metric("female","Female patient records",int(patients.Gender.eq("Female").sum()),"patients","Recorded Gender.")
    metric("insurance","Recorded insurance-code presence",float((~patients.InsuranceID.isin(["","None","Unknown","Uninsured"])).mean()),"ratio","Nonempty insurance identifier; policy validity and patient-to-provider lookup are unavailable.")
    metric("age","Average recorded age",float(patients.Age.mean()),"years","Supplied Age values; no recalculation against the execution date.")
    metric("chronic","Patients with recorded chronic conditions",int((~patients.ChronicCondition.isin(["None","","Unknown"])).sum()),"patients","Any recorded condition other than None/blank/Unknown.")
    metric("appointments","Available appointments",n_app,"appointments","5,000 source rows; this extract does not cover all encounters referenced elsewhere.")
    metric("emergency","Emergency appointments",int(app.VisitType.eq("Emergency").sum()),"appointments","Available appointment extract.")
    metric("consultation","Consultation appointments",int(app.VisitType.eq("Consultation").sum()),"appointments","Available appointment extract.")
    metric("followup","Follow-up appointments",int(app.VisitType.eq("Follow-up").sum()),"appointments","Available appointment extract.")
    metric("referral_rate","Referral association in available appointments",float(ref_distinct/n_app),"ratio","Distinct available appointments with at least one matching referral / available appointments.")
    metric("admission_rate","Admission association in available appointments",float(ad_distinct/n_app),"ratio","Distinct available appointments with at least one matching admission / available appointments.")
    metric("diagnoses","Diagnosis records",len(full_diag),"records","Full diagnosis CSV; the 5,000-row workbook copy is a matching subset, not an additional fact table.")
    metric("lab_tests","Laboratory test records",len(tables["LaboratoryTests"]),"records","All supplied laboratory rows, including unlinked appointments.")
    metric("prescriptions","Prescription records",len(tables["Prescriptions"]),"records","All supplied prescription rows.")
    metric("admissions","Admission records",len(tables["Admissions"]),"records","All supplied admission rows.")
    metric("los","Average supplied length of stay",float(tables["Admissions"].LengthOfStayDays.mean()),"days","All supplied admission duration values; admissions have no dated start/end fields.")
    metric("referrals","Referral records",len(tables["Referrals"]),"records","All supplied referral rows.")
    metric("repeat_admission","Patients with multiple linked admission records",int(repeats.ge(2).sum()),"patients","Descriptive observed repeat-admission indicator; no clinical 30-day readmission definition is supported.")
    for key,name in [("doctors","Doctors"),("nurses","Nurses"),("pharmacists","Pharmacists"),("lab_scientists","LaboratoryScientists"),("radiographers","Radiographers"),("admin_staff","AdministrativeStaff")]:
        metric(key,name+" records",len(tables[name]),"staff","Role-specific supplied master table.")
    metric("staff","All staff records",len(staff),"staff","Six role extracts; StaffID uniqueness checked across the combined population.")
    metric("experience","Average staff experience",float(staff.YearsExperience.mean()),"years","All supplied staff records.")
    metric("staff_ratio","Clinical staff per 1,000 registered patients",(len(staff)-len(tables["AdministrativeStaff"]))/n_pat*1000,"per 1,000","Doctors, nurses, pharmacists, laboratory scientists and radiographers / patient register; not a staffing adequacy standard.")
    metric("doctor_workload","Appointments per registered doctor",n_app/len(tables["Doctors"]),"appointments/doctor","Includes doctors with zero available appointments.")
    metric("facilities","Observed facility identifiers",int(scalar("SELECT COUNT(*) FROM ObservedFacilities")),"identifiers","Union of FacilityIDs in supplied tables; facility names, ownership and locations are absent.")
    metric("beds","Bed register capacity",len(tables["Beds"]),"beds","Supplied bed records; not a dated occupancy census.")
    metric("available_beds","Beds labelled Available",int(tables["Beds"].Status.eq("Available").sum()),"beds","Source status only; all beds carry the same status.")
    metric("rooms","Room records",len(tables["Rooms"]),"rooms","Supplied room inventory.")
    metric("equipment","Equipment records",len(tables["Equipment"]),"items","Supplied medical equipment inventory.")
    metric("billed","Billing amounts",billed,"RWF","All supplied bill Amount values.")
    metric("payments","Recorded payment amounts",paid,"RWF","All AmountPaid values; payment dates and accounting revenue-recognition fields are absent.")
    metric("outstanding","Positive bill balances",outstanding,"RWF","Sum max(bill Amount - aggregate AmountPaid per bill, 0).")
    metric("credit","Credit balances",credit,"RWF","Sum max(aggregate paid per bill - bill Amount, 0).")
    metric("collection_ratio","Recorded payment-to-bill ratio",paid/billed,"ratio","All recorded payment amounts / all billed amounts; not a dated collection-performance rate.")
    metric("average_bill","Average billing amount",float(tables["Billing"].Amount.mean()),"RWF/bill","Total billing / bill count.")
    metric("summary_revenue","Revenue Summary amount",float(summary.Revenue.sum()),"RWF","Separate source series; unreconciled with payment and billing totals.")
    metric("summary_appointments","Revenue Summary appointment count",int(summary.Appointments.sum()),"appointments","Separate source summary, not the available appointment extract.")
    metric("claim_count","Insurance claims",len(claim),"claims","All supplied claim records.")
    metric("claim_approved","Approved share of all claims",float(claim.Status.eq("Approved").mean()),"ratio","Approved / all supplied claims, including Pending. Rejected records are absent.")
    metric("claim_pending","Pending insurance claims",int(claim.Status.eq("Pending").sum()),"claims","Source Status equals Pending.")
    metric("claim_amount","Insurance claim amounts",float(claim.ClaimAmount.sum()),"RWF","Claim amount differs from billed revenue and received payments.")
    metric("satisfaction","Mean recorded feedback rating",float(feedback.Rating.mean()),"out of 5","All supplied feedback records, including unlinked appointments.")
    metric("feedback","Feedback records",len(feedback),"responses","All supplied feedback rows.")
    metric("poor_rating","Ratings 1-2",float(feedback.Rating.le(2).mean()),"ratio","Analytical poor-rating band defined as source Rating 1 or 2.")
    metric("excellent_rating","Ratings 5",float(feedback.Rating.eq(5).mean()),"ratio","Source Rating equals 5.")
    metric("billing_coverage","Billing appointment-link coverage",float(bf.HasAppointment.mean()),"ratio","Bills with a valid appointment row / all bills.")
    metric("feedback_coverage","Feedback appointment-link coverage",float(feedback.AppointmentID.isin(app.AppointmentID).mean()),"ratio","Feedback rows linked to the available appointment extract / all feedback.")
    metric("department_alignment","Appointment department/facility alignment",float(af.DepartmentFacilityAligned.mean()),"ratio","Appointment FacilityID agrees with its department master FacilityID.")
    metric("future_appointments","Available appointments dated after 25 October 2026",int(app.Date.gt("2026-10-25").sum()),"appointments","Supplied training scenario includes future-dated records; not a claim of completed real-world activity.")
    for key,label,reason in [
        ("new_registrations","Newly registered patients","No registration date."),
        ("cancellation","Appointment cancellation rate","No appointment status or cancellation field."),
        ("bed_utilization","Bed occupancy utilization","No dated occupancy census, bed assignments or admission start/end dates."),
        ("room_utilization","Room utilization","No usage or availability history."),
        ("equipment_utilization","Equipment utilization","No usage hours or capacity."),
        ("equipment_availability","Equipment availability","No availability/status field."),
        ("facility_types","Facility type distribution","Facility master table is not supplied."),
        ("facility_provinces","Facility province distribution","Facility-to-geography mapping is not supplied."),
        ("service_revenue","Revenue by healthcare service","No transaction-level ServiceID."),
        ("readmission_rate","Clinical readmission rate","No admission dates, discharge dates or defined readmission window."),
        ("payment_growth","Payment growth by receipt month","No payment receipt date."),
        ("capacity","Department physical capacity","No staffed capacity or department throughput limits.")]:
        metric(key,label,None,"unavailable",reason)
    kd=pd.DataFrame(k)
    write_csv(kd,ROOT/"Analysis/KPI_Definitions.csv")
    pd.DataFrame(findings).to_csv(ROOT/"Analysis/Data_Quality_Findings.csv",index=False)
    sums={x["Key"]:x["Value"] for x in k}
    sums.update({"period_start":app.Date.min(),"period_end":app.Date.max(),
                 "source_files":27,"canonical_tables":len(tables),"sql_queries":len(query_manifest),
                 "appointment_date_basis":"Supplied full-year 2026 training scenario",
                 "units":"RWF","source_diagnosis_subset_rows":len(embedded)})
    check("Combined staff IDs are unique",staff.StaffID.is_unique,staff.StaffID.nunique(),len(staff))
    check("Billing view preserves bill grain",len(bf)==len(tables["Billing"]),len(bf),len(tables["Billing"]))
    check("Appointment view preserves appointment grain",len(af)==len(app),len(af),len(app))
    check("Billing arithmetic reconciles",abs(billed-float(bf.AmountPaid.sum())-outstanding+credit)<0.000001,
          billed-float(bf.AmountPaid.sum())-outstanding+credit,0)
    check("Patient geography coverage",patients.ProvinceName.notna().all(),int(patients.ProvinceName.isna().sum()),0)
    check("SQLite integrity",scalar("PRAGMA integrity_check")=="ok",scalar("PRAGMA integrity_check"),"ok")
    reconciliations=[
        ("Registered patients",n_pat,scalar("SELECT COUNT(*) FROM Patients")),
        ("Available appointments",n_app,scalar("SELECT COUNT(*) FROM Appointments")),
        ("Billing amount",billed,scalar("SELECT SUM(Amount) FROM Billing")),
        ("Payment amount",paid,scalar("SELECT SUM(AmountPaid) FROM Payments")),
        ("Outstanding balance",outstanding,scalar("SELECT SUM(Outstanding) FROM BillingFact")),
        ("Patient age",float(patients.Age.mean()),scalar("SELECT AVG(Age) FROM Patients")),
        ("Mean feedback rating",float(feedback.Rating.mean()),scalar("SELECT AVG(Rating) FROM Feedback")),
        ("Average admission duration",float(tables["Admissions"].LengthOfStayDays.mean()),scalar("SELECT AVG(LengthOfStayDays) FROM Admissions")),
        ("Emergency volume",sums["emergency"],scalar("SELECT COUNT(*) FROM Appointments WHERE VisitType='Emergency'")),
        ("Approved claims",int(claim.Status.eq("Approved").sum()),scalar("SELECT COUNT(*) FROM InsuranceClaims WHERE Status='Approved'")),
        ("Registered doctors",len(tables["Doctors"]),scalar("SELECT COUNT(*) FROM Doctors")),
        ("Chronic-condition patients",sums["chronic"],scalar("SELECT COUNT(*) FROM Patients WHERE ChronicCondition NOT IN ('None','','Unknown')")),
    ]
    rc=[]
    for name,pv,sv in reconciliations:
        diff=float(pv)-float(sv);ok=abs(diff)<0.000001
        rc.append({"Metric":name,"PandasValue":pv,"SQLValue":sv,"Difference":diff,"Matched":ok})
        check("Independent SQL reconciliation: "+name,ok,diff,0)
    write_csv(pd.DataFrame(rc),ROOT/"Analysis/SQL_Reconciliation.csv")
    aggs={}
    def agg(name,sql):
        frame=q(sql)
        write_csv(frame,ROOT/"Analysis"/(name+".csv"))
        aggs[name]=json.loads(frame.to_json(orient="records"))
    agg("PatientProfile","SELECT ProvinceName,Gender,AgeGroup,ChronicCondition,BloodGroup,COUNT(*) AS Patients FROM PatientGeo GROUP BY ProvinceName,Gender,AgeGroup,ChronicCondition,BloodGroup")
    agg("PatientProvince","SELECT ProvinceName,COUNT(*) AS Patients FROM PatientGeo GROUP BY ProvinceName ORDER BY Patients DESC")
    agg("AgeGender","SELECT AgeGroup,Gender,COUNT(*) AS Patients FROM PatientGeo GROUP BY AgeGroup,Gender")
    agg("ChronicConditions","SELECT ChronicCondition,COUNT(*) AS Patients FROM Patients GROUP BY ChronicCondition ORDER BY Patients DESC")
    agg("InsuranceCodes","SELECT InsuranceID,COUNT(*) AS Patients FROM Patients GROUP BY InsuranceID ORDER BY Patients DESC")
    agg("AppointmentCube","SELECT Month,FacilityID,DepartmentName,VisitType,ProvinceName,COUNT(*) AS Appointments,COUNT(DISTINCT PatientID) AS UniquePatients FROM AppointmentFact GROUP BY Month,FacilityID,DepartmentName,VisitType,ProvinceName")
    agg("MonthlyAppointments","SELECT Month,COUNT(*) AS Appointments,COUNT(DISTINCT PatientID) AS UniquePatients FROM AppointmentFact GROUP BY Month ORDER BY Month")
    agg("DailyAppointments","SELECT Date,COUNT(*) AS Appointments FROM Appointments GROUP BY Date ORDER BY Date")
    agg("FirstObserved","SELECT substr(FirstDate,1,7) AS Month,COUNT(*) AS Patients FROM (SELECT PatientID,MIN(Date) AS FirstDate FROM Appointments GROUP BY PatientID) GROUP BY Month ORDER BY Month")
    agg("FacilityAppointments","SELECT FacilityID,COUNT(*) AS Appointments,COUNT(DISTINCT PatientID) AS UniquePatients FROM Appointments GROUP BY FacilityID ORDER BY Appointments DESC,FacilityID")
    agg("DepartmentAppointments","SELECT DepartmentName,COUNT(*) AS Appointments FROM AppointmentFact GROUP BY DepartmentName ORDER BY Appointments DESC")
    agg("Diagnoses","SELECT Diagnosis,COUNT(*) AS Records FROM Diagnoses GROUP BY Diagnosis ORDER BY Records DESC,Diagnosis")
    agg("Severity","SELECT Severity,COUNT(*) AS Records FROM Diagnoses GROUP BY Severity")
    agg("LaboratoryTests","SELECT Test,COUNT(*) AS Records FROM LaboratoryTests GROUP BY Test ORDER BY Records DESC")
    agg("Medications","SELECT Medication,COUNT(*) AS Records FROM Prescriptions GROUP BY Medication ORDER BY Records DESC")
    agg("AdmissionsDuration","SELECT LengthOfStayDays,COUNT(*) AS Records FROM Admissions GROUP BY LengthOfStayDays ORDER BY LengthOfStayDays")
    agg("ReferralDestinations","SELECT ReferredFacilityID,COUNT(*) AS Records FROM Referrals GROUP BY ReferredFacilityID ORDER BY Records DESC,ReferredFacilityID")
    agg("FinancialCube","SELECT Month,FacilityID,DepartmentName,ProvinceName,COUNT(*) AS Bills,SUM(Amount) AS BilledRWF,SUM(AmountPaid) AS PaymentsRWF,SUM(Outstanding) AS OutstandingRWF FROM BillingFact WHERE HasAppointment=1 GROUP BY Month,FacilityID,DepartmentName,ProvinceName")
    agg("PaymentMethods","SELECT Method,COUNT(*) AS Records,SUM(AmountPaid) AS PaymentsRWF FROM Payments GROUP BY Method ORDER BY PaymentsRWF DESC")
    agg("ClaimProviders","SELECT Provider,Status,COUNT(*) AS Claims,SUM(ClaimAmount) AS ClaimAmountRWF FROM InsuranceClaims GROUP BY Provider,Status")
    agg("ClaimBillAssociations","SELECT c.Provider,COUNT(DISTINCT c.BillingID) AS Bills,SUM(p.AmountPaid) AS PaymentsOnClaimAssociatedBillsRWF FROM InsuranceClaims c JOIN PaymentsByBill p ON c.BillingID=p.BillingID GROUP BY c.Provider")
    agg("RevenueSummary","SELECT Month,Revenue AS RevenueRWF,Appointments FROM RevenueSummary ORDER BY Month")
    agg("StaffDistribution","SELECT FacilityID,Role,Department,COUNT(*) AS Staff,AVG(YearsExperience) AS AverageExperience FROM Staff GROUP BY FacilityID,Role,Department")
    agg("BedInventory","SELECT r.FacilityID,r.DepartmentID,b.Status,COUNT(*) AS Beds FROM Beds b LEFT JOIN Rooms r ON b.RoomID=r.RoomID GROUP BY r.FacilityID,r.DepartmentID,b.Status")
    agg("EquipmentInventory","SELECT FacilityID,EquipmentName,COUNT(*) AS Items FROM Equipment GROUP BY FacilityID,EquipmentName")
    agg("FeedbackRatings","SELECT Rating,COUNT(*) AS Responses FROM Feedback GROUP BY Rating ORDER BY Rating")
    agg("FeedbackComments","SELECT Comment,COUNT(*) AS Responses FROM Feedback GROUP BY Comment ORDER BY Responses DESC")
    agg("FeedbackCube","SELECT a.Month,a.FacilityID,a.DepartmentName,COUNT(*) AS Responses,SUM(f.Rating) AS RatingSum,SUM(CASE WHEN f.Rating<=2 THEN 1 ELSE 0 END) AS PoorRatings,SUM(CASE WHEN f.Rating=5 THEN 1 ELSE 0 END) AS ExcellentRatings FROM Feedback f JOIN AppointmentFact a ON f.AppointmentID=a.AppointmentID GROUP BY a.Month,a.FacilityID,a.DepartmentName")
    agg("FacilityFeedback","SELECT a.FacilityID,COUNT(*) AS Responses,AVG(f.Rating) AS MeanRating FROM Feedback f JOIN Appointments a ON f.AppointmentID=a.AppointmentID GROUP BY a.FacilityID ORDER BY MeanRating DESC,a.FacilityID")
    agg("DepartmentFeedback","SELECT a.DepartmentName,COUNT(*) AS Responses,AVG(f.Rating) AS MeanRating FROM Feedback f JOIN AppointmentFact a ON f.AppointmentID=a.AppointmentID GROUP BY a.DepartmentName ORDER BY MeanRating DESC")
    agg("Coverage","SELECT 'Billing' AS Source,COUNT(*) AS Records,SUM(HasAppointment) AS LinkedRecords FROM BillingFact UNION ALL SELECT 'Diagnoses',COUNT(*),SUM(CASE WHEN AppointmentID IN (SELECT AppointmentID FROM Appointments) THEN 1 ELSE 0 END) FROM Diagnoses UNION ALL SELECT 'Feedback',COUNT(*),SUM(CASE WHEN AppointmentID IN (SELECT AppointmentID FROM Appointments) THEN 1 ELSE 0 END) FROM Feedback UNION ALL SELECT 'Laboratory tests',COUNT(*),SUM(CASE WHEN AppointmentID IN (SELECT AppointmentID FROM Appointments) THEN 1 ELSE 0 END) FROM LaboratoryTests UNION ALL SELECT 'Prescriptions',COUNT(*),SUM(CASE WHEN AppointmentID IN (SELECT AppointmentID FROM Appointments) THEN 1 ELSE 0 END) FROM Prescriptions UNION ALL SELECT 'Admissions',COUNT(*),SUM(CASE WHEN AppointmentID IN (SELECT AppointmentID FROM Appointments) THEN 1 ELSE 0 END) FROM Admissions UNION ALL SELECT 'Referrals',COUNT(*),SUM(CASE WHEN AppointmentID IN (SELECT AppointmentID FROM Appointments) THEN 1 ELSE 0 END) FROM Referrals")
    check("Patient profile aggregates reconcile",sum(x["Patients"] for x in aggs["PatientProfile"])==n_pat,
          sum(x["Patients"] for x in aggs["PatientProfile"]),n_pat)
    check("Appointment cube reconciles",sum(x["Appointments"] for x in aggs["AppointmentCube"])==n_app,
          sum(x["Appointments"] for x in aggs["AppointmentCube"]),n_app)
    check("No negative bill balances",bool((bf.Outstanding>=0).all()),int((bf.Outstanding<0).sum()),0)
    check("Claims have one record per bill for provider association",claim.BillingID.is_unique,claim.BillingID.nunique(),len(claim))
    sums["validation_checks"]=len(checks)
    sums["validation_passed"]=sum(x["Passed"] for x in checks)
    sums["validation_failed"]=sum(not x["Passed"] for x in checks)
    payload={"summary":sums,"kpis":k,"data":aggs,"quality":findings,
             "reporting":{"organization":"HealthConnect Rwanda","author":"Iyiola Anjolaoluwa Emmanuel",
                          "programme":"AnalystLab Africa","week":6}}
    (ROOT/"Analysis/Summary.json").write_text(json.dumps(sums,indent=2,allow_nan=False))
    (ROOT/"Analysis/Dashboard_Data.json").write_text(json.dumps(payload,allow_nan=False,separators=(",",":")))
    write_csv(pd.DataFrame(checks),ROOT/"Analysis/Validation_Results.csv")
    con.commit()
    with (ROOT/"SQL/Healthcare_Database.sql").open("w") as f:
        for line in con.iterdump():f.write(line+"\n")
    con.close()
    print(json.dumps(sums,indent=2))
    if sums["validation_failed"]:
        failed=[x for x in checks if not x["Passed"]]
        raise RuntimeError(json.dumps(failed))

if __name__=="__main__":
    main()
