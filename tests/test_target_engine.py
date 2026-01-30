import pytest

from src.data_loader import load_baseline_footprint
from src.target_engine import (
    compute_category_targets,
    compute_target_pathway_aca,
    get_sbti_reduction_rate,
)


def test_compute_target_pathway_aca():
    targets = compute_target_pathway_aca(1000, 2024, 2034, 0.025)
    assert targets[2024] == 1000.0
    assert targets[2025] == pytest.approx(975.0, abs=0.1)
    assert targets[2034] == pytest.approx(1000 * (0.975 ** 10), abs=1.0)


def test_get_sbti_reduction_rate():
    assert get_sbti_reduction_rate("WB2C") == 0.025
    assert get_sbti_reduction_rate("1.5C") == 0.042


def test_compute_category_targets():
    baseline = load_baseline_footprint("ready_to_implement_demo_dataset/baseline_footprint.json")
    targets = compute_category_targets(baseline, 2024, 2034, "WB2C")
    assert "S2C1_Electricity" in targets
    assert targets["S2C1_Electricity"][2024] == 300000.0
    assert targets["S2C1_Electricity"][2034] < 300000.0
