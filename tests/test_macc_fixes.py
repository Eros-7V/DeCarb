"""Tests for MACC calculation fixes.

Verifies:
1. Cost units are in USD (not USD millions)
2. disc_abatement differs across levers with different potentials
3. payback_years is not always 0
4. MAC values are in reasonable range ($/tCO2e)
"""

import pytest

from src.data_loader import load_baseline_footprint, load_company_profile, load_lever_library
from src.bau_engine import compute_bau_pathway_all_categories
from src.finance_engine import (
    compute_financial_metrics_all_levers,
    compute_lever_cashflows,
    compute_payback_years,
    COST_UNIT_MULTIPLIER,
)
from src.macc_engine import (
    compute_macc_all_levers,
    compute_standalone_lever_abatement,
    run_macc_sanity_checks,
)


@pytest.fixture
def demo_data():
    """Load demo dataset."""
    profile = load_company_profile("ready_to_implement_demo_dataset/company_profile.json")
    baseline = load_baseline_footprint("ready_to_implement_demo_dataset/baseline_footprint.json")
    levers = load_lever_library("ready_to_implement_demo_dataset/lever_library.json")
    return profile, baseline, levers


@pytest.fixture
def lever_selections(demo_data):
    """Create lever selections for first 5 levers."""
    profile, baseline, levers = demo_data
    selections = []
    for lever in levers[:5]:
        selections.append({
            "lever_id": lever["lever_id"],
            "bu_id": "ALL",
            "status": "assessed",
            "start_year": lever["ramp"]["default_start_year"],
            "ramp_years": lever["ramp"]["default_duration_years"],
            "commitment_by_year_pct": {},
        })
    return selections


class TestCostUnits:
    """Test that cost units are properly converted."""
    
    def test_cost_multiplier_is_million(self):
        """Verify cost multiplier is 1,000,000."""
        assert COST_UNIT_MULTIPLIER == 1_000_000
    
    def test_cashflows_in_usd(self, demo_data):
        """Verify cashflows are converted to USD from USD millions."""
        profile, baseline, levers = demo_data
        lever = levers[0]  # L01_PUE_Optimization
        
        # Raw data has capex 2.0 in 2025 (USD millions)
        raw_capex_2025 = lever["cost_model"]["capex_by_year"].get("2025", 0)
        assert raw_capex_2025 == 2.0, "Expected 2.0 USD millions in raw data"
        
        selection = {
            "lever_id": lever["lever_id"],
            "start_year": 2025,
            "ramp_years": 3,
        }
        cashflows = compute_lever_cashflows(lever, selection, 2024, 2034)
        
        # Converted should be 2,000,000 USD
        assert cashflows[2025]["capex"] == 2_000_000, \
            f"Expected 2,000,000 USD, got {cashflows[2025]['capex']}"
    
    def test_npv_in_usd(self, demo_data, lever_selections):
        """Verify NPV is in USD (not micro-units)."""
        profile, baseline, levers = demo_data
        
        metrics = compute_financial_metrics_all_levers(
            levers,
            lever_selections,
            profile["base_year"],
            profile["horizon_year"],
            profile.get("finance", {}).get("wacc", 0.08),
        )
        
        for lever_id, m in metrics.items():
            npv = m["npv"]
            # NPV should be in reasonable USD range (millions range for these levers)
            assert abs(npv) > 100, f"NPV for {lever_id} looks too small: {npv}"
            assert abs(npv) < 1e10, f"NPV for {lever_id} looks too large: {npv}"


class TestDiscountedAbatement:
    """Test that disc_abatement is computed correctly per lever."""
    
    def test_standalone_abatement_differs_by_lever(self, demo_data, lever_selections):
        """Verify different levers have different standalone abatement."""
        profile, baseline, levers = demo_data
        
        bau_by_cat = compute_bau_pathway_all_categories(
            baseline, profile, profile["base_year"], profile["horizon_year"]
        )
        
        abatements = {}
        for selection in lever_selections:
            lever_id = selection["lever_id"]
            lever = next(l for l in levers if l["lever_id"] == lever_id)
            
            abatement_by_year = compute_standalone_lever_abatement(
                lever,
                selection,
                bau_by_cat,
                profile["base_year"],
                profile["horizon_year"],
            )
            total = sum(abatement_by_year.values())
            abatements[lever_id] = total
        
        # Different levers should have different abatements
        unique_abatements = set(abatements.values())
        assert len(unique_abatements) > 1, \
            f"All levers have identical abatement: {abatements}"
    
    def test_macc_results_have_distinct_abatements(self, demo_data, lever_selections):
        """Verify MACC results don't all share the same disc_abatement."""
        profile, baseline, levers = demo_data
        
        bau_by_cat = compute_bau_pathway_all_categories(
            baseline, profile, profile["base_year"], profile["horizon_year"]
        )
        
        metrics = compute_financial_metrics_all_levers(
            levers,
            lever_selections,
            profile["base_year"],
            profile["horizon_year"],
            0.08,
        )
        
        macc_results = compute_macc_all_levers(
            levers,
            lever_selections,
            {},  # Not used anymore
            bau_by_cat,
            metrics,
            profile["base_year"],
            profile["horizon_year"],
            0.08,
        )
        
        disc_abatements = [r["disc_abatement"] for r in macc_results]
        unique = set(disc_abatements)
        
        # At least 2 distinct values expected
        assert len(unique) >= 2, \
            f"Expected distinct disc_abatement values, got: {disc_abatements}"


class TestPaybackCalculation:
    """Test that payback years is calculated correctly."""
    
    def test_payback_not_always_zero(self, demo_data, lever_selections):
        """Verify payback is not 0 for all levers."""
        profile, baseline, levers = demo_data
        
        metrics = compute_financial_metrics_all_levers(
            levers,
            lever_selections,
            profile["base_year"],
            profile["horizon_year"],
            0.08,
        )
        
        paybacks = [m["payback"] for m in metrics.values()]
        
        # Not all should be 0
        non_zero_or_none = [p for p in paybacks if p != 0]
        assert len(non_zero_or_none) > 0, \
            f"All payback values are 0: {paybacks}"
    
    def test_payback_requires_investment(self):
        """Verify payback requires initial investment (negative cumulative)."""
        # Cashflows with immediate savings only (no investment)
        cashflows_no_investment = {
            2024: {"net_cost": -100},  # Immediate savings
            2025: {"net_cost": -100},
            2026: {"net_cost": -100},
        }
        
        payback = compute_payback_years(cashflows_no_investment, 2024, 0.08)
        # Should be None because there was never an investment to pay back
        # (cumulative never went negative before going positive)
        # Actually, -net_cost = 100 (benefit), so cumulative = 100 at year 0
        # which is >= 0 but we never had investment (cumulative < 0)
        assert payback is None, \
            f"Expected None for no-investment case, got {payback}"
    
    def test_payback_with_upfront_capex(self):
        """Verify payback works correctly with upfront CapEx."""
        # Typical pattern: CapEx upfront, savings later (more savings to ensure payback)
        cashflows = {
            2024: {"net_cost": 0},       # No activity
            2025: {"net_cost": 1000},    # Investment (CapEx)
            2026: {"net_cost": 0},       # Break-even year
            2027: {"net_cost": -500},    # Savings start
            2028: {"net_cost": -500},    # More savings
            2029: {"net_cost": -500},    # Even more savings (cumulative pays back)
        }
        
        payback = compute_payback_years(cashflows, 2024, 0.08)
        assert payback is not None, "Expected payback to occur"
        assert payback > 0, f"Expected positive payback years, got {payback}"
        assert payback < 10, f"Payback seems too long: {payback}"


class TestMACValues:
    """Test that MAC values are in reasonable range."""
    
    def test_mac_in_reasonable_range(self, demo_data, lever_selections):
        """Verify MAC values are in $/tCO2e range, not micro-units."""
        profile, baseline, levers = demo_data
        
        bau_by_cat = compute_bau_pathway_all_categories(
            baseline, profile, profile["base_year"], profile["horizon_year"]
        )
        
        metrics = compute_financial_metrics_all_levers(
            levers,
            lever_selections,
            profile["base_year"],
            profile["horizon_year"],
            0.08,
        )
        
        macc_results = compute_macc_all_levers(
            levers,
            lever_selections,
            {},
            bau_by_cat,
            metrics,
            profile["base_year"],
            profile["horizon_year"],
            0.08,
        )
        
        finite_macs = [r["mac"] for r in macc_results if abs(r["mac"]) < float("inf")]
        
        # MAC should be in tens/hundreds of $/tCO2e for this demo
        assert all(abs(m) > 0.1 for m in finite_macs), \
            f"MAC values too small (unit bug?): {finite_macs}"
        
        assert all(abs(m) < 10000 for m in finite_macs), \
            f"MAC values too large: {finite_macs}"
    
    def test_sanity_checks_pass(self, demo_data, lever_selections):
        """Verify sanity checks don't flag unit bugs."""
        profile, baseline, levers = demo_data
        
        bau_by_cat = compute_bau_pathway_all_categories(
            baseline, profile, profile["base_year"], profile["horizon_year"]
        )
        
        metrics = compute_financial_metrics_all_levers(
            levers,
            lever_selections,
            profile["base_year"],
            profile["horizon_year"],
            0.08,
        )
        
        macc_results = compute_macc_all_levers(
            levers,
            lever_selections,
            {},
            bau_by_cat,
            metrics,
            profile["base_year"],
            profile["horizon_year"],
            0.08,
        )
        
        warnings = run_macc_sanity_checks(macc_results)
        
        # Should not have unit-related warnings
        unit_warnings = [w for w in warnings if "unit" in w.lower() or "0.01" in w]
        assert len(unit_warnings) == 0, \
            f"Sanity checks flagged unit issues: {unit_warnings}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
