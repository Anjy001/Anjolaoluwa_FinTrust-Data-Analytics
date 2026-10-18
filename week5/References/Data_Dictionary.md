# SwiftLog data dictionary

Definitions follow the supplied fields and the official project clarification. Business meanings not explicitly supplied are analytical assumptions. Original tables retain their source fields.

| Reporting table | Field | Definition |
| --- | --- | --- |
| Customers | CustomerID | Customer identifier. |
| Customers | CustomerName | Provided customer label. |
| Customers | City | Customer city, used as a destination proxy. |
| Dates | Date | Continuous calendar date for the observed order period. |
| Dates | Year | Calendar year. |
| Dates | Quarter | Calendar quarter. |
| Dates | Month | Order month in YYYY-MM format. |
| Dates | MonthName | Calendar month abbreviation. |
| Dates | MonthNumber | Calendar month number. |
| Employees | EmployeeID | Employee identifier. |
| Employees | WarehouseID | Warehouse identifier. |
| Inventory | WarehouseID | Warehouse identifier. |
| Inventory | ProductID | Product identifier. |
| Inventory | Stock | Supplied stock quantity, aggregated across movement records according to official guidance. |
| Inventory | MovementRows | Number of retained movement records in a warehouse-product aggregate. |
| Inventory | WarehouseProductKey | Warehouse and product identifiers combined for an observed stock pair. |
| Inventory | LowStock100 | One when an observed aggregate is below the illustrative 100-unit threshold. |
| InventoryMovements | InventoryRecordID | Source-row-based inventory movement identifier. Repeated source rows remain separate. |
| InventoryMovements | WarehouseID | Warehouse identifier. |
| InventoryMovements | ProductID | Product identifier. |
| InventoryMovements | Stock | Supplied stock quantity, aggregated across movement records according to official guidance. |
| OrderItems | OrderItemID | Order-line identifier. |
| OrderItems | OrderID | Order identifier. |
| OrderItems | ProductID | Product identifier. |
| OrderItems | Quantity | Units ordered on the line. |
| OrderItems | Category | Product category. |
| OrderItems | UnitPrice | Supplied catalogue unit price. Currency, realised sale price and cost are unspecified. |
| OrderItems | LineValue | Quantity multiplied by supplied catalogue UnitPrice. |
| OrderItems | CustomerID | Customer identifier. |
| OrderItems | OrderDate | Order date parsed using month/day/year. |
| OrderItems | Month | Order month in YYYY-MM format. |
| OrderItems | Status | Recorded order lifecycle status, or recorded delivery status in the original delivery table. |
| OrderItems | City | Customer city, used as a destination proxy. |
| OrderItems | HasReturn | One when the order has at least one return event. |
| OrderItems | DeliveredValue | Catalogue-priced line or order value for Delivered status orders, otherwise zero. |
| OrderItems | DeliveredUnits | Line quantity for Delivered status orders, otherwise zero. |
| Orders | OrderID | Order identifier. |
| Orders | CustomerID | Customer identifier. |
| Orders | OrderDate | Order date parsed using month/day/year. |
| Orders | Status | Recorded order lifecycle status, or recorded delivery status in the original delivery table. |
| Orders | Month | Order month in YYYY-MM format. |
| Orders | Quarter | Calendar quarter. |
| Orders | Year | Calendar year. |
| Orders | OrderValue | Sum of catalogue-priced line values for an order. Unpriced orders are identified by HasItems. |
| Orders | Units | Sum of ordered line quantities. |
| Orders | ItemRows | Number of item rows for an order. |
| Orders | HasItems | One when the order has item rows, otherwise zero. |
| Orders | DeliveredValue | Catalogue-priced line or order value for Delivered status orders, otherwise zero. |
| Orders | ReturnCount | Number of return events associated with the order. |
| Orders | HasReturn | One when the order has at least one return event. |
| Orders | City | Customer city, used as a destination proxy. |
| Orders | IsFirstObservedOrder | One for the earliest observed order per customer, breaking date ties by OrderID. |
| Products | ProductID | Product identifier. |
| Products | Category | Product category. |
| Products | UnitPrice | Supplied catalogue unit price. Currency, realised sale price and cost are unspecified. |
| Returns | ReturnID | Return-event identifier. |
| Returns | OrderID | Order identifier. |
| Returns | Reason | Recorded return reason. |
| Shipments | ShipmentID | Shipment identifier. |
| Shipments | OrderID | Order identifier. |
| Shipments | WarehouseID | Warehouse identifier. |
| Shipments | ShipmentDelayDays | Delay field from Shipments, preserved separately from the delivery table. |
| Shipments | DeliveryStatus | Source delivery label. On Time corresponds to 0-2 delay days in all supplied records. |
| Shipments | DelayDays | Recorded delay in days. Both source copies agree. |
| Shipments | CustomerID | Customer identifier. |
| Shipments | OrderDate | Order date parsed using month/day/year. |
| Shipments | Month | Order month in YYYY-MM format. |
| Shipments | Status | Recorded order lifecycle status, or recorded delivery status in the original delivery table. |
| Shipments | City | Customer city, used as a destination proxy. |
| Shipments | RecordedOnTime | One when DeliveryStatus is On Time. |
| Shipments | PositiveDelay | One when recorded delay exceeds zero. |
| Shipments | DelayBand | Recorded delay grouped as zero, 1-2, 3-4 or 5-7 days. |
| Shipments | WarehouseLocation | Warehouse city, kept separate from customer city. |
| Suppliers | SupplierID | Standalone supplier identifier. No product or shipment relationship is supplied. |
| Suppliers | SupplierName | Provided supplier label. |
| Warehouses | WarehouseID | Warehouse identifier. |
| Warehouses | Location | Warehouse city. |
