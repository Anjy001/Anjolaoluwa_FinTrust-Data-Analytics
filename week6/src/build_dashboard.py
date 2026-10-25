"""Build the self-contained aggregate healthcare dashboard."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/"Analysis/Dashboard_Data.json").read_text())
data["geography"]=json.loads((ROOT/"References/Rwanda_Provinces.geojson").read_text())
template=(ROOT/"src/dashboard_template.html").read_text()
encoded=json.dumps(data,ensure_ascii=False,separators=(",",":")).replace("</","<\\/")
(ROOT/"Dashboard/HealthConnect_Dashboard.html").write_text(template.replace("<!-- DATA_PAYLOAD -->",encoded))
print("Dashboard/HealthConnect_Dashboard.html")
