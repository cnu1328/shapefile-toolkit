"""
Tool for filtering shapefile features by attribute rules and downloading the result.
"""

import os
import streamlit as st
import pandas as pd
import geopandas as gpd
from typing import List, Tuple, Optional

from core.base_tool import BaseTool
from core.utils_io import get_gdf_from_upload, create_temp_directory, create_shapefile_zip


FILTER_OPERATORS = [
    "equals",
    "not equals",
    "contains",
    "does not contain",
    "starts with",
    "ends with",
    "greater than",
    "less than",
    "greater or equal",
    "less or equal",
    "is empty",
    "is not empty",
]


def _series_is_empty(s: pd.Series) -> pd.Series:
    str_s = s.astype(str)
    return s.isna() | str_s.str.strip().eq("") | str_s.str.lower().isin(("nan", "none", "<na>"))


def _mask_for_filter(gdf: gpd.GeoDataFrame, column: str, operator: str, value: str) -> pd.Series:
    if column not in gdf.columns or column == "geometry":
        return pd.Series(False, index=gdf.index)

    s = gdf[column]
    value = (value or "").strip()

    if operator == "is empty":
        return _series_is_empty(s)
    if operator == "is not empty":
        return ~_series_is_empty(s)

    if operator == "contains":
        return s.astype(str).str.contains(value, case=False, na=False, regex=False)
    if operator == "does not contain":
        return ~s.astype(str).str.contains(value, case=False, na=False, regex=False)
    if operator == "starts with":
        return s.astype(str).str.lower().str.startswith(value.lower(), na=False)
    if operator == "ends with":
        return s.astype(str).str.lower().str.endswith(value.lower(), na=False)

    if operator in ("greater than", "less than", "greater or equal", "less or equal"):
        sn = pd.to_numeric(s, errors="coerce")
        vn = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
        if pd.isna(vn):
            return pd.Series(False, index=gdf.index)
        if operator == "greater than":
            return sn > vn
        if operator == "less than":
            return sn < vn
        if operator == "greater or equal":
            return sn >= vn
        return sn <= vn

    if operator in ("equals", "not equals"):
        val_stripped = value.strip()
        if val_stripped == "":
            if operator == "equals":
                return _series_is_empty(s)
            return ~_series_is_empty(s)

        sn = pd.to_numeric(s, errors="coerce")
        vn = pd.to_numeric(pd.Series([val_stripped]), errors="coerce").iloc[0]
        if pd.notna(vn):
            num_match = sn == vn
            str_match = s.astype(str).str.strip() == val_stripped
            m = num_match | (sn.isna() & str_match)
        else:
            m = s.astype(str).str.strip().str.casefold() == val_stripped.casefold()

        if operator == "equals":
            return m
        return ~m

    return pd.Series(True, index=gdf.index)


def apply_filters(
    gdf: gpd.GeoDataFrame, rules: List[Tuple[str, str, str]]
) -> Tuple[gpd.GeoDataFrame, str]:
    mask = pd.Series(True, index=gdf.index)
    for column, operator, value in rules:
        if not column:
            continue
        mask &= _mask_for_filter(gdf, column, operator, value)

    filtered = gdf.loc[mask].copy()
    msg = f"{len(filtered)} of {len(gdf)} features match all filters."
    return filtered, msg


class FilterShapefileTool(BaseTool):
    """
    Upload a shapefile ZIP, define N attribute filters (AND), download filtered polygons/lines/points as a new ZIP.
    """

    @property
    def name(self) -> str:
        return "Filter shapefile"

    @property
    def description(self) -> str:
        return (
            "Upload a shapefile ZIP, add multiple attribute filters, and download only the matching features."
        )

    @property
    def icon(self) -> str:
        return "🔎"

    def render_ui(self) -> None:
        st.header(f"{self.icon} {self.name}")
        st.markdown(self.description)
        st.divider()

        ss = st.session_state
        if "filter_tool_gdf" not in ss:
            ss.filter_tool_gdf = None
            ss.filter_tool_filename = None
            ss.filter_tool_attr_columns = []
            ss.filter_tool_filtered = None
            ss.filter_tool_filter_msg = ""

        st.subheader("📁 Step 1: Upload shapefile (ZIP)")
        uploaded = st.file_uploader(
            "ZIP must contain a single shapefile (.shp, .shx, .dbf, and optional .prj)",
            type=["zip"],
            key="filter_shapefile_upload",
        )

        if uploaded is None:
            ss.filter_tool_gdf = None
            ss.filter_tool_filename = None
            ss.filter_tool_filtered = None
            ss.filter_tool_filter_msg = ""
            st.info("Upload a shapefile ZIP to begin.")
            return

        if ss.filter_tool_filename != uploaded.name:
            with st.spinner("Loading shapefile…"):
                with create_temp_directory() as temp_dir:
                    gdf, message = get_gdf_from_upload(uploaded, temp_dir)
                    if gdf is None:
                        st.error(message)
                        ss.filter_tool_gdf = None
                        ss.filter_tool_filename = None
                        ss.filter_tool_filtered = None
                        ss.filter_tool_filter_msg = ""
                        return

                    ss.filter_tool_gdf = gdf
                    ss.filter_tool_filename = uploaded.name
                    ss.filter_tool_attr_columns = [c for c in gdf.columns if c != "geometry"]
                    ss.filter_tool_filtered = None
                    ss.filter_tool_filter_msg = ""
                    st.success(message)

        gdf: Optional[gpd.GeoDataFrame] = ss.filter_tool_gdf
        if gdf is None:
            return

        attr_cols: List[str] = ss.filter_tool_attr_columns
        if not attr_cols:
            st.warning("This layer has no attribute columns to filter on.")
            return

        st.subheader("🧩 Step 2: Build filters (all must match)")
        n_filters = st.number_input(
            "Number of filters",
            min_value=1,
            max_value=25,
            value=1,
            step=1,
            help="Each row is one condition; features must satisfy every condition.",
            key="filter_shapefile_n",
        )

        rules: List[Tuple[str, str, str]] = []
        for i in range(int(n_filters)):
            c1, c2, c3 = st.columns([2, 2, 2])
            with c1:
                col = st.selectbox(
                    "Column",
                    options=attr_cols,
                    key=f"filter_shapefile_col_{i}",
                )
            with c2:
                op = st.selectbox(
                    "Operator",
                    options=FILTER_OPERATORS,
                    key=f"filter_shapefile_op_{i}",
                )
            with c3:
                needs_value = op not in ("is empty", "is not empty")
                val = st.text_input(
                    "Value",
                    key=f"filter_shapefile_val_{i}",
                    disabled=not needs_value,
                    help='Not used for "is empty" / "is not empty".',
                )
            rules.append((col, op, val if needs_value else ""))

        apply = st.button("Apply filters", type="primary", use_container_width=True)
        if apply:
            filtered, msg = apply_filters(gdf, rules)
            ss.filter_tool_filtered = filtered
            ss.filter_tool_filter_msg = msg

        if ss.filter_tool_filtered is not None:
            st.success(ss.filter_tool_filter_msg)
            preview_cols = [c for c in attr_cols if c in ss.filter_tool_filtered.columns][:12]
            if preview_cols:
                st.dataframe(
                    ss.filter_tool_filtered[preview_cols].head(50),
                    use_container_width=True,
                )
                st.caption("Preview up to 50 rows (subset of columns).")

        st.subheader("⬇️ Step 3: Download filtered features")
        if ss.filter_tool_filtered is None:
            st.info('Click "Apply filters" to preview results, then download the shapefile ZIP.')
            return

        filt = ss.filter_tool_filtered
        if len(filt) == 0:
            st.warning("No features match the current filters. Adjust filters and apply again.")
            return

        base = os.path.splitext(ss.filter_tool_filename or "filtered")[0] + "_filtered"

        with create_temp_directory() as out_dir:
            zip_path = create_shapefile_zip(filt, "filtered_output", out_dir)
            with open(zip_path, "rb") as f:
                data = f.read()

        st.download_button(
            label="Download filtered shapefile (ZIP)",
            data=data,
            file_name=f"{base}.zip",
            mime="application/zip",
            use_container_width=True,
        )
