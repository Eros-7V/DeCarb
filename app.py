from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.bau_engine import aggregate_bau_pathway, compute_bau_pathway_all_categories
from src.data_loader import load_baseline_footprint, load_company_profile, load_lever_library
from src.exporter import export_scenario_to_csv, generate_assumptions_log
from src.finance_engine import compute_financial_metrics_all_levers
from src.lever_engine import compute_abatement, compute_net_emissions_all_categories
from src.macc_engine import (
    compute_macc_all_levers,
    prepare_macc_curve_data,
    print_macc_diagnostics,
    run_macc_sanity_checks,
)
from src.target_engine import aggregate_target_pathway, compute_category_targets, compute_gap_to_target


st.set_page_config(page_title="SBTi Decarbonization Autopilot", layout="wide")

profile = load_company_profile("ready_to_implement_demo_dataset/company_profile.json")
baseline = load_baseline_footprint("ready_to_implement_demo_dataset/baseline_footprint.json")
levers = load_lever_library("ready_to_implement_demo_dataset/lever_library.json")

st.sidebar.header("Targets")
pathway = st.sidebar.selectbox("SBTi Pathway", ["WB2C", "1.5C"])

st.sidebar.header("Lever Selection")
selected_lever_ids = st.sidebar.multiselect(
    "Select Levers",
    options=[l["lever_id"] for l in levers],
    default=[l["lever_id"] for l in levers[:5]],
)
lever_selections: list[dict] = []
for lever_id in selected_lever_ids:
    lever = next(l for l in levers if l["lever_id"] == lever_id)
    st.sidebar.subheader(lever["title"])
    start_year = st.sidebar.slider(
        f"{lever_id} Start Year",
        profile["base_year"],
        profile["horizon_year"],
        lever["ramp"]["default_start_year"],
    )
    ramp_years = st.sidebar.slider(
        f"{lever_id} Ramp Years",
        1,
        10,
        lever["ramp"]["default_duration_years"],
    )
    lever_selections.append(
        {
            "lever_id": lever_id,
            "bu_id": "ALL",
            "status": "assessed",
            "start_year": start_year,
            "ramp_years": ramp_years,
            "commitment_by_year_pct": {},
        }
    )

bau_by_cat = compute_bau_pathway_all_categories(
    baseline, profile, profile["base_year"], profile["horizon_year"]
)
bau_total = aggregate_bau_pathway(bau_by_cat)

targets_by_cat = compute_category_targets(
    baseline, profile["base_year"], profile["horizon_year"], pathway
)
target_total = aggregate_target_pathway(targets_by_cat)

net_by_cat = compute_net_emissions_all_categories(
    bau_by_cat,
    levers,
    lever_selections,
    baseline,
    profile["base_year"],
    profile["horizon_year"],
)
net_total = aggregate_bau_pathway(net_by_cat)
gap_total = compute_gap_to_target(net_total, target_total)
abatement_total = compute_abatement(bau_total, net_total)

annual_results = {}
for year in bau_total.keys():
    annual_results[year] = {
        "bau_tco2e": bau_total.get(year, 0.0),
        "net_tco2e": net_total.get(year, 0.0),
        "target_tco2e": target_total.get(year, 0.0),
        "abatement_tco2e": abatement_total.get(year, 0.0),
    }

fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=list(bau_total.keys()),
        y=list(bau_total.values()),
        name="BAU",
        line=dict(color="red"),
    )
)
fig.add_trace(
    go.Scatter(
        x=list(target_total.keys()),
        y=list(target_total.values()),
        name=f"Target ({pathway})",
        line=dict(color="green"),
    )
)
fig.add_trace(
    go.Scatter(
        x=list(net_total.keys()),
        y=list(net_total.values()),
        name="Net Emissions",
        line=dict(color="blue"),
    )
)
fig.update_layout(
    title="BAU vs Target Emissions",
    xaxis_title="Year",
    yaxis_title="tCO2e",
)

financial_metrics = compute_financial_metrics_all_levers(
    levers,
    lever_selections,
    profile["base_year"],
    profile["horizon_year"],
    profile.get("finance", {}).get("wacc", 0.08),
)
macc_results = compute_macc_all_levers(
    levers,
    lever_selections,
    net_by_cat,
    bau_by_cat,
    financial_metrics,
    profile["base_year"],
    profile["horizon_year"],
    profile.get("finance", {}).get("wacc", 0.08),
)

# Print diagnostics to console for debugging
print_macc_diagnostics(macc_results)

# Prepare bar chart data
macc_bar_data = prepare_macc_curve_data(macc_results)

st.title("SBTi Decarbonization Autopilot")
tab1, tab2, tab3, tab4 = st.tabs(["Trajectory", "Finance & MACC", "Lever Details", "Lever Finder (RAG)"])

with tab1:
    st.plotly_chart(fig, use_container_width=True)
    gap_fig = go.Figure()
    gap_fig.add_trace(
        go.Bar(
            x=list(gap_total.keys()),
            y=list(gap_total.values()),
            name="Gap to Target",
        )
    )
    gap_fig.update_layout(
        title="Gap to Target (Net - Target)",
        xaxis_title="Year",
        yaxis_title="tCO2e",
    )
    st.plotly_chart(gap_fig, use_container_width=True)

with tab2:
    # === MACC BAR CHART ===
    if macc_bar_data:
        macc_fig = go.Figure()
        
        # Create proper MACC bars with width = abatement, height = MAC
        for bar in macc_bar_data:
            color = "green" if bar["mac"] < 0 else "steelblue"
            macc_fig.add_trace(
                go.Bar(
                    x=[(bar["x_start"] + bar["x_end"]) / 2],  # Center position
                    y=[bar["mac"]],
                    width=[bar["width"]],
                    name=bar["lever_id"],
                    marker_color=color,
                    hovertemplate=(
                        f"<b>{bar['title']}</b><br>"
                        f"MAC: ${bar['mac']:,.0f}/tCO2e<br>"
                        f"Abatement: {bar['width']:,.0f} tCO2e<br>"
                        f"Cumulative: {bar['x_start']:,.0f} - {bar['x_end']:,.0f} tCO2e"
                        "<extra></extra>"
                    ),
                )
            )
        
        macc_fig.update_layout(
            title="MACC Curve (Discounted) - Bars by Abatement",
            xaxis_title="Cumulative Discounted Abatement (tCO2e)",
            yaxis_title="MAC ($/tCO2e)",
            showlegend=False,
            bargap=0,
            barmode="overlay",
        )
        
        # Add zero line
        macc_fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        
        st.plotly_chart(macc_fig, use_container_width=True)
    else:
        st.info("No MACC data to display. Select levers to see the curve.")
    
    # === MAC by Lever Bar Chart (simpler view) ===
    if macc_results:
        mac_by_lever_fig = go.Figure()
        sorted_results = sorted(macc_results, key=lambda r: r["mac"])
        
        lever_names = [r["lever_id"] for r in sorted_results if r["mac"] != float("inf")]
        mac_values = [r["mac"] for r in sorted_results if r["mac"] != float("inf")]
        colors = ["green" if m < 0 else "steelblue" for m in mac_values]
        
        mac_by_lever_fig.add_trace(
            go.Bar(
                x=lever_names,
                y=mac_values,
                marker_color=colors,
                hovertemplate="<b>%{x}</b><br>MAC: $%{y:,.0f}/tCO2e<extra></extra>",
            )
        )
        mac_by_lever_fig.update_layout(
            title="MAC by Lever (sorted ascending)",
            xaxis_title="Lever",
            yaxis_title="MAC ($/tCO2e)",
            xaxis_tickangle=-45,
        )
        mac_by_lever_fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        
        st.plotly_chart(mac_by_lever_fig, use_container_width=True)

    # === MACC RANKING TABLE ===
    if macc_results:
        macc_df = pd.DataFrame(macc_results)
        st.subheader("MACC Ranking")

        col1, col2, col3, col4 = st.columns(4)
        bu_options = ["All"] + [bu["bu_id"] for bu in profile.get("business_units", [])]
        roi_options = ["All", "<5y", ">=5y", "non_payback"]
        status_options = ["All", "idea", "assessed", "approved", "in_progress", "implemented"]
        lever_type_options = ["All", "quantity", "transfer", "specification"]

        filter_bu = col1.multiselect("Business Unit", options=bu_options, default=["All"])
        filter_roi = col2.selectbox("ROI Bucket", options=roi_options, index=0)
        filter_status = col3.multiselect("Status", options=status_options, default=["All"])
        filter_category = col4.multiselect("Lever Category", options=lever_type_options, default=["All"])

        filtered = macc_df.copy()
        if "All" not in filter_bu:
            filtered = filtered[filtered["bu_id"].isin(filter_bu)]
        if filter_roi != "All":
            filtered = filtered[filtered["roi_bucket"] == filter_roi]
        if "All" not in filter_status:
            filtered = filtered[filtered["status"].isin(filter_status)]
        if "All" not in filter_category:
            filtered = filtered[filtered["lever_type"].isin(filter_category)]

        # Format for display
        display_df = filtered[
            [
                "lever_id",
                "title",
                "lever_type",
                "mac",
                "disc_abatement",
                "npv_cost",
                "payback_years",
                "roi_bucket",
                "status",
            ]
        ].copy()
        
        # Add units to column names
        display_df = display_df.rename(columns={
            "mac": "MAC ($/tCO2e)",
            "disc_abatement": "Disc. Abatement (tCO2e)",
            "npv_cost": "NPV Cost (USD)",
            "payback_years": "Payback (years)",
        })
        
        st.dataframe(display_df, use_container_width=True)
        
        # Sanity check warnings
        warnings = run_macc_sanity_checks(macc_results)
        if warnings:
            st.warning("Sanity Check Warnings:\n" + "\n".join(f"- {w}" for w in warnings))

    total_npv = sum(v.get("npv", 0.0) for v in financial_metrics.values())
    total_disc_abatement = sum(r.get("disc_abatement", 0.0) for r in macc_results)
    
    st.subheader("Finance KPIs")
    col1, col2, col3 = st.columns(3)
    # Display as net savings (multiply by -1: negative NPV cost = positive savings)
    net_savings = -total_npv
    savings_sign = "+" if net_savings >= 0 else ""
    col1.metric("NPV (Net Savings)", f"{savings_sign}${net_savings / 1_000_000:.2f}M")
    col2.metric("Total Disc. Abatement (tCO2e)", f"{total_disc_abatement:,.0f}")
    
    if total_disc_abatement > 0:
        weighted_avg_mac = total_npv / total_disc_abatement
        col3.metric("Weighted Avg MAC ($/tCO2e)", f"${weighted_avg_mac:,.0f}")

    st.subheader("Export")
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "scenario_results.csv"
    if st.button("Export CSV"):
        export_scenario_to_csv(annual_results, macc_results, str(output_path))
        assumptions_log = generate_assumptions_log(
            company_profile=profile,
            baseline=baseline,
            target_settings={"pathway": pathway},
            lever_selections=lever_selections,
        )
        log_path = output_dir / "assumptions_log.txt"
        log_path.write_text(assumptions_log, encoding="utf-8")
        st.success(f"Exported to {output_path} and assumptions_log.txt")
    else:
        st.caption("Click Export CSV to generate outputs.")

with tab3:
    for lever_id in selected_lever_ids:
        lever = next(l for l in levers if l["lever_id"] == lever_id)
        with st.expander(lever["title"]):
            potential = lever.get("potential", {})
            st.write(f"Type: {lever.get('lever_type')}")
            st.write(
                "Potential (min/central/max): "
                f"{potential.get('min_pct', 0):.2%} / "
                f"{potential.get('central_pct', 0):.2%} / "
                f"{potential.get('max_pct', 0):.2%}"
            )
            st.write(f"Uncertainty: {lever.get('uncertainty')}")
            
            # Show financials for this lever
            fm = financial_metrics.get(lever_id, {})
            if fm:
                st.write("---")
                st.write(f"**NPV (USD):** ${fm.get('npv', 0):,.0f}")
                payback = fm.get('payback')
                st.write(f"**Payback:** {payback:.1f} years" if payback else "**Payback:** Never")
                st.write(f"**ROI Bucket:** {fm.get('roi_bucket')}")

with tab4:
    st.caption("Optional: minimal RAG lever finder (requires faiss + sentence-transformers).")
    query = st.text_input("RAG Query", "Reduce data center electricity emissions")
    hotspot_options = [c["category_id"] for c in baseline.get("emissions_by_category", [])]
    hotspots = st.multiselect("Hotspots", options=hotspot_options, default=hotspot_options[:2])
    if st.button("Search Levers"):
        try:
            from src.rag_engine import build_lever_index, search_levers

            if "lever_index" not in st.session_state:
                index, id_to_lever = build_lever_index(levers)
                st.session_state["lever_index"] = index
                st.session_state["lever_id_map"] = id_to_lever

            results = search_levers(
                query=query,
                sector=profile.get("sector", ""),
                hotspots=hotspots,
                index=st.session_state["lever_index"],
                id_to_lever=st.session_state["lever_id_map"],
                top_k=10,
            )
            if results:
                st.dataframe(
                    pd.DataFrame(results)[
                        ["lever_id", "title", "lever_type", "category_targets", "score"]
                    ],
                    use_container_width=True,
                )
            else:
                st.info("No results found.")
        except Exception as exc:  # pragma: no cover - optional dependency path
            st.error(f"RAG unavailable: {exc}")
