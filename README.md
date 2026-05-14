# IPL 2022 Match Analysis

Portfolio-grade sports analytics project built on the IPL 2022 season dataset. The project upgrades a basic exploratory notebook into a reproducible analysis workflow with automated insights, exportable visualizations, and stakeholder-friendly summary artifacts.

## Why this project stands out

- Converts a raw CSV into a structured analytics pipeline using Python and pandas.
- Engineers cricket-specific features such as toss conversion, chase success, venue scoring intensity, and bowling spell impact.
- Produces reusable deliverables including charts, summary tables, and a markdown executive brief.
- Demonstrates end-to-end project ownership: data cleaning, analysis, storytelling, and reproducibility.

## Business-style questions answered

- Which teams were most efficient across the 2022 season?
- How much did winning the toss influence the final result?
- Which venues produced the most runs and the strongest chasing advantage?
- Which players delivered the highest repeated match impact?
- What were the biggest wins of the season by runs and wickets?

## Project structure

```text
ipl_project/
├── IPL.csv
├── IPL_Capstone_Project.ipynb
├── outputs/
│   ├── figures/
│   ├── metrics.json
│   ├── player_summary.csv
│   ├── summary.md
│   ├── team_summary.csv
│   └── venue_summary.csv
├── run_analysis.py
├── src/
│   └── ipl_analysis.py
└── requirements.txt
```

## Tools used

- Python
- pandas
- matplotlib
- seaborn
- Jupyter Notebook

## How to run

```bash
python3 -m pip install -r requirements.txt
python3 run_analysis.py
```

Generated artifacts will be saved in `outputs/`.

## Resume-ready talking points

- Built a reproducible sports analytics pipeline to evaluate IPL 2022 team, player, and venue performance.
- Automated KPI generation and chart exports from a raw match-level dataset using pandas, matplotlib, and seaborn.
- Translated exploratory analysis into portfolio-quality deliverables with executive summaries and structured outputs.

## Next possible upgrades

- Add predictive modeling for match outcomes.
- Publish the analysis as an interactive Streamlit dashboard.
- Expand the dataset to multiple seasons for trend and era comparisons.
