import pytest

from src.lever_engine import (
    apply_quantity_levers,
    apply_transfer_levers,
    compute_net_emissions_category,
)


def test_apply_quantity_levers():
    bau = 1000.0
    levers = [{"lever_id": "L1"}]
    commitment = {"L1": 1.0}
    potential = {"L1": 0.2}
    net = apply_quantity_levers(bau, levers, 2025, commitment, potential)
    assert net == pytest.approx(800.0, abs=0.1)


def test_apply_transfer_levers():
    emissions = 1000.0
    levers = [
        {
            "lever_id": "L1",
            "transfer_params": {"low_carbon_intensity_ratio": 0.1, "max_share_shift": 1.0},
        }
    ]
    commitment = {"L1": 1.0}
    potential = {"L1": 0.5}
    net = apply_transfer_levers(emissions, levers, 2025, commitment, potential)
    assert net == pytest.approx(550.0, abs=1.0)


def test_compute_net_emissions_category():
    bau = {2024: 1000, 2025: 1030, 2026: 1061}
    levers = [
        {
            "lever_id": "L1",
            "lever_type": "quantity",
            "potential": {"central_pct": 0.1},
            "ramp": {"default_start_year": 2025, "default_duration_years": 2, "curve": "linear"},
        }
    ]
    selections = [
        {"lever_id": "L1", "start_year": 2025, "ramp_years": 2, "commitment_by_year_pct": {}}
    ]
    net = compute_net_emissions_category(bau, levers, selections, 2024, 2026)
    assert net[2024] == 1000.0
    assert net[2025] < 1030.0
    assert net[2026] < 1061.0
