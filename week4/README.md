# FinTrust Digital Bank: Week 4

**Iyiola Anjolaoluwa Emmanuel**  
Data Analytics, AnalystLab Africa, Batch E  
Reporting period: January-March 2026

I analysed transaction outcomes, customer activity and risk-review patterns using SQL, Python and Power BI. This continues my FinTrust work from Weeks 1-3.

## Main findings

- 1,500 customers and 12,000 transactions.
- NGN 560.48 million in attempted value and NGN 510.81 million in successful value.
- A 90.47% transaction success rate.
- February daily activity remained stable after adjusting for calendar days.
- Mobile App accounted for 46.98% of failed transactions.
- The highest-value 10% of customers contributed 26.97% of successful transaction value.

## Project files

- [Complete project package](FinTrust_Week4_Package.zip): source data, prepared data, SQL, Python, notebook, charts, query outputs, documentation and the three-page Power BI project.
- [Final report](FinTrust_Final_Report.pdf)
- [Executed notebook](FinTrust_Final_Analysis.ipynb)
- [Presentation](FinTrust_Week4_Presentation.pptx)
- [Python analysis](analysis.py)
- [Dashboard builder](build_dashboard.py)
- [Twelve SQL queries](final_analysis.sql)
- [KPI definitions](KPI_Definitions.md)
- [Testing and refinements](Testing_and_Refinements.md)

## Reproduce the analysis

Download and extract the complete project package. Open a terminal inside the extracted `FinTrust_Week4` folder and run:

```sh
python -m pip install -r requirements.txt
python analysis.py
python build_dashboard.py
```

The extracted package preserves the folders used by the scripts. The Power BI project is at `powerbi/FinTrust_Final.pbip`, alongside its report and semantic-model folders.

## Validation and scope

I checked all twelve SQL outputs against separate pandas calculations. Every output column matched, and all 39 analytical checks passed. The Power BI project passed report-structure and embedded-data checks. Power BI engine execution and live interactions are outside this validation scope.

FinTrust and its data are fictional. Review flags are educational labels. Transaction value does not measure bank revenue, profit, settled funds or confirmed fraud.
