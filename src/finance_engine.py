from typing import Any

# Cost unit multiplier: dataset costs are in USD millions
COST_UNIT_MULTIPLIER = 1_000_000


def compute_discount_factor(year: int, start_year: int, wacc: float) -> float:
    """Compute discount factor: 1 / (1 + WACC)^(year - start_year)."""
    return 1.0 / ((1.0 + wacc) ** (year - start_year))


def _get_year_value(value_map: dict[str, Any], year: int) -> float:
    if not value_map:
        return 0.0
    if year in value_map:
        return float(value_map[year])
    year_str = str(year)
    if year_str in value_map:
        return float(value_map[year_str])
    return 0.0


def compute_lever_cashflows(
    lever: dict,
    lever_selection: dict,
    base_year: int,
    horizon_year: int,
) -> dict[int, dict[str, float]]:
    """Compute annual cashflows (capex, opex, savings) for a lever.
    
    Note: Input costs are in USD millions; output is converted to USD.
    """
    cost_model = lever.get("cost_model", {})
    capex_by_year = cost_model.get("capex_by_year", {})
    opex_by_year = cost_model.get("opex_by_year", {})
    savings_by_year = cost_model.get("savings_by_year", {})

    cashflows: dict[int, dict[str, float]] = {}
    for year in range(base_year, horizon_year + 1):
        # Convert from USD millions to USD
        capex = _get_year_value(capex_by_year, year) * COST_UNIT_MULTIPLIER
        opex = _get_year_value(opex_by_year, year) * COST_UNIT_MULTIPLIER
        savings = _get_year_value(savings_by_year, year) * COST_UNIT_MULTIPLIER
        net_cost = capex + opex - savings
        cashflows[year] = {
            "capex": capex,
            "opex": opex,
            "savings": savings,
            "net_cost": net_cost,
        }
    return cashflows


def compute_lever_npv(
    cashflows: dict[int, dict[str, float]],
    start_year: int,
    wacc: float,
) -> float:
    """Compute NPV of lever costs (discounted). Returns value in USD."""
    npv = 0.0
    for year, values in cashflows.items():
        npv += compute_discount_factor(year, start_year, wacc) * values.get("net_cost", 0.0)
    return npv


def compute_payback_years(
    cashflows: dict[int, dict[str, float]],
    start_year: int,
    wacc: float,
) -> float | None:
    """Compute discounted payback period in years.
    
    Payback is the first year where cumulative net benefit becomes positive
    AFTER having been negative (i.e., after initial investment).
    """
    cumulative = 0.0
    has_invested = False  # Track if we've had net costs (investment)
    
    for year in sorted(cashflows.keys()):
        net_cost = cashflows[year].get("net_cost", 0.0)
        discounted_benefit = compute_discount_factor(year, start_year, wacc) * (-net_cost)
        cumulative += discounted_benefit
        
        # Track if we've made an investment (cumulative went negative)
        if cumulative < 0:
            has_invested = True
        
        # Payback occurs when cumulative becomes positive AFTER investment
        if has_invested and cumulative >= 0:
            return float(year - start_year)
    
    # Never paid back
    return None


def compute_roi_bucket(payback_years: float | None) -> str:
    """Classify ROI bucket."""
    if payback_years is None:
        return "non_payback"
    if payback_years < 5:
        return "<5y"
    return ">=5y"


def compute_financial_metrics_all_levers(
    lever_library: list[dict],
    lever_selections: list[dict],
    base_year: int,
    horizon_year: int,
    wacc: float,
) -> dict[str, dict]:
    """Compute financial metrics for all selected levers."""
    metrics: dict[str, dict] = {}
    lever_by_id = {lever.get("lever_id"): lever for lever in lever_library}
    for selection in lever_selections:
        lever_id = selection.get("lever_id")
        lever = lever_by_id.get(lever_id)
        if not lever:
            continue
        cashflows = compute_lever_cashflows(lever, selection, base_year, horizon_year)
        npv = compute_lever_npv(cashflows, base_year, wacc)
        payback = compute_payback_years(cashflows, base_year, wacc)
        roi_bucket = compute_roi_bucket(payback)
        metrics[lever_id] = {
            "npv": npv,
            "payback": payback,
            "roi_bucket": roi_bucket,
            "cashflows": cashflows,
        }
    return metrics
