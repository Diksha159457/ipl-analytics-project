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

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


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
    return cleaned


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

        toss_win_pct = round(
            100 * self.df["toss_winner_also_match_winner"].mean(), 1
        )
        chasing_win_pct = round(100 * self.df["is_chasing_win"].mean(), 1)

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
        top_venue = venue_summary.sort_values("avg_total_runs", ascending=False).iloc[0]

        return {
            "dataset": {
                "matches": int(self.df.shape[0]),
                "features": int(self.df.shape[1]),
                "season": "IPL 2022",
            },
            "headline_metrics": {
                "toss_to_match_conversion_pct": toss_win_pct,
                "chasing_win_pct": chasing_win_pct,
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
                },
            },
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

        return f"""# IPL 2022 Analysis Summary

## Executive Takeaways

- {top_team["team"]} finished as the most efficient side in this dataset with {top_team["wins"]} wins in {top_team["matches"]} matches ({top_team["win_pct"]}% win rate).
- Teams that won the toss also won the match {headline["toss_to_match_conversion_pct"]}% of the time, showing a meaningful but not decisive toss edge.
- Chasing teams won {headline["chasing_win_pct"]}% of matches, which supports the field-first bias visible across the season.
- {top_player["player"]} stood out as the strongest all-around impact player in this dataset with {top_player["player_of_match_awards"]} player-of-the-match awards.
- {top_venue["venue"]} was the highest-scoring venue with an average total of {top_venue["avg_total_runs"]} runs per match.

## Notable Match Extremes

- Biggest win by runs: {headline["highest_run_win"]["team"]} by {headline["highest_run_win"]["margin"]} runs.
- Biggest win by wickets: {headline["highest_wicket_win"]["team"]} by {headline["highest_wicket_win"]["margin"]} wickets.

## Portfolio Angle

This project turns a raw sports dataset into a reproducible analytics workflow by combining feature engineering, KPI extraction, automated reporting, and export-ready visualizations. It is designed to demonstrate data storytelling, Python-based analysis, and stakeholder-friendly communication.
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
