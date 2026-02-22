from taipy.gui.gui_actions import download


def download_filtered_prod(state):
    csv_content = state.filtered_prod.to_csv(index=False).encode("utf-8")
    return download(state, csv_content, name="filtered_prod_data.csv")


def download_filtered_frac(state):
    csv_content = state.filtered_frac.to_csv(index=False).encode("utf-8")
    return download(state, csv_content, name="filtered_frac_data.csv")
