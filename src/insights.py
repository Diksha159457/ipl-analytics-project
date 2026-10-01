"""Statistical layer on top of the descriptive analysis.

With 74 matches, raw percentages are noisy: 48.6% vs 50% is a coin flip, not a
"toss edge". Every headline rate here comes with a Wilson 95% confidence
interval and an exact two-sided binomial test against 50%, and the summary
wording is chosen from the test result rather than written by hand.

It also fits a one-feature logistic model, P(team batting first wins |
first-innings score), validated with leave-one-out CV, to estimate the season's
par score.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from scipy.stats import binomtest
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import LeaveOneOut, cross_val_predict

ALPHA = 0.05
REQUIRED_COLUMNS = {
    "match_id", "date", "venue", "team1", "team2", "stage", "toss_winner", "toss_decision",
    "first_ings_score", "first_ings_wkts", "second_ings_score", "second_ings_wkts",
    "match_winner", "won_by", "margin", "player_of_the_match", "top_scorer", "highscore",
    "best_bowling", "best_bowling_figure",
}


class DataValidationError(ValueError):
    pass


def validate_matches(df: pd.DataFrame) -> None:
    """Fail fast on data that would make the analysis silently wrong."""
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise DataValidationError(f"missing columns: {sorted(missing)}")
    problems = []
    if df["match_id"].duplicated().any():
        problems.append("duplicate match_id values")
    if not df["won_by"].isin(["Runs", "Wickets"]).all():
        problems.append("won_by must be 'Runs' or 'Wickets'")
    if not df["toss_decision"].isin(["Bat", "Field"]).all():
        problems.append("toss_decision must be 'Bat' or 'Field'")
    if (df["margin"] <= 0).any():
        problems.append("margin must be positive")
    teams_ok = (df["match_winner"] == df["team1"]) | (df["match_winner"] == df["team2"])
    if not teams_ok.all():
        problems.append(f"match_winner not one of the two teams in {int((~teams_ok).sum())} rows")
    if {"batting_first"} <= set(df.columns):
        runs_ok = (df["won_by"] == "Runs") == (df["match_winner"] == df["batting_first"])
        if not runs_ok.all():
            problems.append(f"won_by inconsistent with who batted first in {int((~runs_ok).sum())} rows")
    if problems:
        raise DataValidationError("; ".join(problems))


def batting_first(df: pd.DataFrame) -> pd.Series:
    other = np.where(df["toss_winner"] == df["team1"], df["team2"], df["team1"])
    return pd.Series(np.where(df["toss_decision"] == "Bat", df["toss_winner"], other), index=df.index)


@dataclass(frozen=True)
class RateTest:
    successes: int
    trials: int
    rate_pct: float
    ci_low_pct: float
    ci_high_pct: float
    p_value: float

    @property
    def significant(self) -> bool:
        return self.p_value < ALPHA

    def describe(self) -> str:
        return f"{self.rate_pct}% (95% CI {self.ci_low_pct}–{self.ci_high_pct}%, n={self.trials}, p={self.p_value:.2f})"

    def to_dict(self) -> dict:
        return {**asdict(self), "significant": bool(self.significant)}


def wilson_ci(successes: int, trials: int, z: float = 1.96) -> tuple[float, float]:
    if trials == 0:
        return 0.0, 1.0
    p = successes / trials
    denom = 1 + z**2 / trials
    centre = (p + z**2 / (2 * trials)) / denom
    half = z * math.sqrt(p * (1 - p) / trials + z**2 / (4 * trials**2)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def rate_test(flags: pd.Series) -> RateTest:
    k, n = int(flags.sum()), int(flags.size)
    lo, hi = wilson_ci(k, n)
    p = float(binomtest(k, n, 0.5).pvalue) if n else 1.0
    return RateTest(k, n, round(100 * k / n, 1) if n else 0.0, round(100 * lo, 1), round(100 * hi, 1), round(p, 4))


@dataclass(frozen=True)
class ParScoreModel:
    par_score: float
    runs_per_10pct: float
    loo_accuracy: float
    loo_brier: float
    baseline_brier: float
    n: int

    def to_dict(self) -> dict:
        return asdict(self)


def fit_par_score(df: pd.DataFrame) -> ParScoreModel:
    """Logistic model of P(batting-first side wins) on first-innings score."""
    X = df[["first_ings_score"]].to_numpy(dtype=float)
    y = (df["won_by"] == "Runs").astype(int).to_numpy()
    if len(set(y)) < 2:
        raise ValueError("need both outcomes to fit a par-score model")

    model = LogisticRegression().fit(X, y)
    coef, intercept = float(model.coef_[0][0]), float(model.intercept_[0])
    probs = cross_val_predict(LogisticRegression(), X, y, cv=LeaveOneOut(), method="predict_proba")[:, 1]

    # runs needed to move win probability from 50% to 60%: logit(0.6) / coef
    runs_per_10 = math.log(0.6 / 0.4) / coef if coef else float("inf")
    return ParScoreModel(
        par_score=round(-intercept / coef, 1),
        runs_per_10pct=round(runs_per_10, 1),
        loo_accuracy=round(float(((probs > 0.5) == y).mean()), 3),
        loo_brier=round(float(((probs - y) ** 2).mean()), 3),
        baseline_brier=round(float(((y.mean() - y) ** 2).mean()), 3),
        n=len(y),
    )


def edge_sentence(test: RateTest, subject: str, *, decision_note: str = "") -> str:
    if test.significant:
        direction = "more" if test.rate_pct > 50 else "less"
        return f"{subject} won {direction} often than chance: {test.describe()}.{decision_note}"
    return f"{subject} won {test.describe()}, statistically indistinguishable from a coin flip.{decision_note}"
