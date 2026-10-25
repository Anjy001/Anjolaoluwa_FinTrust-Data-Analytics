-- HealthConnect Rwanda healthcare operations analysis.
-- SQLite 3. Source relationships and reporting definitions are in README.md.
-- Queries 01, 04-06, 08-09 and 14 produce record-level results.
-- Financial facility, department and province results cover linked appointments.

-- Q01: Retrieve all registered patients
SELECT * FROM PatientGeo ORDER BY PatientID;

-- Q02: Count patients by gender
SELECT Gender,COUNT(*) AS Patients FROM Patients GROUP BY Gender ORDER BY Patients DESC;

-- Q03: Count patients by province of residence
SELECT ProvinceName,COUNT(*) AS Patients FROM PatientGeo GROUP BY ProvinceName ORDER BY Patients DESC;

-- Q04: Identify patients above 65 years
SELECT PatientID,Age,Gender,ProvinceName FROM PatientGeo WHERE Age>65 ORDER BY Age DESC,PatientID;

-- Q05: Find patients with recorded chronic conditions
SELECT PatientID,ChronicCondition FROM Patients WHERE ChronicCondition NOT IN ('None','','Unknown') ORDER BY PatientID;

-- Q06: Retrieve patients with recorded insurance codes
SELECT PatientID,InsuranceID FROM Patients WHERE InsuranceID NOT IN ('None','','Unknown','Uninsured') ORDER BY PatientID;

-- Q07: Count patients by blood group
SELECT BloodGroup,COUNT(*) AS Patients FROM Patients GROUP BY BloodGroup ORDER BY Patients DESC;

-- Q08: List all patients at the youngest and oldest recorded ages
SELECT PatientID,Age,CASE WHEN Age=(SELECT MIN(Age) FROM Patients) THEN 'Youngest' ELSE 'Oldest' END AS AgeExtreme
FROM Patients WHERE Age=(SELECT MIN(Age) FROM Patients) OR Age=(SELECT MAX(Age) FROM Patients) ORDER BY Age,PatientID;

-- Q09: Identify duplicate phone numbers
SELECT Phone,COUNT(*) AS PatientRecords FROM Patients WHERE TRIM(Phone)<>'' GROUP BY Phone HAVING COUNT(*)>1 ORDER BY PatientRecords DESC,Phone;

-- Q10: Calculate average recorded patient age
SELECT COUNT(*) AS Patients,AVG(Age) AS AverageAgeYears FROM Patients;

-- Q11: Count available appointments by month
SELECT Month,COUNT(*) AS Appointments FROM AppointmentFact GROUP BY Month ORDER BY Month;

-- Q12: Rank observed facility IDs by available appointment volume
SELECT FacilityID,COUNT(*) AS Appointments,DENSE_RANK() OVER(ORDER BY COUNT(*) DESC) AS VolumeRank
FROM Appointments GROUP BY FacilityID ORDER BY Appointments DESC,FacilityID;

-- Q13: Find busiest department types
SELECT DepartmentName,COUNT(*) AS Appointments FROM AppointmentFact GROUP BY DepartmentName ORDER BY Appointments DESC;

-- Q14: Find doctors with the highest recorded appointment workload
SELECT DoctorID,COUNT(*) AS Appointments FROM Appointments GROUP BY DoctorID ORDER BY Appointments DESC,DoctorID;

-- Q15: Identify referral patterns with explicit appointment-link coverage
SELECT COALESCE(a.FacilityID,'Unlinked appointment') AS OriginFacilityID,r.ReferredFacilityID,COUNT(*) AS Referrals
FROM Referrals r LEFT JOIN Appointments a ON r.AppointmentID=a.AppointmentID
GROUP BY OriginFacilityID,r.ReferredFacilityID ORDER BY Referrals DESC,OriginFacilityID;

-- Q16: Count emergency appointments
SELECT COUNT(*) AS EmergencyAppointments FROM Appointments WHERE VisitType='Emergency';

-- Q17: Calculate appointments per registered doctor, including doctors with no linked appointments
SELECT (SELECT COUNT(*) FROM Appointments) AS Appointments,COUNT(*) AS RegisteredDoctors,
 1.0*(SELECT COUNT(*) FROM Appointments)/NULLIF(COUNT(*),0) AS AppointmentsPerDoctor FROM Doctors;

-- Q18: Retrieve appointments by patient-residence province
SELECT ProvinceName,COUNT(*) AS Appointments FROM AppointmentFact GROUP BY ProvinceName ORDER BY Appointments DESC;

-- Q19: Identify observed facilities with the highest unique patient volume
SELECT FacilityID,COUNT(DISTINCT PatientID) AS UniquePatients FROM Appointments GROUP BY FacilityID ORDER BY UniquePatients DESC,FacilityID;

-- Q20: Find peak consultation dates and weekdays; hours are unavailable
SELECT Date,strftime('%w',Date) AS WeekdaySunday0,COUNT(*) AS ConsultationAppointments
FROM Appointments WHERE VisitType='Consultation' GROUP BY Date ORDER BY ConsultationAppointments DESC,Date;

-- Q21: Top 20 recorded diagnoses in the full diagnosis extract
SELECT Diagnosis,COUNT(*) AS DiagnosisRecords FROM Diagnoses GROUP BY Diagnosis ORDER BY DiagnosisRecords DESC,Diagnosis LIMIT 20;

-- Q22: Most requested laboratory tests
SELECT Test,COUNT(*) AS Tests FROM LaboratoryTests GROUP BY Test ORDER BY Tests DESC,Test;

-- Q23: Most prescribed medications
SELECT Medication,COUNT(*) AS PrescriptionRecords FROM Prescriptions GROUP BY Medication ORDER BY PrescriptionRecords DESC,Medication;

-- Q24: Average supplied admission duration
SELECT COUNT(*) AS AdmissionRecords,AVG(LengthOfStayDays) AS AverageLengthOfStayDays FROM Admissions;

-- Q25: Disease severity distribution
SELECT Severity,COUNT(*) AS DiagnosisRecords FROM Diagnoses GROUP BY Severity ORDER BY DiagnosisRecords DESC;

-- Q26: Laboratory test mix and volume; capacity utilization is unavailable
SELECT Test,COUNT(*) AS Tests,100.0*COUNT(*)/(SELECT COUNT(*) FROM LaboratoryTests) AS ShareOfTestsPercent
FROM LaboratoryTests GROUP BY Test ORDER BY Tests DESC;

-- Q27: Prescription trends in appointment-linked records
SELECT a.Month,p.Medication,COUNT(*) AS LinkedPrescriptions FROM Prescriptions p
JOIN AppointmentFact a ON p.AppointmentID=a.AppointmentID GROUP BY a.Month,p.Medication ORDER BY a.Month,p.Medication;

-- Q28: Referral destinations in the full supplied referral extract
SELECT ReferredFacilityID,COUNT(*) AS Referrals FROM Referrals GROUP BY ReferredFacilityID ORDER BY Referrals DESC,ReferredFacilityID;

-- Q29: Admission associations among distinct diagnosed encounters
SELECT d.Diagnosis,COUNT(DISTINCT d.AppointmentID) AS DiagnosedEncounters,
 COUNT(DISTINCT ad.AppointmentID) AS AdmissionAssociatedEncounters,
 100.0*COUNT(DISTINCT ad.AppointmentID)/NULLIF(COUNT(DISTINCT d.AppointmentID),0) AS AdmissionAssociationPercent
FROM Diagnoses d LEFT JOIN Admissions ad ON d.AppointmentID=ad.AppointmentID
GROUP BY d.Diagnosis ORDER BY AdmissionAssociationPercent DESC,d.Diagnosis;

-- Q30: Clinical record workload by department type for linked appointments
WITH events AS (
 SELECT AppointmentID,'Diagnosis' AS EventType FROM Diagnoses
 UNION ALL SELECT AppointmentID,'Laboratory' FROM LaboratoryTests
 UNION ALL SELECT AppointmentID,'Prescription' FROM Prescriptions
 UNION ALL SELECT AppointmentID,'Admission' FROM Admissions
 UNION ALL SELECT AppointmentID,'Referral' FROM Referrals
)
SELECT a.DepartmentName,e.EventType,COUNT(*) AS LinkedClinicalRecords FROM events e
JOIN AppointmentFact a ON e.AppointmentID=a.AppointmentID GROUP BY a.DepartmentName,e.EventType ORDER BY a.DepartmentName,e.EventType;

-- Q31: Reported payment amounts by appointment-linked facility
SELECT FacilityID,COUNT(*) AS LinkedBills,SUM(Amount) AS BilledRWF,SUM(AmountPaid) AS RecordedPaymentsRWF
FROM BillingFact WHERE HasAppointment=1 GROUP BY FacilityID ORDER BY RecordedPaymentsRWF DESC,FacilityID;

-- Q32: Reported payment amounts by appointment-linked department type
SELECT DepartmentName,COUNT(*) AS LinkedBills,SUM(AmountPaid) AS RecordedPaymentsRWF
FROM BillingFact WHERE HasAppointment=1 GROUP BY DepartmentName ORDER BY RecordedPaymentsRWF DESC;

-- Q33: Revenue attribution to healthcare services is not supported by the supplied billing schema
SELECT 'Revenue by service' AS Metric,NULL AS RecordedPaymentsRWF,
 'Unavailable: billing and appointment records contain no ServiceID; department-level service allocation would duplicate amounts.' AS Definition;

-- Q34: Insurance claims by provider
SELECT Provider,COUNT(*) AS Claims,SUM(ClaimAmount) AS ClaimAmountRWF,
 SUM(CASE WHEN Status='Approved' THEN 1 ELSE 0 END) AS ApprovedClaims,
 SUM(CASE WHEN Status='Pending' THEN 1 ELSE 0 END) AS PendingClaims
FROM InsuranceClaims GROUP BY Provider ORDER BY ClaimAmountRWF DESC;

-- Q35: Outstanding balances after payments aggregated once per bill
SELECT COUNT(*) AS Bills,SUM(Amount) AS BilledRWF,SUM(AmountPaid) AS RecordedPaymentsRWF,
 SUM(Outstanding) AS OutstandingRWF,SUM(Credit) AS CreditRWF FROM BillingFact;

-- Q36: Average billing amount
SELECT COUNT(*) AS Bills,AVG(Amount) AS AverageBillingRWF FROM Billing;

-- Q37: Monthly revenue as supplied separately in Revenue Summary
SELECT Month,Revenue AS ReportedSummaryRevenueRWF,Appointments AS ReportedSummaryAppointments
FROM RevenueSummary ORDER BY Month;

-- Q38: Payment methods in the full payment extract
SELECT Method,COUNT(*) AS PaymentRecords,SUM(AmountPaid) AS RecordedPaymentsRWF FROM Payments
GROUP BY Method ORDER BY RecordedPaymentsRWF DESC;

-- Q39: Highest payment totals among facilities in the linked appointment subset
SELECT FacilityID,SUM(AmountPaid) AS LinkedRecordedPaymentsRWF FROM BillingFact
WHERE HasAppointment=1 GROUP BY FacilityID ORDER BY LinkedRecordedPaymentsRWF DESC,FacilityID LIMIT 10;

-- Q40: Financial ranking of linked facilities by payment amount and collection ratio
SELECT FacilityID,COUNT(*) AS LinkedBills,SUM(Amount) AS BilledRWF,SUM(AmountPaid) AS RecordedPaymentsRWF,
 1.0*SUM(AmountPaid)/NULLIF(SUM(Amount),0) AS RecordedCollectionRatio,
 DENSE_RANK() OVER(ORDER BY SUM(AmountPaid) DESC) AS RecordedPaymentRank
FROM BillingFact WHERE HasAppointment=1 GROUP BY FacilityID ORDER BY RecordedPaymentRank,FacilityID;
