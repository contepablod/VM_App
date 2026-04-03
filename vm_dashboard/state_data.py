import os
from datetime import datetime
from pathlib import Path
from threading import Lock

import pandas as pd


def _env_int(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _build_lov(series):
    values = sorted(
        str(value).strip()
        for value in series.dropna().unique().tolist()
        if str(value).strip()
    )
    return ["All"] + values


def _build_well_lov(series):
    return sorted(
        str(value).strip()
        for value in series.dropna().unique().tolist()
        if str(value).strip()
    )


def _format_ts(timestamp_ns):
    return datetime.fromtimestamp(timestamp_ns / 1_000_000_000).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


_MAX_MTIME_SPREAD_NS = 5_000_000_000  # 5 seconds in nanoseconds


def _source_signature():
    signature = []
    for raw_path in DATA_SOURCE_PATHS:
        path = Path(raw_path)
        signature.append((raw_path, path.stat().st_mtime_ns))
    return tuple(signature)


def _source_files_consistent(signature):
    """Return True if all CSV mtimes are within a tight window.

    If the spread exceeds the threshold, a partial refresh is likely
    in progress and loading would mix old and new datasets.
    """
    mtimes = [mtime for _, mtime in signature]
    return (max(mtimes) - min(mtimes)) <= _MAX_MTIME_SPREAD_NS


def _read_prod_df(path):
    prod_df = pd.read_csv(path)
    prod_df["date"] = pd.to_datetime(
        {"year": prod_df["year"], "month": prod_df["month"], "day": 1},
        errors="coerce",
    ) + pd.offsets.MonthEnd(0)
    return prod_df


def _load_dataframes():
    frac_df = pd.read_csv(DATA_PATH_FRAC)
    prod_df = _read_prod_df(DATA_PATH_PROD)
    drill_df = pd.read_csv(DATA_PATH_DRILL)
    comp_df = pd.read_csv(DATA_PATH_COMP)
    return frac_df, prod_df, drill_df, comp_df


def _year_bounds(prod_df):
    if prod_df.empty:
        return 0, 0
    return int(prod_df["year"].min()), int(prod_df["year"].max())


def _set_runtime_status(signature, prod_df, frac_df, drill_df, comp_df):
    latest_source_mtime = max(mtime for _, mtime in signature)
    return (
        "CSV data ready | "
        f"prod {len(prod_df):,} | "
        f"frac {len(frac_df):,} | "
        f"drill {len(drill_df):,} | "
        f"completion {len(comp_df):,} | "
        f"source mtime {_format_ts(latest_source_mtime)}"
    )


def _apply_loaded_data(frac_df, prod_df, drill_df, comp_df, signature):
    global frac
    global prod
    global drill
    global comp
    global company_lov
    global field_lov
    global well_type_lov
    global well_lov
    global year_min
    global year_max
    global year_range
    global filtered_prod
    global filtered_frac
    global filtered_drill
    global filtered_comp
    global filtered_frac_sample
    global filtered_prod_view
    global filtered_frac_view
    global data_runtime_status
    global _loaded_source_signature

    frac = frac_df
    prod = prod_df
    drill = drill_df
    comp = comp_df

    company_lov = _build_lov(frac["company"])
    field_lov = _build_lov(frac["field"])
    well_type_lov = _build_lov(prod["well_type"])
    well_lov = _build_well_lov(prod["well_name"])
    year_min, year_max = _year_bounds(prod)
    year_range = [year_min, year_max]

    filtered_prod = prod.copy()
    filtered_frac = frac.copy()
    filtered_drill = drill.copy()
    filtered_comp = comp.copy()

    filtered_frac_sample = frac.copy()
    filtered_prod_view = filtered_prod.head(MAX_TABLE_ROWS)
    filtered_frac_view = filtered_frac.head(MAX_TABLE_ROWS)

    data_runtime_status = _set_runtime_status(signature, prod, frac, drill, comp)
    _loaded_source_signature = signature


def ensure_data_loaded(force=False):
    with _data_lock:
        signature = _source_signature()
        if not force and signature == _loaded_source_signature:
            return False
        if not force and not _source_files_consistent(signature):
            # CSV files have divergent mtimes — likely a partial refresh
            # in progress. Skip reload to avoid mixing old and new data.
            return False
        frac_df, prod_df, drill_df, comp_df = _load_dataframes()
        _apply_loaded_data(frac_df, prod_df, drill_df, comp_df, signature)
        return True


# ------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------
MAX_TABLE_ROWS = 2000
FRAC_SAMPLE_N = 5000
MAX_SQL_RESULT_ROWS = 120
MAX_SQL_TOOL_LOOPS = _env_int("VM_MAX_SQL_TOOL_LOOPS", 3)
MAX_AGENT_HISTORY = 12
OPENROUTER_TIMEOUT_SECONDS = _env_int("VM_OPENROUTER_TIMEOUT_SECONDS", 25)
OPENROUTER_MAX_TOKENS = _env_int("VM_OPENROUTER_MAX_TOKENS", 1024)
WEB_SEARCH_TIMEOUT_SECONDS = _env_int("VM_WEB_SEARCH_TIMEOUT_SECONDS", 12)
WEB_SEARCH_MAX_RESULTS = _env_int("VM_WEB_SEARCH_MAX_RESULTS", 5)

SQLITE_DB_PATH = "data/vm_analytics.db"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4.1-mini")
TAVILY_SEARCH_API_URL = os.getenv("TAVILY_SEARCH_API_URL", "https://api.tavily.com/search")

# Paths
DATA_PATH_FRAC = "data/well_frac_data.csv"
DATA_PATH_PROD = "data/well_prod_data.csv"
DATA_PATH_DRILL = "data/drill_data.csv"
DATA_PATH_COMP = "data/completion_data.csv"
DATA_SOURCE_PATHS = (
    DATA_PATH_PROD,
    DATA_PATH_FRAC,
    DATA_PATH_DRILL,
    DATA_PATH_COMP,
)
HEADER1_IMAGE_PATH = "images/vm_map.png"
HEADER2_IMAGE_PATH = "images/vm_rig_night.png"

# Data + runtime metadata
_data_lock = Lock()
_loaded_source_signature = ()
data_runtime_status = "CSV data not loaded"

frac = pd.DataFrame()
prod = pd.DataFrame()
drill = pd.DataFrame()
comp = pd.DataFrame()

# LOVs
company_lov = ["All"]
field_lov = ["All"]
well_type_lov = ["All"]
well_lov = []
year_min = 0
year_max = 0

# Filters
company_filter = "All"
field_filter = "All"
well_type_filter = "All"
year_range = [0, 0]

# Dataframes
filtered_prod = pd.DataFrame()
filtered_frac = pd.DataFrame()
filtered_drill = pd.DataFrame()
filtered_comp = pd.DataFrame()

# Speed helpers
filtered_frac_sample = pd.DataFrame()
filtered_prod_view = pd.DataFrame()
filtered_frac_view = pd.DataFrame()

# Derived dataframes
top_oil_wells_df = pd.DataFrame()
top_gas_wells_df = pd.DataFrame()
prod_time_df = pd.DataFrame()
map_df = pd.DataFrame()
wells_by_type_df = pd.DataFrame()
depth_by_type_df = pd.DataFrame()
avg_lateral_by_company_df = pd.DataFrame()

# Drilling/completion aggregated dataframes
drill_wells_by_year_df = pd.DataFrame()
drill_meters_by_year_df = pd.DataFrame()
drill_meters_by_company_df = pd.DataFrame()
comp_by_year_df = pd.DataFrame()
comp_by_company_df = pd.DataFrame()

# Wells selected
selected_prod_df = pd.DataFrame()
selected_frac_df = pd.DataFrame()

# KPIs - drilling
drilled_wells = 0
drilled_meters = 0.0
avg_depth = 0.0
avg_lateral = 0.0

# KPIs - frac
n_frac_wells = 0
avg_lateral_length = 0.0
avg_stages = 0.0
total_proppant = 0.0
total_fluid = 0.0
avg_proppant_intensity = 0.0
avg_fluid_intensity = 0.0

# KPIs - production
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
web_search_api_key_input = ""
chat_runtime_status = "Initializing..."
sql_cache_status = "SQLite not initialized"
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

ensure_data_loaded(force=True)
