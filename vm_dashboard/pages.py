import taipy.gui.builder as tgb

from .downloads import download_filtered_frac, download_filtered_prod
from .sql_chat import clear_chat, on_chat_action, on_chat_settings_change
from .state_data import (
    HEADER1_IMAGE_PATH,
    HEADER2_IMAGE_PATH,
    chat_users,
    company_lov,
    field_lov,
    prod,
    well_type_lov,
    year_max,
    year_min,
)
from .state_handlers import on_change, sidebar


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
                mode="lines+markers",
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

# Chat Page
with tgb.Page() as chat_page:
    sidebar()
    with tgb.part(class_name="main-content"):
        tgb.text("# 🤖 Chat", mode="md")

        with tgb.part(class_name="card"):
            tgb.text(
                "**Runtime:** {chat_runtime_status}\n\n"
                "**Model:** `{openrouter_model}`\n\n"
                "**Note:** API key is kept in session memory only.\n\n"
                "This assistant uses OpenRouter tool-calling with read-only SQL over local tables: "
                "`prod`, `frac`, `drill`, `completion` and optional web search (Tavily).",
                mode="md",
            )
            with tgb.layout(columns="2 2 2 1"):
                tgb.input(
                    value="{openrouter_model}",
                    label="OpenRouter model",
                    on_change=on_chat_settings_change,
                )
                tgb.input(
                    value="{openrouter_api_key_input}",
                    label="OpenRouter API Key",
                    password=True,
                    on_change=on_chat_settings_change,
                )
                tgb.input(
                    value="{web_search_api_key_input}",
                    label="Tavily API Key (optional)",
                    password=True,
                    on_change=on_chat_settings_change,
                )
                tgb.button("Clear Chat", on_action=clear_chat)

        with tgb.part(class_name="card"):
            tgb.chat(
                messages="{chat_messages}",
                users=chat_users,
                sender_id="user",
                on_action=on_chat_action,
                show_sender=True,
                mode="md",
                height="560px",
                active="{chat_input_active}",
            )

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



PAGES = {
    "/": overview_page,
    "geology": geology_page,
    "drilling": drilling_page,
    "frac": frac_page,
    "production": production_page,
    "map": map_page,
    "wells": wells_page,
    "data": data_page,
    "chat": chat_page,
    "links": links_page,
    "about": about_page,
}
