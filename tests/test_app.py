"""Runs the real Streamlit script headlessly and checks it renders without errors."""

from pathlib import Path

import pytest

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest
APP = Path(__file__).resolve().parents[1] / "app.py"


def test_dashboard_renders_without_exceptions():
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    assert len(at.metric) >= 3  # KPI cards rendered


def test_dashboard_filters_work():
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    teams = at.sidebar.multiselect[0]
    teams.select(teams.options[0]).run()
    assert not at.exception
