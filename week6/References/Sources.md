# Sources

The project uses the HealthConnect Rwanda datasets supplied with AnalystLab Africa's Week 6 Batch E Data Analytics assignment. Original filenames, source URLs, byte counts and SHA-256 hashes are recorded in `Source_Manifest.csv`.

- Official Week 6 announcement, 19 October 2026: https://analystlabafrica.slack.com/archives/C0BUU946M60/p1792407796632549
- Assignment brief: https://drive.google.com/file/d/1H4_WvMhyL1B0XkHjMREfhXHt6Qgca1ae/view
- Programme clarification permitting SQLite, 20 October 2026: https://analystlabafrica.slack.com/archives/C0BUU946M60/p1792481942761039

The supplied workbooks were read as data sources; duplicate copies were not appended to canonical tables. Source files remain unchanged. There are no source rows for facility names, facility ownership or facility geography.

## Geographic boundaries

Rwanda province polygons are distributed by geoBoundaries gbOpen, ADM1, with source attribution to Rwanda Geo Portal, boundary representation year 2020, licensed CC BY 4.0. Province names were normalized only to match the five patient-residence categories; no facility coordinates were inferred.

- Metadata: https://www.geoboundaries.org/api/current/gbOpen/RWA/ADM1/
- Geometry: https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/RWA/ADM1/geoBoundaries-RWA-ADM1_simplified.geojson
- License: https://creativecommons.org/licenses/by/4.0/

The map is an analytical adaptation of the source boundaries, coloured by supplied patient-register counts. Boundaries and labels do not indicate hospital locations.

## Power BI project format

Report source follows Microsoft's Power BI project and PBIR file organization:

- https://learn.microsoft.com/power-bi/developer/projects/projects-report
- https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/report-definition

Source validation checks JSON syntax, field references, relationships, measure references and embedded CSV round trips. These checks are distinct from Power BI Desktop rendering or DAX runtime execution.
