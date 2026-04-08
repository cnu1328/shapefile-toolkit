"""
TIFF Threshold Polygonizer Tool

Reads a GeoTIFF file, lets the user select one band and a lower threshold value,
then converts all pixels whose value is LESS THAN the threshold into vector polygons
clipped to an optional shapefile boundary. The result is exported as a downloadable
shapefile ZIP.

Anti-zigzag smoothing is applied in two stages:
  1. PRE-POLYGONIZE  – morphological closing/opening on the binary mask eliminates
                       the staircase pixel notches before vectorisation.
  2. POST-POLYGONIZE – Shapely simplify (Douglas-Peucker) removes collinear/nearly-
                       collinear vertices; a small outward-then-inward buffer rounds
                       the remaining corners into smooth curves.
"""

import os
import zipfile
import tempfile
import warnings

import numpy as np
import streamlit as st
import geopandas as gpd
from shapely.geometry import shape
from shapely.ops import unary_union

from core.base_tool import BaseTool
from core.utils_io import create_temp_directory, create_shapefile_zip, get_gdf_from_upload

# ── Optional heavy imports ────────────────────────────────────────────────────
try:
    import rasterio
    from rasterio.features import shapes as rasterio_shapes
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False

try:
    from scipy.ndimage import binary_closing, binary_opening
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


# ============================================================================
# Raster helpers
# ============================================================================

def _read_tiff_info(tiff_bytes: bytes) -> dict:
    """Read metadata from a GeoTIFF byte stream."""
    with rasterio.MemoryFile(tiff_bytes) as memfile:
        with memfile.open() as src:
            band_descriptions = []
            for i in range(1, src.count + 1):
                desc = src.descriptions[i - 1]
                band_descriptions.append(desc if desc else f"Band {i}")
            return {
                "band_count": src.count,
                "crs": src.crs,
                "transform": src.transform,
                "width": src.width,
                "height": src.height,
                "nodata": src.nodata,
                "band_descriptions": band_descriptions,
                "dtype": src.dtypes[0],
            }


def _read_band_data(tiff_bytes: bytes, band_index: int):
    """Read one band from a GeoTIFF byte stream.

    Returns (data_array, transform, crs, nodata).
    """
    with rasterio.MemoryFile(tiff_bytes) as memfile:
        with memfile.open() as src:
            return src.read(band_index), src.transform, src.crs, src.nodata


def _get_band_stats(data: np.ndarray, nodata) -> dict:
    """Basic statistics for one band, excluding nodata."""
    arr = data.astype(float)
    if nodata is not None:
        try:
            arr = arr[~np.isclose(arr, float(nodata))]
        except Exception:
            pass
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return {"min": None, "max": None, "mean": None, "std": None,
                "p5": None, "p95": None}
    return {
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
        "p5": float(np.percentile(arr, 5)),
        "p95": float(np.percentile(arr, 95)),
    }


# ============================================================================
# Smoothing helpers
# ============================================================================

def _smooth_mask_morphological(mask: np.ndarray, iterations: int = 2) -> np.ndarray:
    """
    Remove pixel-level staircase noise from a boolean mask using morphological
    closing (fills small gaps/notches) followed by opening (removes tiny blobs).

    Uses scipy.ndimage when available; falls back to a pure-NumPy
    sliding-window approach that is guaranteed to return an array of
    the same shape as *mask* regardless of kernel parity.
    """
    if iterations == 0:
        return mask

    if SCIPY_AVAILABLE:
        r = max(1, iterations)
        y, x = np.ogrid[-r: r + 1, -r: r + 1]
        struct = (x ** 2 + y ** 2 <= r ** 2)
        smoothed = binary_closing(mask, structure=struct, iterations=1)
        smoothed = binary_opening(smoothed, structure=struct, iterations=1)
        return smoothed.astype(bool)

    # ── NumPy-only fallback ──────────────────────────────────────────────────
    # Build a box-filter using sliding_window_view with carefully chosen
    # asymmetric padding so the output shape always equals the input shape.
    #
    # For kernel size k and a 1-D axis of length N:
    #   pad_before = k // 2
    #   pad_after  = k - 1 - k // 2   (= k//2 for even k, k//2 for odd k too)
    # After padding: N + (k-1). sliding_window_view gives N + (k-1) - k + 1 = N. ✓
    from numpy.lib.stride_tricks import sliding_window_view

    k = max(2, iterations * 2 + 1)
    pad_before = k // 2
    pad_after = k - 1 - k // 2  # == k//2 for odd k, k//2-1 for even k but still correct

    padded = np.pad(
        mask.astype(float),
        ((pad_before, pad_after), (pad_before, pad_after)),
        mode="edge",
    )

    # sliding_window_view shape: (H, W, k, k)
    windows = sliding_window_view(padded, (k, k))         # shape (H, W, k, k)
    smoothed = windows.mean(axis=(-2, -1)) >= 0.5         # shape (H, W)  ✓
    return smoothed


def _smooth_geometry(geom, pixel_size: float, smooth_level: int):
    """
    Smooth a single Shapely geometry to remove zigzag/staircase edges.

    Strategy
    --------
    1. ``simplify`` (Douglas-Peucker)   – removes collinear staircase vertices
       with a tolerance proportional to pixel_size.
    2. Buffer in/out trick              – a small outward buffer followed by an
       equal inward buffer rounds the remaining corners into gentle curves.

    Parameters
    ----------
    geom        : Shapely geometry
    pixel_size  : Pixel size in CRS units (used to scale tolerances).
    smooth_level: 0 = none, 1 = light, 2 = medium, 3 = strong
    """
    if smooth_level == 0 or geom is None or geom.is_empty:
        return geom

    # Tolerance scale factors per level
    simplify_factors = {1: 0.5, 2: 1.0, 3: 2.0}
    buffer_factors   = {1: 0.3, 2: 0.7, 3: 1.2}

    simplify_tol = pixel_size * simplify_factors[smooth_level]
    buf_dist     = pixel_size * buffer_factors[smooth_level]

    # Step 1 – simplify (removes staircase vertices)
    geom = geom.simplify(simplify_tol, preserve_topology=True)

    # Step 2 – buffer out then in (rounds remaining corners)
    # resolution=16 quadrant segments give smooth arc approximations.
    geom = geom.buffer(buf_dist, resolution=16).buffer(-buf_dist, resolution=16)

    if geom.is_empty or not geom.is_valid:
        return geom.buffer(0)  # attempt repair

    return geom


# ============================================================================
# Core polygonization
# ============================================================================

def _polygonize_below_threshold(
    data: np.ndarray,
    transform,
    crs,
    nodata,
    threshold: float,
    dissolve: bool = True,
    morph_smooth_iters: int = 2,
    smooth_level: int = 2,
) -> gpd.GeoDataFrame:
    """
    Convert pixels with value < threshold into smooth vector polygons.

    Parameters
    ----------
    data              : 2-D NumPy array (one band).
    transform         : Rasterio affine transform.
    crs               : Rasterio CRS.
    nodata            : NoData value (or None).
    threshold         : Pixels < threshold are polygonized.
    dissolve          : Merge touching regions into single polygons.
    morph_smooth_iters: Morphological smoothing passes on the binary mask
                        (0 = disabled). Eliminates pixel-boundary staircases
                        BEFORE vectorisation.
    smooth_level      : Post-polygonize geometry smoothing strength
                        (0=none, 1=light, 2=medium, 3=strong).
    """

    # ── 1. Build binary mask ──────────────────────────────────────────────────
    valid_mask = data < threshold

    # Exclude NoData
    if nodata is not None:
        try:
            valid_mask &= ~np.isclose(data.astype(float), float(nodata))
        except (ValueError, TypeError):
            pass

    if not valid_mask.any():
        return gpd.GeoDataFrame(columns=["geometry", "pixel_val"], geometry="geometry")

    # ── 2. Morphological smoothing on mask (pre-vectorise) ────────────────────
    if morph_smooth_iters > 0:
        valid_mask = _smooth_mask_morphological(valid_mask, morph_smooth_iters)

    # ── 3. Polygonise ─────────────────────────────────────────────────────────
    mask_uint8 = valid_mask.astype(np.uint8)

    geoms, values = [], []
    for geom_dict, val in rasterio_shapes(mask_uint8, mask=mask_uint8, transform=transform):
        if val == 1:
            geom = shape(geom_dict)
            if not geom.is_empty and geom.is_valid:
                geoms.append(geom)
                values.append(1.0)

    if not geoms:
        return gpd.GeoDataFrame(columns=["geometry", "pixel_val"], geometry="geometry")

    gdf = gpd.GeoDataFrame({"geometry": geoms, "pixel_val": values})

    # Set CRS
    target_crs = crs or "EPSG:4326"
    try:
        gdf = gdf.set_crs(target_crs)
    except Exception:
        gdf = gdf.set_crs("EPSG:4326")

    # ── 4. Dissolve ───────────────────────────────────────────────────────────
    if dissolve:
        dissolved = unary_union(gdf.geometry)
        gdf = gpd.GeoDataFrame({"geometry": [dissolved]})
        try:
            gdf = gdf.set_crs(target_crs, allow_override=True)
        except Exception:
            pass
        gdf = gdf.explode(index_parts=False).reset_index(drop=True)
        gdf["pixel_val"] = 1.0

    # ── 5. Geometry smoothing (post-vectorise) ────────────────────────────────
    if smooth_level > 0:
        # Estimate pixel size from the affine transform
        pixel_size = abs(transform.a)  # width of one pixel in CRS units

        smoothed_geoms = []
        for geom in gdf.geometry:
            try:
                sg = _smooth_geometry(geom, pixel_size, smooth_level)
                smoothed_geoms.append(sg if (sg and not sg.is_empty) else geom)
            except Exception:
                smoothed_geoms.append(geom)

        gdf = gdf.copy()
        gdf["geometry"] = smoothed_geoms
        # Drop any degenerate geometries created by heavy buffering
        gdf = gdf[~gdf.geometry.is_empty & gdf.geometry.is_valid].reset_index(drop=True)

    return gdf


# ============================================================================
# Clip helper
# ============================================================================

def _clip_to_shapefile(
    result_gdf: gpd.GeoDataFrame, boundary_gdf: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """Clip result polygons to a boundary shapefile."""
    if result_gdf.empty:
        return result_gdf

    if boundary_gdf.crs != result_gdf.crs:
        boundary_gdf = boundary_gdf.to_crs(result_gdf.crs)

    union_boundary = unary_union(boundary_gdf.geometry)
    clipped = result_gdf.copy()
    clipped["geometry"] = clipped.geometry.intersection(union_boundary)
    clipped = clipped[~clipped.geometry.is_empty & clipped.geometry.is_valid]
    return clipped.reset_index(drop=True)


# ============================================================================
# Tool Class
# ============================================================================

class TiffToShapefileTool(BaseTool):
    """TIFF Threshold Polygonizer – pixels below threshold → smooth shapefile polygons."""

    @property
    def name(self) -> str:
        return "TIFF Threshold Polygonizer"

    @property
    def description(self) -> str:
        return (
            "Read a GeoTIFF file, select a band and a threshold value. "
            "All pixels below the threshold are grouped into smooth polygons and "
            "exported as a downloadable shapefile."
        )

    @property
    def icon(self) -> str:
        return "🛰️"

    # ── UI ────────────────────────────────────────────────────────────────────

    def render_ui(self) -> None:
        st.header(f"{self.icon} {self.name}")
        st.markdown(
            "Upload a **GeoTIFF** file, choose a single band, set a **lower threshold**, "
            "and download the resulting **smooth** polygons as a shapefile."
        )
        st.divider()

        # Dependency check
        if not RASTERIO_AVAILABLE:
            st.error("❌ **rasterio** is not installed. Run `pip install rasterio`.")
            return

        # ── Step 1: Upload TIFF ───────────────────────────────────────────────
        st.subheader("📁 Step 1: Upload GeoTIFF File")
        st.info("ℹ️ Maximum file size: **1 GB**. Supported formats: `.tif`, `.tiff`.")

        tiff_file = st.file_uploader(
            "Upload GeoTIFF",
            type=["tif", "tiff"],
            key="tiff_upload",
            help="Upload a GeoTIFF raster file (up to 1 GB).",
        )

        if tiff_file is None:
            st.info("👆 Upload a GeoTIFF file to get started.")
            return

        tiff_bytes = tiff_file.read()
        file_size_mb = len(tiff_bytes) / (1024 ** 2)
        st.success(f"✅ File loaded: **{tiff_file.name}** ({file_size_mb:.1f} MB)")

        try:
            tiff_info = _read_tiff_info(tiff_bytes)
        except Exception as exc:
            st.error(f"❌ Could not read TIFF metadata: {exc}")
            return

        with st.expander("📊 Raster Metadata", expanded=False):
            c1, c2, c3 = st.columns(3)
            c1.metric("Bands", tiff_info["band_count"])
            c2.metric("Width (px)", tiff_info["width"])
            c3.metric("Height (px)", tiff_info["height"])
            c4, c5 = st.columns(2)
            c4.metric("Data Type", tiff_info["dtype"])
            c5.metric("No-Data Value", str(tiff_info["nodata"] or "None"))
            if tiff_info["crs"]:
                st.markdown(f"**CRS:** `{tiff_info['crs']}`")
            else:
                st.warning("⚠️ No CRS found – output will default to EPSG:4326.")

        st.divider()

        # ── Step 2: Band Selection ────────────────────────────────────────────
        st.subheader("🎛️ Step 2: Select Band")
        band_labels = [
            f"Band {i}: {tiff_info['band_descriptions'][i - 1]}"
            for i in range(1, tiff_info["band_count"] + 1)
        ]
        selected_band_label = st.selectbox(
            "Choose a band to threshold:",
            options=band_labels,
            key="tiff_band_select",
        )
        selected_band_index = band_labels.index(selected_band_label) + 1

        with st.spinner(f"Reading band {selected_band_index}…"):
            try:
                band_data, band_transform, band_crs, band_nodata = _read_band_data(
                    tiff_bytes, selected_band_index
                )
            except Exception as exc:
                st.error(f"❌ Error reading band: {exc}")
                return

        stats = _get_band_stats(band_data, band_nodata)

        if stats["min"] is not None:
            with st.expander("📈 Band Statistics", expanded=True):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Min",     f"{stats['min']:.4g}")
                c2.metric("Max",     f"{stats['max']:.4g}")
                c3.metric("Mean",    f"{stats['mean']:.4g}")
                c4.metric("Std Dev", f"{stats['std']:.4g}")
                c5, c6 = st.columns(2)
                c5.metric("5th Pct",  f"{stats['p5']:.4g}")
                c6.metric("95th Pct", f"{stats['p95']:.4g}")
        else:
            st.warning("⚠️ All values may be NoData.")

        st.divider()

        # ── Step 3: Threshold ─────────────────────────────────────────────────
        st.subheader("🔢 Step 3: Set Lower Threshold")
        st.markdown(
            "Pixels with values **strictly less than** the threshold "
            "will be converted into polygons."
        )

        try:
            arr_flat = band_data.astype(float).ravel()
            if band_nodata is not None:
                arr_flat = arr_flat[~np.isclose(arr_flat, float(band_nodata))]
            arr_flat = arr_flat[np.isfinite(arr_flat)]
            default_threshold = float(np.percentile(arr_flat, 25)) if arr_flat.size else 0.0
        except Exception:
            default_threshold = stats["mean"] or 0.0

        col_thresh, col_info = st.columns([2, 1])
        with col_thresh:
            threshold_value = st.number_input(
                "Threshold Value",
                value=float(f"{default_threshold:.6g}"),
                step=(
                    float(f"{max((stats['max'] - stats['min']) / 100, 0.001):.4g}")
                    if stats["min"] is not None and stats["max"] is not None
                    else 1.0
                ),
                format="%.6g",
                key="tiff_threshold",
                help="Pixels LESS THAN this value become polygons.",
            )
        with col_info:
            if stats["min"] is not None:
                pct = float(np.mean(band_data < threshold_value)) * 100
                st.metric("Est. % pixels below", f"{pct:.1f}%")

        dissolve_polygons = st.checkbox(
            "Dissolve adjacent pixels into single polygons",
            value=True,
            key="tiff_dissolve",
        )

        st.divider()

        # ── Step 4: Smoothing Controls ────────────────────────────────────────
        st.subheader("✨ Step 4: Edge Smoothing")
        st.markdown(
            "Eliminate the **zigzag/staircase** effect caused by pixel boundaries. "
            "Two complementary techniques are applied in sequence:"
        )

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("**🔬 Pre-smoothing (mask morphology)**")
            st.caption(
                "Closes pixel-level notches and gaps in the binary mask "
                "*before* vectorisation. Higher values → more aggressive fill."
            )
            morph_iters = st.slider(
                "Morphological passes",
                min_value=0, max_value=5, value=2, step=1,
                key="tiff_morph_iters",
                help=(
                    "0 = disabled. Uses binary closing + opening with a disk "
                    "structuring element of radius = passes."
                    + (" (scipy active)" if SCIPY_AVAILABLE else " (scipy not found – NumPy fallback)")
                ),
            )

        with col_b:
            st.markdown("**📐 Post-smoothing (geometry curves)**")
            st.caption(
                "Simplifies and buffers the resulting polygons *after* "
                "vectorisation to produce gentle curves instead of jagged lines."
            )
            smooth_level = st.select_slider(
                "Smoothing strength",
                options=["None (0)", "Light (1)", "Medium (2)", "Strong (3)"],
                value="Medium (2)",
                key="tiff_smooth_level",
            )
            smooth_map = {"None (0)": 0, "Light (1)": 1, "Medium (2)": 2, "Strong (3)": 3}
            smooth_level_int = smooth_map[smooth_level]

        if smooth_level_int > 0:
            pixel_size_est = abs(tiff_info["transform"].a)
            buf_factors = {1: 0.3, 2: 0.7, 3: 1.2}
            st.info(
                f"ℹ️ Post-smoothing will apply a **simplify tolerance** of "
                f"`{pixel_size_est * {1: 0.5, 2: 1.0, 3: 2.0}[smooth_level_int]:.4g}` CRS units "
                f"and a **round-corner buffer** of "
                f"`{pixel_size_est * buf_factors[smooth_level_int]:.4g}` CRS units, "
                f"based on the detected pixel size of `{pixel_size_est:.4g}` CRS units."
            )

        st.divider()

        # ── Step 5: Boundary clip ─────────────────────────────────────────────
        st.subheader("🗺️ Step 5: Clip to Shapefile Boundary (Optional)")
        boundary_zip = st.file_uploader(
            "Upload Boundary Shapefile (ZIP)",
            type=["zip"],
            key="tiff_boundary_upload",
        )

        boundary_gdf = None
        if boundary_zip is not None:
            with create_temp_directory() as tmp:
                boundary_gdf, msg = get_gdf_from_upload(boundary_zip, tmp)
                if boundary_gdf is None:
                    st.error(f"❌ {msg}")
                    boundary_gdf = None
                else:
                    st.success(f"✅ Boundary loaded: {msg}")
                    boundary_gdf = boundary_gdf.copy()

        st.divider()

        # ── Step 6: Process ───────────────────────────────────────────────────
        st.subheader("🚀 Step 6: Generate Polygons")
        _, col_btn, _ = st.columns([1, 2, 1])
        with col_btn:
            process_btn = st.button(
                "🛰️ Generate Smooth Threshold Polygons",
                type="primary",
                use_container_width=True,
                key="tiff_process_btn",
            )

        if process_btn:
            self._run_processing(
                tiff_bytes=tiff_bytes,
                band_index=selected_band_index,
                band_data=band_data,
                band_transform=band_transform,
                band_crs=band_crs,
                band_nodata=band_nodata,
                threshold=threshold_value,
                dissolve=dissolve_polygons,
                morph_iters=morph_iters,
                smooth_level=smooth_level_int,
                boundary_gdf=boundary_gdf,
            )

    # ── Processing ────────────────────────────────────────────────────────────

    def _run_processing(
        self,
        tiff_bytes: bytes,
        band_index: int,
        band_data: np.ndarray,
        band_transform,
        band_crs,
        band_nodata,
        threshold: float,
        dissolve: bool,
        morph_iters: int,
        smooth_level: int,
        boundary_gdf,
    ) -> None:
        """Execute polygonization with smoothing and offer download."""

        progress = st.progress(0, text="Starting…")

        try:
            # 1. Polygonise (with pre- and post-smoothing)
            progress.progress(10, text="Polygonizing pixels below threshold…")
            result_gdf = _polygonize_below_threshold(
                data=band_data,
                transform=band_transform,
                crs=band_crs,
                nodata=band_nodata,
                threshold=threshold,
                dissolve=dissolve,
                morph_smooth_iters=morph_iters,
                smooth_level=smooth_level,
            )
            progress.progress(65, text="Polygonization + smoothing complete.")

            if result_gdf.empty:
                progress.empty()
                st.warning(
                    "⚠️ No pixels found below the threshold. "
                    "Try increasing the threshold or checking band statistics."
                )
                return

            st.info(f"📐 Raw polygon count: **{len(result_gdf)}**")

            # 2. Clip to boundary
            if boundary_gdf is not None:
                progress.progress(72, text="Clipping to shapefile boundary…")
                result_gdf = _clip_to_shapefile(result_gdf, boundary_gdf)
                progress.progress(85, text="Clipping complete.")

                if result_gdf.empty:
                    progress.empty()
                    st.warning(
                        "⚠️ No polygons remain after clipping. "
                        "Check that the TIFF and shapefile overlap."
                    )
                    return

                st.info(f"✂️ Polygon count after clipping: **{len(result_gdf)}**")

            # 3. Save shapefile ZIP
            progress.progress(88, text="Saving shapefile…")
            with create_temp_directory() as tmp_dir:
                output_name = f"smooth_polygons_band{band_index}"
                zip_path = create_shapefile_zip(result_gdf, output_name, tmp_dir)
                with open(zip_path, "rb") as fh:
                    zip_bytes = fh.read()

            progress.progress(100, text="Done!")
            progress.empty()

            # ── Results ───────────────────────────────────────────────────────
            st.success("✅ Smooth polygons generated successfully!")

            c1, c2, c3 = st.columns(3)
            c1.metric("Total Polygons", len(result_gdf))
            total_area = result_gdf.geometry.area.sum()
            c2.metric(
                "Total Area (CRS units²)",
                f"{total_area:,.2f}" if total_area < 1e9 else f"{total_area:.3e}",
            )
            c3.metric("Output File Size", f"{len(zip_bytes) / 1024:.1f} KB")

            with st.expander("🔍 Preview Output Table", expanded=False):
                preview = result_gdf.copy()
                preview["geometry"] = preview.geometry.apply(
                    lambda g: g.geom_type if g else "None"
                )
                st.dataframe(preview.head(50), use_container_width=True)

            st.download_button(
                label="⬇️ Download Smooth Threshold Polygons Shapefile (ZIP)",
                data=zip_bytes,
                file_name=f"smooth_polygons_band{band_index}.zip",
                mime="application/zip",
                use_container_width=True,
                key="tiff_download_btn",
            )

        except MemoryError:
            progress.empty()
            st.error(
                "❌ Not enough memory. Try a smaller TIFF, higher threshold, "
                "or reduce morphological passes."
            )
        except Exception as exc:
            progress.empty()
            st.error(f"❌ Processing failed: {exc}")
            with st.expander("🐞 Error Details"):
                import traceback
                st.code(traceback.format_exc())
