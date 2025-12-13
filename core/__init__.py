"""
Core utilities and base classes for the Shapefile Toolkit.
"""

from .base_tool import BaseTool
from .utils_io import (
    extract_shapefile_from_zip,
    create_shapefile_zip,
    validate_shapefile_components,
    get_gdf_from_upload,
)
from .utils_geo import (
    get_crs_info,
    reproject_gdf,
    validate_schema_compatibility,
    align_schemas,
    COMMON_EPSG_CODES,
)

__all__ = [
    "BaseTool",
    "extract_shapefile_from_zip",
    "create_shapefile_zip",
    "validate_shapefile_components",
    "get_gdf_from_upload",
    "get_crs_info",
    "reproject_gdf",
    "validate_schema_compatibility",
    "align_schemas",
    "COMMON_EPSG_CODES",
]
