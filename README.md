# 🗺️ Shapefile Toolkit

A production-ready Streamlit web application for performing common shapefile operations through a clean, modular, and professional codebase.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.28+-red.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 🌟 Features

The Shapefile Toolkit provides four powerful GIS tools accessible through an intuitive web interface:

### 📊 Shapefile to CSV
- Export shapefile attributes to CSV format
- Customizable separators (comma, semicolon, pipe, tab, or custom)
- Select specific columns to export
- Optional geometry export as Well-Known Text (WKT)
- Preview data before export

### 🔗 Merge Multiple Shapefiles
- Combine 2 or more shapefiles into a single output
- Automatic CRS compatibility checking and reprojection
- Schema validation and automatic alignment
- Support for both Shapefile (ZIP) and GeoPackage output formats
- Detailed merge summary with feature counts

### ➕ Add Two Shapefiles
- Combine exactly two shapefiles by appending features
- Automatic CRS handling with reprojection options
- Schema alignment for different attribute structures
- Clear visualization of input differences
- Transformation summary

### 🌐 Reproject Shapefile
- Transform coordinates to different CRS
- Display current CRS information (EPSG, name, Proj4)
- Choose from common EPSG codes or enter custom codes
- Support for popular projections (WGS 84, Web Mercator, UTM zones, etc.)
- Multiple output format options

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Installation

1. **Clone or download this repository:**

```bash
git clone <repository-url>
cd shapefile-toolkit
```

2. **Install dependencies:**

```bash
pip install -r requirements.txt
```

### Running Locally

Start the Streamlit application:

```bash
streamlit run app.py
```

The application will open in your default web browser at `http://localhost:8501`.

## 📁 Project Structure

```
shapefile-toolkit/
├── app.py                          # Main Streamlit application
├── core/                           # Core utilities and base classes
│   ├── __init__.py
│   ├── base_tool.py                # Abstract base class for tools
│   ├── utils_io.py                 # File I/O utilities
│   └── utils_geo.py                # GIS utilities (CRS, reprojection)
├── tools/                          # Shapefile processing tools
│   ├── __init__.py
│   ├── shapefile_to_csv.py         # CSV export tool
│   ├── merge_shapefiles.py         # Merge N shapefiles
│   ├── add_shapefiles.py           # Add/combine 2 shapefiles
│   ├── reproject_shapefile.py      # CRS transformation
│   └── template_tool.py            # Template for new tools
├── ui/                             # UI components
│   ├── __init__.py
│   ├── homepage.py                 # Dashboard/home page
│   └── layout.py                   # Reusable UI components
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

## 🛠️ Architecture

### Modular Design

The application follows a clean, modular architecture with clear separation of concerns:

- **Core Layer**: Reusable utilities for I/O operations and GIS processing
- **Tools Layer**: Individual tool implementations, each as a self-contained class
- **UI Layer**: Presentation components and styling

### Tool Pattern

Each tool is implemented as a class extending `BaseTool`:

```python
class MyTool(BaseTool):
    @property
    def name(self) -> str:
        return "My Tool Name"
    
    @property
    def description(self) -> str:
        return "Tool description"
    
    @property
    def icon(self) -> str:
        return "🔧"
    
    def render_ui(self) -> None:
        # Implement Streamlit UI here
        pass
```

### Single Instance Pattern

Tools are registered in a singleton `ToolRegistry` to ensure only one instance of each tool exists throughout the application lifecycle.

## 📚 Usage Guide

### Uploading Shapefiles

All tools accept **ZIP files** containing shapefile components:

- Required: `.shp`, `.shx`, `.dbf`
- Optional: `.prj`, `.cpg`, `.sbn`, `.sbx`

**Important:** Each ZIP should contain only one shapefile (one set of components).

### Coordinate Reference Systems (CRS)

The toolkit automatically handles CRS differences:

- Displays current CRS information (EPSG code, name, Proj4 string)
- Offers reprojection options when merging/combining shapefiles
- Supports common EPSG codes and custom codes

### Output Formats

- **Shapefile (ZIP)**: Traditional shapefile format packaged as ZIP
- **GeoPackage (.gpkg)**: Modern single-file format (where applicable)
- **CSV**: For attribute-only exports

## 🔧 Adding New Tools

The toolkit is designed for easy extensibility. To add a new tool:

1. **Create a new file** in the `tools/` directory (e.g., `buffer_tool.py`)

2. **Implement the tool class** extending `BaseTool`:

```python
from core.base_tool import BaseTool
import streamlit as st

class BufferTool(BaseTool):
    @property
    def name(self) -> str:
        return "Buffer Geometries"
    
    @property
    def description(self) -> str:
        return "Create buffer zones around features"
    
    @property
    def icon(self) -> str:
        return "⭕"
    
    def render_ui(self) -> None:
        st.header(f"{self.icon} {self.name}")
        # Implement your UI here
        pass
```

3. **Register the tool** in `app.py`:

```python
from tools.buffer_tool import BufferTool

# In initialize_tools():
registry.register_tool("tool_4", BufferTool())
```

4. **Use core utilities** for common operations:

```python
from core.utils_io import get_gdf_from_upload, create_shapefile_zip
from core.utils_geo import get_crs_info, reproject_gdf
```

See `tools/template_tool.py` for a complete template with detailed comments.

## 🌐 Deployment

### Streamlit Cloud

This application is ready for deployment on [Streamlit Cloud](https://streamlit.io/cloud):

1. Push your code to a GitHub repository
2. Connect your repository to Streamlit Cloud
3. Deploy with `app.py` as the main file
4. Streamlit Cloud will automatically install dependencies from `requirements.txt`

### Other Platforms

The application can also be deployed on:

- **Heroku**: Add a `Procfile` with `web: streamlit run app.py`
- **Docker**: Create a Dockerfile with Python and dependencies
- **AWS/GCP/Azure**: Deploy as a containerized application

**Note:** Ensure sufficient memory allocation for processing large shapefiles.

## ⚠️ Limitations

- **File Size**: Large shapefiles (>100MB) may cause memory issues in browser-based processing
- **Complex Geometries**: Very complex geometries may slow down processing
- **Browser Limits**: Processing happens in-session; closing the browser will lose progress
- **CRS Support**: Some obscure CRS may not be fully supported

## 🔮 Future Enhancements

Potential features for future versions:

- **Spatial Operations**: Clip, intersect, union, difference
- **Attribute Operations**: Filter, dissolve, join
- **Geometry Operations**: Buffer, simplify, centroid
- **Analysis Tools**: Area/length calculation, spatial statistics
- **Visualization**: Interactive maps with Folium or Plotly
- **Batch Processing**: Process multiple operations in sequence
- **Export Formats**: Support for GeoJSON, KML, and other formats

## 🤝 Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

Built with:

- [Streamlit](https://streamlit.io/) - Web application framework
- [GeoPandas](https://geopandas.org/) - Geospatial data processing
- [Shapely](https://shapely.readthedocs.io/) - Geometric operations
- [PyProj](https://pyproj4.github.io/pyproj/) - Coordinate transformations
- [Fiona](https://fiona.readthedocs.io/) - File I/O

## 📧 Support

For issues, questions, or suggestions:

- Open an issue on GitHub
- Check existing documentation
- Review the template tool for implementation examples

---

**Happy mapping! 🗺️**
