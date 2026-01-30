"""MACC (Marginal Abatement Cost Curve) engine.

Computes standalone lever abatement and MAC for proper MACC ranking.
"""

from src.finance_engine import compute_discount_factor
from src.lever_engine import compute_net_emissions_category


def compute_discounted_abatement(
    abatement_by_year: dict[int, float],
    start_year: int,
    wacc: float,
) -> float:
    """Compute discounted abatement (sum of discounted annual abatement)."""
    total = 0.0
    for year, value in abatement_by_year.items():
        total += compute_discount_factor(year, start_year, wacc) * value
    return total


def compute_mac(npv_cost: float, discounted_abatement: float) -> float:
    """Compute Marginal Abatement Cost: NPV_cost / discounted_abatement.
    
    Args:
        npv_cost: Net present value of costs in USD
        discounted_abatement: Discounted abatement in tCO2e
    
    Returns:
        MAC in $/tCO2e
    """
    if discounted_abatement == 0:
        return float("inf")
    return npv_cost / discounted_abatement


def compute_standalone_lever_abatement(
    lever: dict,
    lever_selection: dict,
    bau_by_category: dict[str, dict[int, float]],
    base_year: int,
    horizon_year: int,
) -> dict[int, float]:
    """Compute abatement for a single lever applied in isolation.
    
    This gives the standalone effect of the lever for proper MACC ranking,
    avoiding the issue of using scenario-level abatement which conflates
    multiple lever effects.
    """
    category_targets = lever.get("category_targets", [])
    if not category_targets:
        return {year: 0.0 for year in range(base_year, horizon_year + 1)}
    
    # Apply ONLY this lever to compute its standalone effect
    single_lever_selection = [lever_selection]
    
    abatement_by_year: dict[int, float] = {
        year: 0.0 for year in range(base_year, horizon_year + 1)
    }
    
    for category_id in category_targets:
        bau_by_year = bau_by_category.get(category_id, {})
        if not bau_by_year:
            continue
        
        # Compute net emissions with ONLY this lever
        net_by_year = compute_net_emissions_category(
            bau_by_year,
            [lever],  # Only this lever
            single_lever_selection,
            base_year,
            horizon_year,
        )
        
        # Add category abatement to total
        for year in range(base_year, horizon_year + 1):
            bau_val = bau_by_year.get(year, 0.0)
            net_val = net_by_year.get(year, 0.0)
            abatement_by_year[year] += max(0.0, bau_val - net_val)
    
    return abatement_by_year


def compute_macc_all_levers(
    lever_library: list[dict],
    lever_selections: list[dict],
    net_emissions_by_category: dict[str, dict[int, float]],  # Kept for API compat
    bau_by_category: dict[str, dict[int, float]],
    financial_metrics: dict[str, dict],
    base_year: int,
    horizon_year: int,
    wacc: float,
) -> list[dict]:
    """Compute MACC metrics for all levers and rank by MAC.
    
    Uses standalone lever abatement for proper MACC ranking.
    """
    lever_by_id = {lever.get("lever_id"): lever for lever in lever_library}
    selection_by_id = {sel.get("lever_id"): sel for sel in lever_selections}
    
    results: list[dict] = []
    for selection in lever_selections:
        lever_id = selection.get("lever_id")
        lever = lever_by_id.get(lever_id)
        if not lever:
            continue
        
        # Compute STANDALONE abatement for this lever
        abatement_by_year = compute_standalone_lever_abatement(
            lever,
            selection,
            bau_by_category,
            base_year,
            horizon_year,
        )
        
        disc_abatement = compute_discounted_abatement(abatement_by_year, base_year, wacc)
        npv_cost = financial_metrics.get(lever_id, {}).get("npv", 0.0)
        mac = compute_mac(npv_cost, disc_abatement)
        cum_abatement = sum(abatement_by_year.values())
        payback_years = financial_metrics.get(lever_id, {}).get("payback")
        roi_bucket = financial_metrics.get(lever_id, {}).get("roi_bucket")

        results.append(
            {
                "lever_id": lever_id,
                "title": lever.get("title"),
                "lever_type": lever.get("lever_type"),
                "category_targets": lever.get("category_targets", []),
                "mac": mac,
                "npv_cost": npv_cost,
                "disc_abatement": disc_abatement,
                "cum_abatement": cum_abatement,
                "payback_years": payback_years,
                "roi_bucket": roi_bucket,
                "status": selection.get("status"),
                "bu_id": selection.get("bu_id"),
            }
        )

    results.sort(key=lambda r: r["mac"])
    return results


def prepare_macc_curve_data(macc_results: list[dict]) -> list[dict]:
    """Prepare data for MACC bar chart.
    
    Returns list of dicts with x_start, x_end, y (MAC), lever_id for bar rendering.
    Sorted by MAC ascending.
    """
    sorted_results = sorted(macc_results, key=lambda r: r["mac"])
    cumulative = 0.0
    bar_data: list[dict] = []
    
    for row in sorted_results:
        width = row.get("disc_abatement", 0.0)
        mac = row.get("mac", 0.0)
        
        # Skip infinite MAC levers
        if mac == float("inf") or mac == float("-inf"):
            continue
        
        bar_data.append({
            "lever_id": row.get("lever_id"),
            "title": row.get("title"),
            "x_start": cumulative,
            "x_end": cumulative + width,
            "width": width,
            "mac": mac,
        })
        cumulative += width
    
    return bar_data


def run_macc_sanity_checks(macc_results: list[dict]) -> list[str]:
    """Run sanity checks on MACC results and return warnings."""
    warnings = []
    
    # Check for suspiciously small MAC values (unit bug indicator)
    finite_macs = [r["mac"] for r in macc_results if abs(r["mac"]) < float("inf")]
    if finite_macs and all(abs(m) < 0.01 for m in finite_macs):
        warnings.append(
            f"WARNING: All MAC values are < 0.01 (max={max(finite_macs):.6f}). "
            "This suggests a unit conversion bug."
        )
    
    # Check for identical disc_abatement across different levers
    abatements = {}
    for r in macc_results:
        lever_id = r["lever_id"]
        disc_abatement = r["disc_abatement"]
        if disc_abatement > 0:
            if disc_abatement in abatements:
                warnings.append(
                    f"WARNING: {lever_id} has same disc_abatement ({disc_abatement:.2f}) "
                    f"as {abatements[disc_abatement]}. Check standalone calculation."
                )
            abatements[disc_abatement] = lever_id
    
    # Check for reasonable MAC range for this demo (-2000 to 2000)
    for r in macc_results:
        mac = r["mac"]
        if mac != float("inf") and abs(mac) > 5000:
            warnings.append(
                f"WARNING: {r['lever_id']} has unusual MAC={mac:.2f}. "
                "Expected range is roughly -2000 to 2000 for this demo."
            )
    
    return warnings


def print_macc_diagnostics(macc_results: list[dict], top_n: int = 5) -> None:
    """Print diagnostic table for MACC results."""
    print("\n" + "=" * 80)
    print("MACC DIAGNOSTICS - Top levers by MAC (ascending)")
    print("=" * 80)
    print(f"{'Lever ID':<30} {'NPV (USD)':<15} {'Disc Abate':<15} {'MAC ($/t)':<12} {'Payback':<10}")
    print("-" * 80)
    
    sorted_results = sorted(macc_results, key=lambda r: r["mac"])
    for r in sorted_results[:top_n]:
        mac_str = f"{r['mac']:.2f}" if r['mac'] != float('inf') else "inf"
        payback_str = f"{r['payback_years']:.1f}" if r['payback_years'] is not None else "N/A"
        print(
            f"{r['lever_id']:<30} "
            f"{r['npv_cost']:>14,.0f} "
            f"{r['disc_abatement']:>14,.0f} "
            f"{mac_str:>11} "
            f"{payback_str:>9}"
        )
    
    print("-" * 80)
    
    # Run and print sanity checks
    warnings = run_macc_sanity_checks(macc_results)
    if warnings:
        print("\nSANITY CHECK WARNINGS:")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("\nSanity checks passed.")
    print("=" * 80 + "\n")
