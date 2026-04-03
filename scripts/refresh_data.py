#!/usr/bin/env python3
"""Download official datasets and rebuild app-ready CSV files.

Usage:
    uv run python scripts/refresh_data.py
    uv run python scripts/refresh_data.py --transform-only
    uv run python scripts/refresh_data.py --download-only
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import urllib.request
from pathlib import Path

import pandas as pd


PRODUCTION_URL = (
    "http://datos.energia.gob.ar/dataset/c846e79c-026c-4040-897f-1ad3543b407c/"
    "resource/b5b58cdc-9e07-41f9-b392-fb9ec68b0725/download/"
    "produccin-de-pozos-de-gas-y-petrleo-no-convencional.csv"
)
FRACTURE_URL = (
    "http://datos.energia.gob.ar/dataset/71fa2e84-0316-4a1b-af68-7f35e41f58d7/"
    "resource/2280ad92-6ed3-403e-a095-50139863ab0d/download/"
    "datos-de-fractura-de-pozos-de-hidrocarburos-adjunto-iv-actualizacin-diaria.csv"
)
DRILL_METERS_URL = (
    "http://datos.energia.gob.ar/dataset/7ea2ac77-d7a0-4129-9fbf-6f1a25d94e21/"
    "resource/712805f3-35d4-4825-93c6-98d03aeca203/download/metros-perforados.csv"
)
DRILL_WELLS_URL = (
    "http://datos.energia.gob.ar/dataset/7ea2ac77-d7a0-4129-9fbf-6f1a25d94e21/"
    "resource/af6838ef-f675-4409-ac6a-e7c391a5dbab/download/pozos-en-perforacin.csv"
)
COMPLETION_URL = (
    "http://datos.energia.gob.ar/dataset/7ea2ac77-d7a0-4129-9fbf-6f1a25d94e21/"
    "resource/a2ce14af-5c56-45c2-9b9c-c7a1e5156dff/download/pozos-terminados.csv"
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
RAW_PROD_PATH = DATA_DIR / Path(PRODUCTION_URL).name
RAW_FRAC_PATH = DATA_DIR / Path(FRACTURE_URL).name
RAW_DRILL_WELLS_PATH = DATA_DIR / Path(DRILL_WELLS_URL).name
RAW_DRILL_METERS_PATH = DATA_DIR / Path(DRILL_METERS_URL).name
RAW_COMPLETION_PATH = DATA_DIR / Path(COMPLETION_URL).name
OUT_PROD_PATH = DATA_DIR / "well_prod_data.csv"
OUT_FRAC_PATH = DATA_DIR / "well_frac_data.csv"
OUT_DRILL_PATH = DATA_DIR / "drill_data.csv"
OUT_COMPLETION_PATH = DATA_DIR / "completion_data.csv"


def _download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=destination.parent, prefix=destination.name + ".", suffix=".tmp", delete=False
    ) as tmp_f:
        tmp_path = Path(tmp_f.name)
    try:
        with urllib.request.urlopen(url, timeout=120) as response, tmp_path.open("wb") as out_f:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                out_f.write(chunk)
        tmp_path.replace(destination)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def _require_columns(df: pd.DataFrame, columns: list[str], dataset_name: str) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"{dataset_name} is missing required columns: {missing}")


def _build_frac_df(raw_frac: pd.DataFrame) -> pd.DataFrame:
    frac_columns = [
        "idpozo",
        "sigla",
        "cuenca",
        "yacimiento",
        "formacion_productiva",
        "tipo_reservorio",
        "subtipo_reservorio",
        "longitud_rama_horizontal_m",
        "cantidad_fracturas",
        "arena_bombeada_nacional_tn",
        "arena_bombeada_importada_tn",
        "agua_inyectada_m3",
        "presion_maxima_psi",
        "potencia_equipos_fractura_hp",
        "fecha_inicio_fractura",
        "fecha_fin_fractura",
        "empresa_informante",
        "mes",
        "anio",
    ]
    _require_columns(raw_frac, frac_columns, "fracture raw dataset")

    frac_df = raw_frac[frac_columns].copy()
    frac_df["proppant_pumped_lb"] = (
        frac_df["arena_bombeada_nacional_tn"] + frac_df["arena_bombeada_importada_tn"]
    ) * 2204.62
    frac_df["fluid_pumped_bbl"] = frac_df["agua_inyectada_m3"] * 6.289814
    frac_df["lateral_length_ft"] = frac_df["longitud_rama_horizontal_m"] * 3.281

    frac_df = frac_df.drop(
        columns=[
            "arena_bombeada_nacional_tn",
            "arena_bombeada_importada_tn",
            "agua_inyectada_m3",
            "longitud_rama_horizontal_m",
        ]
    )

    frac_df = frac_df.rename(
        columns={
            "idpozo": "well_id",
            "sigla": "well_name",
            "cuenca": "basin",
            "yacimiento": "field",
            "formacion_productiva": "formation",
            "tipo_reservorio": "reservoir_type",
            "subtipo_reservorio": "reservoir_subtype",
            "cantidad_fracturas": "number_stages",
            "presion_maxima_psi": "maximum_pressure_psi",
            "potencia_equipos_fractura_hp": "horse_power_hp",
            "empresa_informante": "company",
            "fecha_inicio_fractura": "frac_start_date",
            "fecha_fin_fractura": "frac_end_date",
            "mes": "month",
            "anio": "year",
        }
    )

    frac_order = [
        "well_id",
        "month",
        "year",
        "well_name",
        "company",
        "basin",
        "field",
        "formation",
        "reservoir_type",
        "reservoir_subtype",
        "frac_start_date",
        "frac_end_date",
        "lateral_length_ft",
        "number_stages",
        "proppant_pumped_lb",
        "fluid_pumped_bbl",
        "maximum_pressure_psi",
        "horse_power_hp",
    ]
    frac_df = frac_df[frac_order].copy()

    # Apply same filters used in the notebook pipeline.
    frac_df = frac_df.loc[
        (frac_df["formation"].astype(str).str.lower() == "vaca muerta")
        & (frac_df["lateral_length_ft"] > 0)
        & (frac_df["reservoir_type"] == "NO CONVENCIONAL")
        & (frac_df["reservoir_subtype"] == "SHALE")
        & (frac_df["number_stages"] > 0)
        & (frac_df["maximum_pressure_psi"] > 0)
        & (frac_df["horse_power_hp"] > 0)
        & (frac_df["proppant_pumped_lb"] > 0)
        & (frac_df["fluid_pumped_bbl"] > 0)
    ].copy()

    # Explicit wells dropped in original notebook cleanup.
    wells_to_drop = {160207, 160206, 160306, 160308, 160307, 161308, 162243, 162599, 162600}
    frac_df = frac_df[~frac_df["well_id"].isin(wells_to_drop)]

    frac_df = frac_df.drop(columns=["reservoir_type", "reservoir_subtype", "formation", "basin"])
    return frac_df


def _build_prod_df(raw_prod: pd.DataFrame, frac_df: pd.DataFrame) -> pd.DataFrame:
    prod_columns = [
        "idempresa",
        "anio",
        "mes",
        "idpozo",
        "prod_pet",
        "prod_gas",
        "prod_agua",
        "tipopozo",
        "fechaingreso",
        "empresa",
        "sigla",
        "profundidad",
        "formacion",
        "areayacimiento",
        "coordenadax",
        "coordenaday",
        "tipo_de_recurso",
        "sub_tipo_recurso",
        "fecha_data",
    ]
    _require_columns(raw_prod, prod_columns, "production raw dataset")

    prod_df = raw_prod[prod_columns].copy()
    prod_df = prod_df.rename(
        columns={
            "idempresa": "company_id",
            "anio": "year",
            "mes": "month",
            "idpozo": "well_id",
            "prod_pet": "oil_prod_m3",
            "prod_gas": "gas_prod_km3",
            "prod_agua": "water_prod_m3",
            "tipopozo": "well_type",
            "fechaingreso": "entry_date",
            "empresa": "company",
            "sigla": "well_name",
            "profundidad": "depth_m",
            "formacion": "formation",
            "areayacimiento": "field",
            "coordenadax": "Xcoor",
            "coordenaday": "Ycoor",
            "tipo_de_recurso": "type",
            "sub_tipo_recurso": "subtype",
            "fecha_data": "date_data",
        }
    )

    prod_df = prod_df.loc[
        (prod_df["formation"].astype(str).str.lower() == "vaca muerta")
        & (prod_df["well_type"].isin(["Petrol\u00edfero", "Gas\u00edfero", "Otro tipo"]))
        & (prod_df["type"] == "NO CONVENCIONAL")
        & (prod_df["subtype"] == "SHALE")
        & (prod_df["depth_m"] > 0)
    ].copy()

    prod_df = prod_df.sort_values(["well_id", "year", "month"]).copy()
    prod_df["month_count"] = prod_df.groupby("well_id").cumcount() + 1
    prod_df["oil_cum_m3"] = prod_df.groupby("well_id")["oil_prod_m3"].cumsum()
    prod_df["gas_cum_km3"] = prod_df.groupby("well_id")["gas_prod_km3"].cumsum()
    prod_df["water_prod_cum_m3"] = prod_df.groupby("well_id")["water_prod_m3"].cumsum()
    prod_df["depth"] = prod_df["depth_m"] * 3.281
    prod_df = prod_df.drop(columns=["formation"])

    frac_well_ids = set(frac_df["well_id"].dropna().unique().tolist())
    prod_df = prod_df[prod_df["well_id"].isin(frac_well_ids)].copy()

    mapper = {"Petrol\u00edfero": "Oil", "Gas\u00edfero": "Gas", "Otro tipo": "Other"}
    prod_df["well_type"] = prod_df["well_type"].map(mapper)
    prod_df = prod_df.drop(columns=["type", "subtype", "depth_m"])

    final_order = [
        "company_id",
        "year",
        "month",
        "well_id",
        "oil_prod_m3",
        "gas_prod_km3",
        "water_prod_m3",
        "well_type",
        "entry_date",
        "company",
        "well_name",
        "field",
        "Xcoor",
        "Ycoor",
        "date_data",
        "month_count",
        "oil_cum_m3",
        "gas_cum_km3",
        "water_prod_cum_m3",
        "depth",
    ]
    return prod_df[final_order].copy()


def _build_drill_df(
    raw_drill_wells: pd.DataFrame,
    raw_drill_meters: pd.DataFrame,
    fields: set[str],
    companies: set[str],
) -> pd.DataFrame:
    required_columns = [
        "indice_tiempo",
        "anio",
        "mes",
        "idempresa",
        "empresa",
        "idareapermisoconcesion",
        "areapermisoconcesion",
        "idareayacimiento",
        "areayacimiento",
        "idcuenca",
        "cuenca",
        "idprovincia",
        "provincia",
        "idubicacion",
        "ubicacion",
        "idconcepto",
        "concepto",
        "cantidad",
        "observaciones",
        "fecha_data",
    ]
    _require_columns(raw_drill_wells, required_columns, "drilling wells raw dataset")
    _require_columns(raw_drill_meters, required_columns, "drilling meters raw dataset")

    df_wells = raw_drill_wells.rename(columns={"cantidad": "cantidad_wells"})
    df_meters = raw_drill_meters.rename(columns={"cantidad": "cantidad_meters"})

    merge_keys = [
        "indice_tiempo",
        "anio",
        "mes",
        "idempresa",
        "empresa",
        "idareapermisoconcesion",
        "areapermisoconcesion",
        "idareayacimiento",
        "areayacimiento",
        "idcuenca",
        "cuenca",
        "idprovincia",
        "provincia",
        "idubicacion",
        "ubicacion",
        "idconcepto",
        "concepto",
        "observaciones",
        "fecha_data",
    ]
    drill_df = df_wells.merge(df_meters, on=merge_keys, how="inner")
    drill_df = drill_df[
        drill_df["areayacimiento"].isin(fields) & drill_df["empresa"].isin(companies)
    ].copy()

    drill_order = [
        "anio",
        "mes",
        "empresa",
        "areayacimiento",
        "cuenca",
        "ubicacion",
        "concepto",
        "cantidad_wells",
        "cantidad_meters",
        "fecha_data",
    ]
    drill_df = drill_df[drill_order].copy()
    drill_df = drill_df.rename(
        columns={
            "anio": "year",
            "mes": "month",
            "empresa": "company",
            "areayacimiento": "field",
            "cuenca": "basin",
            "ubicacion": "location",
            "concepto": "concept",
            "cantidad_wells": "wells",
            "cantidad_meters": "meters",
            "fecha_data": "date_data",
        }
    )

    drill_df = drill_df[
        drill_df["concept"].isin(["Exploraci\u00f3n", "Avanzada", "Explotaci\u00f3n"])
    ].copy()
    return drill_df


def _build_completion_df(
    raw_completion: pd.DataFrame,
    fields: set[str],
    companies: set[str],
) -> pd.DataFrame:
    required_columns = [
        "anio",
        "mes",
        "empresa",
        "areayacimiento",
        "cuenca",
        "ubicacion",
        "concepto",
        "cantidad",
        "fecha_data",
    ]
    _require_columns(raw_completion, required_columns, "completion raw dataset")

    completion_df = raw_completion[required_columns].copy()
    completion_df = completion_df[
        completion_df["areayacimiento"].isin(fields)
        & completion_df["empresa"].isin(companies)
    ].copy()
    completion_df = completion_df.rename(
        columns={
            "anio": "year",
            "mes": "month",
            "empresa": "company",
            "areayacimiento": "field",
            "cuenca": "basin",
            "ubicacion": "location",
            "concepto": "concept",
            "cantidad": "completion",
            "fecha_data": "date_data",
        }
    )
    return completion_df


def _load_raw_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if not RAW_PROD_PATH.exists():
        raise FileNotFoundError(f"Missing raw production file: {RAW_PROD_PATH}")
    if not RAW_FRAC_PATH.exists():
        raise FileNotFoundError(f"Missing raw fracture file: {RAW_FRAC_PATH}")
    if not RAW_DRILL_WELLS_PATH.exists():
        raise FileNotFoundError(f"Missing raw drilling wells file: {RAW_DRILL_WELLS_PATH}")
    if not RAW_DRILL_METERS_PATH.exists():
        raise FileNotFoundError(f"Missing raw drilling meters file: {RAW_DRILL_METERS_PATH}")
    if not RAW_COMPLETION_PATH.exists():
        raise FileNotFoundError(f"Missing raw completion file: {RAW_COMPLETION_PATH}")

    raw_prod = pd.read_csv(RAW_PROD_PATH, low_memory=False)
    raw_frac = pd.read_csv(RAW_FRAC_PATH, low_memory=False)
    raw_drill_wells = pd.read_csv(RAW_DRILL_WELLS_PATH, low_memory=False)
    raw_drill_meters = pd.read_csv(RAW_DRILL_METERS_PATH, low_memory=False)
    raw_completion = pd.read_csv(RAW_COMPLETION_PATH, low_memory=False)
    return raw_prod, raw_frac, raw_drill_wells, raw_drill_meters, raw_completion


def _atomic_write_csv(df: pd.DataFrame, dest: Path) -> None:
    """Write a CSV to a temp file, then atomically rename into place."""
    with tempfile.NamedTemporaryFile(
        dir=dest.parent, prefix=dest.name + ".", suffix=".tmp", delete=False, mode="w"
    ) as tmp_f:
        tmp_path = Path(tmp_f.name)
    try:
        df.to_csv(tmp_path, index=False)
        tmp_path.replace(dest)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


def _write_outputs(
    prod_df: pd.DataFrame,
    frac_df: pd.DataFrame,
    drill_df: pd.DataFrame,
    completion_df: pd.DataFrame,
) -> None:
    OUT_PROD_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Write all to temp files first, then rename all at once to minimize
    # the window where the app could see a mix of old and new files.
    pairs = [
        (prod_df, OUT_PROD_PATH),
        (frac_df, OUT_FRAC_PATH),
        (drill_df, OUT_DRILL_PATH),
        (completion_df, OUT_COMPLETION_PATH),
    ]
    tmp_paths = []
    try:
        for df, dest in pairs:
            tmp = dest.with_suffix(".csv.tmp")
            df.to_csv(tmp, index=False)
            tmp_paths.append((tmp, dest))
        # All writes succeeded — rename all at once.
        for tmp, dest in tmp_paths:
            tmp.replace(dest)
    except BaseException:
        for tmp, _ in tmp_paths:
            tmp.unlink(missing_ok=True)
        raise


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh dashboard datasets from raw files.")
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="Only download raw files from the endpoints.",
    )
    parser.add_argument(
        "--transform-only",
        action="store_true",
        help="Skip download and only rebuild app CSV files from local raw files.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.download_only and args.transform_only:
        raise ValueError("Use either --download-only or --transform-only, not both.")

    if not args.transform_only:
        print(f"Downloading production dataset -> {RAW_PROD_PATH}")
        _download_file(PRODUCTION_URL, RAW_PROD_PATH)
        print(f"Downloading fracture dataset -> {RAW_FRAC_PATH}")
        _download_file(FRACTURE_URL, RAW_FRAC_PATH)
        print(f"Downloading drilling meters dataset -> {RAW_DRILL_METERS_PATH}")
        _download_file(DRILL_METERS_URL, RAW_DRILL_METERS_PATH)
        print(f"Downloading drilling wells dataset -> {RAW_DRILL_WELLS_PATH}")
        _download_file(DRILL_WELLS_URL, RAW_DRILL_WELLS_PATH)
        print(f"Downloading completion dataset -> {RAW_COMPLETION_PATH}")
        _download_file(COMPLETION_URL, RAW_COMPLETION_PATH)
        print("Download complete.")

    if args.download_only:
        return 0

    print("Building app datasets...")
    (
        raw_prod,
        raw_frac,
        raw_drill_wells,
        raw_drill_meters,
        raw_completion,
    ) = _load_raw_inputs()
    frac_df = _build_frac_df(raw_frac)
    prod_df = _build_prod_df(raw_prod, frac_df)
    fields = set(frac_df["field"].dropna().unique().tolist())
    companies = set(frac_df["company"].dropna().unique().tolist())
    drill_df = _build_drill_df(raw_drill_wells, raw_drill_meters, fields, companies)
    completion_df = _build_completion_df(raw_completion, fields, companies)
    _write_outputs(prod_df, frac_df, drill_df, completion_df)

    print(f"Wrote {OUT_FRAC_PATH} ({len(frac_df):,} rows)")
    print(f"Wrote {OUT_PROD_PATH} ({len(prod_df):,} rows)")
    print(f"Wrote {OUT_DRILL_PATH} ({len(drill_df):,} rows)")
    print(f"Wrote {OUT_COMPLETION_PATH} ({len(completion_df):,} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
