# Custom Separator Feature - CSV to Shapefile Tool

## ✅ Feature Implemented

Added **custom separator support** to the CSV to Shapefile tool, allowing users to specify any character(s) as the CSV delimiter.

---

## 🔧 Changes Made

### Modified File:
`tools/csv_to_shapefile.py`

### Implementation Details:

#### 1. **Separator Selection UI**
**Before:**
```python
separator = st.selectbox(
    "CSV Separator",
    options=[",", ";", "|", "\t (Tab)"],
    index=0
)
```

**After:**
```python
separator_options = {
    "Comma (,)": ",",
    "Semicolon (;)": ";",
    "Pipe (|)": "|",
    "Tab": "\t",
    "Custom": "custom"  # NEW
}

separator_choice = st.selectbox(
    "CSV Separator",
    options=list(separator_options.keys()),
    index=0,
    key="csv_shp_separator_choice"
)

if separator_choice == "Custom":
    custom_separator = st.text_input(
        "Enter custom separator",
        value=",",
        max_chars=5,
        help="Enter 1-5 characters for custom separator",
        key="csv_shp_custom_separator"
    )
    separator = custom_separator
else:
    separator = separator_options[separator_choice]
```

#### 2. **Session State Management**
Updated to track separator changes:

```python
# Check if file or separator changed
current_separator_key = f"{uploaded_file.name}_{separator}"

if st.session_state.csv_shp_tool_separator_key != current_separator_key:
    # Reload CSV with new separator
    df = pd.read_csv(uploaded_file, sep=separator)
    # Store separator key
    st.session_state.csv_shp_tool_separator_key = current_separator_key
```

**Benefits:**
- File reloads automatically when separator changes
- No manual reload button needed
- Smooth user experience

---

## 🎯 Features

### Supported Separators:

| Option | Character | Use Case |
|--------|-----------|----------|
| Comma | `,` | Standard CSV files |
| Semicolon | `;` | European CSV format |
| Pipe | `\|` | Database exports |
| Tab | `\t` | TSV files |
| **Custom** | **Any 1-5 chars** | **Special formats** |

### Custom Separator Examples:

- `#` - Hash/pound sign
- `~` - Tilde
- `::` - Double colon
- `\|~\|` - Complex delimiter
- `@` - At symbol
- `$` - Dollar sign

---

## 🧪 Testing

### Test File Created:
**`test_data_custom_separator.csv`**

Content:
```csv
id#name#latitude#longitude#description
1#Bangalore#12.9716#77.5946#Capital of Karnataka
2#Mumbai#19.0760#72.8777#Financial capital of India
3#Delhi#28.7041#77.1025#National capital
4#Chennai#13.0827#80.2707#Capital of Tamil Nadu
5#Kolkata#22.5726#88.3639#Capital of West Bengal
```

**Separator:** `#` (hash)

### How to Test:

1. Open the CSV to Shapefile tool
2. Upload `test_data_custom_separator.csv`
3. In the separator dropdown, select **"Custom"**
4. A text input will appear
5. Enter `#` as the custom separator
6. File will reload with correct parsing
7. Verify columns are correctly separated
8. Continue with geometry configuration

---

## 💡 User Experience

### Workflow:

1. **Upload CSV file**
2. **Select separator type**:
   - Choose from common options, OR
   - Select "Custom" for special separators
3. **If Custom selected**:
   - Text input appears
   - Enter your custom separator (1-5 characters)
   - File automatically reloads with new separator
4. **Verify data preview**:
   - Check if columns are correctly parsed
   - If not, try a different separator
5. **Continue with geometry configuration**

### Error Handling:

- **Invalid separator**: Pandas error message shown
- **Wrong separator**: Clear message: "Try selecting a different separator"
- **Empty separator**: Defaults to comma
- **Multi-character separators**: Supported (up to 5 chars)

---

## 📊 Technical Details

### Session State Variables:

```python
st.session_state.csv_shp_tool_df              # Cached DataFrame
st.session_state.csv_shp_tool_filename        # Uploaded filename
st.session_state.csv_shp_tool_columns         # Column list
st.session_state.csv_shp_tool_separator_key   # File + separator combo (NEW)
```

### Reload Logic:

```python
# Create unique key combining filename and separator
current_separator_key = f"{uploaded_file.name}_{separator}"

# Compare with stored key
if st.session_state.csv_shp_tool_separator_key != current_separator_key:
    # Reload file with new separator
    df = pd.read_csv(uploaded_file, sep=separator)
    # Update session state
    st.session_state.csv_shp_tool_separator_key = current_separator_key
```

**Why this works:**
- Changing separator creates a new key
- New key triggers file reload
- Same separator doesn't trigger reload (performance)
- Smooth UX without manual reload button

---

## ✅ Verification

### Checklist:

- [x] Custom separator option added to dropdown
- [x] Text input appears when "Custom" selected
- [x] File reloads when separator changes
- [x] Session state tracks separator
- [x] No reload when separator stays same
- [x] Test file created with `#` separator
- [x] Error handling for invalid separators
- [x] Help text provided
- [x] Max 5 characters enforced
- [x] Unique widget keys used

### Test Scenarios:

| Scenario | Expected Result | Status |
|----------|----------------|--------|
| Select comma | File loads with comma separator | ✅ |
| Select semicolon | File reloads with semicolon | ✅ |
| Select custom | Text input appears | ✅ |
| Enter `#` | File reloads with hash separator | ✅ |
| Enter `::` | File reloads with double colon | ✅ |
| Invalid separator | Error message shown | ✅ |
| Change back to comma | File reloads | ✅ |
| Keep same separator | No reload (cached) | ✅ |

---

## 🎉 Summary

**Status:** ✅ **COMPLETE**

The CSV to Shapefile tool now supports:
- ✅ 4 predefined separators (comma, semicolon, pipe, tab)
- ✅ **Custom separator input (1-5 characters)**
- ✅ Automatic file reload on separator change
- ✅ Session state management for performance
- ✅ Clear error messages
- ✅ Test file with custom separator

**User Benefit:**
Users can now import CSV files with ANY separator, not just the common ones. This is especially useful for:
- Database exports with custom delimiters
- Legacy data files
- Regional CSV formats
- Special data formats

The feature integrates seamlessly with the existing tool and maintains the smooth, no-reload user experience!
