from __future__ import annotations

from io import StringIO
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st

from src.ipl_analysis import IPLAnalysis, prepare_ipl_dataframe


PROJECT_ROOT = Path(__file__).resolve().parent


st.set_page_config(
    page_title="IPL 2022 Analytics Dashboard",
    page_icon="🏏",
    layout="wide",
)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(255, 209, 102, 0.18), transparent 28%),
                radial-gradient(circle at top right, rgba(42, 157, 143, 0.14), transparent 24%),
                linear-gradient(180deg, #f8f5ef 0%, #fcfbf8 100%);
        }
        .hero {
            padding: 1.4rem 1.6rem;
            border-radius: 24px;
            color: #f8f5ef;
            background: linear-gradient(135deg, #0b3c49 0%, #1f6f78 55%, #f4a261 100%);
            box-shadow: 0 18px 45px rgba(11, 60, 73, 0.18);
            margin-bottom: 1rem;
        }
        .hero h1 {
            margin: 0;
            font-size: 2.4rem;
        }
        .hero p {
            margin: 0.45rem 0 0;
            font-size: 1rem;
            max-width: 56rem;
        }
        .insight-card {
            background: rgba(255,255,255,0.78);
            border: 1px solid rgba(11, 60, 73, 0.08);
            border-radius: 18px;
            padding: 1rem 1.1rem;
            margin-bottom: 0.75rem;
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
        }
        .section-label {
            font-size: 0.8rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #6b7280;
            margin-bottom: 0.35rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def load_default_analysis() -> IPLAnalysis:
    return IPLAnalysis(PROJECT_ROOT / "IPL.csv", PROJECT_ROOT / "outputs")


@st.cache_data(show_spinner=False)
def load_uploaded_dataframe(file_bytes: bytes) -> pd.DataFrame:
    text = file_bytes.decode("utf-8")
    return prepare_ipl_dataframe(pd.read_csv(StringIO(text)))


def get_filtered_dataframe(
    df: pd.DataFrame, teams: list[str], venues: list[str], stages: list[str]
) -> pd.DataFrame:
    filtered = df.copy()
    if teams:
        filtered = filtered[
            filtered["team1"].isin(teams) | filtered["team2"].isin(teams)
        ]
    if venues:
        filtered = filtered[filtered["venue"].isin(venues)]
    if stages:
        filtered = filtered[filtered["stage"].isin(stages)]
    return filtered


def build_team_table(df: pd.DataFrame) -> pd.DataFrame:
    appearances = pd.concat([df["team1"], df["team2"]]).value_counts()
    wins = df["match_winner"].value_counts()
    summary = (
        pd.DataFrame({"matches": appearances, "wins": wins})
        .fillna(0)
        .astype(int)
        .sort_values(["wins", "matches"], ascending=False)
    )
    summary["win_pct"] = (100 * summary["wins"] / summary["matches"]).round(1)
    return summary.reset_index(names="team")


def build_player_table(df: pd.DataFrame) -> pd.DataFrame:
    scoring = (
        df.groupby("top_scorer")
        .agg(
            appearances=("match_id", "count"),
            cumulative_top_score_runs=("highscore", "sum"),
            best_score=("highscore", "max"),
        )
        .sort_values(["cumulative_top_score_runs", "appearances"], ascending=False)
        .reset_index(names="player")
    )
    awards = (
        df["player_of_the_match"]
        .value_counts()
        .rename_axis("player")
        .reset_index(name="player_of_match_awards")
    )
    merged = scoring.merge(awards, on="player", how="outer").fillna(0)
    numeric_columns = [column for column in merged.columns if column != "player"]
    merged[numeric_columns] = merged[numeric_columns].astype(int)
    return merged.sort_values(
        ["player_of_match_awards", "cumulative_top_score_runs"], ascending=False
    )


def build_venue_table(df: pd.DataFrame) -> pd.DataFrame:
    venue = (
        df.groupby("venue")
        .agg(
            matches=("match_id", "count"),
            avg_first_innings_score=("first_ings_score", "mean"),
            avg_total_runs=("total_match_runs", "mean"),
            chasing_win_pct=("is_chasing_win", "mean"),
        )
        .reset_index()
        .sort_values("avg_total_runs", ascending=False)
    )
    venue["avg_first_innings_score"] = venue["avg_first_innings_score"].round(1)
    venue["avg_total_runs"] = venue["avg_total_runs"].round(1)
    venue["chasing_win_pct"] = (100 * venue["chasing_win_pct"]).round(1)
    return venue


def render_header() -> None:
    st.markdown(
        """
        <div class="hero">
            <div class="section-label">Deployable Portfolio Project</div>
            <h1>IPL 2022 Analytics Dashboard</h1>
            <p>
                Explore team efficiency, toss impact, player influence, venue behavior,
                and match-level outliers through an interactive sports analytics app.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_strip(df: pd.DataFrame) -> None:
    toss_conversion = 100 * df["toss_winner_also_match_winner"].mean()
    chasing_rate = 100 * df["is_chasing_win"].mean()
    avg_first_innings = df["first_ings_score"].mean()
    avg_total_runs = df["total_match_runs"].mean()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Matches", f"{len(df)}")
    col2.metric("Toss to Win", f"{toss_conversion:.1f}%")
    col3.metric("Chasing Wins", f"{chasing_rate:.1f}%")
    col4.metric("Avg Total Runs", f"{avg_total_runs:.1f}")

    st.caption(f"Average first-innings total in the filtered view: {avg_first_innings:.1f}")


def render_story_cards(team_table: pd.DataFrame, player_table: pd.DataFrame, venue_table: pd.DataFrame) -> None:
    top_team = team_table.iloc[0]
    top_player = player_table.iloc[0]
    top_venue = venue_table.iloc[0]

    col1, col2, col3 = st.columns(3)
    col1.markdown(
        f"""
        <div class="insight-card">
            <div class="section-label">Team Leader</div>
            <strong>{top_team["team"]}</strong><br/>
            {int(top_team["wins"])} wins in {int(top_team["matches"])} matches
            with a {top_team["win_pct"]:.1f}% win rate.
        </div>
        """,
        unsafe_allow_html=True,
    )
    col2.markdown(
        f"""
        <div class="insight-card">
            <div class="section-label">Impact Player</div>
            <strong>{top_player["player"]}</strong><br/>
            {int(top_player["player_of_match_awards"])} player-of-the-match awards
            and a best score of {int(top_player["best_score"])}.
        </div>
        """,
        unsafe_allow_html=True,
    )
    col3.markdown(
        f"""
        <div class="insight-card">
            <div class="section-label">Scoring Venue</div>
            <strong>{top_venue["venue"]}</strong><br/>
            {top_venue["avg_total_runs"]:.1f} average total runs and
            {top_venue["chasing_win_pct"]:.1f}% chasing wins.
        </div>
        """,
        unsafe_allow_html=True,
    )


def team_chart(team_table: pd.DataFrame) -> None:
    top_teams = team_table.head(8)
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(data=top_teams, x="win_pct", y="team", color="#1f6f78", ax=ax)
    ax.set_title("Top Teams by Win Rate")
    ax.set_xlabel("Win Rate (%)")
    ax.set_ylabel("")
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


def player_chart(player_table: pd.DataFrame) -> None:
    top_players = player_table.head(8)
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(
        data=top_players,
        x="player_of_match_awards",
        y="player",
        color="#f4a261",
        ax=ax,
    )
    ax.set_title("Most Player of the Match Awards")
    ax.set_xlabel("Awards")
    ax.set_ylabel("")
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


def venue_chart(venue_table: pd.DataFrame) -> None:
    top_venues = venue_table.head(8)
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(
        data=top_venues,
        x="avg_total_runs",
        y="venue",
        color="#e76f51",
        ax=ax,
    )
    ax.set_title("Highest-Scoring Venues")
    ax.set_xlabel("Average Total Runs")
    ax.set_ylabel("")
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


def match_trend_chart(df: pd.DataFrame) -> None:
    trend = df.sort_values("date")[["date", "total_match_runs", "match_winner"]]
    fig, ax = plt.subplots(figsize=(11, 4.5))
    sns.lineplot(data=trend, x="date", y="total_match_runs", marker="o", color="#264653", ax=ax)
    ax.set_title("Match Scoring Trend Through the Season")
    ax.set_xlabel("")
    ax.set_ylabel("Total Match Runs")
    plt.xticks(rotation=35, ha="right")
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


def render_downloads(team_table: pd.DataFrame, player_table: pd.DataFrame, venue_table: pd.DataFrame) -> None:
    st.subheader("Download Filtered Tables")
    c1, c2, c3 = st.columns(3)
    c1.download_button(
        "Download team summary",
        team_table.to_csv(index=False).encode("utf-8"),
        file_name="team_summary_filtered.csv",
        mime="text/csv",
    )
    c2.download_button(
        "Download player summary",
        player_table.to_csv(index=False).encode("utf-8"),
        file_name="player_summary_filtered.csv",
        mime="text/csv",
    )
    c3.download_button(
        "Download venue summary",
        venue_table.to_csv(index=False).encode("utf-8"),
        file_name="venue_summary_filtered.csv",
        mime="text/csv",
    )


def render_sidebar(default_df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    st.sidebar.header("Dashboard Controls")
    uploaded_file = st.sidebar.file_uploader("Upload a CSV", type=["csv"])
    data_source = "Built-in IPL 2022 dataset"
    df = default_df

    if uploaded_file is not None:
        df = load_uploaded_dataframe(uploaded_file.getvalue())
        data_source = "Uploaded CSV"

    teams = sorted(pd.unique(pd.concat([df["team1"], df["team2"]])))
    venues = sorted(df["venue"].unique())
    stages = sorted(df["stage"].unique())

    selected_teams = st.sidebar.multiselect("Teams", teams)
    selected_venues = st.sidebar.multiselect("Venues", venues)
    selected_stages = st.sidebar.multiselect("Stages", stages)

    filtered_df = get_filtered_dataframe(df, selected_teams, selected_venues, selected_stages)
    st.sidebar.caption(f"Data source: {data_source}")
    st.sidebar.caption(f"Matches in current view: {len(filtered_df)}")
    return filtered_df, data_source


def main() -> None:
    inject_styles()
    default_analysis = load_default_analysis()
    filtered_df, data_source = render_sidebar(default_analysis.df)

    render_header()
    st.caption(f"Current data source: {data_source}")

    if filtered_df.empty:
        st.warning("No matches match the current filters. Try broadening the selection.")
        return

    team_table = build_team_table(filtered_df)
    player_table = build_player_table(filtered_df)
    venue_table = build_venue_table(filtered_df)

    render_metric_strip(filtered_df)
    render_story_cards(team_table, player_table, venue_table)

    left, right = st.columns((1.05, 0.95))
    with left:
        st.subheader("Team Performance")
        team_chart(team_table)
        st.dataframe(team_table, use_container_width=True, hide_index=True)

    with right:
        st.subheader("Player Impact")
        player_chart(player_table)
        st.dataframe(player_table.head(12), use_container_width=True, hide_index=True)

    st.subheader("Venue Intelligence")
    v1, v2 = st.columns((1, 1))
    with v1:
        venue_chart(venue_table)
    with v2:
        match_trend_chart(filtered_df)

    st.dataframe(venue_table, use_container_width=True, hide_index=True)

    st.subheader("Executive Summary")
    st.markdown(
        default_analysis.build_summary_markdown(default_analysis.compute_metrics())
    )
    render_downloads(team_table, player_table, venue_table)


if __name__ == "__main__":
    main()
