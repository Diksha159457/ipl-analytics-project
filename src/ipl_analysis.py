from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
XDG_CACHE_DIR = PROJECT_ROOT / ".cache"
MPL_CACHE_DIR = XDG_CACHE_DIR / "matplotlib"
XDG_CACHE_DIR.mkdir(parents=True, exist_ok=True)
MPL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("XDG_CACHE_HOME", str(XDG_CACHE_DIR))
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CACHE_DIR))

import matplotlib  # noqa: E402

matplotlib.use("Agg")  # headless: works in CI, servers and Streamlit Cloud
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402

from src.insights import (  # noqa: E402
    batting_first,
    edge_sentence,
    fit_par_score,
    rate_test,
    validate_matches,
)

MIN_VENUE_MATCHES = 5  # don't crown a "highest scoring venue" on 2 playoff games


TEAM_NAME_FIXES = {
    "Banglore": "Bangalore",
}


def prepare_ipl_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    team_columns = ["team1", "team2", "toss_winner", "match_winner"]
    for column in team_columns:
        cleaned[column] = cleaned[column].replace(TEAM_NAME_FIXES)

    normalized_dates = cleaned["date"].astype(str).str.replace(" ", "", regex=False)
    cleaned["date"] = pd.to_datetime(normalized_dates, format="%B%d,%Y")
    cleaned["best_bowling_wickets"] = (
        cleaned["best_bowling_figure"].str.split("--").str[0].astype(int)
    )
    cleaned["best_bowling_runs"] = (
        cleaned["best_bowling_figure"].str.split("--").str[1].astype(int)
    )
    cleaned["toss_winner_also_match_winner"] = (
        cleaned["toss_winner"] == cleaned["match_winner"]
    )
    cleaned["is_chasing_win"] = cleaned["won_by"].eq("Wickets")
    cleaned["total_match_runs"] = (
        cleaned["first_ings_score"] + cleaned["second_ings_score"]
    )
    cleaned["batting_first"] = batting_first(cleaned)
    validate_matches(cleaned)
    return cleaned


@dataclass(frozen=True)
class _RateView:
    """Read-only view of a serialised RateTest, so the summary can be rebuilt from metrics.json."""

    successes: int
    trials: int
    rate_pct: float
    ci_low_pct: float
    ci_high_pct: float
    p_value: float
    significant: bool

    def describe(self) -> str:
        return (
            f"{self.rate_pct}% (95% CI {self.ci_low_pct}–{self.ci_high_pct}%, "
            f"n={self.trials}, p={self.p_value:.2f})"
        )


@dataclass
class AnalysisArtifacts:
    metrics: dict
    summary_markdown: str


class IPLAnalysis:
    def __init__(self, csv_path: Path, output_dir: Path) -> None:
        self.csv_path = csv_path
        self.output_dir = output_dir
        self.figures_dir = output_dir / "figures"
        self.df = self._load_data()

    def _load_data(self) -> pd.DataFrame:
        df = pd.read_csv(self.csv_path)
        return prepare_ipl_dataframe(df)

    def build_team_summary(self) -> pd.DataFrame:
        appearances = pd.concat([self.df["team1"], self.df["team2"]]).value_counts()
        wins = self.df["match_winner"].value_counts()

        team_summary = (
            pd.DataFrame({"matches": appearances, "wins": wins})
            .fillna(0)
            .astype(int)
            .sort_values(["wins", "matches"], ascending=False)
        )
        team_summary["win_pct"] = (
            100 * team_summary["wins"] / team_summary["matches"]
        ).round(1)
        return team_summary.reset_index(names="team")

    def build_player_summary(self) -> pd.DataFrame:
        top_scorers = (
            self.df.groupby("top_scorer")
            .agg(
                matches_as_top_scorer=("match_id", "count"),
                cumulative_top_score_runs=("highscore", "sum"),
                best_score=("highscore", "max"),
            )
            .sort_values(
                ["cumulative_top_score_runs", "matches_as_top_scorer"],
                ascending=False,
            )
            .reset_index(names="player")
        )

        awards = (
            self.df["player_of_the_match"]
            .value_counts()
            .rename_axis("player")
            .reset_index(name="player_of_match_awards")
        )

        bowling = (
            self.df.groupby("best_bowling")
            .agg(
                best_bowling_awards=("match_id", "count"),
                wickets_in_best_spells=("best_bowling_wickets", "sum"),
                runs_conceded_in_best_spells=("best_bowling_runs", "sum"),
            )
            .sort_values(
                ["wickets_in_best_spells", "best_bowling_awards"], ascending=False
            )
            .reset_index(names="player")
        )

        merged = (
            top_scorers.merge(awards, on="player", how="outer")
            .merge(bowling, on="player", how="outer")
            .fillna(0)
        )
        integer_columns = [col for col in merged.columns if col != "player"]
        merged[integer_columns] = merged[integer_columns].astype(int)
        return merged

    def build_venue_summary(self) -> pd.DataFrame:
        venue_summary = (
            self.df.groupby("venue")
            .agg(
                matches=("match_id", "count"),
                avg_first_innings_score=("first_ings_score", "mean"),
                chasing_win_pct=("is_chasing_win", "mean"),
                avg_total_runs=("total_match_runs", "mean"),
            )
            .sort_values("matches", ascending=False)
            .reset_index()
        )
        venue_summary["avg_first_innings_score"] = venue_summary[
            "avg_first_innings_score"
        ].round(1)
        venue_summary["chasing_win_pct"] = (
            100 * venue_summary["chasing_win_pct"]
        ).round(1)
        venue_summary["avg_total_runs"] = venue_summary["avg_total_runs"].round(1)
        return venue_summary

    def compute_metrics(self) -> dict:
        team_summary = self.build_team_summary()
        player_summary = self.build_player_summary()
        venue_summary = self.build_venue_summary()

        toss_test = rate_test(self.df["toss_winner_also_match_winner"])
        chase_test = rate_test(self.df["is_chasing_win"])
        fielded = self.df[self.df["toss_decision"] == "Field"]
        field_choice_test = rate_test(fielded["toss_winner_also_match_winner"])
        field_share = round(100 * len(fielded) / len(self.df), 1)
        par = fit_par_score(self.df)

        highest_run_win = self.df[self.df["won_by"] == "Runs"].nlargest(1, "margin")[
            ["match_winner", "margin"]
        ].iloc[0]
        highest_wicket_win = self.df[
            self.df["won_by"] == "Wickets"
        ].nlargest(1, "margin")[["match_winner", "margin"]].iloc[0]

        top_team = team_summary.iloc[0].to_dict()
        top_player = player_summary.sort_values(
            ["player_of_match_awards", "cumulative_top_score_runs"], ascending=False
        ).iloc[0]
        eligible = venue_summary[venue_summary["matches"] >= MIN_VENUE_MATCHES]
        top_venue = (eligible if len(eligible) else venue_summary).sort_values(
            "avg_total_runs", ascending=False
        ).iloc[0]

        return {
            "dataset": {
                "matches": int(self.df.shape[0]),
                "features": int(self.df.shape[1]),
                "season": "IPL 2022",
            },
            "headline_metrics": {
                "toss_to_match_conversion_pct": toss_test.rate_pct,
                "chasing_win_pct": chase_test.rate_pct,
                "chose_to_field_pct": field_share,
                "highest_run_win": {
                    "team": highest_run_win["match_winner"],
                    "margin": int(highest_run_win["margin"]),
                },
                "highest_wicket_win": {
                    "team": highest_wicket_win["match_winner"],
                    "margin": int(highest_wicket_win["margin"]),
                },
            },
            "leaders": {
                "top_team": {
                    "team": top_team["team"],
                    "wins": int(top_team["wins"]),
                    "matches": int(top_team["matches"]),
                    "win_pct": float(top_team["win_pct"]),
                },
                "top_player": {
                    "player": top_player["player"],
                    "player_of_match_awards": int(top_player["player_of_match_awards"]),
                    "cumulative_top_score_runs": int(
                        top_player["cumulative_top_score_runs"]
                    ),
                },
                "highest_scoring_venue": {
                    "venue": top_venue["venue"],
                    "avg_total_runs": float(top_venue["avg_total_runs"]),
                    "matches": int(top_venue["matches"]),
                    "min_matches_required": MIN_VENUE_MATCHES,
                },
            },
            "statistical_tests": {
                "toss_winner_wins_match": toss_test.to_dict(),
                "chasing_side_wins": chase_test.to_dict(),
                "toss_winner_who_fielded_wins": field_choice_test.to_dict(),
            },
            "par_score_model": par.to_dict(),
        }

    def create_visuals(self) -> None:
        self.figures_dir.mkdir(parents=True, exist_ok=True)
        sns.set_theme(style="whitegrid", palette="crest")

        team_summary = self.build_team_summary().head(10)
        plt.figure(figsize=(12, 6))
        sns.barplot(data=team_summary, x="win_pct", y="team")
        plt.title("Top IPL 2022 Teams by Win Rate")
        plt.xlabel("Win Rate (%)")
        plt.ylabel("")
        plt.tight_layout()
        plt.savefig(self.figures_dir / "team_win_rate.png", dpi=200)
        plt.close()

        toss_summary = pd.DataFrame(
            {
                "metric": ["Won toss and match", "Won toss only"],
                "matches": [
                    int(self.df["toss_winner_also_match_winner"].sum()),
                    int((~self.df["toss_winner_also_match_winner"]).sum()),
                ],
            }
        )
        plt.figure(figsize=(8, 5))
        sns.barplot(data=toss_summary, x="metric", y="matches", color="#2a9d8f")
        plt.title("How Often Toss Advantage Converted Into Match Wins")
        plt.xlabel("")
        plt.ylabel("Matches")
        plt.tight_layout()
        plt.savefig(self.figures_dir / "toss_impact.png", dpi=200)
        plt.close()

        player_awards = (
            self.df["player_of_the_match"]
            .value_counts()
            .head(10)
            .rename_axis("player")
            .reset_index(name="awards")
        )
        plt.figure(figsize=(12, 6))
        sns.barplot(data=player_awards, x="awards", y="player", color="#264653")
        plt.title("Most Player of the Match Awards")
        plt.xlabel("Awards")
        plt.ylabel("")
        plt.tight_layout()
        plt.savefig(self.figures_dir / "player_of_match_leaders.png", dpi=200)
        plt.close()

        venue_summary = (
            self.build_venue_summary()
            .sort_values("avg_first_innings_score", ascending=False)
            .head(8)
        )
        plt.figure(figsize=(12, 6))
        sns.barplot(data=venue_summary, x="avg_first_innings_score", y="venue", color="#e76f51")
        plt.title("Highest-Scoring Venues by Average First Innings Total")
        plt.xlabel("Average First Innings Score")
        plt.ylabel("")
        plt.tight_layout()
        plt.savefig(self.figures_dir / "venue_scoring.png", dpi=200)
        plt.close()

    def build_summary_markdown(self, metrics: dict) -> str:
        top_team = metrics["leaders"]["top_team"]
        top_player = metrics["leaders"]["top_player"]
        headline = metrics["headline_metrics"]
        top_venue = metrics["leaders"]["highest_scoring_venue"]
        tests = {k: _RateView(**v) for k, v in metrics["statistical_tests"].items()}
        par = metrics["par_score_model"]

        toss_line = edge_sentence(tests["toss_winner_wins_match"], "Teams that won the toss")
        chase_line = edge_sentence(
            tests["chasing_side_wins"],
            "Chasing sides",
            decision_note=(
                f" Captains still chose to field {headline['chose_to_field_pct']}% of the time, "
                "a preference the results don't justify."
                if not tests["chasing_side_wins"].significant
                else ""
            ),
        )
        model_edge = par["baseline_brier"] - par["loo_brier"]

        return f"""# IPL 2022 Analysis Summary

## Executive Takeaways

- {top_team["team"]} was the most successful side, with {top_team["wins"]} wins in {top_team["matches"]} matches ({top_team["win_pct"]}% win rate).
- {toss_line}
- {chase_line}
- **Par score ≈ {par["par_score"]:.0f}.** A logistic model on first-innings score alone puts the batting-first side's win probability at 50% around {par["par_score"]:.0f} runs. Every ~{par["runs_per_10pct"]:.0f} extra runs lifts it by 10 points. Leave-one-out accuracy is {par["loo_accuracy"]:.0%} (Brier {par["loo_brier"]} vs {par["baseline_brier"]} for a no-skill baseline, {model_edge:.3f} better).
- {top_player["player"]} had the most repeated impact, with {top_player["player_of_match_awards"]} player-of-the-match awards.
- {top_venue["venue"]} was the highest-scoring venue among grounds with at least {top_venue["min_matches_required"]} matches: {top_venue["avg_total_runs"]} runs per match on average over {top_venue["matches"]} games.

## Notable Match Extremes

- Biggest win by runs: {headline["highest_run_win"]["team"]} by {headline["highest_run_win"]["margin"]} runs.
- Biggest win by wickets: {headline["highest_wicket_win"]["team"]} by {headline["highest_wicket_win"]["margin"]} wickets.

## Method notes

- Rates use Wilson 95% confidence intervals and an exact two-sided binomial test against 50% (α = 0.05).
- One season is {metrics["dataset"]["matches"]} matches, so effects smaller than roughly ±11 points can't be detected. "No significant edge" means "no evidence of an edge", not "proof there is none".
- Venues with fewer than {top_venue["min_matches_required"]} matches are excluded from venue leaderboards to avoid small-sample extremes.
"""

    def export(self) -> AnalysisArtifacts:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.create_visuals()
        metrics = self.compute_metrics()
        summary_markdown = self.build_summary_markdown(metrics)

        (self.output_dir / "metrics.json").write_text(
            json.dumps(metrics, indent=2), encoding="utf-8"
        )
        (self.output_dir / "summary.md").write_text(
            summary_markdown, encoding="utf-8"
        )
        self.build_team_summary().to_csv(
            self.output_dir / "team_summary.csv", index=False
        )
        self.build_player_summary().to_csv(
            self.output_dir / "player_summary.csv", index=False
        )
        self.build_venue_summary().to_csv(
            self.output_dir / "venue_summary.csv", index=False
        )
        return AnalysisArtifacts(metrics=metrics, summary_markdown=summary_markdown)


def run_analysis() -> AnalysisArtifacts:
    analysis = IPLAnalysis(
        csv_path=PROJECT_ROOT / "IPL.csv",
        output_dir=PROJECT_ROOT / "outputs",
    )
    return analysis.export()
