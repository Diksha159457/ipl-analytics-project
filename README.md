# IPL 2022 Analytics Dashboard

A portfolio-ready sports analytics project that transforms a raw IPL 2022 match dataset into a reproducible Python analysis pipeline and a deployable Streamlit dashboard.

This project is designed to showcase data cleaning, feature engineering, KPI reporting, visual storytelling, and lightweight product thinking in one polished repository.

## Live application

Live dashboard: [IPL Analytics Project](https://ipl-analytics-project-zx8cnbgusgmujruunxov7n.streamlit.app/)

## Project overview

The original dataset contains match-level IPL 2022 information such as teams, toss decisions, venues, scores, player awards, and bowling figures. This project turns that static data into an interactive analytics experience that helps answer practical performance questions around team efficiency, toss impact, venue behavior, and player influence.

## What this project demonstrates

- Built a reusable analytics pipeline with `pandas` instead of keeping the work locked inside a notebook.
- Cleaned inconsistent source values such as malformed date strings and team-name variations.
- Engineered cricket-specific metrics like toss-to-win conversion, chasing success rate, and venue scoring intensity.
- Generated structured outputs including charts, summary tables, and an executive-style markdown report.
- Created a deployable Streamlit dashboard for interactive exploration and public portfolio presentation.

## Key features

- Interactive dashboard with filters for teams, venues, and match stages
- KPI cards for match count, toss conversion, chasing wins, and scoring trends
- Team, player, and venue performance views
- CSV upload support for exploring compatible datasets
- Downloadable filtered summary tables
- Reproducible Python script for offline analysis export

## Business questions answered

- Which teams were the most efficient across the IPL 2022 season?
- How strongly did toss wins influence match outcomes?
- Which venues were highest scoring, and where was chasing most successful?
- Which players had the strongest repeated impact on results?
- What were the biggest wins by runs and wickets?

## Project structure

```text
ipl_project/
├── IPL.csv
├── IPL_Capstone_Project.ipynb
├── app.py
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
├── requirements.txt
└── .streamlit/
    └── config.toml
```

## Tech stack

- Python
- pandas
- matplotlib
- seaborn
- Streamlit
- Jupyter Notebook

## Local setup

```bash
python3 -m pip install -r requirements.txt
python3 run_analysis.py
streamlit run app.py
```

Generated analysis artifacts are saved in `outputs/`.

## Deployment

This project is ready to deploy on Streamlit Community Cloud.

1. Push the repository to GitHub.
2. Open [Streamlit Community Cloud](https://share.streamlit.io/).
3. Select the repository.
4. Set the main file path to `app.py`.
5. Deploy using `requirements.txt`.

## Resume-ready highlights

- Built a reproducible sports analytics pipeline to evaluate IPL 2022 team, player, and venue performance.
- Automated data cleaning, KPI extraction, chart generation, and stakeholder-friendly summaries from a raw CSV dataset.
- Converted exploratory notebook work into a deployable Streamlit dashboard for interactive analysis and portfolio presentation.

## Future improvements

- Add predictive modeling for match outcomes
- Extend the project to multiple IPL seasons for trend analysis
- Add advanced player efficiency metrics and matchup comparisons
- Add dashboard screenshots and richer project visuals to the repository
