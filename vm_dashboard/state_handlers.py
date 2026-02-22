import pandas as pd
import taipy.gui.builder as tgb
from taipy.gui.gui_actions import navigate

from .sql_chat import _chat_welcome_message, _update_chat_runtime_status, ensure_sqlite_db
from .state_data import (
    FRAC_SAMPLE_N,
    MAX_TABLE_ROWS,
    OPENROUTER_DEFAULT_MODEL,
    chat_users,
    comp,
    drill,
    frac,
    prod,
)


# ------------------------------------------------------------------
# STATE UPDATE (DATA & KPIs)
# ------------------------------------------------------------------
def update_state(state):
    # ---------- FILTER PRODUCTION DATA ----------
    d1 = prod.copy()

    company_filter = state.company_filter
    field_filter = state.field_filter
    well_type_filter = state.well_type_filter

    # company filter
    if isinstance(company_filter, list):
        if "All" not in company_filter:
            d1 = d1[d1["company"].isin(company_filter)]
    elif company_filter != "All":
        d1 = d1[d1["company"] == company_filter]

    # field filter
    if isinstance(field_filter, list):
        if "All" not in field_filter:
            d1 = d1[d1["field"].isin(field_filter)]
    elif field_filter != "All":
        d1 = d1[d1["field"] == field_filter]

    # well type filter
    if isinstance(well_type_filter, list):
        if "All" not in well_type_filter:
            d1 = d1[d1["well_type"].isin(well_type_filter)]
    elif well_type_filter != "All":
        d1 = d1[d1["well_type"] == well_type_filter]

    # year range
    d1 = d1[(d1["year"] >= state.year_range[0]) & (d1["year"] <= state.year_range[1])]
    state.filtered_prod = d1
    state.filtered_prod_view = d1.head(MAX_TABLE_ROWS)

    # ---------- FILTER FRAC DATA ----------
    d2 = frac.copy()

    if isinstance(company_filter, list):
        if "All" not in company_filter:
            d2 = d2[d2["company"].isin(company_filter)]
    elif company_filter != "All":
        d2 = d2[d2["company"] == company_filter]

    if isinstance(field_filter, list):
        if "All" not in field_filter:
            d2 = d2[d2["field"].isin(field_filter)]
    elif field_filter != "All":
        d2 = d2[d2["field"] == field_filter]

    if "well_type" in d2.columns:
        if isinstance(well_type_filter, list):
            if "All" not in well_type_filter:
                d2 = d2[d2["well_type"].isin(well_type_filter)]
        elif well_type_filter != "All":
            d2 = d2[d2["well_type"] == well_type_filter]

    d2 = d2[(d2["year"] >= state.year_range[0]) & (d2["year"] <= state.year_range[1])]

    if not d2.empty:
        d2 = d2.copy()
        lateral = d2["lateral_length_ft"].replace(0, pd.NA)
        d2["proppant_intensity_lbft"] = d2["proppant_pumped_lb"] / lateral
        d2["fluid_intensity_bblft"] = d2["fluid_pumped_bbl"] / lateral

    if not d1.empty and not d2.empty:
        cum = (
            d1.groupby("well_id", as_index=False)[["oil_prod_m3", "gas_prod_km3"]]
            .sum()
            .rename(
                columns={
                    "oil_prod_m3": "oil_cum_m3_raw",
                    "gas_prod_km3": "gas_cum_km3_raw",
                }
            )
        )
        cum["oil_cum_km3"] = cum["oil_cum_m3_raw"] / 1_000_000.0
        cum["gas_cum_Mm3"] = cum["gas_cum_km3_raw"] / 1_000.0

        d2 = d2.merge(
            cum[["well_id", "oil_cum_km3", "gas_cum_Mm3"]],
            on="well_id",
            how="left",
        )

    state.filtered_frac = d2
    state.filtered_frac_view = d2.head(MAX_TABLE_ROWS)

    if not d2.empty:
        state.avg_lateral_by_company_df = (
            d2.groupby("company", as_index=False)["lateral_length_ft"]
            .mean()
            .sort_values("lateral_length_ft", ascending=False)
        )
    else:
        state.avg_lateral_by_company_df = d2.head(0)

    if len(d2) > FRAC_SAMPLE_N:
        state.filtered_frac_sample = d2.sample(FRAC_SAMPLE_N, random_state=0)
    else:
        state.filtered_frac_sample = d2

    # ---------- FILTER DRILL DATA ----------
    d3 = drill.copy()

    if isinstance(company_filter, list):
        if "All" not in company_filter:
            d3 = d3[d3["company"].isin(company_filter)]
    elif company_filter != "All":
        d3 = d3[d3["company"] == company_filter]

    if isinstance(field_filter, list):
        if "All" not in field_filter:
            d3 = d3[d3["field"].isin(field_filter)]
    elif field_filter != "All":
        d3 = d3[d3["field"] == field_filter]

    d3 = d3[(d3["year"] >= state.year_range[0]) & (d3["year"] <= state.year_range[1])]
    state.filtered_drill = d3

    if not d3.empty:
        state.drill_wells_by_year_df = d3.groupby("year", as_index=False)["wells"].sum()
        state.drill_meters_by_year_df = d3.groupby("year", as_index=False)[
            "meters"
        ].sum()
        state.drill_meters_by_company_df = (
            d3.groupby("company", as_index=False)["meters"]
            .sum()
            .sort_values("meters", ascending=False)
        )
    else:
        state.drill_wells_by_year_df = d3.head(0)
        state.drill_meters_by_year_df = d3.head(0)
        state.drill_meters_by_company_df = d3.head(0)

    # ---------- FILTER COMPLETION DATA ----------
    d4 = comp.copy()

    if isinstance(state.company_filter, list):
        if "All" not in state.company_filter:
            d4 = d4[d4["company"].isin(state.company_filter)]
    elif state.company_filter != "All":
        d4 = d4[d4["company"] == state.company_filter]

    if isinstance(state.field_filter, list):
        if "All" not in state.field_filter:
            d4 = d4[d4["field"].isin(state.field_filter)]
    elif state.field_filter != "All":
        d4 = d4[d4["field"] == state.field_filter]

    d4 = d4[(d4["year"] >= state.year_range[0]) & (d4["year"] <= state.year_range[1])]
    state.filtered_comp = d4

    if not d4.empty:
        if "completion" in d4.columns:
            state.comp_by_year_df = (
                d4.groupby("year", as_index=False)["completion"]
                .sum()
                .rename(columns={"completion": "completions"})
            )
            state.comp_by_company_df = (
                d4.groupby("company", as_index=False)["completion"]
                .sum()
                .rename(columns={"completion": "completions"})
                .sort_values("completions", ascending=False)
            )
        else:
            state.comp_by_year_df = (
                d4.groupby("year", as_index=False)
                .size()
                .rename(columns={"size": "completions"})
            )
            state.comp_by_company_df = (
                d4.groupby("company", as_index=False)
                .size()
                .rename(columns={"size": "completions"})
            )
    else:
        state.comp_by_year_df = d4.head(0)
        state.comp_by_company_df = d4.head(0)

    # ---------- KPIs: drilling ----------
    if not d3.empty:
        state.drilled_wells = int(d3["wells"].sum())
        state.drilled_meters = round(float(d3["meters"].sum()), 2)
    else:
        state.drilled_wells = 0
        state.drilled_meters = 0.0

    # ---------- LATEST RECORD PER WELL (for map & well-level charts) ----------
    if not d1.empty:
        latest = (
            d1.sort_values(["well_id", "year", "month"])
            .groupby("well_id", as_index=False)
            .tail(1)
        )
    else:
        latest = d1.head(0)

    # ---------- KPIs: production ----------
    state.n_wells = d1["well_id"].nunique() if not d1.empty else 0
    state.total_oil = round(d1["oil_prod_m3"].sum() / 1_000_000, 2) if not d1.empty else 0.0
    state.total_gas = round(d1["gas_prod_km3"].sum() / 1_000, 2) if not d1.empty else 0.0
    state.total_water = (
        round(d1["water_prod_m3"].sum() / 1_000_000, 2) if not d1.empty else 0.0
    )

    # ---------- WELLS BY TYPE ----------
    if not latest.empty:
        state.wells_by_type_df = (
            latest.groupby("well_type", as_index=False)["well_id"]
            .nunique()
            .rename(columns={"well_id": "n_wells"})
            .sort_values("n_wells", ascending=False)
        )
    else:
        state.wells_by_type_df = latest.head(0)

    # ---------- DEPTH BY WELL TYPE ----------
    if not latest.empty:
        state.depth_by_type_df = (
            latest.groupby("well_type", as_index=False)["depth"]
            .mean()
            .rename(columns={"depth": "avg_depth"})
            .sort_values("avg_depth", ascending=False)
        )
    else:
        state.depth_by_type_df = latest.head(0)

    # ---------- TOP OIL WELLS ----------
    state.top_oil_wells_df = (
        (
            latest[["well_name", "oil_cum_m3"]]
            .dropna()
            .groupby("well_name", as_index=False)["oil_cum_m3"]
            .max()
            .sort_values("oil_cum_m3", ascending=False)
            .head(20)
        )
        if not latest.empty
        else latest.head(0)
    )

    # ---------- TOP GAS WELLS ----------
    state.top_gas_wells_df = (
        (
            latest[["well_name", "gas_cum_km3"]]
            .dropna()
            .groupby("well_name", as_index=False)["gas_cum_km3"]
            .max()
            .sort_values("gas_cum_km3", ascending=False)
            .head(20)
        )
        if not latest.empty
        else latest.head(0)
    )

    # ---------- PRODUCTION OVER TIME ----------
    if not d1.empty:
        state.prod_time_df = (
            d1.groupby("date", as_index=False)[
                ["oil_prod_m3", "gas_prod_km3", "water_prod_m3"]
            ]
            .sum()
            .sort_values("date")
        )
    else:
        state.prod_time_df = d1.head(0)

    # ---------- MAP DATA ----------
    if not latest.empty:
        latest2 = latest.copy()
        state.max_oil = latest2["oil_cum_m3"].max()
        state.max_gas = latest2["gas_cum_km3"].max()

        oil = latest2["oil_cum_m3"].fillna(0)
        q95_oil = oil.quantile(0.95)
        if q95_oil <= 0:
            q95_oil = 1.0
        latest2["oil_size"] = 4 + 36 * oil.clip(upper=q95_oil) / q95_oil

        gas = latest2["gas_cum_km3"].fillna(0)
        q95_gas = gas.quantile(0.95)
        if q95_gas <= 0:
            q95_gas = 1.0
        latest2["gas_size"] = 4 + 36 * gas.clip(upper=q95_gas) / q95_gas

        metric = getattr(state, "map_metric", "Oil")
        p = getattr(state, "map_min_percentile", 0)

        if metric == "Oil":
            metric_series = oil
            size_col = "oil_size"
            metric_label = "Oil (m³)"
            fill_color = "rgba(0,160,0,0.55)"
            border_color = "darkgreen"
        else:
            metric_series = gas
            size_col = "gas_size"
            metric_label = "Gas (km³)"
            fill_color = "rgba(220,0,0,0.55)"
            border_color = "darkred"

        cutoff = metric_series.quantile(p / 100.0) if 0 <= p <= 100 else 0
        map_latest = latest2[metric_series >= cutoff].copy()

        map_latest["map_size"] = map_latest[size_col]
        map_latest["map_metric_value"] = metric_series.loc[map_latest.index]
        map_latest["map_color"] = fill_color
        map_latest["map_border_color"] = border_color

        map_latest["hover_text"] = (
            "Well: "
            + map_latest["well_name"].astype(str)
            + "<br>Company: "
            + map_latest["company"].astype(str)
            + "<br>Field: "
            + map_latest["field"].astype(str)
            + "<br>"
            + metric_label
            + ": "
            + map_latest["map_metric_value"].round(1).astype(str)
        )

        state.map_metric_label = metric_label
        state.map_df = map_latest[
            [
                "well_id",
                "well_name",
                "Xcoor",
                "Ycoor",
                "oil_cum_m3",
                "gas_cum_km3",
                "map_size",
                "map_color",
                "map_border_color",
                "hover_text",
            ]
        ]
    else:
        state.max_oil = 0
        state.max_gas = 0
        state.map_metric_label = ""
        state.map_df = latest.head(0)

    # ---------- KPIs: frac ----------
    if not d2.empty:
        state.n_frac_wells = d2["well_id"].nunique()
        state.avg_lateral_length = round(d2["lateral_length_ft"].mean(), 0)
        state.avg_stages = round(d2["number_stages"].mean(), 1)
        state.total_proppant = round(d2["proppant_pumped_lb"].sum() / 1_000_000, 2)
        state.total_fluid = round(d2["fluid_pumped_bbl"].sum() / 1_000_000, 2)
        state.avg_proppant_intensity = (
            round(d2["proppant_intensity_lbft"].dropna().mean(), 1)
            if "proppant_intensity_lbft" in d2.columns
            else 0.0
        )
        state.avg_fluid_intensity = (
            round(d2["fluid_intensity_bblft"].dropna().mean(), 2)
            if "fluid_intensity_bblft" in d2.columns
            else 0.0
        )
    else:
        state.n_frac_wells = 0
        state.avg_lateral_length = 0.0
        state.avg_stages = 0.0
        state.total_proppant = 0.0
        state.total_fluid = 0.0
        state.avg_proppant_intensity = 0.0
        state.avg_fluid_intensity = 0.0

    state.avg_depth = round(state.filtered_prod["depth"].mean(), 2) if not state.filtered_prod.empty else 0.0
    state.avg_lateral = (
        round(state.filtered_frac["lateral_length_ft"].mean(), 2) if not state.filtered_frac.empty else 0.0
    )

    if state.selected_well:
        state.selected_prod_df = state.filtered_prod[
            state.filtered_prod["well_name"] == state.selected_well
        ]
        state.selected_frac_df = state.filtered_frac[
            state.filtered_frac["well_name"] == state.selected_well
        ]
    else:
        state.selected_prod_df = state.filtered_prod.head(0)
        state.selected_frac_df = state.filtered_frac.head(0)


# ------------------------------------------------------------------
# NAVIGATION STATE UPDATE
# ------------------------------------------------------------------
def update_nav(state):
    current = getattr(state, "active_page", "overview")

    state.nav_overview = "nav-button active" if current in ("overview", "/") else "nav-button"
    state.nav_geology = "nav-button active" if current == "geology" else "nav-button"
    state.nav_drilling = "nav-button active" if current == "drilling" else "nav-button"
    state.nav_frac = "nav-button active" if current == "frac" else "nav-button"
    state.nav_production = "nav-button active" if current == "production" else "nav-button"
    state.nav_map = "nav-button active" if current == "map" else "nav-button"
    state.nav_wells = "nav-button active" if current == "wells" else "nav-button"
    state.nav_data = "nav-button active" if current == "data" else "nav-button"
    state.nav_chat = "nav-button active" if current == "chat" else "nav-button"
    state.nav_links = "nav-button active" if current == "links" else "nav-button"
    state.nav_about = "nav-button active" if current == "about" else "nav-button"


# ------------------------------------------------------------------
# CALLBACKS
# ------------------------------------------------------------------
def on_change(state, var_name, var_value):
    if var_name in [
        "company_filter",
        "field_filter",
        "well_type_filter",
        "year_range",
        "map_metric",
        "map_min_percentile",
        "selected_well",
    ]:
        update_state(state)


def on_init(state):
    if not hasattr(state, "active_page"):
        state.active_page = "overview"
    if not hasattr(state, "map_metric") or not state.map_metric:
        state.map_metric = "Oil"
    if not hasattr(state, "openrouter_model") or not state.openrouter_model:
        state.openrouter_model = OPENROUTER_DEFAULT_MODEL
    if not hasattr(state, "openrouter_api_key_input"):
        state.openrouter_api_key_input = ""
    if not hasattr(state, "web_search_api_key_input"):
        state.web_search_api_key_input = ""
    if not hasattr(state, "chat_messages") or not state.chat_messages:
        state.chat_messages = [["m0", _chat_welcome_message(), "assistant"]]
    if not hasattr(state, "chat_users"):
        state.chat_users = chat_users
    if not hasattr(state, "sql_last_result"):
        state.sql_last_result = pd.DataFrame()
    if not hasattr(state, "sql_last_query"):
        state.sql_last_query = ""
    if not hasattr(state, "sql_agent_history"):
        state.sql_agent_history = []
    if not hasattr(state, "chat_busy"):
        state.chat_busy = False
    if not hasattr(state, "chat_input_active"):
        state.chat_input_active = True
    ensure_sqlite_db()
    _update_chat_runtime_status(state)
    update_state(state)
    update_nav(state)


# Navigation actions
def go_overview(state):
    state.active_page = "overview"
    update_nav(state)
    navigate(state, to="/")


def go_geology(state):
    state.active_page = "geology"
    update_nav(state)
    navigate(state, to="geology")


def go_drilling(state):
    state.active_page = "drilling"
    update_nav(state)
    navigate(state, to="drilling")


def go_production(state):
    state.active_page = "production"
    update_nav(state)
    navigate(state, to="production")


def go_frac(state):
    state.active_page = "frac"
    update_nav(state)
    navigate(state, to="frac")


def go_map(state):
    state.active_page = "map"
    update_nav(state)
    navigate(state, to="map")


def go_wells(state):
    state.active_page = "wells"
    update_nav(state)
    navigate(state, to="wells")


def go_data(state):
    state.active_page = "data"
    update_nav(state)
    navigate(state, to="data")


def go_chat(state):
    state.active_page = "chat"
    update_nav(state)
    navigate(state, to="chat")


def go_links(state):
    state.active_page = "links"
    update_nav(state)
    navigate(state, to="links")


def go_about(state):
    state.active_page = "about"
    update_nav(state)
    navigate(state, to="about")


def sidebar():
    with tgb.part(class_name="sidebar"):
        tgb.text("## 📘 Navigation", mode="md")
        tgb.button("🏠 OVERVIEW", class_name="{nav_overview}", on_action=go_overview)
        tgb.button("🪨 GEOLOGY", class_name="{nav_geology}", on_action=go_geology)
        tgb.button("🛠️ DRILLING", class_name="{nav_drilling}", on_action=go_drilling)
        tgb.button("💥 FRAC", class_name="{nav_frac}", on_action=go_frac)
        tgb.button("📈 PRODUCTION", class_name="{nav_production}", on_action=go_production)
        tgb.button("🗺️ MAP", class_name="{nav_map}", on_action=go_map)
        tgb.button("🔎 WELLS", class_name="{nav_wells}", on_action=go_wells)
        tgb.button("📄 DATA", class_name="{nav_data}", on_action=go_data)
        tgb.button("🤖 CHAT", class_name="{nav_chat}", on_action=go_chat)
        tgb.button("🔗 LINKS", class_name="{nav_links}", on_action=go_links)
        tgb.button("ℹ️ ABOUT", class_name="{nav_about}", on_action=go_about)
