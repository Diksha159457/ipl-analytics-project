import json
from pathlib import Path

import pandas as pd
import pytest

from src.insights import (
    DataValidationError,
    batting_first,
    edge_sentence,
    fit_par_score,
    rate_test,
    validate_matches,
    wilson_ci,
)
from src.ipl_analysis import PROJECT_ROOT, IPLAnalysis, prepare_ipl_dataframe

RAW = pd.read_csv(PROJECT_ROOT / "IPL.csv")


@pytest.fixture(scope="module")
def analysis(tmp_path_factory):
    return IPLAnalysis(PROJECT_ROOT / "IPL.csv", tmp_path_factory.mktemp("out"))


# ── cleaning ────────────────────────────────────────────────────────────────


def test_prepare_parses_dates_and_bowling_figures():
    df = prepare_ipl_dataframe(RAW)
    assert df["date"].dt.year.eq(2022).all()
    assert df.loc[0, ["best_bowling_wickets", "best_bowling_runs"]].tolist() == [3, 20]
    assert not df["team1"].str.contains("Banglore").any()


def test_batting_first_is_consistent_with_result_type():
    df = prepare_ipl_dataframe(RAW)
    runs_wins = df["won_by"] == "Runs"
    assert (df.loc[runs_wins, "match_winner"] == df.loc[runs_wins, "batting_first"]).all()
    assert (df.loc[~runs_wins, "match_winner"] != df.loc[~runs_wins, "batting_first"]).all()


def test_batting_first_logic():
    df = pd.DataFrame(
        {"team1": ["A", "A"], "team2": ["B", "B"], "toss_winner": ["A", "B"], "toss_decision": ["Bat", "Field"]}
    )
    assert batting_first(df).tolist() == ["A", "A"]


# ── validation ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "mutate,fragment",
    [
        (lambda d: d.drop(columns=["venue"]), "missing columns"),
        (lambda d: d.assign(won_by="Draw"), "won_by"),
        (lambda d: d.assign(margin=0), "margin"),
        (lambda d: pd.concat([d, d.head(1)]), "duplicate match_id"),
        (lambda d: d.assign(match_winner="Atlantis"), "match_winner"),
    ],
)
def test_validation_rejects_bad_data(mutate, fragment):
    with pytest.raises(DataValidationError, match=fragment):
        validate_matches(mutate(RAW.copy()))


def test_validation_catches_flipped_result_type():
    df = prepare_ipl_dataframe(RAW)
    df.loc[0, "won_by"] = "Runs" if df.loc[0, "won_by"] == "Wickets" else "Wickets"
    with pytest.raises(DataValidationError, match="batted first"):
        validate_matches(df)


# ── statistics ──────────────────────────────────────────────────────────────


def test_wilson_ci_known_value():
    lo, hi = wilson_ci(36, 74)
    assert (round(lo, 3), round(hi, 3)) == (0.376, 0.598)


def test_wilson_ci_edges():
    assert wilson_ci(0, 0) == (0.0, 1.0)
    lo, hi = wilson_ci(10, 10)
    assert hi == 1.0 and lo > 0.6


def test_rate_test_flags_real_effect_only():
    assert not rate_test(pd.Series([True] * 36 + [False] * 38)).significant
    strong = rate_test(pd.Series([True] * 60 + [False] * 14))
    assert strong.significant and "more often than chance" in edge_sentence(strong, "X")


def test_par_score_model_beats_baseline():
    par = fit_par_score(prepare_ipl_dataframe(RAW))
    assert 150 < par.par_score < 195
    assert par.loo_brier < par.baseline_brier
    assert par.loo_accuracy > 0.6


def test_par_score_needs_both_outcomes():
    df = prepare_ipl_dataframe(RAW)
    with pytest.raises(ValueError):
        fit_par_score(df[df["won_by"] == "Runs"])


# ── metrics & report ────────────────────────────────────────────────────────


def test_team_summary_totals(analysis):
    teams = analysis.build_team_summary()
    assert teams["wins"].sum() == len(analysis.df)
    assert teams["matches"].sum() == 2 * len(analysis.df)


def test_venue_leader_respects_minimum_sample(analysis):
    leader = analysis.compute_metrics()["leaders"]["highest_scoring_venue"]
    assert leader["matches"] >= leader["min_matches_required"]
    assert leader["venue"] != "Eden Gardens, Kolkata"  # only 2 playoff games


def test_summary_wording_follows_the_statistics(analysis):
    metrics = analysis.compute_metrics()
    text = analysis.build_summary_markdown(metrics)
    assert not metrics["statistical_tests"]["toss_winner_wins_match"]["significant"]
    assert "indistinguishable from a coin flip" in text
    assert "meaningful" not in text  # v1 called a 48.6% rate a "meaningful toss edge"
    assert "Par score" in text


def test_export_writes_all_artifacts(analysis):
    analysis.export()
    out = analysis.output_dir
    for name in ["metrics.json", "summary.md", "team_summary.csv", "player_summary.csv", "venue_summary.csv"]:
        assert (out / name).exists(), name
    assert len(list((out / "figures").glob("*.png"))) == 4
    json.loads((out / "metrics.json").read_text())


def test_committed_outputs_are_up_to_date(analysis):
    """Fails if someone changes the analysis without re-running `python run_analysis.py`."""
    committed = json.loads((Path(PROJECT_ROOT) / "outputs" / "metrics.json").read_text())
    assert committed == json.loads(json.dumps(analysis.compute_metrics()))
