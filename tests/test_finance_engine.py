import pytest

from src.finance_engine import compute_discount_factor, compute_lever_npv, compute_payback_years


def test_compute_discount_factor():
    assert compute_discount_factor(2025, 2024, 0.08) == pytest.approx(1 / 1.08, abs=0.001)
    assert compute_discount_factor(2024, 2024, 0.08) == 1.0


def test_compute_lever_npv():
    cashflows = {
        2025: {"net_cost": -100},
        2026: {"net_cost": 50},
    }
    npv = compute_lever_npv(cashflows, 2024, 0.08)
    assert npv < 0


def test_compute_payback_years():
    cashflows = {
        2025: {"net_cost": -50},
        2026: {"net_cost": -50},
        2027: {"net_cost": 100},
    }
    payback = compute_payback_years(cashflows, 2024, 0.08)
    assert payback is not None
    assert payback < 3.0
