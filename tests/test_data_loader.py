import pytest

from src.data_loader import (
    load_baseline_footprint,
    load_company_profile,
    load_lever_library,
    validate_company_profile,
)


def test_load_company_profile():
    profile = load_company_profile("ready_to_implement_demo_dataset/company_profile.json")
    assert profile["company_id"] == "DC-DEMO-001"
    assert profile["base_year"] == 2024
    assert profile["horizon_year"] == 2034


def test_load_baseline_footprint():
    baseline = load_baseline_footprint("ready_to_implement_demo_dataset/baseline_footprint.json")
    assert len(baseline["emissions_by_category"]) == 8
    assert baseline["emissions_by_category"][0]["category_id"] == "S2C1_Electricity"


def test_load_lever_library():
    levers = load_lever_library("ready_to_implement_demo_dataset/lever_library.json")
    assert len(levers) == 12
    assert levers[0]["lever_id"] == "L01_PUE_Optimization"


def test_validate_company_profile():
    profile = load_company_profile("ready_to_implement_demo_dataset/company_profile.json")
    is_valid, errors = validate_company_profile(profile)
    assert is_valid, f"Validation failed: {errors}"
