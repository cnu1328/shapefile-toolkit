"""
Verification script for new tools.
Run this to verify the tools are properly integrated.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def verify_imports():
    """Verify all tools can be imported."""
    print("=" * 60)
    print("VERIFICATION: Tool Imports")
    print("=" * 60)
    
    try:
        from tools import (
            ShapefileToCSVTool,
            MergeShapefilesTool,
            AddShapefilesTool,
            ReprojectShapefileTool,
            ExcelToCSVTool,
            CSVToShapefileTool,
        )
        print("✅ All tools imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def verify_tool_properties():
    """Verify tool properties are correctly defined."""
    print("\n" + "=" * 60)
    print("VERIFICATION: Tool Properties")
    print("=" * 60)
    
    from tools import ExcelToCSVTool, CSVToShapefileTool
    
    # Test Excel to CSV tool
    excel_tool = ExcelToCSVTool()
    print(f"\nExcel to CSV Tool:")
    print(f"  Name: {excel_tool.name}")
    print(f"  Icon: {excel_tool.icon}")
    print(f"  Description: {excel_tool.description[:50]}...")
    
    # Test CSV to Shapefile tool
    csv_tool = CSVToShapefileTool()
    print(f"\nCSV to Shapefile Tool:")
    print(f"  Name: {csv_tool.name}")
    print(f"  Icon: {csv_tool.icon}")
    print(f"  Description: {csv_tool.description[:50]}...")
    
    print("\n✅ Tool properties verified")
    return True


def verify_dependencies():
    """Verify required dependencies are installed."""
    print("\n" + "=" * 60)
    print("VERIFICATION: Dependencies")
    print("=" * 60)
    
    dependencies = {
        'streamlit': 'Streamlit',
        'pandas': 'Pandas',
        'geopandas': 'GeoPandas',
        'shapely': 'Shapely',
        'openpyxl': 'OpenPyXL (for Excel support)',
    }
    
    all_installed = True
    for module, name in dependencies.items():
        try:
            __import__(module)
            print(f"✅ {name}")
        except ImportError:
            print(f"❌ {name} - NOT INSTALLED")
            all_installed = False
    
    return all_installed


def verify_tool_methods():
    """Verify tools have required methods."""
    print("\n" + "=" * 60)
    print("VERIFICATION: Tool Methods")
    print("=" * 60)
    
    from tools import ExcelToCSVTool, CSVToShapefileTool
    
    required_methods = ['name', 'description', 'icon', 'render_ui', 'get_card_info']
    
    for ToolClass in [ExcelToCSVTool, CSVToShapefileTool]:
        tool = ToolClass()
        print(f"\n{tool.name}:")
        
        for method in required_methods:
            if hasattr(tool, method):
                print(f"  ✅ {method}")
            else:
                print(f"  ❌ {method} - MISSING")
                return False
    
    print("\n✅ All required methods present")
    return True


def verify_csv_to_shapefile_methods():
    """Verify CSV to Shapefile tool has geometry handling methods."""
    print("\n" + "=" * 60)
    print("VERIFICATION: CSV to Shapefile Geometry Methods")
    print("=" * 60)
    
    from tools import CSVToShapefileTool
    
    tool = CSVToShapefileTool()
    
    methods = [
        'detect_geometry_columns',
        'parse_wkt_geometry',
        'create_point_from_coords',
    ]
    
    for method in methods:
        if hasattr(tool, method):
            print(f"✅ {method}")
        else:
            print(f"❌ {method} - MISSING")
            return False
    
    print("\n✅ All geometry methods present")
    return True


def verify_test_data():
    """Verify test data files exist."""
    print("\n" + "=" * 60)
    print("VERIFICATION: Test Data Files")
    print("=" * 60)
    
    test_files = [
        'test_data_latlon.csv',
        'test_data_wkt.csv',
    ]
    
    all_exist = True
    for file in test_files:
        if os.path.exists(file):
            size = os.path.getsize(file)
            print(f"✅ {file} ({size} bytes)")
        else:
            print(f"❌ {file} - NOT FOUND")
            all_exist = False
    
    return all_exist


def main():
    """Run all verifications."""
    print("\n" + "=" * 60)
    print("SHAPEFILE TOOLKIT - NEW TOOLS VERIFICATION")
    print("=" * 60)
    
    results = []
    
    results.append(("Imports", verify_imports()))
    results.append(("Tool Properties", verify_tool_properties()))
    results.append(("Dependencies", verify_dependencies()))
    results.append(("Tool Methods", verify_tool_methods()))
    results.append(("Geometry Methods", verify_csv_to_shapefile_methods()))
    results.append(("Test Data", verify_test_data()))
    
    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name:.<40} {status}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 ALL VERIFICATIONS PASSED!")
        print("\nThe new tools are ready to use:")
        print("  1. Excel to CSV Tool")
        print("  2. CSV to Shapefile Tool")
        print("\nRun: streamlit run app.py")
        print("Then navigate to the new tools from the homepage.")
    else:
        print("\n⚠️  SOME VERIFICATIONS FAILED")
        print("Please check the errors above and fix them.")
    
    print()


if __name__ == "__main__":
    main()
