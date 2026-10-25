# Data dictionary

| Canonical table | Rows | Grain and key | Main fields and interpretation |
| --- | ---: | --- | --- |
| Patients | 20,000 | PatientID | Supplied age, gender, insurance code, recorded chronic condition, blood group, VillageID and status. Age retained; Active does not establish recent attendance. |
| Countries / Provinces / Districts / Sectors / Villages | 1 / 5 / 30 / 120 / 480 | Respective geographic ID | Administrative lookup chain for patient residence. |
| Appointments | 5,000 | AppointmentID | PatientID, DoctorID, FacilityID, DepartmentID, Date and VisitType. No appointment status or visit time. |
| Diagnoses | 60,000 | DiagnosisID | AppointmentID, Diagnosis, Severity. Full CSV; workbook subset excluded from append. |
| LaboratoryTests | 5,000 | LabID | AppointmentID, Test, Result. Results are descriptive source fields. |
| Prescriptions | 5,000 | PrescriptionID | AppointmentID, Medication, Dosage. No dispensing or consumption quantities. |
| Admissions | 5,000 | AdmissionID | AppointmentID and LengthOfStayDays; no admission/discharge dates or bed assignments. |
| Referrals | 4,708 | ReferralID | AppointmentID and ReferredFacilityID; destination ID does not provide facility characteristics. |
| Billing | 60,000 | BillingID | AppointmentID, Amount and Status. No invoice date or ServiceID. |
| Payments | 60,000 | PaymentID | BillingID, AmountPaid, Method. No receipt date. |
| InsuranceClaims | 42,036 | ClaimID | BillingID, Provider, ClaimAmount, Status; no claim dates. Provider belongs to claims, not patient insurance-code lookup. |
| Feedback | 21,064 | FeedbackID | AppointmentID, Rating 1–5, Comment. No submission dates; comment category is separate from rating. |
| RevenueSummary | 12 | Month | Revenue and Appointments. Separate unreconciled monthly source. |
| Departments / Specialties / Services | 200 / 200 / 400 | Respective ID | Facility and department reference data. Services are not linked to billing transactions. |
| Equipment / Rooms / Beds | 200 / 400 / 2,000 | Respective ID | Inventory references; no dated usage. Beds have a uniformly Available source status. |
| Doctors / Nurses | 350 / 700 | StaffID | Role, facility, department, specialty and years of experience. |
| Pharmacists / LaboratoryScientists / Radiographers / AdministrativeStaff | 50 / 40 / 30 / 80 | StaffID | Same staff schema. Combined Staff view has 1,250 rows. |
| OwnershipTypes | 4 | OwnershipTypeID | Standalone lookup; no facility ownership assignment is supplied. |

## Derived model

`PatientGeo` joins the residence lookup chain and assigns age bands 0–17, 18–34, 35–49, 50–64 and 65+. `AppointmentFact` adds residence province, department type and a facility-alignment flag without overwriting the recorded appointment facility. `ObservedFacilities` is a union of source identifiers, not an inferred facility master.

`PaymentsByBill` aggregates payment amounts by BillingID. `BillingFact` retains the bill grain, joins those payment amounts once, and calculates positive balances and credits. `HasAppointment` identifies records that can be attributed to the available appointment extract. Unlinked amounts remain in full financial totals.

Aggregate CSV files retain their grain in their column names. `AppointmentCube` and `FinancialCube` represent linked encounter cohorts. `FeedbackCube` contains rating sums and response counts, permitting weighted means. Do not average facility means without weighting by response counts. Do not sum distinct patient counts across groups that can contain the same patient.

Monetary fields are reported in Rwandan francs (RWF). Ratios retain their exact analytical numerator and denominator definitions in `Analysis/KPI_Definitions.csv`; Power BI measures are separately documented in `Dashboard/Measure_Definitions.csv`.
