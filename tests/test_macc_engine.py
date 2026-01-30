import pytest

from src.macc_engine import compute_discounted_abatement, compute_mac


def test_compute_discounted_abatement():
    abatement = {2025: 1000, 2026: 2000}
    disc = compute_discounted_abatement(abatement, 2024, 0.08)
    expected = 1000 / 1.08 + 2000 / (1.08**2)
    assert disc == pytest.approx(expected, abs=1.0)


def test_compute_mac():
    mac = compute_mac(1000000, 50000)
    assert mac == pytest.approx(20.0, abs=0.1)
