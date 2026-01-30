#!/usr/bin/env python3
"""Standalone script to verify MACC calculations.

Run: python verify_macc.py

Expected output:
- MAC values in range -500 to +500 $/tCO2e for most levers
- Different disc_abatement values for different levers
- Payback years that vary (not all 0)
- Sanity checks should pass
"""

from src.data_loader import load_baseline_footprint, load_company_profile, load_lever_library
from src.bau_engine import compute_bau_pathway_all_categories
from src.finance_engine import compute_financial_metrics_all_levers, COST_UNIT_MULTIPLIER
from src.macc_engine import (
    compute_macc_all_levers,
    print_macc_diagnostics,
    run_macc_sanity_checks,
)


def main():
    print("=" * 80)
    print("MACC VERIFICATION SCRIPT")
    print("=" * 80)
    
    # Load data
    print("\n1. Loading demo data...")
    profile = load_company_profile("ready_to_implement_demo_dataset/company_profile.json")
    baseline = load_baseline_footprint("ready_to_implement_demo_dataset/baseline_footprint.json")
    levers = load_lever_library("ready_to_implement_demo_dataset/lever_library.json")
    
    print(f"   Company: {profile['name']}")
    print(f"   Base year: {profile['base_year']}, Horizon: {profile['horizon_year']}")
    print(f"   WACC: {profile['finance']['wacc']:.1%}")
    print(f"   Levers loaded: {len(levers)}")
    print(f"   Cost unit multiplier: {COST_UNIT_MULTIPLIER:,} (costs are in USD millions)")
    
    # Create lever selections (all levers)
    lever_selections = []
    for lever in levers:
        lever_selections.append({
            "lever_id": lever["lever_id"],
            "bu_id": "ALL",
            "status": "assessed",
            "start_year": lever["ramp"]["default_start_year"],
            "ramp_years": lever["ramp"]["default_duration_years"],
            "commitment_by_year_pct": {},
        })
    
    print(f"\n2. Computing BAU pathway...")
    bau_by_cat = compute_bau_pathway_all_categories(
        baseline, profile, profile["base_year"], profile["horizon_year"]
    )
    
    total_baseline = sum(c["base_year_tco2e"] for c in baseline["emissions_by_category"])
    print(f"   Total baseline emissions (2024): {total_baseline:,.0f} tCO2e")
    
    print(f"\n3. Computing financial metrics...")
    wacc = profile.get("finance", {}).get("wacc", 0.08)
    financial_metrics = compute_financial_metrics_all_levers(
        levers,
        lever_selections,
        profile["base_year"],
        profile["horizon_year"],
        wacc,
    )
    
    print(f"   Computed for {len(financial_metrics)} levers")
    
    # Show sample NPV values
    print("\n   Sample NPV values (should be in USD, not micro-units):")
    for lever_id in list(financial_metrics.keys())[:3]:
        npv = financial_metrics[lever_id]["npv"]
        payback = financial_metrics[lever_id]["payback"]
        roi = financial_metrics[lever_id]["roi_bucket"]
        payback_str = f"{payback:.1f}" if payback is not None else "Never"
        print(f"   - {lever_id}: NPV=${npv:,.0f}, Payback={payback_str}y, ROI={roi}")
    
    print(f"\n4. Computing MACC...")
    macc_results = compute_macc_all_levers(
        levers,
        lever_selections,
        {},  # net_emissions not used for standalone calc
        bau_by_cat,
        financial_metrics,
        profile["base_year"],
        profile["horizon_year"],
        wacc,
    )
    
    # Print detailed diagnostics
    print_macc_diagnostics(macc_results, top_n=len(macc_results))
    
    # Verify key assertions
    print("\n5. Running verification checks...")
    
    # Check 1: MAC values in reasonable range
    finite_macs = [r["mac"] for r in macc_results if abs(r["mac"]) < float("inf")]
    if all(abs(m) > 0.1 for m in finite_macs):
        print("   ✓ MAC values are not micro-units (all |MAC| > 0.1)")
    else:
        print("   ✗ MAC values look like micro-units!")
    
    # Check 2: Different disc_abatement values
    disc_abatements = [r["disc_abatement"] for r in macc_results]
    unique_abatements = len(set(round(a, 2) for a in disc_abatements))
    if unique_abatements > 1:
        print(f"   ✓ disc_abatement varies ({unique_abatements} unique values)")
    else:
        print("   ✗ All disc_abatement values are identical!")
    
    # Check 3: Payback not all zero
    paybacks = [r["payback_years"] for r in macc_results]
    non_zero_paybacks = [p for p in paybacks if p is not None and p != 0]
    if len(non_zero_paybacks) > 0:
        print(f"   ✓ Payback varies ({len(non_zero_paybacks)} levers with non-zero payback)")
    else:
        print("   ✗ All payback values are 0!")
    
    # Check 4: Sanity checks
    warnings = run_macc_sanity_checks(macc_results)
    if not warnings:
        print("   ✓ All sanity checks passed")
    else:
        print(f"   ✗ Sanity check warnings: {len(warnings)}")
        for w in warnings:
            print(f"     - {w}")
    
    print("\n" + "=" * 80)
    print("VERIFICATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
