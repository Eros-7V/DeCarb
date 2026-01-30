def compute_bau_pathway_category(
    base_year_emissions: float,
    base_year: int,
    horizon_year: int,
    growth_rate: float,
) -> dict[int, float]:
    """Compute BAU emissions for a category using growth rate."""
    bau: dict[int, float] = {}
    for year in range(base_year, horizon_year + 1):
        t = year - base_year
        bau[year] = base_year_emissions * ((1 + growth_rate) ** t)
    return bau


def compute_bau_pathway_all_categories(
    baseline: dict,
    company_profile: dict,
    base_year: int,
    horizon_year: int,
) -> dict[str, dict[int, float]]:
    """Compute BAU pathway for all categories."""
    bau: dict[str, dict[int, float]] = {}
    growth_assumptions = company_profile.get("growth_assumptions", {})
    category_growth = growth_assumptions.get("by_category_growth_rate", {})
    default_growth = growth_assumptions.get("annual_growth_rate", 0.0)
    for category in baseline.get("emissions_by_category", []):
        category_id = category.get("category_id")
        base_year_tco2e = category.get("base_year_tco2e", 0.0)
        growth = category_growth.get(category_id, default_growth)
        bau[category_id] = compute_bau_pathway_category(
            base_year_tco2e, base_year, horizon_year, growth
        )
    return bau


def aggregate_bau_pathway(bau_by_category: dict[str, dict[int, float]]) -> dict[int, float]:
    """Sum BAU emissions across all categories per year."""
    total: dict[int, float] = {}
    for category_bau in bau_by_category.values():
        for year, value in category_bau.items():
            total[year] = total.get(year, 0.0) + value
    return total
