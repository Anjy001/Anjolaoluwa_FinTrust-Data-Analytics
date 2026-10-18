"""Prepare and reconcile the SwiftLog logistics reporting dataset."""
from pathlib import Path
import hashlib
import json
import platform
import sqlite3

import numpy as np
import pandas as pd


def run_analysis(root=None):
    root = Path(root) if root else Path(__file__).resolve().parents[1]
    original = root / 'Data' / 'Original_Datasets'
    processed = root / 'Data' / 'Processed'
    outputs = root / 'Analysis'
    processed.mkdir(parents=True, exist_ok=True)
    outputs.mkdir(exist_ok=True)
    tables = {}
    profile = []
    checks = []
    transformations = []
    source_files = []

    def check(name, passed, observed):
        checks.append({'Check': name, 'Passed': bool(passed), 'Observed': str(observed)})
        if not passed:
            raise ValueError(f'{name}: {observed}')

    for path in sorted(original.glob('SwiftLog_*.csv')):
        name = path.stem.replace('SwiftLog_', '')
        frame = pd.read_csv(path)
        source_files.append({'File': path.name, 'Rows': len(frame),
                             'SHA256': hashlib.sha256(path.read_bytes()).hexdigest()})
        for column in frame.columns:
            profile.append({'Table': name, 'Column': column, 'Type': str(frame[column].dtype),
                            'Rows': len(frame), 'Missing': int(frame[column].isna().sum()),
                            'Distinct': int(frame[column].nunique())})
            if frame[column].dtype == 'object':
                cleaned = frame[column].str.strip()
                transformations.append({'Table': name, 'Field': column,
                                        'Transformation': 'Trim outer whitespace',
                                        'ChangedRows': int(frame[column].ne(cleaned).sum())})
                frame[column] = cleaned
        tables[name] = frame

    customers = tables['Customers'].copy()
    orders = tables['Orders'].copy()
    items = tables['Order_Items'].copy()
    products = tables['Products'].copy()
    shipments = tables['Shipments'].copy()
    delivery = tables['Delivery_Performance'].copy()
    returns = tables['Returns'].copy()
    inventory_moves = tables['Inventory'].copy()
    warehouses = tables['Warehouses'].copy()
    employees = tables['Employees'].copy()
    suppliers = tables['Suppliers'].copy()

    for name, key in [('Customers','CustomerID'), ('Orders','OrderID'),
                      ('Order_Items','OrderItemID'), ('Products','ProductID'),
                      ('Shipments','ShipmentID'), ('Delivery_Performance','ShipmentID'),
                      ('Returns','ReturnID'), ('Warehouses','WarehouseID'),
                      ('Employees','EmployeeID'), ('Suppliers','SupplierID')]:
        f = tables[name]
        check(f'{name} primary key', f[key].notna().all() and f[key].is_unique, len(f))
    for child, foreign, parent, primary in [
        ('Orders','CustomerID','Customers','CustomerID'),
        ('Order_Items','OrderID','Orders','OrderID'),
        ('Order_Items','ProductID','Products','ProductID'),
        ('Inventory','ProductID','Products','ProductID'),
        ('Inventory','WarehouseID','Warehouses','WarehouseID'),
        ('Shipments','OrderID','Orders','OrderID'),
        ('Shipments','WarehouseID','Warehouses','WarehouseID'),
        ('Delivery_Performance','ShipmentID','Shipments','ShipmentID'),
        ('Employees','WarehouseID','Warehouses','WarehouseID'),
        ('Returns','OrderID','Orders','OrderID')]:
        missing = int((~tables[child][foreign].isin(tables[parent][primary])).sum())
        check(f'{child}.{foreign} relationship', missing == 0, missing)

    orders['OrderDate'] = pd.to_datetime(orders['OrderDate'], format='%m/%d/%Y', errors='raise')
    orders['Month'] = orders['OrderDate'].dt.strftime('%Y-%m')
    orders['Quarter'] = 'Q' + orders['OrderDate'].dt.quarter.astype(str)
    orders['Year'] = orders['OrderDate'].dt.year
    items = items.merge(products, on='ProductID', how='left', validate='many_to_one')
    items['LineValue'] = (items['Quantity'] * items['UnitPrice']).round(2)
    item_totals = items.groupby('OrderID').agg(OrderValue=('LineValue','sum'),
                Units=('Quantity','sum'), ItemRows=('OrderItemID','size')).reset_index()
    orders = orders.merge(item_totals, on='OrderID', how='left', validate='one_to_one')
    orders['HasItems'] = orders['ItemRows'].notna().astype(int)
    for column in ['OrderValue','Units','ItemRows']:
        orders[column] = orders[column].fillna(0)
    orders['DeliveredValue'] = orders['OrderValue'].where(orders['Status'].eq('Delivered'), 0)
    return_counts = returns.groupby('OrderID').size().rename('ReturnCount')
    orders['ReturnCount'] = orders['OrderID'].map(return_counts).fillna(0).astype(int)
    orders['HasReturn'] = orders['ReturnCount'].gt(0).astype(int)
    orders = orders.merge(customers[['CustomerID','City']], on='CustomerID', validate='many_to_one')
    first_ids = orders.sort_values(['OrderDate','OrderID']).drop_duplicates('CustomerID')['OrderID']
    orders['IsFirstObservedOrder'] = orders['OrderID'].isin(first_ids).astype(int)
    items = items.merge(orders[['OrderID','CustomerID','OrderDate','Month','Status','City','HasReturn']],
                        on='OrderID', validate='many_to_one')
    items['DeliveredValue'] = items['LineValue'].where(items['Status'].eq('Delivered'), 0)
    items['DeliveredUnits'] = items['Quantity'].where(items['Status'].eq('Delivered'), 0)

    shipments = shipments.rename(columns={'DelayDays':'ShipmentDelayDays'})
    delivery = delivery.rename(columns={'Status':'DeliveryStatus','DelayDays':'DelayDays'})
    shipments = shipments.merge(delivery, on='ShipmentID', how='left', validate='one_to_one')
    shipments = shipments.merge(orders[['OrderID','CustomerID','OrderDate','Month','Status','City']],
                                on='OrderID', how='left', validate='many_to_one')
    shipments['RecordedOnTime'] = shipments['DeliveryStatus'].eq('On Time').astype(int)
    shipments['PositiveDelay'] = shipments['DelayDays'].gt(0).astype(int)
    shipments['DelayBand'] = pd.cut(shipments['DelayDays'], [-1,0,2,4,7],
                                      labels=['0 days','1-2 days','3-4 days','5-7 days']).astype(str)
    shipments = shipments.merge(warehouses.rename(columns={'Location':'WarehouseLocation'}),
                                 on='WarehouseID', validate='many_to_one')
    inventory_moves.insert(0, 'InventoryRecordID', [f'IM{i:05}' for i in range(1,len(inventory_moves)+1)])
    inventory = inventory_moves.groupby(['WarehouseID','ProductID'],as_index=False).agg(
        Stock=('Stock','sum'), MovementRows=('InventoryRecordID','size'))
    inventory['WarehouseProductKey'] = inventory['WarehouseID'] + '_' + inventory['ProductID']
    inventory['LowStock100'] = inventory['Stock'].lt(100).astype(int)

    monthly = orders.groupby('Month',as_index=False).agg(Orders=('OrderID','size'),
        DeliveredValue=('DeliveredValue','sum'), PricedOrders=('HasItems','sum'),
        FirstObservedCustomers=('IsFirstObservedOrder','sum'), ReturnedOrders=('HasReturn','sum'))
    monthly['ObservedDays'] = [len(pd.date_range(max(pd.Timestamp(m+'-01'), orders.OrderDate.min()),
        min(pd.Timestamp(m+'-01')+pd.offsets.MonthEnd(0),orders.OrderDate.max()))) for m in monthly.Month]
    monthly['OrdersPerObservedDay'] = monthly['Orders'] / monthly['ObservedDays']
    customer_summary = orders.groupby(['CustomerID','City'],as_index=False).agg(
        Orders=('OrderID','size'), DeliveredValue=('DeliveredValue','sum'),
        FirstOrder=('OrderDate','min'), LastOrder=('OrderDate','max'))
    product_summary = items.groupby(['ProductID','Category'],as_index=False).agg(
        DeliveredValue=('DeliveredValue','sum'), DeliveredUnits=('DeliveredUnits','sum'),
        OrderedUnits=('Quantity','sum'), ProductOrders=('OrderID','nunique'))
    associations = items[['OrderID','ProductID','HasReturn']].drop_duplicates(['OrderID','ProductID'])
    associated = associations.groupby('ProductID')['HasReturn'].sum().rename('ReturnAssociatedOrders')
    product_summary = product_summary.merge(associated,on='ProductID',validate='one_to_one')
    product_summary['ReturnAssociatedOrderRate'] = product_summary.ReturnAssociatedOrders / product_summary.ProductOrders
    warehouse_summary = shipments.groupby(['WarehouseID','WarehouseLocation'],as_index=False).agg(
        Shipments=('ShipmentID','size'), RecordedOnTime=('RecordedOnTime','sum'),
        AverageDelayDays=('DelayDays','mean'))
    warehouse_summary['RecordedOnTimeRate'] = warehouse_summary.RecordedOnTime / warehouse_summary.Shipments
    stock_summary = inventory.groupby('WarehouseID',as_index=False).agg(
        AggregateStock=('Stock','sum'), ObservedProducts=('ProductID','nunique'), LowStockPairs=('LowStock100','sum'))
    warehouse_summary = warehouse_summary.merge(stock_summary,on='WarehouseID',validate='one_to_one')
    headcount = employees.groupby('WarehouseID').size().rename('Employees')
    warehouse_summary['Employees'] = warehouse_summary.WarehouseID.map(headcount)
    warehouse_summary['ShipmentsPerEmployee'] = warehouse_summary.Shipments / warehouse_summary.Employees
    warehouse_summary['InventoryShareProxy'] = warehouse_summary.AggregateStock / inventory.Stock.sum()
    regions = shipments.groupby('City',as_index=False).agg(Shipments=('ShipmentID','size'),
        RecordedOnTime=('RecordedOnTime','sum'),AverageDelayDays=('DelayDays','mean'))
    regions['Delayed'] = regions.Shipments - regions.RecordedOnTime
    regions['DelayedRate'] = regions.Delayed / regions.Shipments
    reasons = returns.groupby('Reason',as_index=False).agg(ReturnEvents=('ReturnID','size'),
                                                           Orders=('OrderID','nunique'))
    dates = pd.DataFrame({'Date':pd.date_range(orders.OrderDate.min(),orders.OrderDate.max())})
    dates['Year']=dates.Date.dt.year
    dates['Quarter']='Q'+dates.Date.dt.quarter.astype(str)
    dates['Month']=dates.Date.dt.strftime('%Y-%m')
    dates['MonthName']=dates.Date.dt.strftime('%b')
    dates['MonthNumber']=dates.Date.dt.month

    delivered = orders.Status.eq('Delivered')
    priced_delivered = delivered & orders.HasItems.eq(1)
    metrics = {
        'Orders':len(orders),'Customers':len(customers),'ActiveCustomers':orders.CustomerID.nunique(),
        'Products':len(products),'Shipments':len(shipments),'DeliveredOrders':int(delivered.sum()),
        'PricedDeliveredOrders':int(priced_delivered.sum()),'PricedOrders':int(orders.HasItems.sum()),
        'OrdersWithoutItems':int(orders.HasItems.eq(0).sum()),
        'AllOrderValue':float(items.LineValue.sum()),'DeliveredOrderValue':float(orders.DeliveredValue.sum()),
        'AveragePricedDeliveredOrderValue':float(orders.loc[priced_delivered,'OrderValue'].mean()),
        'DeliveredUnits':int(items.DeliveredUnits.sum()),
        'RecordedOnTime':int(shipments.RecordedOnTime.sum()),
        'RecordedOnTimeRate':float(shipments.RecordedOnTime.mean()),
        'RecordedDelayed':int(shipments.DeliveryStatus.eq('Delayed').sum()),
        'PositiveDelayRate':float(shipments.PositiveDelay.mean()),
        'AverageDelayDays':float(shipments.DelayDays.mean()),
        'ZeroDelayShipments':int(shipments.DelayDays.eq(0).sum()),
        'ReturnEvents':len(returns),'ReturnedOrders':returns.OrderID.nunique(),
        'ReturnOrderRate':returns.OrderID.nunique()/len(orders),
        'ReturnOrdersNotDelivered':int(orders.loc[orders.HasReturn.eq(1),'Status'].ne('Delivered').sum()),
        'AggregateInventoryQuantity':int(inventory.Stock.sum()),'InventoryRows':len(inventory_moves),
        'ObservedWarehouseProductPairs':len(inventory),'UnobservedWarehouseProductPairs':len(warehouses)*len(products)-len(inventory),
        'RepeatedInventoryPairs':int(tables['Inventory'].duplicated(['WarehouseID','ProductID']).sum()),
        'ExactRepeatedInventoryRows':int(tables['Inventory'].duplicated().sum()),
        'LowStockPairs100':int(inventory.LowStock100.sum()),
        'Employees':len(employees),'Suppliers':len(suppliers),
        'RepeatActiveCustomers':int(customer_summary.Orders.gt(1).sum()),
        'RepeatCustomerRate':float(customer_summary.Orders.gt(1).mean()),
        'StartDate':str(orders.OrderDate.min().date()),'EndDate':str(orders.OrderDate.max().date()),
        'TopProduct':product_summary.sort_values(['DeliveredValue','ProductID'],ascending=[False,True]).iloc[0].to_dict(),
        'TopCustomer':customer_summary.sort_values(['DeliveredValue','CustomerID'],ascending=[False,True]).iloc[0].to_dict(),
        'PeakMonth':monthly.sort_values('Orders',ascending=False).iloc[0].to_dict(),
        'PythonVersion':platform.python_version(),'PandasVersion':pd.__version__,'NumPyVersion':np.__version__
    }
    check('Order-item joins preserve grain',len(items)==len(tables['Order_Items']),len(items))
    check('Shipment joins preserve grain',len(shipments)==len(tables['Shipments']),len(shipments))
    check('Inventory rows retained',len(inventory_moves)==len(tables['Inventory']),len(inventory_moves))
    check('Inventory aggregation preserves stock',inventory.Stock.sum()==inventory_moves.Stock.sum(),inventory.Stock.sum())
    check('Recorded on-time status follows 0-2 day rule',
          shipments.RecordedOnTime.eq(shipments.DelayDays.le(2).astype(int)).all(),'All shipment rows')
    check('Delivery delay copies agree',shipments.DelayDays.eq(shipments.ShipmentDelayDays).all(),'All shipment rows')
    check('Non-negative quantities and prices',items.Quantity.ge(0).all() and products.UnitPrice.ge(0).all(),'All item and product rows')
    check('Monthly order reconciliation',monthly.Orders.sum()==len(orders),int(monthly.Orders.sum()))
    check('Customer value reconciliation',np.isclose(customer_summary.DeliveredValue.sum(),metrics['DeliveredOrderValue'],rtol=0,atol=0.000001),customer_summary.DeliveredValue.sum())
    check('Product value reconciliation',np.isclose(product_summary.DeliveredValue.sum(),metrics['DeliveredOrderValue'],rtol=0,atol=0.000001),product_summary.DeliveredValue.sum())
    check('Return order rate bounded',0<=metrics['ReturnOrderRate']<=1,metrics['ReturnOrderRate'])

    with sqlite3.connect(':memory:') as connection:
        for name, frame in tables.items(): frame.to_sql(name,connection,index=False)
        queries = {
          'Orders': 'SELECT COUNT(*) FROM Orders',
          'DeliveredOrders': "SELECT COUNT(*) FROM Orders WHERE Status='Delivered'",
          'ReturnedOrders': 'SELECT COUNT(DISTINCT OrderID) FROM Returns',
          'RecordedOnTime': "SELECT COUNT(*) FROM Delivery_Performance WHERE Status='On Time'",
          'AverageDelayDays': 'SELECT AVG(DelayDays) FROM Delivery_Performance',
          'AggregateInventoryQuantity': 'SELECT SUM(Stock) FROM Inventory',
          'DeliveredOrderValue': "SELECT SUM(i.Quantity*p.UnitPrice) FROM Order_Items i JOIN Products p USING(ProductID) JOIN Orders o USING(OrderID) WHERE o.Status='Delivered'",
          'PricedDeliveredOrders': "SELECT COUNT(DISTINCT o.OrderID) FROM Orders o JOIN Order_Items i USING(OrderID) WHERE o.Status='Delivered'",
          'AllOrderValue': 'SELECT SUM(i.Quantity*p.UnitPrice) FROM Order_Items i JOIN Products p USING(ProductID)',
          'DeliveredUnits': "SELECT SUM(i.Quantity) FROM Order_Items i JOIN Orders o USING(OrderID) WHERE o.Status='Delivered'",
          'ActiveCustomers': 'SELECT COUNT(DISTINCT CustomerID) FROM Orders',
          'OrdersWithoutItems': 'SELECT COUNT(*) FROM Orders o WHERE NOT EXISTS (SELECT 1 FROM Order_Items i WHERE i.OrderID=o.OrderID)'
        }
        sql_records=[]
        for name, query in queries.items():
            value=connection.execute(query).fetchone()[0]
            check(f'SQL reconciliation: {name}',np.isclose(value,metrics[name],rtol=0,atol=0.000001),value)
            sql_records.append({'Metric':name,'SQLValue':value,'PandasValue':metrics[name]})
        (root/'src'/'validation.sql').write_text('\n\n'.join('-- '+name+'\n'+query+';' for name,query in queries.items()))
    prepared = {'Customers':customers,'Orders':orders,'OrderItems':items,'Products':products,
        'Suppliers':suppliers,'Warehouses':warehouses,'Inventory':inventory,'InventoryMovements':inventory_moves,
        'Shipments':shipments,'Employees':employees,'Returns':returns,'Dates':dates}
    summaries={'Monthly':monthly,'CustomerSummary':customer_summary,'ProductSummary':product_summary,
               'WarehouseSummary':warehouse_summary,'RegionSummary':regions,'ReturnReasons':reasons}
    for name,frame in prepared.items(): frame.to_csv(processed/(name+'.csv'),index=False,date_format='%Y-%m-%d')
    for name,frame in summaries.items(): frame.to_csv(outputs/(name+'.csv'),index=False,date_format='%Y-%m-%d')
    pd.DataFrame(profile).to_csv(outputs/'Source_Profile.csv',index=False)
    pd.DataFrame(checks).to_csv(outputs/'Validation_Results.csv',index=False)
    pd.DataFrame(sql_records).to_csv(outputs/'SQL_Reconciliation.csv',index=False)
    pd.DataFrame(transformations).to_csv(outputs/'Transformations.csv',index=False)
    pd.DataFrame(source_files).to_csv(outputs/'Source_Manifest.csv',index=False)
    metrics['ChecksPassed']=len(checks)
    (outputs/'Summary.json').write_text(json.dumps(metrics,indent=2,default=str))
    return {'metrics':metrics,'tables':prepared,'summaries':summaries,'checks':pd.DataFrame(checks)}


if __name__ == '__main__':
    result=run_analysis()
    print(json.dumps(result['metrics'],indent=2,default=str))
