import logging
import os

from taipy.gui import Gui

from vm_dashboard.downloads import (  # noqa: F401
    download_filtered_frac,
    download_filtered_prod,
)
from vm_dashboard.pages import PAGES
from vm_dashboard.sql_chat import (  # noqa: F401
    clear_chat,
    on_chat_action,
    on_chat_settings_change,
    rebuild_sql_cache,
)
from vm_dashboard.state_data import *  # noqa: F401,F403
from vm_dashboard.state_handlers import (  # noqa: F401
    go_about,
    go_chat,
    go_data,
    go_drilling,
    go_frac,
    go_geology,
    go_links,
    go_map,
    go_overview,
    go_production,
    go_wells,
    on_change,
    on_init,
)


if __name__ == "__main__":
    log_level_name = os.getenv("LOG_LEVEL", "WARNING").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    port = int(os.getenv("PORT", "5000"))
    gui = Gui(pages=PAGES, css_file="css/styles.css")
    gui.run(
        title="Vaca Muerta Dashboard",
        dark_mode=False,
        host="0.0.0.0",
        port=port,
        use_reloader=False,
        debug=False,
    )
