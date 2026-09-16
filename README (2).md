# FinTrust Digital Bank — Week 1: Understand & Plan
**AnalystLab Africa — Experience Lab Internship Programme**
Project: FinTrust Financial Intelligence & Digital Banking Support Solution

## Overview
Week 1 deliverable: business understanding, resource/data review, track objectives,
success criteria and a Weeks 2-4 plan for each of the five tracks.

## Repository structure
```
fintrust/
|- data/                     # approved FinTrust resources (synthetic)
|  |- FinTrust_Customer_Data.xlsx
|  |- FinTrust_Transaction_Data.xlsx
|  |- FinTrust_Data_Dictionary.xlsx
|- notebooks/
|  |- FinTrust_Week1_Analysis.ipynb    # full reproducible analysis
|- src/
|  |- profile.py             # schema / missingness / relationship checks
|  |- analysis.py            # metrics, cross-tabs, tests, baseline model, figures
|- outputs/
|  |- fig1_eda.png
|  |- fig2_wireframe.png
|  |- fig3_mle_arch.png
|  |- fig4_arch.png
|  |- FinTrust_KPI_Table.csv
|  |- results.json
|- README.md
```

## How to run
```bash
pip install pandas numpy scikit-learn scipy matplotlib openpyxl
python src/profile.py     # data understanding
python src/analysis.py    # full analysis + figures
```
Deterministic: `random_state=42` throughout.

## Key findings
- 1,500 customers x 12 fields; 12,000 transactions x 11 fields; join on `Customer_ID`.
- 0 orphan transactions, 0 customers without transactions, 8.0 transactions per customer.
- 192 missing cells, confined to `Device_Type` (96) and `Location` (96).
- Total transaction value NGN 560,477,355; success rate 90.47%; risk-review rate 19.60%.
- `Transaction.Location` != `Customer.City` (12.7% agreement) - a genuine data-quality trap.
- Risk review is significantly associated with international transactions, amount, status and night-time.