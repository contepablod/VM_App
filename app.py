import os
import pandas as pd
import taipy.gui.builder as tgb
from taipy.gui import Gui
from taipy.gui.gui_actions import download, navigate


# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------
def download_filtered_prod(state):
    csv_content = state.filtered_prod.to_csv(index=False).encode("utf-8")
    return download(state, csv_content, name="filtered_prod_data.csv")


def download_filtered_frac(state):
    csv_content = state.filtered_frac.to_csv(index=False).encode("utf-8")
    return download(state, csv_content, name="filtered_frac_data.csv")


# ------------------------------------------------------------------
# CONFIG & DATA
# ------------------------------------------------------------------
MAX_TABLE_ROWS = 2000
FRAC_SAMPLE_N = 5000

# Paths
DATA_PATH_FRAC = "data/well_frac_data.csv"
DATA_PATH_PROD = "data/well_prod_data.csv"
DATA_PATH_DRILL = "data/drill_data.csv"
DATA_PATH_COMP = 'data/completion_data.csv'
HEADER1_IMAGE_PATH = "images/vm_map.png"
HEADER2_IMAGE_PATH = "images/vm_rig_night.png"

# CSV's
frac = pd.read_csv(DATA_PATH_FRAC)
prod = pd.read_csv(DATA_PATH_PROD)
drill = pd.read_csv(DATA_PATH_DRILL)
comp = pd.read_csv(DATA_PATH_COMP)

prod["date"] = pd.to_datetime(
    pd.DataFrame({"year": prod["year"], "month": prod["month"], "day": 31}),
    errors="coerce",
)

# LOV's
company_lov = ["All"] + sorted(frac["company"].dropna().unique())
field_lov = ["All"] + sorted(frac["field"].dropna().unique())
well_type_lov = ["All"] + sorted(prod["well_type"].dropna().unique())
year_min = int(prod["year"].min())
year_max = int(prod["year"].max())

# Filters
company_filter = "All"
field_filter = "All"
well_type_filter = "All"
year_range = [year_min, year_max]

# Dataframes
filtered_prod = prod.copy()
filtered_frac = frac.copy()
filtered_drill = drill.copy()
filtered_comp = comp.copy()

# speed helpers
filtered_frac_sample = frac.copy()
filtered_prod_view = pd.DataFrame()
filtered_frac_view = pd.DataFrame()

# derived df's
top_oil_wells_df = pd.DataFrame()
top_gas_wells_df = pd.DataFrame()
prod_time_df = pd.DataFrame()
map_df = pd.DataFrame()
wells_by_type_df = pd.DataFrame()
depth_by_type_df = pd.DataFrame()
avg_lateral_by_company_df = pd.DataFrame()

# drilling/completion aggregated dfs
drill_wells_by_year_df = pd.DataFrame()
drill_meters_by_year_df = pd.DataFrame()
drill_meters_by_company_df = pd.DataFrame()

comp_by_year_df = pd.DataFrame()
comp_by_company_df = pd.DataFrame()

# Wells selected
selected_prod_df = pd.DataFrame()
selected_frac_df = pd.DataFrame()


# KPIs – drilling
drilled_wells = 0
drilled_meters = 0.0
avg_depth = 0.0
avg_lateral = 0.0

# KPIs – frac
n_frac_wells = 0
avg_lateral_length = 0.0
avg_stages = 0.0
total_proppant = 0.0
total_fluid = 0.0
avg_proppant_intensity = 0.0
avg_fluid_intensity = 0.0

# KPIs – production
n_wells = 0
total_oil = 0.0
total_gas = 0.0
total_water = 0.0

# Map / spatial
max_oil = 0
max_gas = 0
sizeref_oil = 0
sizeref_gas = 0
map_metric = "Oil"
map_min_percentile = 0
map_metric_label = "Oil"
text = ""
selected_well = ""

# Navigation state
active_page = "overview"
nav_overview = "nav-button active"
nav_drilling = nav_production = nav_frac = nav_map = nav_wells = nav_data = (
    nav_links
) = nav_geology = nav_about = "nav-button"


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

    # field fIlter
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

    # company filter
    if isinstance(company_filter, list):
        if "All" not in company_filter:
            d2 = d2[d2["company"].isin(company_filter)]
    elif company_filter != "All":
        d2 = d2[d2["company"] == company_filter]

    # field filter
    if isinstance(field_filter, list):
        if "All" not in field_filter:
            d2 = d2[d2["field"].isin(field_filter)]
    elif field_filter != "All":
        d2 = d2[d2["field"] == field_filter]

    # well type filter
    if "well_type" in d2.columns:
        if isinstance(well_type_filter, list):
            if "All" not in well_type_filter:
                d2 = d2[d2["well_type"].isin(well_type_filter)]
        elif well_type_filter != "All":
            d2 = d2[d2["well_type"] == well_type_filter]

    d2 = d2[(d2["year"] >= state.year_range[0]) & (d2["year"] <= state.year_range[1])]

    # ---- Add frac intensity metrics  ----
    if not d2.empty:
        d2 = d2.copy()

        lateral = d2["lateral_length_ft"].replace(0, pd.NA)  # avoid division by zero
        d2["proppant_intensity_lbft"] = d2["proppant_pumped_lb"] / lateral
        d2["fluid_intensity_bblft"] = d2["fluid_pumped_bbl"] / lateral

    # ---- Add cumulative production to frac from prod ----
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
        cum["oil_cum_km3"] = cum["oil_cum_m3_raw"] / 1_000_000.0  # m³ -> ~Mm³
        cum["gas_cum_Mm3"] = cum["gas_cum_km3_raw"] / 1_000.0  # km³ -> ~Mm³

        d2 = d2.merge(
            cum[["well_id", "oil_cum_km3", "gas_cum_Mm3"]],
            on="well_id",
            how="left",
        )

    state.filtered_frac = d2
    state.filtered_frac_view = d2.head(MAX_TABLE_ROWS)

    # --- Avg lateral length by company precomputed ---
    if not d2.empty:
        state.avg_lateral_by_company_df = (
            d2.groupby("company", as_index=False)["lateral_length_ft"]
            .mean()
            .sort_values("lateral_length_ft", ascending=False)
        )
    else:
        state.avg_lateral_by_company_df = d2.head(0)

    # sample for heavy scatters
    if len(d2) > FRAC_SAMPLE_N:
        state.filtered_frac_sample = d2.sample(FRAC_SAMPLE_N, random_state=0)
    else:
        state.filtered_frac_sample = d2

    # ---------- FILTER DRILL DATA ----------
    d3 = drill.copy()

    # company filter
    if isinstance(company_filter, list):
        if "All" not in company_filter:
            d3 = d3[d3["company"].isin(company_filter)]
    elif company_filter != "All":
        d3 = d3[d3["company"] == company_filter]

    # field filter
    if isinstance(field_filter, list):
        if "All" not in field_filter:
            d3 = d3[d3["field"].isin(field_filter)]
    elif field_filter != "All":
        d3 = d3[d3["field"] == field_filter]

    # year range
    d3 = d3[(d3["year"] >= state.year_range[0]) & (d3["year"] <= state.year_range[1])]
    state.filtered_drill = d3

    # Precompute drilling groupbys
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

    # Company filter
    if isinstance(state.company_filter, list):
        if "All" not in state.company_filter:
            d4 = d4[d4["company"].isin(state.company_filter)]
    elif state.company_filter != "All":
        d4 = d4[d4["company"] == state.company_filter]

    # Field filter
    if isinstance(state.field_filter, list):
        if "All" not in state.field_filter:
            d4 = d4[d4["field"].isin(state.field_filter)]
    elif state.field_filter != "All":
        d4 = d4[d4["field"] == state.field_filter]

    # Year filter
    d4 = d4[(d4["year"] >= state.year_range[0]) & (d4["year"] <= state.year_range[1])]

    state.filtered_comp = d4

    # Precompute completion groupbys
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
            # fallback to counting rows if completion column missing
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

    # ---------- LATEST RECORD PER WELL (for KPIs & map) ----------
    latest = d1 if not d1.empty else d1.head(0)

    # ---------- KPIs: production ----------
    state.n_wells = latest["well_id"].nunique() if not latest.empty else 0
    state.total_oil = (
        round(latest["oil_prod_m3"].sum() / 1_000_000, 2) if not latest.empty else 0.0
    )
    state.total_gas = (
        round(latest["gas_prod_km3"].sum() / 1_000, 2) if not latest.empty else 0.0
    )
    state.total_water = (
        round(latest["water_prod_m3"].sum() / 1_000_000, 2) if not latest.empty else 0.0
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

        # basic stats
        state.max_oil = latest2["oil_cum_m3"].max()
        state.max_gas = latest2["gas_cum_km3"].max()

        # bubble sizes for OIL (95% quantile scaling)
        oil = latest2["oil_cum_m3"].fillna(0)
        q95_oil = oil.quantile(0.95)
        if q95_oil <= 0:
            q95_oil = 1.0
        latest2["oil_size"] = 4 + 36 * oil.clip(upper=q95_oil) / q95_oil

        # bubble sizes for GAS
        gas = latest2["gas_cum_km3"].fillna(0)
        q95_gas = gas.quantile(0.95)
        if q95_gas <= 0:
            q95_gas = 1.0
        latest2["gas_size"] = 4 + 36 * gas.clip(upper=q95_gas) / q95_gas

        # Map toggle
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
        state.total_fluid = round(d2["fluid_pumped_bbl"].sum() / 1_000_100, 2)

        # intensity KPIs
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

    if not state.filtered_prod.empty:
        state.avg_depth = round(state.filtered_prod["depth"].mean(), 2)
    else:
        state.avg_depth = 0.0

    if not state.filtered_frac.empty:
        state.avg_lateral = round(
            state.filtered_frac["lateral_length_ft"].mean(), 2
        )
    else:
        state.avg_lateral = 0.0

    # ---------- Selected well data ----------
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

    state.nav_overview = "nav-button active" if current == "overview" else "nav-button"
    state.nav_geology = "nav-button active" if current == "geology" else "nav-button"
    state.nav_drilling = "nav-button active" if current == "drilling" else "nav-button"
    state.nav_frac = "nav-button active" if current == "frac" else "nav-button"
    state.nav_production = (
        "nav-button active" if current == "production" else "nav-button"
    )
    state.nav_map = "nav-button active" if current == "map" else "nav-button"
    state.nav_wells = "nav-button active" if current == "wells" else "nav-button"
    state.nav_data = "nav-button active" if current == "data" else "nav-button"
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
        state.active_page = "/"
    if not hasattr(state, "map_metric") or not state.map_metric:
        state.map_metric = "Oil"
    update_state(state)
    update_nav(state)


# Navigation actions
def go_overview(state):
    state.active_page = "/"
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
        tgb.button(
            "📈 PRODUCTION", class_name="{nav_production}", on_action=go_production
        )
        tgb.button("🗺️ MAP", class_name="{nav_map}", on_action=go_map)
        tgb.button("🔎 WELLS", class_name="{nav_wells}", on_action=go_wells)
        tgb.button("📄 DATA", class_name="{nav_data}", on_action=go_data)
        tgb.button("🔗 LINKS", class_name="{nav_links}", on_action=go_links)
        tgb.button("ℹ️ ABOUT", class_name="{nav_about}", on_action=go_about)


# ------------------------------------------------------------------
# PAGE LAYOUTS
# ------------------------------------------------------------------
with tgb.Page() as overview_page:
    sidebar()
    with tgb.part(class_name="main_content"):
        tgb.text("# 🛢️ Vaca Muerta Formation – Overview", mode="md")
        with tgb.part(class_name="card"):
            with tgb.layout(columns="1 2"):
                with tgb.part():
                    tgb.image(HEADER1_IMAGE_PATH, width="100%", height="100%")
                with tgb.part(class_name="card"):
                    tgb.text(
                        "### 🌎 About Vaca Muerta\n\n"
                        "Vaca Muerta is a vast shale formation located in the Neuquén Basin in western Argentina, widely "
                        "recognized as one of the largest and most significant unconventional oil and gas reserves in the world. "
                        "The formation stretches across several provinces and covers an area of roughly 30,000 square kilometers. "
                        "Its geological origins date back to the transition between the Late Jurassic and Early Cretaceous periods, "
                        "when an ancient inland sea deposited thick layers of organic-rich sediment. Over millions of years, these "
                        "sediments were buried and slowly transformed into a rock unit with exceptional potential for hydrocarbon "
                        "generation. The shale is extremely fine grained and has very low natural permeability. As a result, the "
                        "large quantities of oil and gas trapped within it cannot move freely, which makes advanced techniques such "
                        "as horizontal drilling and hydraulic fracturing essential for releasing the hydrocarbons stored in the "
                        "formation.\n\n"
                        "The size and richness of Vaca Muerta have made it a central focus of Argentina’s energy policy and long-term "
                        "development strategy. Geological assessments from both national and international institutions describe it "
                        "as one of the most promising shale resources outside North America, placing it in the same category as "
                        "major United States plays such as the Permian Basin. This potential has attracted large-scale investment "
                        "from both Argentine and foreign companies. YPF, the national oil company, has partnered with global firms "
                        "such as Chevron, Shell, ExxonMobil, and TotalEnergies to develop pilot projects and full production blocks. "
                        "Over the past decade, drilling efficiency has increased significantly, well productivity has improved, and "
                        "new infrastructure has been built to handle growing output. Key projects include high-capacity gas pipelines "
                        "designed to connect the Neuquén Basin with major industrial centers and, in the future, with export terminals "
                        "that could allow Argentina to enter the global liquefied natural gas market.\n\n"
                        "Economic studies emphasize the transformative role Vaca Muerta could play. Higher domestic production has "
                        "already reduced Argentina’s reliance on energy imports, and continued development could lead to sustained "
                        "economic growth, increased employment, and greater industrial activity in related sectors such as "
                        "construction, transportation, and petrochemicals. The region surrounding the formation, especially the town "
                        "of Añelo, has experienced rapid expansion as workers and businesses move in to support the growing industry. "
                        "Local governments, companies, and national agencies have begun planning to expand housing, public services, "
                        "and infrastructure to accommodate this development.\n\n"
                        # "At the same time, Vaca Muerta has become the subject of important environmental and social discussions. "
                        # "Scientific and environmental reports highlight concerns about the large volumes of water required for "
                        # "hydraulic fracturing in an area where water resources are limited. Researchers have also examined the "
                        # "increase in seismic activity associated with wastewater disposal wells in parts of the basin. Air quality, "
                        # "methane emissions, and the long-term management of drilling waste have become central topics in regional "
                        # "environmental assessments. Social studies have documented the pressure that rapid industrialization places "
                        # "on local communities, which face rising costs of living, growing demand for services, and changes to "
                        # "traditional economic activities. These issues have led experts to call for strong regulation, continuous "
                        # "monitoring, and clear planning to ensure that the benefits of development are balanced with protection of "
                        # "the environment and the well-being of nearby populations.\n\n"
                        "Taken as a whole, Vaca Muerta represents an extraordinary combination of geological richness, technological "
                        "challenge, economic potential, and environmental complexity. It is one of the most influential energy "
                        "projects in Latin America and continues to shape Argentina’s national policy, international partnerships, "
                        "and long-term economic outlook. The future of the formation will depend not only on technological innovation "
                        "and global energy markets but also on Argentina’s ability to manage environmental impacts, support local "
                        "communities, and develop infrastructure that allows the resource to be used sustainably and responsibly.",
                        mode="md",
                    )
                # Add spacing
            with tgb.part():
                tgb.text("&nbsp;", mode="md")
            with tgb.part():
                tgb.image(HEADER2_IMAGE_PATH, width="100%")

        tgb.text("### 🔍 Filters", mode="md")
        with tgb.layout(columns="1 1 1 1"):
            tgb.selector(
                label="Company",
                value="{company_filter}",
                lov=company_lov,
                multiple=True,
                dropdown=True,
                on_change=on_change,
            )
            tgb.selector(
                label="Field",
                value="{field_filter}",
                lov=field_lov,
                multiple=True,
                dropdown=True,
                on_change=on_change,
            )
            tgb.selector(
                label="Well Type",
                value="{well_type_filter}",
                lov=well_type_lov,
                multiple=True,
                dropdown=True,
                on_change=on_change,
            )
            with tgb.part():
                tgb.text("📅 Year Range")
                tgb.slider(
                    value="{year_range}",
                    min=year_min,
                    max=year_max,
                    on_change=on_change,
                )

        with tgb.part(class_name="card"):
            tgb.text("## KPIs", mode="md")
            with tgb.layout(columns="1 1 1"):
                with tgb.part():
                    tgb.text("### 📊 Production", mode="md")
                    # tgb.text("**#️⃣ Number of wells:** {n_wells}", mode="md")
                    tgb.text("**🛢️ Total Oil (Mm³):** {total_oil}", mode="md")
                    tgb.text("**🔥 Total Gas (Mm³):** {total_gas}", mode="md")
                    tgb.text("**💧 Total Water (Mm³):** {total_water}", mode="md")
                with tgb.part():
                    tgb.text("### 📌 Drilling", mode="md")
                    tgb.text(
                        "**Total Wells Drilled:** {drilled_wells}",
                        mode="md",
                    )
                    tgb.text(
                        "**Total Drilled Meters:** {drilled_meters}",
                        mode="md",
                    )
                    tgb.text(
                        "**Average Depth (ft):** {avg_depth}",
                        mode="md",
                    )
                    tgb.text(
                        "**Average Lateral Length (ft):** {avg_lateral}",
                        mode="md",
                    )
                with tgb.part():
                    tgb.text("### 💥 Frac", mode="md")
                    tgb.text("**🧵 Frac'd wells:** {n_frac_wells}", mode="md")
                    tgb.text("**📏 Avg lateral (ft):** {avg_lateral_length}", mode="md")
                    tgb.text("**🎯 Avg stages:** {avg_stages}", mode="md")
                    tgb.text("**🪨 Proppant (Mlb):** {total_proppant}", mode="md")
                    tgb.text("**💧 Fluid (Mbbl):** {total_fluid}", mode="md")
                    tgb.text(
                        "**🪨 Intensity (lb/ft):** {avg_proppant_intensity}",
                        mode="md",
                    )
                    tgb.text(
                        "**💧 Intensity (bbl/ft):** {avg_fluid_intensity}",
                        mode="md",
                    )

# Geology Page
with tgb.Page() as geology_page:
    sidebar()
    with tgb.part(class_name="main-content"):
        tgb.text("# 🪨 Geology & Stratigraphy", mode="md")

        # Regional / stratigraphic description
        with tgb.part(class_name="card"):
            tgb.text("### 🧭 Regional Setting", mode="md")
            tgb.text(
                "Vaca Muerta is part of the Neuquén Basin in western Argentina. It consists of organic-rich "
                "marine shales deposited during the Late Jurassic–Early Cretaceous in a back-arc basin setting. "
                "Over time, burial and heating generated large volumes of hydrocarbons that are now trapped "
                "within low-permeability mudstones and interbedded siltstones.",
                mode="md",
            )

            tgb.text(
                "- **Lithology:** predominantly black shales with carbonate and silty intervals.\n"
                "- **Environment:** deep-water to outer-shelf depositional setting.\n"
                "- **Play type:** unconventional, tight/low-permeability source rock reservoir.\n",
                mode="md",
            )

        # Depth distribution
        with tgb.part(class_name="card"):
            tgb.text("### 📏 Depth Distribution of Wells", mode="md")
            tgb.chart(
                type="histogram",
                data="{filtered_prod}",
                x="depth",
                height="350px",
                layout={
                    "xaxis": {"title": {"text": "Depth (ft)"}},
                    "yaxis": {"title": {"text": "Number of wells"}},
                },
            )

        # Average depth by well type
        with tgb.part(class_name="card"):
            tgb.text("### 🧱 Average Depth by Well Type", mode="md")
            tgb.chart(
                type="bar",
                data="{depth_by_type_df}",
                x="well_type",
                y="avg_depth",
                height="350px",
                layout={
                    "xaxis": {"title": {"text": "Well Type"}, "automargin": True},
                    "yaxis": {
                        "title": {"text": "Average Depth (ft)"},
                        "automargin": True,
                    },
                },
            )

        tgb.text(
            "_Note: depths are taken from the latest record per well after filtering by company, field, "
            "well type, and year range._",
            mode="md",
        )

# Drilling Page
with tgb.Page() as drilling_page:
    sidebar()
    with tgb.part(class_name="main-content"):
        tgb.text("# 🛠️ Drilling Analytics", mode="md")

        # --- Wells & meters drilled per year ---
        with tgb.part(class_name="card"):
            tgb.text("### ⛏️ Activity per Year", mode="md")
            with tgb.layout(columns="1 1"):
                # Wells drilled per year
                with tgb.part():
                    tgb.text("Wells Drilled per Year", mode="md")
                    tgb.chart(
                        type="bar",
                        data="{drill_wells_by_year_df}",
                        x="year",
                        y="wells",
                        height="320px",
                        layout={
                            "xaxis": {"title": {"text": "Year"}},
                            "yaxis": {"title": {"text": "Wells Drilled"}},
                        },
                    )
                # Meters drilled per year
                with tgb.part():
                    tgb.text("Meters Drilled per Year", mode="md")
                    tgb.chart(
                        type="bar",
                        data="{drill_meters_by_year_df}",
                        x="year",
                        y="meters",
                        height="320px",
                        layout={
                            "xaxis": {"title": {"text": "Year"}},
                            "yaxis": {"title": {"text": "Meters Drilled"}},
                        },
                    )

        # --- Meters per company ---
        with tgb.part(class_name="card"):
            tgb.text("### 🏢 Meters Drilled by Company", mode="md")
            tgb.chart(
                type="bar",
                data="{drill_meters_by_company_df}",
                x="company",
                y="meters",
                height="380px",
                layout={
                    "xaxis": {"title": {"text": "Company"}, "automargin": True},
                    "yaxis": {"title": {"text": "Meters Drilled"}, "automargin": True},
                },
            )

        # --- Depth distribution ---
        with tgb.part(class_name="card"):
            tgb.text("### 📏 Depth Distribution (ft)", mode="md")
            tgb.chart(
                type="histogram",
                data="{filtered_prod}",
                x="depth",
                height="350px",
                layout={
                    "xaxis": {"title": {"text": "Depth (ft)"}},
                    "yaxis": {"title": {"text": "Count"}},
                },
            )

        # --- Lateral length analysis ---
        tgb.text("### 📐 Lateral Length Analysis", mode="md")
        with tgb.layout(columns="1 1"):
            with tgb.part(class_name="card"):
                tgb.text("Lateral Length Distribution", mode="md")
                tgb.chart(
                    type="histogram",
                    data="{filtered_frac}",
                    x="lateral_length_ft",
                    height="350px",
                    layout={
                        "xaxis": {"title": {"text": "Lateral Length (ft)"}},
                        "yaxis": {"title": {"text": "Count"}},
                    },
                )

            with tgb.part(class_name="card"):
                tgb.text("Average Lateral Length by Company", mode="md")
                tgb.chart(
                    type="bar",
                    data="{avg_lateral_by_company_df}",
                    x="company",
                    y="lateral_length_ft",
                    height="350px",
                    layout={
                        "xaxis": {"title": {"text": "Company"}, "automargin": True},
                        "yaxis": {
                            "title": {"text": "Avg Lateral (ft)"},
                            "automargin": True,
                        },
                    },
                )

                # --- Completion Analytics ---
        tgb.text("### 🎯 Completion Analytics", mode="md")

        with tgb.layout(columns="1 1"):

            # --- Completions per Year ---
            with tgb.part(class_name="card"):
                tgb.text("Completions per Year", mode="md")
                tgb.chart(
                    type="bar",
                    data="{comp_by_year_df}",
                    x="year",
                    y="completions",
                    height="350px",
                    layout={
                        "xaxis": {"title": {"text": "Year"}},
                        "yaxis": {"title": {"text": "Completions"}},
                    },
                )

            # --- Completions per Company ---
            with tgb.part(class_name="card"):
                tgb.text("Completions by Company", mode="md")
                tgb.chart(
                    type="bar",
                    data="{comp_by_company_df}",
                    x="company",
                    y="completions",
                    height="350px",
                    layout={
                        "xaxis": {"title": {"text": "Company"}, "automargin": True},
                        "yaxis": {"title": {"text": "Completions"}},
                    },
                )

                tgb.text(
                    "_All drilling trends update dynamically with filters (company, field, well type, year range)._",
                    mode="md",
                )


# Frac Page
with tgb.Page() as frac_page:
    sidebar()
    with tgb.part(class_name="main-content"):
        tgb.text("# 💥 Frac Diagnostics", mode="md")

        with tgb.part(class_name="card"):
            tgb.text("### Frac Intensity KPIs", mode="md")
            tgb.text(
                "**🪨 Avg proppant intensity (lb/ft):** {avg_proppant_intensity}",
                mode="md",
            )
            tgb.text(
                "**💧 Avg fluid intensity (bbl/ft):** {avg_fluid_intensity}", mode="md"
            )
            tgb.text("**📏 Avg lateral length (ft):** {avg_lateral_length}", mode="md")
            tgb.text("**🎯 Avg stages:** {avg_stages}", mode="md")

        tgb.text("### Treatment Intensities", mode="md")
        with tgb.layout(columns="1 1"):
            with tgb.part(class_name="card"):
                tgb.chart(
                    type="scatter",
                    data="{filtered_frac_sample}",
                    x="lateral_length_ft",
                    y="proppant_pumped_lb",
                    marker={"color": "orange", "opacity": 0.5},
                    mode="markers",
                    text="well_name",
                    height="450px",
                    layout={
                        "xaxis": {"title": "Lateral Length (ft)"},
                        "yaxis": {"title": "Proppant (lb)"},
                    },
                )

            with tgb.part(class_name="card"):
                tgb.chart(
                    type="scatter",
                    data="{filtered_frac_sample}",
                    x="lateral_length_ft",
                    y="fluid_pumped_bbl",
                    marker={"color": "deepskyblue", "opacity": 0.6},
                    mode="markers",
                    text="well_name",
                    height="450px",
                    layout={
                        "xaxis": {"title": "Lateral Length (ft)"},
                        "yaxis": {"title": "Fluid (bbl)"},
                    },
                )

        tgb.text("### Depth / Lateral vs Production", mode="md")
        with tgb.layout(columns="1 1"):
            with tgb.part(class_name="card"):
                tgb.text("📏 Lateral vs Cum Oil", mode="md")
                tgb.chart(
                    type="scatter",
                    data="{filtered_frac_sample}",
                    x="lateral_length_ft",
                    y="oil_cum_km3",
                    marker={"color": "green", "opacity": 0.5},
                    mode="markers",
                    text="well_name",
                    height="450px",
                    layout={
                        "xaxis": {"title": "Lateral Length (ft)"},
                        "yaxis": {"title": "Cum Oil (km³)"},
                    },
                )

            with tgb.part(class_name="card"):
                tgb.text("📏 Lateral vs Cum Gas", mode="md")
                tgb.chart(
                    type="scatter",
                    data="{filtered_frac_sample}",
                    x="lateral_length_ft",
                    y="gas_cum_Mm3",
                    marker={"color": "red", "opacity": 0.6},
                    mode="markers",
                    text="well_name",
                    height="450px",
                    layout={
                        "xaxis": {"title": "Lateral Length (ft)"},
                        "yaxis": {"title": "Cum Gas (Mm³)"},
                    },
                )

        tgb.text("### Stages vs Production", mode="md")
        with tgb.layout(columns="1 1"):
            with tgb.part(class_name="card"):
                tgb.text("#️⃣ Stages vs Cum Oil", mode="md")
                tgb.chart(
                    type="scatter",
                    data="{filtered_frac_sample}",
                    x="number_stages",
                    y="oil_cum_km3",
                    marker={"color": "green", "opacity": 0.5},
                    mode="markers",
                    height="450px",
                    layout={
                        "xaxis": {"title": "Stages"},
                        "yaxis": {"title": "Cumulative Oil (km³)"},
                    },
                )

            with tgb.part(class_name="card"):
                tgb.text("#️⃣ Stages vs Cum Gas", mode="md")
                tgb.chart(
                    type="scatter",
                    data="{filtered_frac_sample}",
                    x="number_stages",
                    y="gas_cum_Mm3",
                    marker={"color": "red", "opacity": 0.5},
                    mode="markers",
                    height="450px",
                    layout={
                        "xaxis": {"title": "Stages"},
                        "yaxis": {"title": "Cumulative Gas (Mm³)"},
                    },
                )

        tgb.text("### Intensity vs Production", mode="md")
        with tgb.layout(columns="1 1"):
            with tgb.part(class_name="card"):
                tgb.text("🪨 Proppant Intensity vs Cum Oil", mode="md")
                tgb.chart(
                    type="scatter",
                    data="{filtered_frac_sample}",
                    x="proppant_intensity_lbft",
                    y="oil_cum_km3",
                    marker={"color": "orange", "opacity": 0.6},
                    mode="markers",
                    height="400px",
                    layout={
                        "xaxis": {"title": "Proppant Intensity (lb/ft)"},
                        "yaxis": {"title": "Cumulative Oil (km³)"},
                    },
                )

            with tgb.part(class_name="card"):
                tgb.text("💧 Fluid Intensity vs Cum Oil", mode="md")
                tgb.chart(
                    type="scatter",
                    data="{filtered_frac_sample}",
                    x="fluid_intensity_bblft",
                    y="oil_cum_km3",
                    marker={"color": "deepskyblue", "opacity": 0.6},
                    mode="markers",
                    height="400px",
                    layout={
                        "xaxis": {"title": "Fluid Intensity (bbl/ft)"},
                        "yaxis": {"title": "Cumulative Oil (km³)"},
                    },
                )

        with tgb.layout(columns="1 1"):
            with tgb.part(class_name="card"):
                tgb.text("🪨 Proppant Intensity vs Cum Gas", mode="md")
                tgb.chart(
                    type="scatter",
                    data="{filtered_frac_sample}",
                    x="proppant_intensity_lbft",
                    y="gas_cum_Mm3",
                    marker={"color": "orange", "opacity": 0.6},
                    mode="markers",
                    height="400px",
                    layout={
                        "xaxis": {"title": "Proppant Intensity (lb/ft)"},
                        "yaxis": {"title": "Cumulative Gas (Mm³)"},
                    },
                )

            with tgb.part(class_name="card"):
                tgb.text("💧 Fluid Intensity vs Cum Gas", mode="md")
                tgb.chart(
                    type="scatter",
                    data="{filtered_frac_sample}",
                    x="fluid_intensity_bblft",
                    y="gas_cum_Mm3",
                    marker={"color": "deepskyblue", "opacity": 0.6},
                    mode="markers",
                    height="400px",
                    layout={
                        "xaxis": {"title": "Fluid Intensity (bbl/ft)"},
                        "yaxis": {"title": "Cumulative Gas (Mm³)"},
                    },
                )
# Production Page
with tgb.Page() as production_page:
    sidebar()
    with tgb.part(class_name="main_content"):
        tgb.text("# 📈 Production Analysis", mode="md")
        with tgb.layout(columns="1 2"):
            with tgb.part(class_name="card"):
                tgb.text("### ⛓️ Wells by Type", mode="md")
                tgb.chart(
                    type="bar",
                    data="{wells_by_type_df}",
                    x="well_type",
                    y="n_wells",
                    height="350px",
                    width="100%",
                    layout={
                        "yaxis": {
                            "title": {"text": "Number of wells", "standoff": 10},
                            "automargin": True,
                        },
                        "xaxis": {
                            "title": {"text": "Well Type", "standoff": 10},
                            "automargin": True,
                        },
                    },
                )
            with tgb.part(class_name="card"):
                tgb.text("### 🛢️🔥💧 Monthly Production Over Time", mode="md")
                tgb.chart(
                    type="line",
                    data="{prod_time_df}",
                    x="date",
                    y=["oil_prod_m3", "gas_prod_km3", "water_prod_m3"],
                    color=["green", "red", "blue"],
                    name=["Oil", "Gas", "Water"],
                    height="400px",
                )

        with tgb.layout(columns="1 1"):
            with tgb.part(class_name="card"):
                tgb.text("### 🛢️ Top Oil Wells (Cum)", mode="md")
                tgb.chart(
                    type="bar",
                    data="{top_oil_wells_df}",
                    y="oil_cum_m3",
                    x="well_name",
                    layout={
                        "xaxis": {
                            "title": {"text": "Well Name", "standoff": 10},
                            "automargin": True,
                        },
                        "yaxis": {
                            "title": {"text": "Cummulative Oil (m3)", "standoff": 10},
                            "automargin": True,
                        },
                    },
                    color="green",
                    height="400px",
                )

            with tgb.part(class_name="card"):
                tgb.text("### 🔥 Top Gas Wells (Cum)", mode="md")
                tgb.chart(
                    type="bar",
                    data="{top_gas_wells_df}",
                    y="gas_cum_km3",
                    x="well_name",
                    layout={
                        "xaxis": {
                            "title": {"text": "Well Name", "standoff": 10},
                            "automargin": True,
                        },
                        "yaxis": {
                            "title": {"text": "Cummulative Gas (km3)", "standoff": 10},
                            "automargin": True,
                        },
                    },
                    color="red",
                    height="400px",
                )

# Map Page
with tgb.Page() as map_page:
    sidebar()
    with tgb.part(class_name="main-content"):
        tgb.text("# 🗺️ Spatial Analysis", mode="md")

        with tgb.layout(columns="1 1"):
            tgb.selector(
                label="Map metric",
                value="{map_metric}",
                lov=["Oil", "Gas"],
                on_change=on_change,
            )
            tgb.slider(
                labels="Min Percentile",
                value="{map_min_percentile}",
                min=0,
                max=100,
                step=5,
                on_change=on_change,
            )

        tgb.chart(
            type="scatter",
            data="{map_df}",
            x="Xcoor",
            y="Ycoor",
            marker={
                "size": "map_size",
                "color": "map_color",
                "line": {"width": 1, "color": "map_border_color"},
            },
            text="hover_text",
            mode="markers",
            height="700px",
            width="100%",
            layout={
                "xaxis": {"scaleanchor": "y"},
                "yaxis": {"automargin": True},
            },
        )

# Wells Page
with tgb.Page() as wells_page:
    sidebar()
    with tgb.part(class_name="main-content"):
        tgb.text("# 🔎 Well Explorer", mode="md")

        well_lov = sorted(prod["well_name"].dropna().unique())
        tgb.selector(
            label="Select Well",
            value="{selected_well}",
            lov=well_lov,
            dropdown=True,
            on_change=on_change,
        )

        with tgb.part(class_name="card"):
            tgb.text("### Production History", mode="md")
            tgb.chart(
                type="line",
                data="{selected_prod_df}",
                x="date",
                y=["oil_prod_m3", "gas_prod_km3", "water_prod_m3"],
                color=["green", "red", "blue"],
                height="400px",
            )

        with tgb.part(class_name="card"):
            tgb.text("### Frac Treatment", mode="md")
            tgb.table(data="{selected_frac_df}")

# Data Page
with tgb.Page() as data_page:
    sidebar()
    with tgb.part(class_name="main-content"):
        tgb.text("# 📄 Data Explorer", mode="md")

        tgb.text("### Production Table", mode="md")
        tgb.table(data="{filtered_prod_view}")
        tgb.button("Download Prod Data CSV", on_action=download_filtered_prod)

        tgb.text("### Frac Table", mode="md")
        tgb.table(data="{filtered_frac_view}")
        tgb.button("Download Frac Data CSV", on_action=download_filtered_frac)

# Links of Interest Page
with tgb.Page() as links_page:
    sidebar()
    with tgb.part(class_name="main-content"):
        tgb.text("# 🔗 Links of Interest", mode="md")
        tgb.text(
            "Curated external resources related to Vaca Muerta, unconventional reservoirs, and Argentina’s energy sector.",
            mode="md",
        )

        tgb.text(
            "### 1. 🌎 General Overview\n"
            "**Wikipedia – Vaca Muerta**  \n"
            "A broad introduction: geology, development history, reserves, and operators.  \n"
            "<https://en.wikipedia.org/wiki/Vaca_Muerta>\n\n"
            "**Global Energy Monitor – Vaca Muerta Profile**  \n"
            "Summarizes key facts, environmental considerations, and major corporate players.  \n"
            "<https://www.gem.wiki/Vaca_Muerta>\n\n"
            "---\n\n"
            "### 2. 🧪 Geological & Technical Studies\n"
            "**Legarreta & Villar (2015) – Technical Geological Study**  \n"
            "In-depth stratigraphy, lithology, and depositional environment of the formation.  \n"
            "<https://www.geolabsur.com/Biblioteca/Legarreta_Villar_2015_VM_Urtec.pdf>\n\n"
            "**MDPI Applied Sciences (2024) – “Overview of Recent Developments”**  \n"
            "Scientific review of geology, production technologies, and environmental issues.  \n"
            "<https://www.mdpi.com/2076-3417/14/4/1366>\n\n"
            "---\n\n"
            "### 3. 💼 Energy Industry & Economics\n"
            "**Reuters – “Vaca Muerta propels Argentina closer to energy self-sufficiency”**  \n"
            "Explains recent production growth and Argentina’s potential as a global energy supplier.  \n"
            "<https://www.reuters.com/business/energy/vaca-muerta-shale-formation-propels-argentina-closer-energy-self-sufficiency-2025-06-17/>\n\n"
            "**AAPG Explorer – “Vaca Muerta’s ascent positions Argentina for energy independence”**  \n"
            "Industry-focused analysis on operations, productivity, and investment trends.  \n"
            "<https://www.aapg.org/news-and-media/details/explorer/articleid/69194/vaca-muerta%E2%80%99s-ascent-positions-argentina-for-energy-independence>\n\n"
            "**PwC – “Invest in Vaca Muerta: The Future of Argentina”**  \n"
            "Comprehensive economic and investment report covering reserves, costs, and infrastructure.  \n"
            "<https://www.pwc.com.ar/es/assets/document/invest-in-vaca-muerta.pdf>\n\n"
            "**Rystad Energy – “Vaca Muerta signals Argentina pivot towards LNG exports”**  \n"
            "Expert analysis on LNG potential and Argentina’s emerging export strategy.  \n"
            "<https://www.rystadenergy.com/news/vaca-muerta-signals-argentina-pivot-towards-lng-exports>\n\n"
            "---\n\n"
            "### 4. 🌍 Environment & Social Issues\n"
            "**Environmental Defense Fund – Methane Emissions in Argentina**  \n"
            "Covers methane risks, monitoring gaps, and regulatory challenges.  \n"
            "<https://www.edf.org/climate/methane-argentina>\n\n"
            "**Investigación & Ciencia (Spanish) – “Impactos del fracking en Vaca Muerta”**  \n"
            "Discusses water use, seismicity, and socio-environmental impacts.  \n"
            "<https://www.investigacionyciencia.es/revistas/medio-ambiente/impactos-del-fracking-en-vaca-muerta-2022>\n\n"
            "---\n\n"
            "### 5. 🏛️ Government & Policy\n"
            "**Government of Argentina – Vaca Muerta Overview & History**  \n"
            "Official energy-policy perspective, development strategy, and historical context.  \n"
            "<https://www.argentina.gob.ar/economia/energia/vaca-muerta/historia>\n\n"
            "**Ministry of Energy – Hydrocarbon Development Data**  \n"
            "Production statistics, infrastructure planning, and national reports.  \n"
            "<https://www.argentina.gob.ar/economia/energia/hidrocarburos>\n\n",
            mode="md",
        )

        # with tgb.part(class_name="card"):
        #     tgb.text("### 🧪 Technical / Geological", mode="md")
        #     tgb.text(
        #         "- Shale reservoir characterization\n"
        #         "- Hydraulic fracturing design and best practices\n"
        #         "- Horizontal drilling and completion technologies\n",
        #         mode="md",
        #     )

        # with tgb.part(class_name="card"):
        #     tgb.text("### 🏛️ Regulatory & Policy", mode="md")
        #     tgb.text(
        #         "- National and provincial hydrocarbon regulations\n"
        #         "- Environmental impact assessment frameworks\n"
        #         "- Local content and investment promotion policies\n",
        #         mode="md",
        #     )

        # with tgb.part(class_name="card"):
        #     tgb.text("### 🌍 Environment & Communities", mode="md")
        #     tgb.text(
        #         "- Water use and management in hydraulic fracturing\n"
        #         "- Induced seismicity and subsurface risks\n"
        #         "- Socio-economic impacts on local communities (e.g., Añelo)\n",
        #         mode="md",
        #     )


# About Page
with tgb.Page() as about_page:
    sidebar()
    with tgb.part(class_name="main-content"):
        tgb.text("# ℹ️ About this Dashboard", mode="md")

        with tgb.part(class_name="card"):
            tgb.text("### 🎯 Purpose", mode="md")
            tgb.text(
                "This dashboard provides an integrated view of drilling, completion, and production data "
                "for the Vaca Muerta shale play. It is designed to help engineers, geoscientists, and "
                "decision-makers quickly explore well performance, frac designs, and spatial patterns.",
                mode="md",
            )

        with tgb.part(class_name="card"):
            tgb.text("### 🗂️ Data Sources", mode="md")
            tgb.text(
                "- **Production data (`prod`)**: Monthly oil, gas, water, and cumulative volumes by well.\n"
                "- **Frac data (`frac`)**: Treatment parameters such as lateral length, stages, proppant and fluid volumes.\n"
                "- **Spatial data**: Well coordinates (`Xcoor`, `Ycoor`) for mapping and spatial analysis.\n",
                mode="md",
            )

        with tgb.part(class_name="card"):
            tgb.text("### 🧮 Key Assumptions", mode="md")
            tgb.text(
                "- Cumulative volumes in the production table are assumed to be **up to the record date**.\n"
                "- Frac cumulative volumes are treated as **final totals** for the treatment.\n"
                "- Map bubble sizes are scaled using the 95th percentile to avoid a few outliers dominating the view.\n",
                mode="md",
            )

        with tgb.part(class_name="card"):
            tgb.text("### ⚠️ Limitations & Notes", mode="md")
            tgb.text(
                "- The dashboard is exploratory and should not replace detailed engineering studies.\n"
                "- Data quality, missing values, and reporting delays can affect interpretations.\n"
                "- Always cross-check with official datasets and internal technical analyses.\n",
                mode="md",
            )

        tgb.text(
            "_Maintainer: Pablo Conte",
            mode="md",
        )
        tgb.text(
            "Information is updated monthly",
            mode="md",
        )


# ------------------------------------------------------------------
# APP ENTRYPOINT
# ------------------------------------------------------------------
if __name__ == "__main__":
    pages = {
        "/": overview_page,
        "geology": geology_page,
        "drilling": drilling_page,
        "frac": frac_page,
        "production": production_page,
        "map": map_page,
        "wells": wells_page,
        "data": data_page,
        "links": links_page,
        "about": about_page,
    }
    port = int(os.getenv("PORT", "5000"))  # for Render / Vercel / etc.
    gui = Gui(pages=pages, css_file="css/styles.css")
    gui.run(
        title="Vaca Muerta Dashboard",
        dark_mode=False,
        host="0.0.0.0",
        port=port,
        use_reloader=False,
        debug=False,
    )
