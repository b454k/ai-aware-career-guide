# BLS employment projections, 2025–35 (ROADMAP 10.16)

US Bureau of Labor Statistics, Employment Projections program, released 2026-08-27. Public domain
(https://www.bls.gov/opub/copyright-information.htm).

bls.gov refuses scripted downloads (HTTP 403), so these files were extracted on 2026-10-18 in a browser from the
two workbooks below, keeping only the columns the app uses. To refresh, open the workbooks in a browser and
extract the same columns.

| File | From | Columns kept |
| --- | --- | --- |
| `projections_2025_35.csv` | [`occupation.xlsx`](https://www.bls.gov/emp/ind-occ-matrix/occupation.xlsx) (413,398 bytes, SHA-256 `a7d060f0576f7d4f5b829b9a0bb4a6c11a12766d159ebb0e07aab5bd2e7583c5`), Table 1.2, the 831 "Line item" occupations | National Employment Matrix (NEM) code; employment 2025 and 2035, in thousands; percent change 2025–35; openings per year, annual average, in thousands |
| `factors_2025_35.csv` | the same workbook, Table 1.12 "Factors affecting occupational utilization" | every row for "Total, all industries" (200), and the industry-specific rows that mention AI, automation, machine learning, chatbots or robots (185); 385 rows in all |
| `onet_to_nem_exceptions.txt` | [`nem-onet-to-soc-crosswalk.xlsx`](https://www.bls.gov/emp/classifications-crosswalks/nem-onet-to-soc-crosswalk.xlsx) (94,441 bytes, SHA-256 `cf3c6e6cf1198f9896a0e280c7503f6cc2202be0660d5decff9c4562c78556e3`) | the 34 O\*NET-SOC codes whose NEM code is not their first seven characters; every other O\*NET-SOC code maps to its first seven |

All US occupations together: 170,280,800 jobs in 2025, projected 176,198,500 in 2035 (+3.5%, Table 1.1).
