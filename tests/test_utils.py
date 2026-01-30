import pytest

from src.utils import linear_ramp, s_curve_ramp


def test_linear_ramp():
    assert linear_ramp(2025, 3, 2024) == 0.0
    assert linear_ramp(2025, 3, 2025) == 0.0
    assert linear_ramp(2025, 3, 2026) == pytest.approx(1 / 3, abs=0.01)
    assert linear_ramp(2025, 3, 2027) == pytest.approx(2 / 3, abs=0.01)
    assert linear_ramp(2025, 3, 2028) == 1.0


def test_s_curve_ramp():
    assert s_curve_ramp(2025, 3, 2024) == 0.0
    assert s_curve_ramp(2025, 3, 2025) < 0.1
    assert s_curve_ramp(2025, 3, 2026.5) == pytest.approx(0.5, abs=0.1)
    assert s_curve_ramp(2025, 3, 2028) == 1.0
