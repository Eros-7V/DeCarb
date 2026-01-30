def compute_target_pathway_aca(
    base_year_emissions: float,
    base_year: int,
    horizon_year: int,
    annual_reduction_rate: float,
) -> dict[int, float]:
    """Compute ACA target pathway. Returns {year: target_emissions}."""
    targets: dict[int, float] = {}
    for year in range(base_year, horizon_year + 1):
        t = year - base_year
        targets[year] = base_year_emissions * ((1 - annual_reduction_rate) ** t)
    return targets


def get_sbti_reduction_rate(pathway: str) -> float:
    """Get annual reduction rate for SBTi pathway."""
    if pathway == "WB2C":
        return 0.025
    if pathway == "1.5C":
        return 0.042
    raise ValueError(f"Unknown pathway: {pathway}")


def compute_category_targets(
    baseline: dict,
    base_year: int,
    horizon_year: int,
    pathway: str,
) -> dict[str, dict[int, float]]:
    """Compute target pathway for each emission category."""
    targets: dict[str, dict[int, float]] = {}
    rate = get_sbti_reduction_rate(pathway)
    for category in baseline.get("emissions_by_category", []):
        category_id = category.get("category_id")
        base_year_tco2e = category.get("base_year_tco2e", 0.0)
        targets[category_id] = compute_target_pathway_aca(
            base_year_tco2e, base_year, horizon_year, rate
        )
    return targets


def aggregate_target_pathway(targets_by_category: dict[str, dict[int, float]]) -> dict[int, float]:
    """Aggregate target pathway across categories."""
    total: dict[int, float] = {}
    for category_targets in targets_by_category.values():
        for year, value in category_targets.items():
            total[year] = total.get(year, 0.0) + value
    return total


def compute_gap_to_target(
    net_emissions: dict[int, float],
    target_emissions: dict[int, float],
) -> dict[int, float]:
    """Compute annual gap (net - target). Positive = above target."""
    gap: dict[int, float] = {}
    for year, net_value in net_emissions.items():
        gap[year] = net_value - target_emissions.get(year, 0.0)
    return gap
