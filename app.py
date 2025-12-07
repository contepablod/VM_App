import os
import pandas as pd
import taipy.gui.builder as tgb
from taipy.gui import Gui
from taipy.gui.gui_actions import download, navigate


# ------------------------------------------------------------------
# CONFIG & DATA
# ------------------------------------------------------------------
def download_filtered(state):
    return download(state.filtered_prod, "filtered_data.csv")


DATA_PATH = "data/well_frac_prod_data_VM.csv"
DATA_PATH_PROD = "data/well_prod_data.csv"
HEADER1_IMAGE_PATH = "images/vm_map.png"
HEADER2_IMAGE_PATH = "images/vm_rig_night.png"

frac = pd.read_csv(DATA_PATH)
prod = pd.read_csv(DATA_PATH_PROD)

prod["date"] = pd.to_datetime(
    pd.DataFrame({"year": prod["year"], "month": prod["month"], "day": 1}),
    errors="coerce",
)

company_lov = ["All"] + sorted(frac["company"].dropna().unique())
field_lov = ["All"] + sorted(frac["field"].dropna().unique())
well_type_lov = ["All"] + sorted(prod["well_type"].dropna().unique())

year_min = int(prod["year"].min())
year_max = int(prod["year"].max())

# Filters (global defaults copied into state)
company_filter = "All"
field_filter = "All"
well_type_filter = "All"
year_range = [year_min, year_max]

# Dataframes (placeholders for state)
filtered_prod = prod.copy()
filtered_frac = frac.copy()
top_oil_wells_df = pd.DataFrame()
top_gas_wells_df = pd.DataFrame()
prod_time_df = pd.DataFrame()
map_df = pd.DataFrame()
wells_by_type_df = pd.DataFrame()
depth_by_type_df = pd.DataFrame()

# KPIs – production
n_wells = 0
total_oil = 0.0
total_gas = 0.0
total_water = 0.0

# KPIs – frac
n_frac_wells = 0
avg_lateral_length = 0.0
avg_stages = 0.0
total_proppant_klb = 0.0
total_fluid_kbbl = 0.0
avg_proppant_intensity = 0.0  # lb/ft
avg_fluid_intensity = 0.0  # bbl/ft

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
active_page = "/"
nav_overview = "nav-button active"
nav_production = nav_frac = nav_map = nav_wells = nav_data = nav_links = nav_geology = nav_about = "nav-button"


# ------------------------------------------------------------------
# STATE UPDATE (DATA & KPIs)
# ------------------------------------------------------------------
def update_state(state):
    # ---------- FILTER PRODUCTION DATA ----------
    d1 = prod.copy()

    # company filter
    company_filter = state.company_filter
    if isinstance(company_filter, list):
        if "All" not in company_filter:
            d1 = d1[d1["company"].isin(company_filter)]
    elif company_filter != "All":
        d1 = d1[d1["company"] == company_filter]

    # field filter
    field_filter = state.field_filter
    if isinstance(field_filter, list):
        if "All" not in field_filter:
            d1 = d1[d1["field"].isin(field_filter)]
    elif field_filter != "All":
        d1 = d1[d1["field"] == field_filter]

    # well type filter
    well_type_filter = state.well_type_filter
    if isinstance(well_type_filter, list):
        if "All" not in well_type_filter:
            d1 = d1[d1["well_type"].isin(well_type_filter)]
    elif well_type_filter != "All":
        d1 = d1[d1["well_type"] == well_type_filter]

    # year range
    d1 = d1[(d1["year"] >= state.year_range[0]) & (d1["year"] <= state.year_range[1])]
    state.filtered_prod = d1

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

    # well type filter (if present in frac dataset)
    if "well_type" in d2.columns:
        if isinstance(well_type_filter, list):
            if "All" not in well_type_filter:
                d2 = d2[d2["well_type"].isin(well_type_filter)]
        elif well_type_filter != "All":
            d2 = d2[d2["well_type"] == well_type_filter]

    d2 = d2[
        (d2["year_x"] >= state.year_range[0]) & (d2["year_x"] <= state.year_range[1])
    ]
    # ---- Add frac intensity metrics (lb/ft and bbl/ft) ----
    if not d2.empty:
        d2 = d2.copy()
        # avoid division by zero
        lateral = d2["lateral_length_ft"].replace(0, pd.NA)

        d2["proppant_intensity_lbft"] = d2["proppant_pumped_lb"] / lateral
        d2["fluid_intensity_bblft"] = d2["fluid_pumped_bbl"] / lateral

    state.filtered_frac = d2

    # ---------- LATEST RECORD PER WELL (for KPIs & map) ----------
    if not d1.empty:
        idx_latest = d1.groupby("well_id")["month_count"].idxmax()
        latest = d1.loc[idx_latest]
    else:
        latest = d1.head(0)

    # ---------- KPIs: production ----------
    state.n_wells = latest["well_id"].nunique()
    state.total_oil = round(latest["oil_cum_m3"].sum() / 1_000, 2)
    state.total_gas = round(latest["gas_cum_km3"].sum() / 1_000, 2)
    state.total_water = round(latest["water_prod_cum_m3"].sum() / 1_000, 2)

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

    # ---------- DEPTH BY WELL TYPE (for Geology page) ----------
    if not latest.empty:
        state.depth_by_type_df = (
            latest.groupby("well_type", as_index=False)["depth_m"]
            .mean()
            .rename(columns={"depth_m": "avg_depth_m"})
            .sort_values("avg_depth_m", ascending=False)
        )
    else:
        state.depth_by_type_df = latest.head(0)

    # ---------- TOP OIL WELLS ----------
    state.top_oil_wells_df = (
        latest[["well_name", "oil_cum_m3"]]
        .dropna()
        .groupby("well_name", as_index=False)["oil_cum_m3"]
        .max()
        .sort_values("oil_cum_m3", ascending=False)
        .head(20)
    )

    # ---------- TOP GAS WELLS ----------
    state.top_gas_wells_df = (
        latest[["well_name", "gas_cum_km3"]]
        .dropna()
        .groupby("well_name", as_index=False)["gas_cum_km3"]
        .max()
        .sort_values("gas_cum_km3", ascending=False)
        .head(20)
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
        latest = latest.copy()

        # basic stats (if you need them)
        state.max_oil = latest["oil_cum_m3"].max()
        state.max_gas = latest["gas_cum_km3"].max()

        # bubble sizes for OIL (95% quantile scaling)
        oil = latest["oil_cum_m3"].fillna(0)
        q95_oil = oil.quantile(0.95)
        if q95_oil <= 0:
            q95_oil = 1.0
        latest["oil_size"] = 4 + 36 * oil.clip(upper=q95_oil) / q95_oil

        # bubble sizes for GAS
        gas = latest["gas_cum_km3"].fillna(0)
        q95_gas = gas.quantile(0.95)
        if q95_gas <= 0:
            q95_gas = 1.0
        latest["gas_size"] = 4 + 36 * gas.clip(upper=q95_gas) / q95_gas

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
        map_latest = latest[metric_series >= cutoff].copy()

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
        state.total_proppant_klb = round(d2["proppant_pumped_lb"].sum() / 1_000, 2)
        state.total_fluid_kbbl = round(d2["fluid_pumped_bbl"].sum() / 1_000, 2)

        # intensity KPIs (drop NaNs before mean)
        if "proppant_intensity_lbft" in d2.columns:
            state.avg_proppant_intensity = round(
                d2["proppant_intensity_lbft"].dropna().mean(), 1
            )
        else:
            state.avg_proppant_intensity = 0.0

        if "fluid_intensity_bblft" in d2.columns:
            state.avg_fluid_intensity = round(
                d2["fluid_intensity_bblft"].dropna().mean(), 2
            )
        else:
            state.avg_fluid_intensity = 0.0

    else:
        state.n_frac_wells = 0
        state.avg_lateral_length = 0.0
        state.avg_stages = 0.0
        state.total_proppant_klb = 0.0
        state.total_fluid_kbbl = 0.0
        state.avg_proppant_intensity = 0.0
        state.avg_fluid_intensity = 0.0


# ------------------------------------------------------------------
# NAVIGATION STATE UPDATE
# ------------------------------------------------------------------
def update_nav(state):
    current = getattr(state, "active_page", "/")

    state.nav_overview = "nav-button active" if current == "/" else "nav-button"
    state.nav_production = (
        "nav-button active" if current == "production" else "nav-button"
    )
    state.nav_frac = "nav-button active" if current == "frac" else "nav-button"
    state.nav_map = "nav-button active" if current == "map" else "nav-button"
    state.nav_wells = "nav-button active" if current == "wells" else "nav-button"
    state.nav_data = "nav-button active" if current == "data" else "nav-button"
    state.nav_links = "nav-button active" if current == "links" else "nav-button"
    state.nav_about = "nav-button active" if current == "about" else "nav-button"
    state.nav_geology = "nav-button active" if current == "geology" else "nav-button"


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


def go_geology(state):
    state.active_page = "geology"
    update_nav(state)
    navigate(state, to="geology")


def sidebar():
    with tgb.part(class_name="sidebar"):
        tgb.text("## 📘 Navigation", mode="md")
        tgb.button("🏠 OVERVIEW", class_name="{nav_overview}", on_action=go_overview)
        tgb.button("🪨 GEOLOGY", class_name="{nav_geology}", on_action=go_geology)
        tgb.button(
            "📈 PRODUCTION", class_name="{nav_production}", on_action=go_production
        )
        tgb.button("💥 FRAC", class_name="{nav_frac}", on_action=go_frac)
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
        # --- Image + Description Side-by-Side ---
        with tgb.part(class_name="card"):
            with tgb.layout(columns="1 2"):
                with tgb.part():
                    tgb.image(HEADER1_IMAGE_PATH, width="100%", height="100%")
                # Right: Text card
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
                tgb.image("images/vm_rig_night.png", width="100%")

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
            with tgb.layout(columns="2 2"):
                with tgb.part():
                    tgb.text("### 📊 Production KPIs", mode="md")
                    tgb.text("**#️⃣ Number of wells:** {n_wells}", mode="md")
                    tgb.text("**🛢️ Total Oil (m³):** {total_oil}", mode="md")
                    tgb.text("**🔥 Total Gas (km³):** {total_gas}", mode="md")
                    tgb.text("**💧 Total Water (m³):** {total_water}", mode="md")

                with tgb.part():
                    tgb.text("### 💥 Frac KPIs", mode="md")
                    tgb.text("**🧵 Frac'd wells:** {n_frac_wells}", mode="md")
                    tgb.text("**📏 Avg lateral (ft):** {avg_lateral_length}", mode="md")
                    tgb.text("**🎯 Avg stages:** {avg_stages}", mode="md")
                    tgb.text("**🪨 Proppant (klb):** {total_proppant_klb}", mode="md")
                    tgb.text("**💧 Fluid (kbbl):** {total_fluid_kbbl}", mode="md")
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
                x="depth_m",
                height="350px",
                layout={
                    "xaxis": {"title": {"text": "Measured depth (m)"}},
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
                y="avg_depth_m",
                height="350px",
                layout={
                    "xaxis": {"title": {"text": "Well Type"}, "automargin": True},
                    "yaxis": {
                        "title": {"text": "Average depth (m)"},
                        "automargin": True,
                    },
                },
            )

        tgb.text(
            "_Note: depths are taken from the latest record per well after filtering by company, field, "
            "well type, and year range._",
            mode="md",
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

# Frac Page
with tgb.Page() as frac_page:
    sidebar()
    with tgb.part(class_name="main-content"):
        tgb.text("# 💥 Frac Diagnostics", mode="md")

        # ---- Intensity KPIs ----
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
        with tgb.part(class_name="card"):
            tgb.chart(
                type="scatter",
                data="{filtered_frac}",
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
                data="{filtered_frac}",
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

        tgb.text("### Stages vs Production", mode="md")
        with tgb.part(class_name="card"):
            tgb.chart(
                type="scatter",
                data="{filtered_frac}",
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

        # ---- Intensity vs Oil Production ----
        tgb.text("### Intensity vs Oil Response", mode="md")
        with tgb.layout(columns="1 1"):
            with tgb.part(class_name="card"):
                tgb.text("🪨 Proppant Intensity vs Cum Oil", mode="md")
                tgb.chart(
                    type="scatter",
                    data="{filtered_frac}",
                    x="proppant_intensity_lbft",
                    y="oil_cum_km3",
                    marker={"color": "orange", "opacity": 0.6},
                    mode="markers",
                    height="400px",
                    layout={
                        "xaxis": {"title": "Proppant Intensity (lb/ft)"},
                        "yaxis": {"title": "Cumulative Oil (m³)"},
                    },
                )

            with tgb.part(class_name="card"):
                tgb.text("💧 Fluid Intensity vs Cum Oil", mode="md")
                tgb.chart(
                    type="scatter",
                    data="{filtered_frac}",
                    x="fluid_intensity_bblft",
                    y="oil_cum_km3",
                    marker={"color": "deepskyblue", "opacity": 0.6},
                    mode="markers",
                    height="400px",
                    layout={
                        "xaxis": {"title": "Fluid Intensity (bbl/ft)"},
                        "yaxis": {"title": "Cumulative Oil (m³)"},
                    },
                )
        # ---- Intensity vs Gas Production ----
        tgb.text("### Intensity vs Gas Response", mode="md")
        with tgb.layout(columns="1 1"):
            with tgb.part(class_name="card"):
                tgb.text("🪨 Proppant Intensity vs Cum Gas", mode="md")
                tgb.chart(
                    type="scatter",
                    data="{filtered_frac}",
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
                    data="{filtered_frac}",
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

# Map Page
with tgb.Page() as map_page:
    sidebar()
    with tgb.part(class_name="main-content"):
        tgb.text("# 🗺️ Full Spatial Analysis", mode="md")

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
                data="{filtered_prod[filtered_prod['well_name']==selected_well]}",
                x="date",
                y=["oil_prod_m3", "gas_prod_km3", "water_prod_m3"],
                height="400px",
            )

        with tgb.part(class_name="card"):
            tgb.text("### Frac Treatment", mode="md")
            tgb.table(data="{filtered_frac[filtered_frac['well_name']==selected_well]}")

# Data Page
with tgb.Page() as data_page:
    sidebar()
    with tgb.part(class_name="main-content"):
        tgb.text("# 📄 Data Explorer", mode="md")

        tgb.text("### Production Table", mode="md")
        tgb.table(data="{filtered_prod}")

        tgb.text("### Frac Table", mode="md")
        tgb.table(data="{filtered_frac}")

        tgb.button("Download Production CSV", on_action=download_filtered)

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
        "production": production_page,
        "frac": frac_page,
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
        host="0.0.0.0",  # IMPORTANT in Docker
        port=port,
        use_reloader=False,
        debug=False,
    )
