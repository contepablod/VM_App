import os

import pandas as pd

def _env_int(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


# ------------------------------------------------------------------
# CONFIG & DATA
# ------------------------------------------------------------------
MAX_TABLE_ROWS = 2000
FRAC_SAMPLE_N = 5000
MAX_SQL_RESULT_ROWS = 120
MAX_SQL_TOOL_LOOPS = _env_int("VM_MAX_SQL_TOOL_LOOPS", 3)
MAX_AGENT_HISTORY = 12
OPENROUTER_TIMEOUT_SECONDS = _env_int("VM_OPENROUTER_TIMEOUT_SECONDS", 25)
OPENROUTER_MAX_TOKENS = _env_int("VM_OPENROUTER_MAX_TOKENS", 1024)

SQLITE_DB_PATH = "data/vm_analytics.db"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4.1-mini")

# Paths
DATA_PATH_FRAC = "data/well_frac_data.csv"
DATA_PATH_PROD = "data/well_prod_data.csv"
DATA_PATH_DRILL = "data/drill_data.csv"
DATA_PATH_COMP = "data/completion_data.csv"
HEADER1_IMAGE_PATH = "images/vm_map.png"
HEADER2_IMAGE_PATH = "images/vm_rig_night.png"

# CSV's
frac = pd.read_csv(DATA_PATH_FRAC)
prod = pd.read_csv(DATA_PATH_PROD)
drill = pd.read_csv(DATA_PATH_DRILL)
comp = pd.read_csv(DATA_PATH_COMP)

# Build a valid month-end date from year/month for every record.
prod["date"] = pd.to_datetime(
    {"year": prod["year"], "month": prod["month"], "day": 1}, errors="coerce"
) + pd.offsets.MonthEnd(0)

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

# Chat / SQL Copilot
CHAT_WELCOME_TEXT = "Hi! I am your assistant. How can I help you today?"
chat_users = {"assistant": "SQL Copilot", "user": "You"}
chat_sender_id = "user"
chat_messages = [["m0", CHAT_WELCOME_TEXT, "assistant"]]
sql_agent_history = []
openrouter_model = OPENROUTER_DEFAULT_MODEL
openrouter_api_key_input = ""
openrouter_key_status = "Missing"
chat_runtime_status = "Initializing..."
sql_last_query = ""
sql_last_result = pd.DataFrame()
chat_busy = False
chat_input_active = True

# Navigation state
active_page = "overview"
nav_overview = "nav-button active"
nav_drilling = nav_production = nav_frac = nav_map = nav_wells = nav_data = (
    nav_links
) = nav_geology = nav_chat = nav_about = "nav-button"
