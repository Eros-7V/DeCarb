import pytest

from src.bau_engine import (
    aggregate_bau_pathway,
    compute_bau_pathway_all_categories,
    compute_bau_pathway_category,
)
from src.data_loader import load_baseline_footprint, load_company_profile


def test_compute_bau_pathway_category():
    bau = compute_bau_pathway_category(1000, 2024, 2034, 0.03)
    assert bau[2024] == 1000.0
    assert bau[2025] == pytest.approx(1030.0, abs=0.1)
    assert bau[2034] == pytest.approx(1000 * (1.03**10), abs=1.0)


def test_compute_bau_pathway_all_categories():
    baseline = load_baseline_footprint("ready_to_implement_demo_dataset/baseline_footprint.json")
    profile = load_company_profile("ready_to_implement_demo_dataset/company_profile.json")
    bau = compute_bau_pathway_all_categories(baseline, profile, 2024, 2034)
    assert "S2C1_Electricity" in bau
    assert bau["S2C1_Electricity"][2024] == 300000.0
    assert bau["S2C1_Electricity"][2034] > 300000.0


def test_aggregate_bau_pathway():
    bau_by_cat = {"S1": {2024: 100, 2025: 103}, "S2": {2024: 200, 2025: 206}}
    total = aggregate_bau_pathway(bau_by_cat)
    assert total[2024] == 300.0
    assert total[2025] == 309.0
