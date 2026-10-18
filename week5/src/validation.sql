-- Orders
SELECT COUNT(*) FROM Orders;

-- DeliveredOrders
SELECT COUNT(*) FROM Orders WHERE Status='Delivered';

-- ReturnedOrders
SELECT COUNT(DISTINCT OrderID) FROM Returns;

-- RecordedOnTime
SELECT COUNT(*) FROM Delivery_Performance WHERE Status='On Time';

-- AverageDelayDays
SELECT AVG(DelayDays) FROM Delivery_Performance;

-- AggregateInventoryQuantity
SELECT SUM(Stock) FROM Inventory;

-- DeliveredOrderValue
SELECT SUM(i.Quantity*p.UnitPrice) FROM Order_Items i JOIN Products p USING(ProductID) JOIN Orders o USING(OrderID) WHERE o.Status='Delivered';

-- PricedDeliveredOrders
SELECT COUNT(DISTINCT o.OrderID) FROM Orders o JOIN Order_Items i USING(OrderID) WHERE o.Status='Delivered';

-- AllOrderValue
SELECT SUM(i.Quantity*p.UnitPrice) FROM Order_Items i JOIN Products p USING(ProductID);

-- DeliveredUnits
SELECT SUM(i.Quantity) FROM Order_Items i JOIN Orders o USING(OrderID) WHERE o.Status='Delivered';

-- ActiveCustomers
SELECT COUNT(DISTINCT CustomerID) FROM Orders;

-- OrdersWithoutItems
SELECT COUNT(*) FROM Orders o WHERE NOT EXISTS (SELECT 1 FROM Order_Items i WHERE i.OrderID=o.OrderID);