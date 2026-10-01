# IPL 2022 Analytics Dashboard

[![CI](https://github.com/Diksha159457/ipl-analytics-project/actions/workflows/ci.yml/badge.svg)](https://github.com/Diksha159457/ipl-analytics-project/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Coverage](https://img.shields.io/badge/coverage-99%25-brightgreen)

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

## Key findings (with the statistics)

One season is 74 matches, so headline percentages are noisy. Every rate below has a Wilson 95% confidence interval and an exact binomial test against 50%. The report's wording is generated from the test result, so it can't overclaim.

| Question | Result | Verdict |
|---|---|---|
| Does winning the toss help? | Toss winners won **48.6%** (95% CI 37.6–59.8%, p = 0.91) | No detectable edge |
| Is chasing easier? | Chasing sides won **50.0%** (95% CI 38.9–61.1%, p = 1.00) | No detectable edge, even though captains chose to field **79.7%** of the time |
| What's a winning first-innings score? | Logistic model on first-innings score: **par ≈ 172**; about 7 runs adds 10 points of win probability | Leave-one-out accuracy **76%**, Brier **0.184** vs **0.25** baseline |
| Highest-scoring venue? | **Brabourne Stadium**: 341.4 avg total over 16 games | Venues with fewer than 5 games excluded (Eden Gardens' 389.5 came from 2 playoff matches) |

> v1 of this report described a 48.6% toss-to-win rate as "a meaningful toss edge" and a 50% chasing rate as "supporting the field-first bias". The data supports neither, so the summary now derives its claims from the tests.

## Data quality checks

`prepare_ipl_dataframe()` validates the data before any analysis runs:

- required columns are present
- `match_id` is unique
- `won_by` is in {Runs, Wickets}
- margins are positive
- the winner is one of the two teams
- **`won_by` is consistent with who batted first**, which is derived from the toss winner and decision

A malformed CSV uploaded to the dashboard now shows an error message instead of crashing the app.

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
│   ├── ipl_analysis.py   # cleaning, summaries, charts, report
│   └── insights.py       # validation, significance tests, par-score model
├── tests/                # 21 tests incl. headless Streamlit AppTest
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
- SciPy (binomial tests), scikit-learn (logistic regression, LOOCV)
- Jupyter Notebook

## Local setup

```bash
python3 -m pip install -r requirements.txt
python3 run_analysis.py
streamlit run app.py
```

Generated analysis artifacts are saved in `outputs/`.

### Tests

```bash
pip install -r requirements-dev.txt
pytest --cov=src     # 21 tests, 99% coverage
```

The suite covers cleaning, every validation rule, the statistics (including a known Wilson interval), the par-score model against its baseline, and the report wording. It also runs the real dashboard headlessly with Streamlit's `AppTest`. One test fails if `outputs/metrics.json` is stale, which keeps committed results reproducible. CI runs all of this on every push and adds the regenerated report to the job summary.

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
- Added significance testing and a cross-validated par-score model. This showed that the season's apparent toss and chasing advantages were noise.
- Converted exploratory notebook work into a deployable Streamlit dashboard for interactive analysis and portfolio presentation.

## Future improvements

- ~~Add predictive modeling for match outcomes~~ ✅ par-score model (extend with venue and wickets-in-hand)
- Extend the project to multiple IPL seasons for trend analysis
- Add advanced player efficiency metrics and matchup comparisons
- Add dashboard screenshots and richer project visuals to the repository
