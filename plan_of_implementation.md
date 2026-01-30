1) One-page Jury Demo Goal

Single-sentence goal (what the jury will see):
An end-to-end, SBTi-aligned decarbonization “autopilot” that takes a company’s baseline emissions and growth plan, sets an SBTi pathway, recommends sector-relevant levers (RAG), and simulates BAU vs Net Emissions while ranking levers on a discounted MACC + ROI to prove the plan is feasible and financeable.

Simulation story (the “this is doable” proof):
“MACC ranks decarbonization levers by impact and discounted cost to guide target-driven decisions across the business-plan horizon. We simulate two scenarios—BAU (no levers) vs Net Emissions (selected levers)—and show how lever commitments close the SBTi target gap year-by-year.”

WOW moments (3–5):

Target gap closes live: toggle SBTi pathway (WB2C vs 1.5°C), and the target line updates; the gap is shown instantly.

Levers appear from context: enter sector + footprint hotspots → RAG returns an “actionable lever list” with assumptions + evidence snippets.

Trajectory reacts to sliders: adjust a lever’s ramp/commitment → BAU vs Net line shifts immediately.

MACC reorders dynamically: the MACC curve and ranking reorder based on the scenario (discounted costs/abatement).

Finance feasibility in one glance: filter levers by ROI < 5 years, BU, category, implementation status.

Exactly what we input during the demo (keep it 60–90 sec):

Company profile: sector (pick ONE for demo), regions, business units (2–3), growth rate (e.g., 3%/yr), base year (2024), horizon (2034).

Baseline emissions: preloaded dataset by Scope + category (or upload a CSV).

SBTi target choice: WB2C (2.5%/yr) vs 1.5°C (4.2%/yr) and optional Scope 3 method.

WACC (e.g., 8%), carbon price toggle (optional).

Select 5–8 levers from the RAG list; adjust 2 sliders (start year + ramp).

Exactly what we show on screen (the proof artifacts):

A single dashboard with:

Target trajectory vs BAU vs Net Emissions (annual)

Gap-to-target (by year and cumulative)

MACC curve + ranked table with filters (BU/category/status/ROI bucket)

Finance panel: NPV, payback, CapEx/OpEx/Savings breakdown

Lever cards with assumptions + uncertainty band (min/central/max)

2) Product Spec (implementation-ready)
Target users

KPMG consultant (ESG/Climate): build client-ready pathways fast; scenario comparison; defend assumptions.

Client sustainability team: manage lever pipeline; track progress; update assumptions.

BU lead / finance partner: validate feasibility via cost, ROI, capex envelope.

User journey (5 steps)

Target-setting (SBTi): choose base year, horizon, pathway (WB2C/1.5°C), scopes covered, and method for Scope 3.

Lever discovery (RAG): input sector + footprint hotspots → suggested lever library with evidence and typical ranges.

Roadmap build: select levers, assign BU/category, set start year + ramp curve + annual commitment.

MACC prioritization: compute discounted costs/abatement → MACC curve + filters + ROI buckets; optionally “auto-build” a target-meeting portfolio.

Reporting/export: export scenario summary (CSV/Excel/PDF) and assumption log.

Screens (max 6) with key widgets/charts

Screen 1 — Company & Baseline

Inputs: sector dropdown, base year, horizon, growth (%), BUs.

Baseline table: emissions by Scope + category (S1C1…S3C15).

Output: baseline hotspot chart (top categories).

Screen 2 — SBTi Targets

Choose: WB2C vs 1.5°C (uses reduction rates), optional Scope 3 method.

Output: target pathway line + “required annual reduction” summary.

Screen 3 — Lever Finder (RAG)

Prompt box + “hotspots to prioritize” chips.

Output: lever list (cards) with: lever type (quantity/transfer/spec), scope/category, typical potential range, typical cost drivers, prerequisites.

Screen 4 — Scenario Builder

“Selected levers” table: start year, ramp (linear/S-curve), potential %, commitment %, BU, status.

Output chart: BAU vs Net emissions + target line (live).

Screen 5 — MACC & Finance

MACC curve (bar widths = abatement, height = MAC) + ranked table.

Filters: BU, lever category, lever/project, implementation status, ROI bucket (<5y / >5y).

KPIs: total abatement, % target achieved, CapEx/OpEx/Savings, NPV, payback.

Screen 6 — Report & Assumptions

One-click export; assumptions log; “what changed vs last scenario”.

3) Data Model (concrete JSON schemas)
3.1 Company profile
{
  "type": "object",
  "required": ["company_id", "name", "sector", "base_year", "horizon_year", "growth_assumptions", "business_units"],
  "properties": {
    "company_id": {"type": "string"},
    "name": {"type": "string"},
    "sector": {"type": "string"},
    "regions": {"type": "array", "items": {"type": "string"}},
    "base_year": {"type": "integer"},
    "horizon_year": {"type": "integer"},
    "growth_assumptions": {
      "type": "object",
      "properties": {
        "annual_growth_rate": {"type": "number"},
        "by_category_growth_rate": {
          "type": "object",
          "additionalProperties": {"type": "number"}
        }
      }
    },
    "business_units": {
      "type": "array",
      "items": {"type": "object", "required": ["bu_id", "name"], "properties": {"bu_id": {"type": "string"}, "name": {"type": "string"}}}
    },
    "finance": {
      "type": "object",
      "properties": {
        "wacc": {"type": "number"},
        "currency": {"type": "string"},
        "carbon_price_path": {
          "type": "object",
          "additionalProperties": {"type": "number"}
        }
      }
    }
  }
}

3.2 Baseline footprint (by scope/category)
{
  "type": "object",
  "required": ["inventory_method", "emissions_by_category"],
  "properties": {
    "inventory_method": {"type": "string", "enum": ["GHG Protocol", "Other"]},
    "emissions_by_category": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["category_id", "scope", "category_name", "base_year_tco2e"],
        "properties": {
          "category_id": {"type": "string", "description": "e.g., S2C1, S3C1"},
          "scope": {"type": "string", "enum": ["S1", "S2", "S3"]},
          "category_name": {"type": "string"},
          "base_year_tco2e": {"type": "number"},
          "bu_split": {
            "type": "object",
            "additionalProperties": {"type": "number"},
            "description": "BU share weights summing to 1.0"
          }
        }
      }
    }
  }
}

3.3 Lever library item
{
  "type": "object",
  "required": ["lever_id", "title", "lever_type", "scope_targets", "category_targets", "potential", "ramp", "cost_model"],
  "properties": {
    "lever_id": {"type": "string"},
    "title": {"type": "string"},
    "description": {"type": "string"},
    "lever_type": {"type": "string", "enum": ["quantity", "transfer", "specification"]},
    "scope_targets": {"type": "array", "items": {"type": "string", "enum": ["S1", "S2", "S3"]}},
    "category_targets": {"type": "array", "items": {"type": "string"}},
    "prerequisites": {"type": "array", "items": {"type": "string"}},
    "potential": {
      "type": "object",
      "required": ["min_pct", "central_pct", "max_pct"],
      "properties": {"min_pct": {"type": "number"}, "central_pct": {"type": "number"}, "max_pct": {"type": "number"}}
    },
    "transfer_params": {
      "type": "object",
      "properties": {
        "low_carbon_intensity_ratio": {"type": "number", "description": "e.g., 0.2 means 80% reduction on shifted share"},
        "max_share_shift": {"type": "number"}
      }
    },
    "ramp": {
      "type": "object",
      "properties": {
        "default_start_year": {"type": "integer"},
        "default_duration_years": {"type": "integer"},
        "curve": {"type": "string", "enum": ["linear", "s_curve"]}
      }
    },
    "cost_model": {
      "type": "object",
      "properties": {
        "capex_by_year": {"type": "object", "additionalProperties": {"type": "number"}},
        "opex_by_year": {"type": "object", "additionalProperties": {"type": "number"}},
        "savings_by_year": {"type": "object", "additionalProperties": {"type": "number"}},
        "headcount_by_year": {"type": "object", "additionalProperties": {"type": "number"}},
        "cost_per_tco2e": {"type": "number", "description": "optional simplified model"}
      }
    },
    "uncertainty": {"type": "string", "enum": ["low", "medium", "high"]},
    "evidence_snippets": {"type": "array", "items": {"type": "string"}}
  }
}

3.4 Scenario (selected levers + commitments)
{
  "type": "object",
  "required": ["scenario_id", "name", "target_settings", "lever_selections"],
  "properties": {
    "scenario_id": {"type": "string"},
    "name": {"type": "string"},
    "target_settings": {
      "type": "object",
      "required": ["pathway", "base_year", "target_year", "scopes_included"],
      "properties": {
        "pathway": {"type": "string", "enum": ["WB2C", "1.5C", "custom"]},
        "base_year": {"type": "integer"},
        "target_year": {"type": "integer"},
        "scopes_included": {"type": "array", "items": {"type": "string", "enum": ["S1", "S2", "S3"]}},
        "method_by_scope": {
          "type": "object",
          "additionalProperties": {"type": "string", "enum": ["ACA", "GEVA", "PhysicalIntensity", "SupplierEngagement"]}
        }
      }
    },
    "lever_selections": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["lever_id", "bu_id", "status", "start_year", "ramp_years", "commitment_by_year_pct"],
        "properties": {
          "lever_id": {"type": "string"},
          "bu_id": {"type": "string"},
          "status": {"type": "string", "enum": ["idea", "assessed", "approved", "in_progress", "implemented"]},
          "start_year": {"type": "integer"},
          "ramp_years": {"type": "integer"},
          "commitment_by_year_pct": {"type": "object", "additionalProperties": {"type": "number"}},
          "override_potential_pct": {"type": "number"}
        }
      }
    }
  }
}

3.5 Outputs (trajectory + MACC)
{
  "type": "object",
  "required": ["annual", "lever_results", "summary"],
  "properties": {
    "annual": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["year", "bau_tco2e", "net_tco2e", "target_tco2e", "abatement_tco2e"],
        "properties": {
          "year": {"type": "integer"},
          "bau_tco2e": {"type": "number"},
          "net_tco2e": {"type": "number"},
          "target_tco2e": {"type": "number"},
          "abatement_tco2e": {"type": "number"},
          "capex": {"type": "number"},
          "opex": {"type": "number"},
          "savings": {"type": "number"},
          "headcount": {"type": "number"}
        }
      }
    },
    "lever_results": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["lever_id", "disc_cost_npv", "disc_abatement", "mac", "roi_bucket", "payback_years"],
        "properties": {
          "lever_id": {"type": "string"},
          "disc_cost_npv": {"type": "number"},
          "disc_abatement": {"type": "number"},
          "mac": {"type": "number"},
          "payback_years": {"type": "number"},
          "roi_bucket": {"type": "string", "enum": ["<5y", ">=5y", "non_payback"]},
          "cum_abatement": {"type": "number"}
        }
      }
    },
    "summary": {
      "type": "object",
      "properties": {
        "pct_target_achieved": {"type": "number"},
        "total_disc_cost_npv": {"type": "number"},
        "total_disc_abatement": {"type": "number"},
        "macc_weighted_avg": {"type": "number"}
      }
    }
  }
}


4) Deterministic Algorithms (implementable)
4A) Target engine (SBTi-aligned, simplified but faithful)
Inputs (from the Excel structure):
Base year = 2024; target year = 2034 (prototype horizon)
Default annual reduction rates:
WB2C: 2.5%/yr
1.5°C: 4.2%/yr
Economic intensity (GEVA): 7%/yr
Categories list: S1/S2/S3 categories (S1C1…S3C15)
Absolute Contraction Approach (ACA) trajectory
Let E0E_0E0​ be base-year emissions (scope/category or total).
Let rrr be annual reduction rate.
Target for year yyy:
Etarget(y)=E0⋅(1−r)(y−base_year)E_{target}(y) = E_0 \cdot (1-r)^{(y-\text{base\_year})}Etarget​(y)=E0​⋅(1−r)(y−base_year)

Pseudocode:
def target_path_aca(E0, base_year, years, annual_rate):
    # annual_rate e.g. 0.042
    target = {}
    for y in years:
        t = y - base_year
        target[y] = E0 * ((1 - annual_rate) ** t)
    return target


Net-zero placeholder logic (prototype-safe):
Choose long-term year = 2050 (or horizon if demo-limited).
Residual fraction (prototype assumption): 10% remaining emissions at net-zero year.
Compute implied annual rate:
rNZ=1−(residual)1/(2050−base_year)r_{NZ} = 1 - (residual)^{1/(2050-base\_year)}rNZ​=1−(residual)1/(2050−base_year)
Residual emissions in 2050 are flagged as “to neutralize” (offsets/removals), but not used to claim abatement.

def net_zero_long_term_rate(residual_fraction, base_year, nz_year=2050):
    n = nz_year - base_year
    return 1 - (residual_fraction ** (1/n))


4B) Lever quantification engine (physical) — BAU vs Net Emissions

BAU emissions per category
E_bau[k,y] = E0[k] * (1 + growth_rate[k]) ** (y - base_year)


Lever ramp / commitment
Each lever has:
Potential ppp (max achievable fraction)
Commitment c(y)c(y)c(y) in [0,1] (cumulative achieved by year y based on ramp curve)
Effective fraction f(y)=p⋅c(y)f(y) = p \cdot c(y)f(y)=p⋅c(y)
Order of operations to avoid double counting (matches the lever types concept):
Apply quantity levers → reduce the emissions base
Apply transfer levers → shift share to low-carbon alternative
Apply specification levers → reduce intensity of the remaining base
Per category-year computation

def apply_levers(E_bau, quantity_fracs, transfer_params, spec_fracs):
    # quantity_fracs: list of f(y) fractions
    # transfer_params: list of (share_shift(y), low_carbon_ratio)
    # spec_fracs: list of f(y) fractions
    
    # 1) Quantity
    mult_q = 1.0
    for fq in quantity_fracs:
        mult_q *= (1 - fq)  # multiplicative to reduce overlap
    E1 = E_bau * mult_q
    
    # 2) Transfer (cap total shifted share to 1.0)
    shifted = 0.0
    mult_t = 1.0
    for share, ratio in transfer_params:
        remaining_share = max(0.0, 1.0 - shifted)
        eff_share = min(share, remaining_share)
        mult_t *= (1 - eff_share * (1 - ratio))
        shifted += eff_share
    E2 = E1 * mult_t
    
    # 3) Specification
    mult_s = 1.0
    for fs in spec_fracs:
        mult_s *= (1 - fs)
    E3 = E2 * mult_s
    
    return E3  # net emissions after levers


Annual abatement
abatement[y] = sum_k(E_bau[k,y] - E_net[k,y])


4C) Financial engine (CapEx / OpEx / Savings + discounting)

Discount factor (use standard PV):
df[y] = 1 / (1 + WACC) ** (y - start_year)


Lever cashflows
net_cost[y] = capex[y] + opex[y] - savings[y]  # add carbon price terms if enabled
npv_cost = sum(df[y] * net_cost[y] for y in years)


Payback (discounted)
cum = 0
for y in years:
    cum += df[y] * (-net_cost[y])  # treat "benefit" as -cost
    if cum >= 0: payback = y - start_year; break


ROI buckets

ROI < 5y if payback_years < 5

else ≥5y

if never pays back → “non_payback”

4D) MACC engine (discounted)

Discounted abatement
disc_abatement = sum(df[y] * abatement[y] for y in years)


Marginal Abatement Cost
MAC = npv_cost / disc_abatement   # $/tCO2e


Example with 4 levers (toy numbers)

Lever A: NPV cost = -2M (saves money), disc abatement 50k → MAC = -40 $/t

Lever B: NPV cost = 1M, disc abatement 20k → MAC = 50 $/t

Lever C: NPV cost = 6M, disc abatement 60k → MAC = 100 $/t

Lever D: NPV cost = 0.5M, disc abatement 5k → MAC = 100 $/t
Rank by MAC ascending, then tie-break by abatement or status.



5) “LLM where it helps, rules where it must” architecture
LLM/RAG (where it helps)

Lever discovery & explanation: retrieve lever candidates relevant to sector + hotspots; draft lever descriptions, prerequisites, and “why it matters here.”

Assumption assistant: propose default potentials/cost ranges when data missing (clearly labeled).

Narrative/reporting: generate scenario summary and executive narrative.

Deterministic engine (where it must be rule-based)

Target math (ACA/GEVA trajectories)

BAU growth + lever application math (quantity/transfer/spec)

Discounting (WACC PV), NPV, payback, ROI buckets

MACC calculation + ranking + filters

Text architecture diagram


[Inputs]
  ├─ Company profile + growth + WACC
  ├─ Baseline emissions by scope/category (from CSV or preloaded)
  └─ SBTi target settings (WB2C/1.5C/GEVA)

[Lever Knowledge]
  ├─ Lever library docs (sector playbooks, internal notes, public summaries)
  └─ Vector store (FAISS) + embeddings

[LLM/RAG Layer]
  ├─ Query builder: sector + hotspots + constraints
  ├─ Retriever: top-N lever candidates + evidence snippets
  └─ Generator: lever cards (type, scope/category, default ranges, prerequisites)

[Scenario Builder UI]
  ├─ Select levers + set ramp/commitment + BU/status
  └─ Optional: “Auto-close gap” (greedy/optimizer)

[Deterministic Calculators]
  ├─ Target engine (ACA/GEVA)
  ├─ BAU + lever quantification engine
  ├─ Financial engine (cashflows, NPV, payback)
  └─ MACC engine (discounted MAC + ranking)

[Dashboards]
  ├─ BAU vs Net vs Target
  ├─ Gap-to-target & contribution by lever
  └─ MACC curve + filters + finance KPIs

[Exports]
  └─ CSV/Excel/PDF + assumptions log



6) Prototype Plan (buildable)
Recommended stack (fast + hackathon-friendly)

Python + Streamlit (UI)

pandas / numpy (calculations)

plotly (interactive charts, MACC)

FAISS (vector store) + sentence-transformers (embeddings)

Optional: FastAPI if you want clean API separation

Step-by-step build checklist

Data: create a demo dataset (baseline + 10 levers) for ONE sector.

Target engine: implement ACA path with WB2C/1.5°C rates; render target line.

BAU engine: implement growth-driven BAU per category and total.

Lever engine: implement lever ramp + order-of-ops (quantity → transfer → spec).

Finance engine: cashflows + discounting + payback/ROI buckets.

MACC: compute MAC per lever + curve data + ranking table + filters.

RAG: load lever docs → embeddings → retrieval → lever cards generator.

UI: 4 screens minimum (Baseline, Targets, Scenario, MACC).

Export: scenario outputs to CSV + “assumptions log” text.


Minimal demo dataset strategy (credible and sufficient)

Pick one sector (e.g., “IT / Data Centers” or “Retail”). Preload:

Baseline emissions (2024) by categories:

Scope 2 electricity (big), Scope 3 capital goods/servers, Scope 3 business travel, etc.

Growth rate: 3%/yr for electricity + 5%/yr for servers (prototype assumptions).

10–12 levers with:

lever_type (quantity/transfer/spec)

category targets

potential (min/central/max)

ramp defaults

simplified cost model (either per-year numbers or $/tCO2e)

Must be able to render (required):

Target pathway

Lever abatements

BAU vs Net trajectory

MACC ranking + filters (BU/category/status/ROI bucket)