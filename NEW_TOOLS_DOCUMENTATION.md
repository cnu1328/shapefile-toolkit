# New Tools Documentation

## Overview

Two powerful new tools have been added to the Shapefile Toolkit:

1. **Excel to CSV** - Convert Excel spreadsheets to CSV format
2. **CSV to Shapefile** - Convert CSV files with geometry data to Shapefiles

---

## 1. Excel to CSV Tool 📑

### Purpose
Convert Excel spreadsheet data to CSV format with flexible options for sheet selection and formatting.

### Features

#### ✅ Multi-Sheet Support
- Automatically detects all sheets in the Excel workbook
- Displays sheet information (rows, columns, status)
- Allows selection of specific sheet to convert

#### ✅ Error Handling
- Detects and reports sheets that cannot be read
- Shows clear error messages for problematic sheets
- Continues processing other sheets even if one fails

#### ✅ Customizable Output
- **Separator Options**:
  - Comma (,)
  - Semicolon (;)
  - Pipe (|)
  - Tab
  - Custom separator (user-defined)

- **Additional Options**:
  - Include/exclude row index
  - Handle empty cells (leave empty, replace with 'NULL', or replace with '0')

#### ✅ Session State Management
- File loaded once, parameters changed instantly
- No reload when changing options
- Smooth user experience

### Usage Workflow

1. **Upload Excel File**
   - Supports .xlsx and .xls formats
   - Automatically loads all sheets

2. **View Sheet Information**
   - Table showing all sheets with row/column counts
   - Status indicator (✅ Ready or ❌ Error)

3. **Select Sheet and Configure**
   - Choose which sheet to convert
   - Select separator type
   - Configure empty cell handling
   - Choose whether to include row index

4. **Convert and Download**
   - Click "Convert to CSV"
   - Download generated CSV file
   - View conversion summary

### Edge Cases Handled

| Edge Case | Handling |
|-----------|----------|
| Empty sheet | Warning message, prevents conversion |
| Unreadable sheet | Marked as error, excluded from selection |
| Merged cells | Handled by pandas (unmerged) |
| Formulas | Values exported (not formulas) |
| Special characters | UTF-8 encoding preserves all characters |
| Large files | Efficient pandas processing |
| Multiple sheets with same name | Pandas handles internally |

### Example Use Cases

1. **Data Migration**: Convert Excel database to CSV for import into other systems
2. **Data Sharing**: Share data with users who don't have Excel
3. **Data Processing**: Prepare Excel data for analysis in Python/R
4. **Format Standardization**: Convert various Excel formats to standard CSV

---

## 2. CSV to Shapefile Tool 🗺️

### Purpose
Convert CSV files containing geometry data into GIS-compatible Shapefile format.

### Features

#### ✅ Automatic Geometry Detection
The tool intelligently detects potential geometry columns:

- **WKT Columns**: Detects columns with keywords like 'wkt', 'geometry', 'geom', 'shape'
- **Latitude Columns**: Detects 'lat', 'latitude', 'y'
- **Longitude Columns**: Detects 'lon', 'long', 'longitude', 'x'
- **X/Y Coordinates**: Detects 'x', 'y', 'easting', 'northing'

#### ✅ Multiple Geometry Input Methods

**Method 1: WKT (Well-Known Text)**
- Supports all geometry types:
  - POINT (x y)
  - LINESTRING (x1 y1, x2 y2, ...)
  - POLYGON ((x1 y1, x2 y2, ...))
  - MULTIPOINT, MULTILINESTRING, MULTIPOLYGON
  - GEOMETRYCOLLECTION
- Parses WKT strings using Shapely
- Validates geometry and reports errors

**Method 2: Latitude/Longitude**
- Creates Point geometries from lat/lon columns
- Automatically sets CRS to EPSG:4326 (WGS84)
- Validates coordinate values
- Skips rows with invalid coordinates

**Method 3: X/Y Coordinates**
- Creates Point geometries from X/Y columns
- User specifies appropriate CRS
- Supports projected coordinate systems
- Validates coordinate values

#### ✅ Flexible CRS Selection
- Choose from common EPSG codes (WGS84, Web Mercator, UTM zones, etc.)
- Enter custom EPSG code
- CRS descriptions provided
- Proper CRS assignment to output

#### ✅ Comprehensive Validation
- Checks for empty CSV files
- Validates geometry parsing
- Reports number of invalid geometries
- Shows geometry type distribution
- Skips invalid rows automatically

#### ✅ Multiple Output Formats
- Shapefile (ZIP) - Traditional format
- GeoPackage (.gpkg) - Modern single-file format

### Usage Workflow

1. **Upload CSV File**
   - Select CSV separator (comma, semicolon, pipe, tab)
   - File loaded and validated

2. **View Data Preview**
   - First 10 rows displayed
   - Column names shown
   - Row/column count summary

3. **Configure Geometry**
   - Choose geometry method (WKT, Lat/Lon, or X/Y)
   - Tool suggests detected columns
   - Select appropriate columns
   - View sample geometry values

4. **Parse Geometry**
   - Click parse/create button
   - Tool validates all geometries
   - Reports success count and errors
   - Shows geometry types found

5. **Select CRS**
   - Choose from common EPSG codes or enter custom
   - CRS applied to output

6. **Export Shapefile**
   - Choose output format (ZIP or GeoPackage)
   - Click convert button
   - Download created shapefile
   - View conversion summary

### Edge Cases Handled

| Edge Case | Handling |
|-----------|----------|
| Empty CSV | Error message, prevents conversion |
| Invalid WKT | Skips row, reports count |
| Invalid coordinates | Skips row, reports count |
| Mixed geometry types | Accepts all, reports distribution |
| Missing values | Skips rows with null geometry |
| Wrong separator | User can change separator |
| No geometry column | Clear error message |
| Large CSV files | Efficient pandas/geopandas processing |
| Special characters in attributes | UTF-8 encoding preserves data |

### Supported Geometry Types

| Type | WKT Example | Lat/Lon | X/Y |
|------|-------------|---------|-----|
| Point | `POINT (30 10)` | ✅ | ✅ |
| LineString | `LINESTRING (30 10, 10 30, 40 40)` | ✅ | ❌ |
| Polygon | `POLYGON ((30 10, 40 40, 20 40, 10 20, 30 10))` | ✅ | ❌ |
| MultiPoint | `MULTIPOINT ((10 40), (40 30))` | ✅ | ❌ |
| MultiLineString | `MULTILINESTRING ((10 10, 20 20), (15 15, 30 15))` | ✅ | ❌ |
| MultiPolygon | `MULTIPOLYGON (((30 20, 45 40, 10 40, 30 20)))` | ✅ | ❌ |

### Example Use Cases

1. **GPS Data**: Convert GPS tracks (lat/lon CSV) to shapefile
2. **Survey Data**: Convert field survey coordinates to GIS format
3. **Database Export**: Convert PostGIS/database exports to shapefile
4. **Web Data**: Convert web service JSON/CSV responses to shapefile
5. **Analysis Results**: Convert analysis output coordinates to spatial format

### CSV Format Examples

**Example 1: WKT Format**
```csv
id,name,geometry
1,Location A,POINT (77.5946 12.9716)
2,Location B,POINT (77.6412 13.0827)
3,Route,LINESTRING (77.5946 12.9716, 77.6412 13.0827)
```

**Example 2: Lat/Lon Format**
```csv
id,name,latitude,longitude
1,Location A,12.9716,77.5946
2,Location B,13.0827,77.6412
```

**Example 3: X/Y Format**
```csv
id,name,x_coord,y_coord
1,Location A,500000,1430000
2,Location B,510000,1440000
```

---

## Technical Implementation

### Session State Management
Both tools use Streamlit session state to:
- Cache uploaded files
- Prevent unnecessary reprocessing
- Enable smooth parameter changes
- Maintain user experience

### Error Handling Strategy
1. **Validation**: Check inputs before processing
2. **Try-Catch**: Wrap operations in exception handlers
3. **User Feedback**: Clear error messages with details
4. **Graceful Degradation**: Skip invalid data, process valid data
5. **Debug Info**: Expandable error details for troubleshooting

### Performance Considerations
- **Lazy Loading**: Files loaded only when changed
- **Efficient Libraries**: Pandas and GeoPandas for fast processing
- **Memory Management**: Temporary files cleaned up automatically
- **Progress Indicators**: Spinners show processing status

---

## Testing Checklist

### Excel to CSV Tool

- [ ] Upload .xlsx file
- [ ] Upload .xls file
- [ ] File with multiple sheets
- [ ] File with empty sheet
- [ ] File with unreadable sheet
- [ ] Change separator without reload
- [ ] Test all separator types
- [ ] Test custom separator
- [ ] Include/exclude index
- [ ] Different empty cell handling
- [ ] Large Excel file (>1000 rows)
- [ ] Excel with formulas
- [ ] Excel with merged cells
- [ ] Excel with special characters

### CSV to Shapefile Tool

- [ ] CSV with WKT Point geometries
- [ ] CSV with WKT LineString geometries
- [ ] CSV with WKT Polygon geometries
- [ ] CSV with mixed geometry types
- [ ] CSV with lat/lon columns
- [ ] CSV with X/Y coordinates
- [ ] CSV with invalid geometries
- [ ] CSV with missing values
- [ ] Different CSV separators
- [ ] Large CSV file (>1000 rows)
- [ ] Different CRS selections
- [ ] Output as Shapefile ZIP
- [ ] Output as GeoPackage
- [ ] CSV with special characters

---

## Summary

✅ **Excel to CSV**: Production-ready with comprehensive error handling  
✅ **CSV to Shapefile**: Supports all major geometry formats and coordinate systems  
✅ **Session State**: Smooth UX without reloads  
✅ **Error Handling**: Graceful handling of edge cases  
✅ **Documentation**: Complete usage guide  
✅ **Testing**: Ready for verification

Both tools are fully integrated into the Shapefile Toolkit and ready for use!
