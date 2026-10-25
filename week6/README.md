# HealthConnect Rwanda: Healthcare Operations and Performance Analytics

**Iyiola Anjolaoluwa Emmanuel · AnalystLab Africa · Week 6**

This project examines the supplied HealthConnect Rwanda healthcare scenario across patient demographics, clinical activity, finance, staffing, operations and patient experience. The analysis separates complete source totals from the smaller appointment-linked subsets used for facility and encounter-month comparisons.

## Findings

| Measure | Result | Basis |
| --- | ---: | --- |
| Registered patient records | 20,000 | Full supplied register |
| Available appointments | 5,000 | Supplied encounter extract |
| Patients observed in available appointments | 4,443 | Distinct linked patients |
| Billed amounts | RWF 9,309,401,961 | All 60,000 bills |
| Recorded payment amounts | RWF 8,389,454,556 | All payment records; receipt dates absent |
| Positive bill balances | RWF 919,947,405 | Payments aggregated once per bill |
| Mean feedback rating | 2.99 / 5 | All 21,064 responses |
| Ratings of 1–2 | 40.44% | Numeric ratings, independent of comment category |

Only 8.33% of bills and 8.34% of feedback responses link to available appointments. Facility identifiers disagree with the referenced department's facility in 94.88% of appointments. These gaps limit attribution; they do not justify deleting unmatched transactions or inventing missing encounters.

The separate RevenueSummary reports RWF 1,132,677,500 and 60,809 appointments. It is retained as an unreconciled source rather than relabelled as the transaction total. The full supplied 2026 scenario extends to 28 December and includes 864 appointments dated after 25 October 2026.

## Data and approach

Twenty-seven unchanged files contain 25 CSV extracts and two Excel workbooks. Thirty canonical tables retain the full 60,000-row diagnosis CSV; the workbook's 5,000 diagnosis rows are an identical subset. Facility workbook sheets duplicate the corresponding CSVs and are reconciled rather than appended.

Text fields were trimmed, numeric fields typed, and slash-form birth dates normalized to ISO dates. All supplied birth dates fall on 1 January; the recorded Age field is retained. Missing appointment references remain explicit. Payments are aggregated by BillingID before balances are calculated, preventing row multiplication.

Forty SQL questions were executed in SQLite, which the programme team explicitly permitted. The analysis passes 122 validation checks and twelve independent SQL-to-Python reconciliations. The SQL dump was restored and principal totals verified. Validation checks describe the executed data pipeline; they do not establish that the incomplete source extracts represent the full healthcare network.

## Project files

- `SQL/healthcare_analysis.sql`: all forty numbered analytical queries.
- `SQL/model_views.sql`: patient geography, staff, appointment and billing views.
- `Analysis/`: KPI definitions, aggregate outputs, source coverage and validation results.
- `Dashboard/HealthConnect_Dashboard.html`: six offline analytical views with filters, saved views, tooltips and aggregate CSV export.
- `Dashboard/Measures.dax` and `Measure_Definitions.csv`: 61 documented measures, including explicit unavailable measures.
- `Dashboard/PowerQuery_External.m`: typed model import definitions.
- `Report/Business_Insights_Report.pdf`: five-page report with findings, limitations and ten evidence-based recommendations required by the brief.
- `Report/Executive_Dashboard.pdf`: six analytical dashboard pages.
- `Presentation/Executive_Presentation.pptx`: fourteen slides with editable native charts and tables.
- `src/`: executable preparation, reporting, dashboard and Power BI source builders.
- `References/`: source manifest, data dictionary and geographic attribution.

The Power BI source builder produces a `.pbip` project, PBIR report definitions, six main pages, three support pages, twenty model tables and seventeen relationships. It includes date and residence hierarchies, DAX time intelligence, drill-through, report tooltips, navigation, bookmarks, a claims matrix and financial exploration definitions. The public `Dashboard/PowerBI_Report_Source.zip` contains the report and an external-data semantic model; its `DataFolder` parameter identifies the local `Data/Processed` folder after the pipeline runs. The private project includes embedded snapshots. These definitions are source-level artifacts; Power BI Desktop rendering and `.pbix` export are separate runtime operations.

## Reproducibility

Use Python 3.11 or later. Install the versions in `requirements.txt`. Obtain the original assignment files using `References/Source_Manifest.csv` and place them in `Data/Original` using the supplied filenames. The private project archive contains these inputs and the executed database.

```bash
python -m pip install -r requirements.txt
python src/analysis.py
python src/build_powerbi.py
python src/build_report.py
python src/build_dashboard.py
```

`analysis.py` creates the canonical SQLite database, SQL dump, forty query outputs, processed tables and analytical aggregates. `build_powerbi.py` creates the report definitions and portable import snapshots from that database. The HTML dashboard opens directly in a modern browser and needs no server. The presentation's editable chart workbooks retain the source aggregate values used in its charts; ratio values are rounded to twelve significant digits for portable workbook storage.

PDF reproduction uses DejaVu Sans at `/usr/share/fonts/truetype/dejavu`; the font paths are set at the top of `src/build_report.py`. The report and dashboard plots use Matplotlib.

## Interpretation and data handling

Province means patient residence, not facility location. Twenty facility IDs are observed, but a facility master containing names, types, ownership and geography is absent. Billing, payments and feedback have no transaction dates. Service keys, dated occupancy, room/equipment usage and admission/discharge episodes are absent. New registration counts, cancellation rates, physical utilization, clinical readmission rates and revenue by service remain unavailable.

Public files contain analytical aggregates and reproducible code. Patient names, contact fields, individual clinical extracts, record-level query results, the database and embedded individual-data model snapshots are retained only in the private project archive. Unique patient counts are non-additive across overlapping aggregate groups. Recommendations concern reconciliation, measurement coverage, pending claims and descriptive service-feedback review; no causal treatment or staffing-adequacy conclusions are made.
