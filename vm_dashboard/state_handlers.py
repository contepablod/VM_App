import pandas as pd
import taipy.gui.builder as tgb
from taipy.gui.gui_actions import navigate

from . import state_data
from .sql_chat import (
    _chat_welcome_message,
    _update_chat_runtime_status,
    ensure_sqlite_db,
    get_sqlite_db_status,
)


# ------------------------------------------------------------------
# STATE UPDATE (DATA & KPIs)
# ------------------------------------------------------------------
def _normalize_selector_value(value, lov):
    valid_values = {item for item in lov if item != "All"}
    if isinstance(value, list):
        if "All" in value:
            return "All"
        selected = [item for item in value if item in valid_values]
        return selected if selected else "All"
    return value if value in valid_values else "All"


def _apply_filters(df, company_filter, field_filter, well_type_filter, year_range):
    """Apply company/field/well_type/year filters to a DataFrame."""
    if isinstance(company_filter, list):
        if "All" not in company_filter:
            df = df[df["company"].isin(company_filter)]
    elif company_filter != "All":
        df = df[df["company"] == company_filter]

    if isinstance(field_filter, list):
        if "All" not in field_filter:
            df = df[df["field"].isin(field_filter)]
    elif field_filter != "All":
        df = df[df["field"] == field_filter]

    if "well_type" in df.columns:
        if isinstance(well_type_filter, list):
            if "All" not in well_type_filter:
                df = df[df["well_type"].isin(well_type_filter)]
        elif well_type_filter != "All":
            df = df[df["well_type"] == well_type_filter]

    df = df[(df["year"] >= year_range[0]) & (df["year"] <= year_range[1])]
    return df


def _sync_runtime_state(state, force_data_reload=False):
    state_data.ensure_data_loaded(force=force_data_reload)

    state.company_lov = list(state_data.company_lov)
    state.field_lov = list(state_data.field_lov)
    state.well_type_lov = list(state_data.well_type_lov)
    state.year_min = state_data.year_min
    state.year_max = state_data.year_max
    state.data_runtime_status = state_data.data_runtime_status
    state.sql_cache_status = get_sqlite_db_status()

    state.company_filter = _normalize_selector_value(
        getattr(state, "company_filter", "All"),
        state.company_lov,
    )
    state.field_filter = _normalize_selector_value(
        getattr(state, "field_filter", "All"),
        state.field_lov,
    )
    state.well_type_filter = _normalize_selector_value(
        getattr(state, "well_type_filter", "All"),
        state.well_type_lov,
    )

    current_year_range = getattr(
        state,
        "year_range",
        [state.year_min, state.year_max],
    )
    if not isinstance(current_year_range, list) or len(current_year_range) != 2:
        current_year_range = [state.year_min, state.year_max]

    try:
        year_start = int(current_year_range[0]) if current_year_range else state.year_min
    except (TypeError, ValueError):
        year_start = state.year_min
    try:
        year_end = int(current_year_range[1]) if current_year_range else state.year_max
    except (TypeError, ValueError):
        year_end = state.year_max
    year_start = max(state.year_min, min(year_start, state.year_max))
    year_end = max(state.year_min, min(year_end, state.year_max))
    if year_start > year_end:
        year_start, year_end = state.year_min, state.year_max
    state.year_range = [year_start, year_end]


def update_state(state):
    # ---------- FILTER PRODUCTION DATA ----------
    company_filter = state.company_filter
    field_filter = state.field_filter
    well_type_filter = state.well_type_filter

    d1 = _apply_filters(
        state_data.prod.copy(), company_filter, field_filter, well_type_filter, state.year_range
    )
    state.filtered_prod = d1
    state.filtered_prod_view = d1.head(state_data.MAX_TABLE_ROWS)

    # ---------- FILTER FRAC DATA ----------
    d2 = _apply_filters(
        state_data.frac.copy(), company_filter, field_filter, well_type_filter, state.year_range
    )

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
    state.filtered_frac_view = d2.head(state_data.MAX_TABLE_ROWS)

    if not d2.empty:
        state.avg_lateral_by_company_df = (
            d2.groupby("company", as_index=False)["lateral_length_ft"]
            .mean()
            .sort_values("lateral_length_ft", ascending=False)
        )
    else:
        state.avg_lateral_by_company_df = d2.head(0)

    if len(d2) > state_data.FRAC_SAMPLE_N:
        state.filtered_frac_sample = d2.sample(state_data.FRAC_SAMPLE_N, random_state=0)
    else:
        state.filtered_frac_sample = d2

    # ---------- FILTER DRILL DATA ----------
    d3 = _apply_filters(
        state_data.drill.copy(), company_filter, field_filter, well_type_filter, state.year_range
    )
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
    d4 = _apply_filters(
        state_data.comp.copy(), company_filter, field_filter, well_type_filter, state.year_range
    )
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

    state.avg_depth = round(latest["depth"].mean(), 2) if not latest.empty else 0.0
    state.avg_lateral = (
        round(state.filtered_frac["lateral_length_ft"].mean(), 2) if not state.filtered_frac.empty else 0.0
    )

    state.well_lov = sorted(state.filtered_prod["well_name"].dropna().unique().tolist())
    selected_well = getattr(state, "selected_well", "")
    if selected_well and selected_well not in state.well_lov:
        state.selected_well = ""

    if getattr(state, "selected_well", ""):
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
# NAVIGATION
# ------------------------------------------------------------------
_NAV_PAGES = [
    ("overview", "/", "🏠 OVERVIEW"),
    ("geology", "geology", "🪨 GEOLOGY"),
    ("drilling", "drilling", "🛠️ DRILLING"),
    ("frac", "frac", "💥 FRAC"),
    ("production", "production", "📈 PRODUCTION"),
    ("map", "map", "🗺️ MAP"),
    ("wells", "wells", "🔎 WELLS"),
    ("data", "data", "📄 DATA"),
    ("chat", "chat", "🤖 CHAT"),
    ("links", "links", "🔗 LINKS"),
    ("about", "about", "ℹ️ ABOUT"),
]


def update_nav(state):
    current = getattr(state, "active_page", "overview")
    for page_name, _, _ in _NAV_PAGES:
        attr = f"nav_{page_name}"
        is_active = current == page_name or (page_name == "overview" and current == "/")
        setattr(state, attr, "nav-button active" if is_active else "nav-button")


_NAV_DESTINATIONS = {name: dest for name, dest, _ in _NAV_PAGES}


def _go_to_page(state, page_name, destination):
    state.active_page = page_name
    update_state(state)
    update_nav(state)
    navigate(state, to=destination)


def go_overview(state):
    _go_to_page(state, "overview", "/")


def go_geology(state):
    _go_to_page(state, "geology", "geology")


def go_drilling(state):
    _go_to_page(state, "drilling", "drilling")


def go_frac(state):
    _go_to_page(state, "frac", "frac")


def go_production(state):
    _go_to_page(state, "production", "production")


def go_map(state):
    _go_to_page(state, "map", "map")


def go_wells(state):
    _go_to_page(state, "wells", "wells")


def go_data(state):
    _go_to_page(state, "data", "data")


def go_chat(state):
    _go_to_page(state, "chat", "chat")


def go_links(state):
    _go_to_page(state, "links", "links")


def go_about(state):
    _go_to_page(state, "about", "about")


_NAV_ACTIONS = {
    "overview": go_overview,
    "geology": go_geology,
    "drilling": go_drilling,
    "frac": go_frac,
    "production": go_production,
    "map": go_map,
    "wells": go_wells,
    "data": go_data,
    "chat": go_chat,
    "links": go_links,
    "about": go_about,
}


def sidebar():
    with tgb.part(class_name="sidebar"):
        tgb.text("## 📘 Navigation", mode="md")
        for page_name, _, label in _NAV_PAGES:
            tgb.button(
                label,
                class_name="{nav_" + page_name + "}",
                on_action=_NAV_ACTIONS[page_name],
            )


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
    _sync_runtime_state(state)

    if not hasattr(state, "active_page"):
        state.active_page = "overview"
    if not hasattr(state, "map_metric") or not state.map_metric:
        state.map_metric = "Oil"
    if not hasattr(state, "openrouter_model") or not state.openrouter_model:
        state.openrouter_model = state_data.OPENROUTER_DEFAULT_MODEL
    if not hasattr(state, "openrouter_api_key_input"):
        state.openrouter_api_key_input = ""
    if not hasattr(state, "web_search_api_key_input"):
        state.web_search_api_key_input = ""
    if not hasattr(state, "chat_messages") or not state.chat_messages:
        state.chat_messages = [["m0", _chat_welcome_message(), "assistant"]]
    if not hasattr(state, "chat_users"):
        state.chat_users = state_data.chat_users
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
    if not hasattr(state, "selected_well"):
        state.selected_well = ""
    ensure_sqlite_db()
    state.sql_cache_status = get_sqlite_db_status()
    _update_chat_runtime_status(state)
    update_state(state)
    update_nav(state)


def reload_dashboard_data(state):
    state_data.ensure_data_loaded(force=True)
    ensure_sqlite_db(force=True)
    state.sql_cache_status = get_sqlite_db_status()
    update_state(state)
    _update_chat_runtime_status(state)
