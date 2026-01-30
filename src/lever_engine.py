from typing import Any

from src.utils import get_ramp_commitment


def _clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    return max(min_value, min(max_value, value))


def _get_selection_for_lever(lever_id: str, lever_selections: list[dict]) -> dict | None:
    for selection in lever_selections:
        if selection.get("lever_id") == lever_id:
            return selection
    return None


def _get_commitment_for_year(selection: dict, lever: dict, year: int) -> float:
    commitment_by_year = selection.get("commitment_by_year_pct", {})
    if commitment_by_year:
        if year in commitment_by_year:
            return _clamp(float(commitment_by_year[year]))
        year_str = str(year)
        if year_str in commitment_by_year:
            return _clamp(float(commitment_by_year[year_str]))
    return _clamp(
        get_ramp_commitment(
            lever,
            year,
            start_year_override=selection.get("start_year"),
            duration_override=selection.get("ramp_years"),
        )
    )


def _get_effective_potential(lever: dict, selection: dict | None) -> float:
    if selection and selection.get("override_potential_pct") is not None:
        return _clamp(float(selection["override_potential_pct"]))
    return _clamp(float(lever.get("potential", {}).get("central_pct", 0.0)))


def apply_quantity_levers(
    bau_emissions: float,
    quantity_levers: list[dict],
    year: int,
    commitment_by_lever: dict[str, float],
    potential_by_lever: dict[str, float],
) -> float:
    """Apply quantity levers multiplicatively to reduce base emissions."""
    multiplier = 1.0
    for lever in quantity_levers:
        lever_id = lever.get("lever_id")
        potential = potential_by_lever.get(lever_id, 0.0)
        commitment = commitment_by_lever.get(lever_id, 0.0)
        effective_frac = _clamp(potential * commitment)
        multiplier *= (1 - effective_frac)
    return bau_emissions * multiplier


def apply_transfer_levers(
    emissions_after_quantity: float,
    transfer_levers: list[dict],
    year: int,
    commitment_by_lever: dict[str, float],
    potential_by_lever: dict[str, float],
) -> float:
    """Apply transfer levers to shift share to low-carbon alternative."""
    shifted = 0.0
    multiplier = 1.0
    for lever in transfer_levers:
        lever_id = lever.get("lever_id")
        potential = potential_by_lever.get(lever_id, 0.0)
        commitment = commitment_by_lever.get(lever_id, 0.0)
        transfer_params = lever.get("transfer_params", {})
        low_carbon_ratio = float(transfer_params.get("low_carbon_intensity_ratio", 1.0))
        max_share_shift = float(transfer_params.get("max_share_shift", 1.0))

        remaining_share = max(0.0, 1.0 - shifted)
        desired_shift = _clamp(potential * commitment, 0.0, max_share_shift)
        eff_share = min(desired_shift, remaining_share)
        multiplier *= (1 - eff_share * (1 - low_carbon_ratio))
        shifted += eff_share
    return emissions_after_quantity * multiplier


def apply_specification_levers(
    emissions_after_transfer: float,
    spec_levers: list[dict],
    year: int,
    commitment_by_lever: dict[str, float],
    potential_by_lever: dict[str, float],
) -> float:
    """Apply specification levers to reduce intensity."""
    multiplier = 1.0
    for lever in spec_levers:
        lever_id = lever.get("lever_id")
        potential = potential_by_lever.get(lever_id, 0.0)
        commitment = commitment_by_lever.get(lever_id, 0.0)
        effective_frac = _clamp(potential * commitment)
        multiplier *= (1 - effective_frac)
    return emissions_after_transfer * multiplier


def compute_net_emissions_category(
    bau_by_year: dict[int, float],
    levers: list[dict],
    lever_selections: list[dict],
    base_year: int,
    horizon_year: int,
) -> dict[int, float]:
    """Compute net emissions for a category after applying levers."""
    net: dict[int, float] = {}
    selection_by_lever_id: dict[str, dict] = {
        sel.get("lever_id"): sel for sel in lever_selections if sel.get("lever_id")
    }

    quantity_levers = [l for l in levers if l.get("lever_type") == "quantity"]
    transfer_levers = [l for l in levers if l.get("lever_type") == "transfer"]
    spec_levers = [l for l in levers if l.get("lever_type") == "specification"]

    for year in range(base_year, horizon_year + 1):
        commitment_by_lever: dict[str, float] = {}
        potential_by_lever: dict[str, float] = {}
        for lever in levers:
            lever_id = lever.get("lever_id")
            selection = selection_by_lever_id.get(lever_id, {})
            commitment_by_lever[lever_id] = _get_commitment_for_year(selection, lever, year)
            potential_by_lever[lever_id] = _get_effective_potential(lever, selection)

        bau_value = bau_by_year.get(year, 0.0)
        after_quantity = apply_quantity_levers(
            bau_value, quantity_levers, year, commitment_by_lever, potential_by_lever
        )
        after_transfer = apply_transfer_levers(
            after_quantity, transfer_levers, year, commitment_by_lever, potential_by_lever
        )
        after_spec = apply_specification_levers(
            after_transfer, spec_levers, year, commitment_by_lever, potential_by_lever
        )
        net[year] = after_spec

    return net


def compute_net_emissions_all_categories(
    bau_by_category: dict[str, dict[int, float]],
    lever_library: list[dict],
    lever_selections: list[dict],
    baseline: dict,
    base_year: int,
    horizon_year: int,
) -> dict[str, dict[int, float]]:
    """Compute net emissions for all categories."""
    net_by_category: dict[str, dict[int, float]] = {}
    for category in baseline.get("emissions_by_category", []):
        category_id = category.get("category_id")
        levers_for_category = [
            lever
            for lever in lever_library
            if category_id in lever.get("category_targets", [])
        ]
        net_by_category[category_id] = compute_net_emissions_category(
            bau_by_category.get(category_id, {}),
            levers_for_category,
            lever_selections,
            base_year,
            horizon_year,
        )
    return net_by_category


def compute_abatement(
    bau_by_year: dict[int, float],
    net_by_year: dict[int, float],
) -> dict[int, float]:
    """Compute annual abatement (BAU - Net)."""
    return {year: bau_by_year.get(year, 0.0) - net_by_year.get(year, 0.0) for year in bau_by_year}
