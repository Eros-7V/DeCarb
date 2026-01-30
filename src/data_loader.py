import json
from pathlib import Path
from typing import Any

import pandas as pd


def _load_json(file_path: str | Path) -> Any:
    path = Path(file_path)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _parse_json_cell(value: Any) -> dict:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return {}
        return json.loads(value)
    return {}


def _parse_list_cell(value: Any) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return []


def _to_float(value: Any, default: float | None = None) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load_company_profile(file_path: str) -> dict:
    """Load and validate company_profile.json. Returns dict with company data."""
    profile = _load_json(file_path)
    is_valid, errors = validate_company_profile(profile)
    if not is_valid:
        raise ValueError(f"Company profile validation failed: {errors}")
    return profile


def load_baseline_footprint(file_path: str) -> dict:
    """Load baseline_footprint.json or CSV. Returns dict with emissions_by_category list."""
    path = Path(file_path)
    if path.suffix.lower() == ".json":
        baseline = _load_json(file_path)
    elif path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
        emissions_by_category = []
        for _, row in df.iterrows():
            emissions_by_category.append(
                {
                    "category_id": str(row.get("category_id", "")).strip(),
                    "scope": str(row.get("scope", "")).strip(),
                    "category_name": str(row.get("category_name", "")).strip(),
                    "base_year_tco2e": _to_float(row.get("base_year_tco2e"), 0.0),
                    "bu_split": _parse_json_cell(row.get("bu_split")),
                }
            )
        baseline = {
            "inventory_method": "GHG Protocol",
            "emissions_by_category": emissions_by_category,
        }
    else:
        raise ValueError(f"Unsupported baseline file type: {path.suffix}")

    is_valid, errors = validate_baseline_footprint(baseline)
    if not is_valid:
        raise ValueError(f"Baseline validation failed: {errors}")
    return baseline


def load_lever_library(file_path: str) -> list:
    """Load lever_library.json or CSV. Returns list of lever dicts."""
    path = Path(file_path)
    if path.suffix.lower() == ".json":
        levers = _load_json(file_path)
    elif path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
        levers = []
        for _, row in df.iterrows():
            lever_type = str(row.get("lever_type", "")).strip()
            transfer_low_ratio = _to_float(row.get("transfer_low_carbon_ratio"))
            transfer_max_share = _to_float(row.get("transfer_max_share_shift"))
            transfer_params = {}
            if transfer_low_ratio is not None or transfer_max_share is not None:
                transfer_params = {
                    "low_carbon_intensity_ratio": transfer_low_ratio or 0.0,
                    "max_share_shift": transfer_max_share or 0.0,
                }
            levers.append(
                {
                    "lever_id": str(row.get("lever_id", "")).strip(),
                    "title": str(row.get("title", "")).strip(),
                    "description": "",
                    "lever_type": lever_type,
                    "scope_targets": _parse_list_cell(row.get("scope_targets")),
                    "category_targets": _parse_list_cell(row.get("category_targets")),
                    "potential": {
                        "min_pct": _to_float(row.get("potential_min_pct"), 0.0),
                        "central_pct": _to_float(row.get("potential_central_pct"), 0.0),
                        "max_pct": _to_float(row.get("potential_max_pct"), 0.0),
                    },
                    "transfer_params": transfer_params if lever_type == "transfer" else {},
                    "ramp": {
                        "default_start_year": int(_to_float(row.get("default_start_year"), 0) or 0),
                        "default_duration_years": int(_to_float(row.get("default_duration_years"), 0) or 0),
                        "curve": str(row.get("curve", "")).strip(),
                    },
                    "cost_model": {
                        "capex_by_year": _parse_json_cell(row.get("capex_by_year")),
                        "opex_by_year": _parse_json_cell(row.get("opex_by_year")),
                        "savings_by_year": _parse_json_cell(row.get("savings_by_year")),
                        "headcount_by_year": _parse_json_cell(row.get("headcount_by_year")),
                    },
                    "uncertainty": str(row.get("uncertainty", "")).strip(),
                    "evidence_snippets": [],
                }
            )
    else:
        raise ValueError(f"Unsupported lever library file type: {path.suffix}")

    is_valid, errors = validate_lever_library(levers)
    if not is_valid:
        raise ValueError(f"Lever library validation failed: {errors}")
    return levers


def validate_company_profile(profile: dict) -> tuple[bool, list[str]]:
    """Validate company profile schema. Returns (is_valid, error_messages)."""
    errors: list[str] = []
    required = ["company_id", "name", "sector", "base_year", "horizon_year", "growth_assumptions", "business_units"]
    for field in required:
        if field not in profile:
            errors.append(f"Missing company field: {field}")
    if "base_year" in profile and "horizon_year" in profile:
        if profile["base_year"] >= profile["horizon_year"]:
            errors.append("base_year must be less than horizon_year")
    growth = profile.get("growth_assumptions", {})
    if "annual_growth_rate" not in growth:
        errors.append("growth_assumptions.annual_growth_rate is required")
    business_units = profile.get("business_units", [])
    if not isinstance(business_units, list) or len(business_units) == 0:
        errors.append("business_units must be a non-empty list")
    else:
        for bu in business_units:
            if "bu_id" not in bu or "name" not in bu:
                errors.append("Each business unit must include bu_id and name")
                break
    finance = profile.get("finance", {})
    if finance:
        wacc = finance.get("wacc")
        if wacc is None or wacc <= 0:
            errors.append("finance.wacc must be > 0")
    return (len(errors) == 0, errors)


def validate_baseline_footprint(baseline: dict) -> tuple[bool, list[str]]:
    """Validate baseline footprint schema."""
    errors: list[str] = []
    if "inventory_method" not in baseline:
        errors.append("Missing inventory_method")
    emissions = baseline.get("emissions_by_category", [])
    if not isinstance(emissions, list) or len(emissions) == 0:
        errors.append("emissions_by_category must be a non-empty list")
    for item in emissions:
        for field in ["category_id", "scope", "category_name", "base_year_tco2e"]:
            if field not in item:
                errors.append(f"Missing baseline field: {field}")
        scope = item.get("scope")
        if scope not in {"S1", "S2", "S3"}:
            errors.append(f"Invalid scope: {scope}")
        base_year_tco2e = item.get("base_year_tco2e", 0)
        if base_year_tco2e is None or base_year_tco2e < 0:
            errors.append("base_year_tco2e must be >= 0")
        bu_split = item.get("bu_split")
        if isinstance(bu_split, dict) and bu_split:
            total = sum(bu_split.values())
            if abs(total - 1.0) > 1e-6:
                errors.append(f"bu_split must sum to 1.0 for {item.get('category_id')}")
    return (len(errors) == 0, errors)


def validate_lever_library(levers: list) -> tuple[bool, list[str]]:
    """Validate lever library schema."""
    errors: list[str] = []
    if not isinstance(levers, list) or len(levers) == 0:
        return False, ["Lever library must be a non-empty list"]
    for lever in levers:
        for field in ["lever_id", "title", "lever_type", "scope_targets", "category_targets", "potential", "ramp", "cost_model"]:
            if field not in lever:
                errors.append(f"Missing lever field: {field}")
        lever_type = lever.get("lever_type")
        if lever_type not in {"quantity", "transfer", "specification"}:
            errors.append(f"Invalid lever_type: {lever_type}")
        potential = lever.get("potential", {})
        min_pct = potential.get("min_pct")
        central_pct = potential.get("central_pct")
        max_pct = potential.get("max_pct")
        if min_pct is None or central_pct is None or max_pct is None:
            errors.append(f"Lever {lever.get('lever_id')} missing potential values")
        elif not (min_pct <= central_pct <= max_pct):
            errors.append(f"Lever {lever.get('lever_id')} potential range invalid")
        ramp = lever.get("ramp", {})
        if ramp.get("curve") not in {"linear", "s_curve"}:
            errors.append(f"Lever {lever.get('lever_id')} invalid ramp curve")
        if lever_type == "transfer":
            transfer_params = lever.get("transfer_params", {})
            if "low_carbon_intensity_ratio" not in transfer_params or "max_share_shift" not in transfer_params:
                errors.append(f"Lever {lever.get('lever_id')} missing transfer_params")
    return (len(errors) == 0, errors)
