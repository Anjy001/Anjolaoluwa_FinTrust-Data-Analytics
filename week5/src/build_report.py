"""Create the SwiftLog executive report, analytical figures and documentation."""
from pathlib import Path
from xml.sax.saxutils import escape
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import findfont, FontProperties
import reportlab
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'Report';IMAGES=ROOT/'Images';REF=ROOT/'References'
for p in [REPORT,IMAGES,REF]:p.mkdir(exist_ok=True)
m=json.loads((ROOT/'Analysis/Summary.json').read_text())
monthly=pd.read_csv(ROOT/'Analysis/Monthly.csv')
regions=pd.read_csv(ROOT/'Analysis/RegionSummary.csv')
warehouses=pd.read_csv(ROOT/'Analysis/WarehouseSummary.csv')
products=pd.read_csv(ROOT/'Analysis/ProductSummary.csv')
customers=pd.read_csv(ROOT/'Analysis/CustomerSummary.csv')
reasons=pd.read_csv(ROOT/'Analysis/ReturnReasons.csv')
navy='#142F43';teal='#137D7B';gold='#CE8C29';red='#BF4A3C';muted='#587082'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.labelcolor':muted,'xtick.color':muted,'ytick.color':muted,'axes.edgecolor':'#D8E3E8','figure.facecolor':'white','axes.titleweight':'bold'})

def chart(name,labels,values,title,xlabel='',horizontal=False,colour=teal,pct=False):
    fig,ax=plt.subplots(figsize=(8.5,3.5))
    labels=[str(v) for v in labels]
    if horizontal:
        ax.barh(labels,values,color=colour,height=.6);ax.invert_yaxis();ax.set_xlabel(xlabel)
        if pct:ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    else:
        ax.bar(labels,values,color=colour,width=.6);ax.set_ylabel(xlabel)
    ax.set_title(title,loc='left',fontsize=13,pad=12);ax.grid(axis='x' if horizontal else 'y',color='#e7eef1',linewidth=.6);ax.set_axisbelow(True)
    fig.tight_layout();fig.savefig(IMAGES/(name+'.png'),dpi=180,bbox_inches='tight');plt.close(fig)

chart('Monthly_Orders',monthly.Month.str[5:],monthly.Orders,'Monthly order volume','Orders')
chart('Monthly_Daily_Orders',monthly.Month.str[5:],monthly.OrdersPerObservedDay,'Orders per observed calendar day','Orders per day')
chart('Delivery_by_City',regions.City,regions.DelayedRate,'Recorded delayed shipment rate by customer city','Delayed share',True,red,True)
chart('Warehouse_OnTime',warehouses.WarehouseID,warehouses.RecordedOnTimeRate,'Recorded on-time delivery by warehouse','On-time share',True,teal,True)
chart('Warehouse_Inventory',warehouses.WarehouseID,warehouses.AggregateStock,'Aggregate inventory quantity by warehouse','Quantity proxy',True)
chart('Warehouse_Workload',warehouses.WarehouseID,warehouses.ShipmentsPerEmployee,'Shipment workload per employee','Shipments per employee',True,gold)
top_p=products.sort_values('DeliveredValue',ascending=False).head(8)
chart('Top_Products',top_p.ProductID,top_p.DeliveredValue,'Products with highest delivered catalogue value','Catalogue price units',True)
top_c=customers.sort_values('DeliveredValue',ascending=False).head(8)
chart('Top_Customers',top_c.CustomerID,top_c.DeliveredValue,'Customers with highest delivered catalogue value','Catalogue price units',True)
chart('Return_Reasons',reasons.Reason,reasons.ReturnEvents,'Return events by recorded reason','Return events',True,gold)

recommendations=[
 ('Delivery optimisation','Kano has 845 delayed records among 1,287 shipments (65.66%), compared with 61.04% in Lagos. Review Kano routes, dispatch cut-offs and last-mile handoffs, then test a targeted service intervention.','Logistics lead','Recorded delayed rate by city, with a confirmed SLA.'),
 ('Logistics optimisation','W05 has a 32.04% recorded on-time rate, while W01 reaches 41.27%. Compare route mix and dispatch processes before transferring operating practices between sites.','Operations manager','Warehouse on-time rate adjusted for route mix.'),
 ('Inventory management','264 of 2,455 observed warehouse-product aggregates are below the illustrative 100-unit threshold. Validate current balances and demand before setting product-specific replenishment points.','Inventory manager','Validated low-stock exceptions and stockout events.'),
 ('Warehouse efficiency','Shipment workload ranges from 19.93 per employee at W13 to 37.78 at W14. Pilot cross-training or shift balancing after collecting handling hours and service workload.','Warehouse manager','Shipments per handling hour and service quality.'),
 ('Supplier improvement','All 150 suppliers lack a product or shipment relationship. Capture supplier-to-product and purchase-order mappings, receipt dates, promised dates and defect outcomes before introducing a supplier scorecard.','Procurement lead','Supplier mapping coverage and receipt performance.'),
 ('Customer retention','951 of 991 active customers place more than one observed order. Prioritise delivery communications for repeat purchasers and measure subsequent purchasing with cohorts rather than treating repeat activity as retention.','Customer service lead','Cohort repeat purchasing and delivery complaints.'),
 ('Operational cost control','1,626 orders carry Cancelled status, yet every order has a shipment record. Reconcile lifecycle timing and enforce cancellation checks before release to picking or dispatch. Cost savings require a measured handling-cost baseline.','Fulfilment manager','Verified avoidable dispatches and handling cost.'),
 ('Return reduction','Late Delivery accounts for 185 of 500 return events (37.0%), followed by Wrong Item at 163 (32.6%). Combine delay communication with item scans and packing verification.','Quality and service leads','Return reasons and confirmed item-level return rates.'),
 ('Performance monitoring','236 orders have no item records, and 315 of 473 return-associated orders are currently Pending or Cancelled. Introduce completeness checks and timestamped status history. Retain all inventory movement records.','Data owner','Order-item coverage and lifecycle reconciliation.'),
 ('Business growth','P203 contributes 85,977.99 catalogue price units of delivered value, and customer C0223 contributes 57,592.36. Protect availability for high-value demand and test relevant offers only after checking margin and service capacity.','Commercial lead','Delivered value, contribution margin and service performance.')
]

pdfmetrics.registerFont(TTFont('DejaVu',findfont(FontProperties(family='DejaVu Sans',weight='normal'))))
pdfmetrics.registerFont(TTFont('DejaVuBold',findfont(FontProperties(family='DejaVu Sans',weight='bold'))))
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyD',fontName='DejaVu',fontSize=9.7,leading=13.7,spaceAfter=8,textColor=colors.HexColor(navy)))
styles.add(ParagraphStyle(name='SmallD',fontName='DejaVu',fontSize=8.3,leading=11,spaceAfter=6,textColor=colors.HexColor(muted)))
styles.add(ParagraphStyle(name='TitleD',fontName='DejaVuBold',fontSize=23,leading=28,spaceAfter=12,textColor=colors.HexColor(navy)))
styles.add(ParagraphStyle(name='HeadingD',fontName='DejaVuBold',fontSize=14,leading=18,spaceAfter=9,textColor=colors.HexColor(teal)))
styles.add(ParagraphStyle(name='TableD',fontName='DejaVu',fontSize=8.5,leading=11,textColor=colors.HexColor(navy)))

def p(text,style='BodyD'):return Paragraph(escape(str(text)),styles[style])
def heading(text):return p(text,'HeadingD')
def table(headers,rows,widths):
    cells=[[p(x,'TableD') for x in headers]]+[[p(x,'TableD') for x in row] for row in rows]
    t=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E5F1F0')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),6),('LINEBELOW',(0,0),(-1,0),.7,colors.HexColor(teal)),('LINEBELOW',(0,1),(-1,-1),.35,colors.HexColor('#D8E3E8'))]))
    return t
def image(name,width=510,height=185):return Image(str(IMAGES/(name+'.png')),width=width,height=height,kind='proportional')
def footer(c,doc):
    c.setStrokeColor(colors.HexColor('#D8E3E8'));c.line(42,40,A4[0]-42,40)
    c.setFont('DejaVu',7.3);c.setFillColor(colors.HexColor(muted));c.drawString(42,27,'SwiftLog executive business intelligence | 1 Jan - 8 Sep 2026');c.drawRightString(A4[0]-42,27,str(doc.page))

story=[p('SwiftLog Logistics','TitleD'),heading('Executive Business Intelligence Report'),
 p('Iyiola Anjolaoluwa Emmanuel | AnalystLab Africa | Data Analytics | Week 5','SmallD'),
 p('The analysis integrates customer, order, product, inventory, warehouse, shipment, delivery, employee and return records to assess logistics service and commercial activity. The supplied history covers 1 January to 8 September 2026.'),
 p('Service reliability requires management attention. The recorded on-time rate is 36.28%, and the mean recorded delay is 3.57 days. Kano has the highest delayed share among the four customer cities. Warehouse workload and recorded service performance vary, although the data does not establish the causes.'),
 table(['Indicator','Result','Interpretation'],[
  ['Orders / active customers','5,000 / 991','1,000 customers appear in the customer catalogue.'],
  ['Delivered catalogue value','7,107,470.53','Estimated from supplied catalogue prices. Currency is unspecified.'],
  ['Priced delivered AOV','4,504.10','1,578 priced delivered orders.'],
  ['Recorded on-time rate','36.28%','1,814 of 5,000 shipment records.'],
  ['Return-associated order rate','9.46%','473 distinct orders, from 500 return events.'],
  ['Aggregate stock quantity','1,007,764','Undated movement aggregate, rather than an on-hand balance.']],[127,117,266]),Spacer(1,11),
 heading('Data preparation and reconciliation'),
 p('All 11 source datasets and the supplied dictionary were inspected. Text fields were trimmed, identifiers and relationships were checked, and dates were parsed explicitly as month/day/year. No source values were missing. Joins preserve order-item and shipment grain. All 4,000 inventory records remain in the movement table, including three identical rows, following the official treatment of repeated inventory records.'),
 p('The reporting pipeline passes 43 analytical checks. Twelve SQL calculations independently reconcile headline measures to pandas. Power Query import partitions apply explicit types and text transformations, with date fields and conditional stock fields. The Power BI model contains 14 tables and 12 relationships.','SmallD'),
 PageBreak(),heading('Demand, customers and product value'),image('Monthly_Orders',height=195),
 p('August records the largest monthly order count: 654, with 997,020.90 catalogue price units of delivered value. April has the highest daily activity among complete months at 21.27 orders per day. August averages 21.10. September contains only eight days and averages 19.25 orders per observed day, so its 154 orders cannot be compared directly with a complete month.'),
 table(['Leading product','Category','Delivered catalogue value'],[[r.ProductID,r.Category,f'{r.DeliveredValue:,.2f}'] for r in top_p.head(4).itertuples()],[135,150,225]),Spacer(1,10),
 p('Product P203 leads delivered value at 85,977.99, followed by P085 at 83,844.00. These are catalogue-priced values for Delivered orders. Neither recognised revenue nor profit can be inferred because actual selling prices, currency, discounts, settlement and costs are absent.'),
 p('Customer C0223, in Kano, has the highest delivered catalogue value at 57,592.36 across eight observed orders. There are 991 active customers, of whom 951 place at least two orders. The 95.96% repeat-customer indicator describes activity within the supplied history. It does not establish a retention rate or a customer acquisition trend.'),
 p('236 orders have no order-item records. Eighty of these have Delivered status. Their value remains unpriced. The average order value denominator includes only the 1,578 delivered orders with item records, avoiding an implicit zero-value assumption for the missing baskets.','SmallD'),
 PageBreak(),heading('Delivery, warehouse workload and inventory'),
 table(['Customer city','Shipments','Delayed','Delayed share'],[[r.City,f'{r.Shipments:,}',f'{r.Delayed:,}',f'{r.DelayedRate:.2%}'] for r in regions.itertuples()],[145,110,110,145]),Spacer(1,10),
 p('Kano has the highest delayed share at 65.66% and the largest delayed count at 845. Lagos has the lowest share at 61.04%. Customer city serves as the available destination proxy. The source does not contain shipment destination, route distance or carrier data.'),
 p('The source consistently labels recorded delays of 0-2 days as On Time and 3-7 days as Delayed. The recorded on-time rate is therefore 36.28%, while only 12.22% of shipments have zero delay. The 3.57-day average is delay, not total delivery duration. Dispatch, arrival and promised timestamps are absent.'),
 table(['Warehouse','On-time rate','Shipments / employee','Aggregate stock'],[
  ['W01','41.27%','22.13','56,539'],['W05','32.04%','23.86','63,125'],
  ['W13','35.13%','19.93','63,211'],['W14','38.53%','37.78','69,883']],[100,120,155,135]),Spacer(1,10),
 p('W01 has the highest recorded on-time rate, while W05 has the lowest. W14 has the highest shipment workload per employee, and W13 the lowest. These measures describe service and workload. They cannot establish cost efficiency without handling hours, route mix, operating costs and service complexity.'),
 p('Inventory aggregates cover 2,455 warehouse-product pairs. Under an illustrative threshold of 100 units, 264 pairs (10.75%) are below the threshold. The other 1,295 possible warehouse-product combinations are unobserved and remain unknown. W12 has the largest aggregate stock quantity at 77,517. The quantities have no date and do not measure current stock or capacity utilisation.'),
 PageBreak(),heading('Returns and measurement boundaries'),
 image('Return_Reasons',height=180),
 p('The source records 500 return events across 473 orders. Late Delivery contributes 185 events (37.0%), Wrong Item contributes 163 (32.6%), and Damaged contributes 152 (30.4%). Multiple events can belong to one order.'),
 p('P032 has the highest observed return-associated order share: 10 of its 47 orders (21.28%) carry a return record. The returned product and quantity are absent. This is a basket association and cannot be interpreted as P032 having the highest actual product return rate.'),
 heading('Assumptions and Data Limitations'),
 table(['Area','Definition or limitation'],[
 ['Value','Quantity multiplied by current catalogue UnitPrice. Delivered status defines the reported value subset. Currency, realised selling prices, cost and profit are unavailable.'],
 ['Dates and status','OrderDate defines shipment and return cohorts. It does not supply dispatch or return dates. 315 return-associated orders currently have Pending or Cancelled status. Without lifecycle timestamps, timing cannot be reconciled.'],
 ['Inventory and capacity','Official guidance treats repeated rows as stock movements and directs aggregation. Dated opening/closing balances and capacity are absent. Standard inventory turnover and physical utilisation are not estimable.'],
 ['Supplier performance','150 suppliers form a standalone reference table. No supplier-to-product, purchase order or shipment relationship exists. No supplier ranking or numerical performance score is inferred.'],
 ['Retention and geography','Repeat purchasing is an observation-window indicator. Customer city is a destination proxy. First observed order is not a verified acquisition date.']],[110,400]),
 p('The supplied data dictionary is a CSV containing filenames without field definitions. Project field definitions and KPI assumptions are recorded in References/Data_Dictionary.md and Analysis/KPI_Definitions.csv. Source files remain unchanged.','SmallD'),
 PageBreak(),heading('Business recommendations')]
for n,(title,evidence,owner,kpi) in enumerate(recommendations,1):
    story.append(p(f'{n}. {title}. {evidence} Owner: {owner}.','BodyD'))
story += [heading('Expected business impact'),p('At the observed shipment volume, each percentage point of recorded on-time improvement corresponds to 50 shipments. A five-percentage-point service scenario would therefore represent 250 shipments. This is scenario arithmetic, rather than a forecast or an achieved benefit. Financial savings require verified unit costs and operational measurement.'),
 p('The results support targeted delivery reviews, controlled inventory decisions and stronger lifecycle data. A supplier score, true stock turnover, physical capacity utilisation and recognised revenue remain outside the evidence provided.'),
 p('Sources: AnalystLab Africa Week 5 brief and original SwiftLog datasets; official clarification dated 13 October 2026. Source links and transformation definitions are retained in References/Sources.md.','SmallD')]
doc=SimpleDocTemplate(str(REPORT/'Executive_BI_Report.pdf'),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=52,title='SwiftLog Executive Business Intelligence Report',author='Iyiola Anjolaoluwa Emmanuel')
doc.build(story,onFirstPage=footer,onLaterPages=footer)

preview_pages=[
 ('Executive overview',['Monthly_Orders','Delivery_by_City'],['5,000 orders; delivered catalogue value 7,107,470.53.','Recorded on-time rate 36.28%; return-associated order rate 9.46%.']),
 ('Customer analytics',['Top_Customers','Monthly_Daily_Orders'],['991 active customers; 951 repeat customers (95.96%).','Customer city and first observed orders describe the supplied history.']),
 ('Inventory and warehouses',['Warehouse_Inventory','Warehouse_Workload'],['1,007,764 aggregate stock units; 264 observed pairs below the illustrative threshold.','Workload and stock quantity are proxies. Capacity and current balances are unavailable.']),
 ('Shipment and delivery',['Delivery_by_City','Warehouse_OnTime'],['3,186 recorded delayed shipments; average recorded delay 3.57 days.','Recorded On Time status corresponds to 0-2 delay days. Transit duration is unavailable.']),
 ('Suppliers and products',['Top_Products','Return_Reasons'],['P203 leads delivered catalogue value at 85,977.99.','Suppliers remain a standalone catalogue. Returns are identified at order level.'])]
c=canvas.Canvas(str(REPORT/'Dashboard_Preview.pdf'),pagesize=landscape(A4))
pw,ph=landscape(A4)
for n,(title,charts,notes) in enumerate(preview_pages,1):
    c.setFillColor(colors.HexColor(navy));c.setFont('DejaVuBold',20);c.drawString(35,ph-43,'SwiftLog - '+title)
    c.setFont('DejaVu',9);c.setFillColor(colors.HexColor(muted));c.drawString(35,ph-62,'Analytical page preview | supplied data, 1 January - 8 September 2026')
    for j,name in enumerate(charts):c.drawImage(str(IMAGES/(name+'.png')),35+j*390,ph-307,width=380,height=208,preserveAspectRatio=True,anchor='c')
    c.setFillColor(colors.HexColor(navy));c.setFont('DejaVu',11)
    for j,line in enumerate(notes):c.drawString(40,ph-350-j*24,line)
    c.setFillColor(colors.HexColor(muted));c.setFont('DejaVu',8.5)
    c.drawString(40,48,'Analytical previews. Interactive report: Dashboard/SwiftLog_Dashboard.html. Power BI source: SwiftLog_Analytics.pbip.')
    c.drawRightString(pw-35,25,str(n));c.showPage()
c.save()

definitions={
 'CustomerID':'Customer identifier.','CustomerName':'Provided customer label.','City':'Customer city, used as a destination proxy.',
 'OrderID':'Order identifier.','OrderDate':'Order date parsed using month/day/year.','Status':'Recorded order lifecycle status, or recorded delivery status in the original delivery table.',
 'OrderItemID':'Order-line identifier.','ProductID':'Product identifier.','Quantity':'Units ordered on the line.','Category':'Product category.',
 'UnitPrice':'Supplied catalogue unit price. Currency, realised sale price and cost are unspecified.',
 'SupplierID':'Standalone supplier identifier. No product or shipment relationship is supplied.','SupplierName':'Provided supplier label.',
 'WarehouseID':'Warehouse identifier.','Location':'Warehouse city.','Stock':'Supplied stock quantity, aggregated across movement records according to official guidance.',
 'ShipmentID':'Shipment identifier.','DelayDays':'Recorded delay in days. Both source copies agree.','EmployeeID':'Employee identifier.',
 'ReturnID':'Return-event identifier.','Reason':'Recorded return reason.','Month':'Order month in YYYY-MM format.','Year':'Calendar year.','Quarter':'Calendar quarter.',
 'OrderValue':'Sum of catalogue-priced line values for an order. Unpriced orders are identified by HasItems.','Units':'Sum of ordered line quantities.',
 'ItemRows':'Number of item rows for an order.','HasItems':'One when the order has item rows, otherwise zero.',
 'DeliveredValue':'Catalogue-priced line or order value for Delivered status orders, otherwise zero.',
 'ReturnCount':'Number of return events associated with the order.','HasReturn':'One when the order has at least one return event.',
 'IsFirstObservedOrder':'One for the earliest observed order per customer, breaking date ties by OrderID.',
 'LineValue':'Quantity multiplied by supplied catalogue UnitPrice.','DeliveredUnits':'Line quantity for Delivered status orders, otherwise zero.',
 'ShipmentDelayDays':'Delay field from Shipments, preserved separately from the delivery table.',
 'DeliveryStatus':'Source delivery label. On Time corresponds to 0-2 delay days in all supplied records.',
 'RecordedOnTime':'One when DeliveryStatus is On Time.','PositiveDelay':'One when recorded delay exceeds zero.',
 'DelayBand':'Recorded delay grouped as zero, 1-2, 3-4 or 5-7 days.','WarehouseLocation':'Warehouse city, kept separate from customer city.',
 'InventoryRecordID':'Source-row-based inventory movement identifier. Repeated source rows remain separate.',
 'MovementRows':'Number of retained movement records in a warehouse-product aggregate.',
 'WarehouseProductKey':'Warehouse and product identifiers combined for an observed stock pair.',
 'LowStock100':'One when an observed aggregate is below the illustrative 100-unit threshold.',
 'Date':'Continuous calendar date for the observed order period.','MonthName':'Calendar month abbreviation.','MonthNumber':'Calendar month number.'}
dictionary=['# SwiftLog data dictionary','', 'Definitions follow the supplied fields and the official project clarification. Business meanings not explicitly supplied are analytical assumptions. Original tables retain their source fields.','', '| Reporting table | Field | Definition |','| --- | --- | --- |']
for file in sorted((ROOT/'Data/Processed').glob('*.csv')):
    for col in pd.read_csv(file,nrows=0).columns:
        dictionary.append('| '+file.stem+' | '+col+' | '+definitions[col]+' |')
(REF/'Data_Dictionary.md').write_text('\n'.join(dictionary)+'\n')
source_ids=[('SwiftLog_Customers.csv','1A6iVLA5mbhB2QPciamyc2d6MDu4g6A2S'),('SwiftLog_Orders.csv','1hAnRVbuuUwSNT-NHBiqcTauforoFXaB5'),('SwiftLog_Order_Items.csv','1COJIBfnQS7mZWDwUtAtguy09X2-qKKuL'),('SwiftLog_Products.csv','1bUS1pKdkO_4zRJoHTVxq9OtLjXh3_r-0'),('SwiftLog_Suppliers.csv','1TCgyfks3o0tIiL1MFGQ_m95v_a1JIYae'),('SwiftLog_Warehouses.csv','1rSwvf5pvvHfpg1grCY0sOed2vGbGvoWq'),('SwiftLog_Inventory.csv','1i4__uIP3Sjig3fPbI2VKfs3gNx92t5zP'),('SwiftLog_Shipments.csv','1weV42n20HK9AyQFcKYHzfe4ewEwzjqYm'),('SwiftLog_Delivery_Performance.csv','1xmzlt_NftK75kiMQwUlDTj5pkp0x8sQ4'),('SwiftLog_Employees.csv','11Um3ztCcaNN6ufwKyylz8wcEp90RMm43'),('SwiftLog_Returns.csv','12hP9-papZuhgOzmgESlbW0i36Y3LzvHW'),('SwiftLog_Data_Dictionary.csv','1LE02Re4YTc3sjku6puan-Nj9qw7DTMrC')]
sources=['# Sources and methodology references','','- [AnalystLab Africa Week 5 official brief](https://drive.google.com/file/d/19y9ExoOOp0uVa7wrhzQ12cqZ_7WznWxA/view). Data Analytics track.','- [Official dataset clarification, 13 October 2026](https://analystlabafrica.slack.com/archives/C0BUU946M60/p1791881712554999). Inventory movement aggregation, standalone suppliers, warehouse proxies and assumptions.','','## Original datasets','']
sources += ['- ['+name+'](https://drive.google.com/file/d/'+id+'/view)' for name,id in source_ids]
sources += ['','## Technical references','','- [Microsoft Power BI project format](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-overview).','- [Power BI report definition format](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report).','- [Power BI semantic model format](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-dataset).','- [Microsoft public report JSON schemas](https://github.com/microsoft/json-schemas/tree/main/fabric/item/report/definition).','','Analysis/Source_Manifest.csv records source row counts and SHA-256 hashes. Analysis/Transformations.csv records text transformations. Analysis/Validation_Results.csv and SQL_Reconciliation.csv contain executed analytical checks.']
(REF/'Sources.md').write_text('\n'.join(sources)+'\n')
(ROOT/'requirements.txt').write_text(f'pandas=={pd.__version__}\nnumpy=={np.__version__}\nmatplotlib=={matplotlib.__version__}\nreportlab=={reportlab.Version}\n')
content={'recommendations':[{'title':t,'evidence':e,'owner':o,'measure':k} for t,e,o,k in recommendations],
 'metrics':m,'monthly':monthly.to_dict('records'),'regions':regions.to_dict('records'),'warehouses':warehouses.to_dict('records'),
 'top_products':top_p.to_dict('records'),'top_customers':top_c.to_dict('records'),'return_reasons':reasons.to_dict('records')}
(ROOT/'Analysis/Presentation_Data.json').write_text(json.dumps(content,indent=2))
print(json.dumps({'report':str(REPORT/'Executive_BI_Report.pdf'),'preview':str(REPORT/'Dashboard_Preview.pdf'),'charts':9,'recommendations':len(recommendations)}))
