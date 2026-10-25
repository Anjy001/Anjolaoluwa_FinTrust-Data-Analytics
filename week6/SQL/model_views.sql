CREATE VIEW PatientGeo AS
SELECT p.*,v.SectorID,s.DistrictID,d.DistrictName,d.ProvinceID,pr.ProvinceName,
 CASE WHEN p.Age<18 THEN '0-17' WHEN p.Age<35 THEN '18-34'
      WHEN p.Age<50 THEN '35-49' WHEN p.Age<65 THEN '50-64' ELSE '65+' END AS AgeGroup
FROM Patients p
LEFT JOIN Villages v ON p.VillageID=v.VillageID
LEFT JOIN Sectors s ON v.SectorID=s.SectorID
LEFT JOIN Districts d ON s.DistrictID=d.DistrictID
LEFT JOIN Provinces pr ON d.ProvinceID=pr.ProvinceID;

CREATE VIEW Staff AS
SELECT * FROM Doctors UNION ALL SELECT * FROM Nurses UNION ALL
SELECT * FROM Pharmacists UNION ALL SELECT * FROM LaboratoryScientists UNION ALL
SELECT * FROM Radiographers UNION ALL SELECT * FROM AdministrativeStaff;

CREATE VIEW ObservedFacilities AS
SELECT FacilityID FROM Departments UNION SELECT FacilityID FROM Appointments
UNION SELECT FacilityID FROM Staff UNION SELECT FacilityID FROM Rooms
UNION SELECT FacilityID FROM Equipment UNION SELECT ReferredFacilityID FROM Referrals;

CREATE VIEW AppointmentFact AS
SELECT a.*,substr(a.Date,1,7) AS Month,p.Gender,p.AgeGroup,p.ProvinceName,
 p.ChronicCondition,p.InsuranceID,d.DepartmentName,
 CASE WHEN d.FacilityID=a.FacilityID THEN 1 ELSE 0 END AS DepartmentFacilityAligned
FROM Appointments a
LEFT JOIN PatientGeo p ON a.PatientID=p.PatientID
LEFT JOIN Departments d ON a.DepartmentID=d.DepartmentID;

CREATE VIEW PaymentsByBill AS
SELECT BillingID,SUM(AmountPaid) AS AmountPaid,COUNT(*) AS PaymentRecords,
 CASE WHEN COUNT(DISTINCT Method)=1 THEN MIN(Method) ELSE 'Multiple methods' END AS Method
FROM Payments GROUP BY BillingID;

CREATE VIEW BillingFact AS
SELECT b.BillingID,b.AppointmentID,b.Amount,b.Status AS BillingStatus,
 COALESCE(p.AmountPaid,0) AS AmountPaid,
 MAX(b.Amount-COALESCE(p.AmountPaid,0),0) AS Outstanding,
 MAX(COALESCE(p.AmountPaid,0)-b.Amount,0) AS Credit,
 COALESCE(p.PaymentRecords,0) AS PaymentRecords,p.Method,
 a.FacilityID,a.DepartmentID,a.DepartmentName,a.ProvinceName,a.Date,a.Month,
 CASE WHEN a.AppointmentID IS NOT NULL THEN 1 ELSE 0 END AS HasAppointment
FROM Billing b LEFT JOIN PaymentsByBill p ON b.BillingID=p.BillingID
LEFT JOIN AppointmentFact a ON b.AppointmentID=a.AppointmentID;
