from datetime import datetime
from typing import Any

import pandas as pd


def export_scenario_to_csv(
    annual_results: dict[int, dict[str, float]],
    macc_results: list[dict],
    output_path: str,
):
    """Export annual trajectory and MACC results to CSV."""
    # Export annual trajectory
    annual_rows = []
    for year, values in annual_results.items():
        row = {"year": year}
        row.update(values)
        annual_rows.append(row)
    annual_df = pd.DataFrame(annual_rows).sort_values("year")
    annual_df.to_csv(output_path, index=False)

    # Export MACC results with proper column names
    if macc_results:
        macc_df = pd.DataFrame(macc_results)
        
        # Rename columns to include units
        column_renames = {
            "mac": "mac_usd_per_tco2e",
            "npv_cost": "npv_cost_usd",
            "disc_abatement": "disc_abatement_tco2e",
            "cum_abatement": "cum_abatement_tco2e",
            "payback_years": "payback_years",
        }
        macc_df = macc_df.rename(columns=column_renames)
        
        # Select and order columns for export
        export_columns = [
            "lever_id",
            "title",
            "lever_type",
            "mac_usd_per_tco2e",
            "npv_cost_usd",
            "disc_abatement_tco2e",
            "cum_abatement_tco2e",
            "payback_years",
            "roi_bucket",
            "status",
            "bu_id",
        ]
        available_columns = [c for c in export_columns if c in macc_df.columns]
        macc_df = macc_df[available_columns]
        
        macc_path = output_path.replace(".csv", "_macc.csv")
        macc_df.to_csv(macc_path, index=False)


def generate_assumptions_log(
    company_profile: dict,
    baseline: dict,
    target_settings: dict,
    lever_selections: list[dict],
) -> str:
    """Generate text log of all assumptions used in scenario."""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("SCENARIO ASSUMPTIONS LOG")
    lines.append("=" * 60)
    lines.append(f"")
    lines.append(f"Generated: {datetime.utcnow().isoformat()}Z")
    lines.append(f"")
    lines.append("--- Company Profile ---")
    lines.append(f"Company ID: {company_profile.get('company_id')}")
    lines.append(f"Company Name: {company_profile.get('name')}")
    lines.append(f"Sector: {company_profile.get('sector')}")
    lines.append(f"Base Year: {company_profile.get('base_year')}")
    lines.append(f"Horizon Year: {company_profile.get('horizon_year')}")
    lines.append(f"")
    lines.append("--- Financial Parameters ---")
    lines.append(f"WACC: {company_profile.get('finance', {}).get('wacc', 0.08):.1%}")
    lines.append(f"Currency: {company_profile.get('finance', {}).get('currency', 'USD')}")
    lines.append(f"Cost Units: Input data in USD millions, converted to USD for calculations")
    lines.append(f"")
    lines.append("--- Target Settings ---")
    lines.append(f"SBTi Pathway: {target_settings.get('pathway')}")
    reduction_rate = 0.025 if target_settings.get('pathway') == 'WB2C' else 0.042
    lines.append(f"Annual Reduction Rate: {reduction_rate:.1%}")
    lines.append(f"")
    lines.append("--- Lever Selections ---")
    for selection in lever_selections:
        lines.append(f"")
        lines.append(f"  Lever: {selection.get('lever_id')}")
        lines.append(f"    Status: {selection.get('status')}")
        lines.append(f"    Start Year: {selection.get('start_year')}")
        lines.append(f"    Ramp Duration: {selection.get('ramp_years')} years")
        lines.append(f"    Business Unit: {selection.get('bu_id')}")
    lines.append(f"")
    lines.append("=" * 60)
    return "\n".join(lines)
