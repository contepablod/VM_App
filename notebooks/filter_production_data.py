# Filter production data to only include wells that are in the filtered fracturing data

# Get the list of well IDs from filtered fracturing data
well_ids_in_frac = filtered_data_frac['well_id'].unique()

# Filter production data to only include wells that are in the fracturing data
filtered_data_prod = data_prod[data_prod['idpozo'].isin(well_ids_in_frac)]

print(f"Original production data: {len(data_prod)} rows")
print(f"Filtered production data: {len(filtered_data_prod)} rows")
print(f"Number of unique wells in frac data: {len(well_ids_in_frac)}")
print(f"Number of unique wells in filtered prod data: {filtered_data_prod['idpozo'].nunique()}")