// DataFolder is a text parameter containing the absolute Data/Processed path.

// Appointments
let
    Source = Csv.Document(File.Contents(DataFolder & "/Model_Appointments.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"AppointmentID", type text}, {"PatientID", type text}, {"DoctorID", type text}, {"FacilityID", type text}, {"DepartmentID", type text}, {"Date", type date}, {"VisitType", type text}, {"Month", type text}, {"Gender", type text}, {"AgeGroup", type text}, {"ProvinceName", type text}, {"ChronicCondition", type text}, {"InsuranceID", type text}, {"DepartmentName", type text}, {"DepartmentFacilityAligned", Int64.Type}, {"IsFirstObserved", Int64.Type}}, "en-US")
in
    Typed

// Patients
let
    Source = Csv.Document(File.Contents(DataFolder & "/Model_Patients.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"PatientID", type text}, {"Gender", type text}, {"Age", Int64.Type}, {"MaritalStatus", type text}, {"Occupation", type text}, {"Education", type text}, {"VillageID", type text}, {"InsuranceID", type text}, {"BloodGroup", type text}, {"HeightCm", Int64.Type}, {"WeightKg", Int64.Type}, {"ChronicCondition", type text}, {"Status", type text}, {"BMI", type number}, {"SectorID", type text}, {"DistrictID", type text}, {"DistrictName", type text}, {"ProvinceID", type text}, {"ProvinceName", type text}, {"AgeGroup", type text}, {"CountryName", type text}, {"AgeSort", Int64.Type}}, "en-US")
in
    Typed

// Billing
let
    Source = Csv.Document(File.Contents(DataFolder & "/Model_Billing.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"BillingID", type text}, {"AppointmentID", type text}, {"Amount", Int64.Type}, {"BillingStatus", type text}, {"AmountPaid", Int64.Type}, {"Outstanding", Int64.Type}, {"Credit", Int64.Type}, {"PaymentRecords", Int64.Type}, {"Method", type text}, {"FacilityID", type text}, {"DepartmentID", type text}, {"DepartmentName", type text}, {"ProvinceName", type text}, {"Date", type date}, {"Month", type text}, {"HasAppointment", Int64.Type}, {"BalanceFlag", type text}}, "en-US")
in
    Typed

// Staff
let
    Source = Csv.Document(File.Contents(DataFolder & "/Model_Staff.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"StaffID", type text}, {"Role", type text}, {"Department", type text}, {"Specialty", type text}, {"FacilityID", type text}, {"DepartmentID", type text}, {"YearsExperience", Int64.Type}, {"Status", type text}}, "en-US")
in
    Typed

// Facilities
let
    Source = Csv.Document(File.Contents(DataFolder & "/Model_Facilities.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"FacilityID", type text}}, "en-US")
in
    Typed

// Diagnoses
let
    Source = Csv.Document(File.Contents(DataFolder & "/Model_Diagnoses.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"DiagnosisID", type text}, {"AppointmentID", type text}, {"Diagnosis", type text}, {"Severity", type text}, {"HasAppointment", Int64.Type}}, "en-US")
in
    Typed

// LaboratoryTests
let
    Source = Csv.Document(File.Contents(DataFolder & "/Model_LaboratoryTests.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"LabID", type text}, {"AppointmentID", type text}, {"Test", type text}, {"Result", type text}, {"HasAppointment", Int64.Type}}, "en-US")
in
    Typed

// Prescriptions
let
    Source = Csv.Document(File.Contents(DataFolder & "/Model_Prescriptions.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"PrescriptionID", type text}, {"AppointmentID", type text}, {"Medication", type text}, {"Dosage", type text}, {"HasAppointment", Int64.Type}}, "en-US")
in
    Typed

// Admissions
let
    Source = Csv.Document(File.Contents(DataFolder & "/Model_Admissions.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"AdmissionID", type text}, {"AppointmentID", type text}, {"LengthOfStayDays", Int64.Type}, {"HasAppointment", Int64.Type}}, "en-US")
in
    Typed

// Referrals
let
    Source = Csv.Document(File.Contents(DataFolder & "/Model_Referrals.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"ReferralID", type text}, {"AppointmentID", type text}, {"ReferredFacilityID", type text}, {"HasAppointment", Int64.Type}}, "en-US")
in
    Typed

// Payments
let
    Source = Csv.Document(File.Contents(DataFolder & "/Model_Payments.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"PaymentID", type text}, {"BillingID", type text}, {"AmountPaid", Int64.Type}, {"Method", type text}}, "en-US")
in
    Typed

// Feedback
let
    Source = Csv.Document(File.Contents(DataFolder & "/Model_Feedback.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"FeedbackID", type text}, {"AppointmentID", type text}, {"Rating", Int64.Type}, {"Comment", type text}, {"HasAppointment", Int64.Type}}, "en-US")
in
    Typed

// Departments
let
    Source = Csv.Document(File.Contents(DataFolder & "/Model_Departments.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"DepartmentID", type text}, {"DepartmentName", type text}, {"FacilityID", type text}}, "en-US")
in
    Typed

// Beds
let
    Source = Csv.Document(File.Contents(DataFolder & "/Model_Beds.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"BedID", type text}, {"RoomID", type text}, {"Status", type text}}, "en-US")
in
    Typed

// Rooms
let
    Source = Csv.Document(File.Contents(DataFolder & "/Model_Rooms.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"RoomID", type text}, {"DepartmentID", type text}, {"FacilityID", type text}, {"RoomName", type text}}, "en-US")
in
    Typed

// Equipment
let
    Source = Csv.Document(File.Contents(DataFolder & "/Model_Equipment.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"EquipmentID", type text}, {"EquipmentName", type text}, {"DepartmentID", type text}, {"FacilityID", type text}}, "en-US")
in
    Typed

// Services
let
    Source = Csv.Document(File.Contents(DataFolder & "/Model_Services.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"ServiceID", type text}, {"ServiceName", type text}, {"DepartmentID", type text}}, "en-US")
in
    Typed

// RevenueSummary
let
    Source = Csv.Document(File.Contents(DataFolder & "/Model_RevenueSummary.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"Month", type text}, {"Revenue", Int64.Type}, {"Appointments", Int64.Type}}, "en-US")
in
    Typed

// Claims
let
    Source = Csv.Document(File.Contents(DataFolder & "/Model_Claims.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"ClaimID", type text}, {"BillingID", type text}, {"Provider", type text}, {"ClaimAmount", type number}, {"Status", type text}}, "en-US")
in
    Typed

// Dates
let
    Source = Csv.Document(File.Contents(DataFolder & "/Model_Dates.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Nulls = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Nulls, {{"Date", type date}, {"Year", Int64.Type}, {"Quarter", type text}, {"Month", type text}, {"MonthNumber", Int64.Type}}, "en-US")
in
    Typed