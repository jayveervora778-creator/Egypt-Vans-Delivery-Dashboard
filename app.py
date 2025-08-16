import os, io, tempfile, datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="Vans Interactive Dashboard", layout="wide", page_icon="🚐")

# Custom CSS for better styling
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        border: 1px solid #e0e0e0;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .dashboard-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 1rem;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="dashboard-header">
    <h1>🚐 Vans Data Interactive Dashboard</h1>
    <p>Professional analytics for delivery operations data</p>
</div>
""", unsafe_allow_html=True)

# ---------- Authentication (optional) ----------
PASSWORD = os.getenv("STREAMLIT_DASH_PASSWORD", "")
if PASSWORD:
    def login():
        with st.form("login", clear_on_submit=False):
            pwd = st.text_input("🔐 Enter Password", type="password")
            ok = st.form_submit_button("🚀 Access Dashboard")
        return ok, pwd
    
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        ok, pwd = login()
        if ok and pwd == PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        elif ok:
            st.error("❌ Incorrect password")
            st.stop()
        else:
            st.info("🔒 Enter the password to access the dashboard.")
            st.stop()

# ---------- Helper Functions ----------
def _flatten_columns(columns):
    """Flatten multi-level column names"""
    flattened = []
    for col in columns:
        if isinstance(col, tuple) or isinstance(col, list):
            parts = [str(x) for x in col if str(x) != "nan" and str(x).strip()]
            flattened.append(" - ".join(parts).strip())
        else:
            flattened.append(str(col).strip())
    return flattened

# Temporarily disable caching to avoid PyArrow issues with mixed data types
# @st.cache_data(show_spinner="Loading data...")
def load_excel_file(path_or_bytes):
    """Load Excel file with proper survey data structure support"""
    try:
        # Load raw data to examine structure
        df_raw = pd.read_excel(path_or_bytes, header=None)
        
        # Based on analysis: Row 0 = main headers, Row 2 = sub-headers, Row 3+ = data
        if len(df_raw) < 4:
            st.error("Excel file doesn't have enough rows for survey data")
            return pd.DataFrame()
        
        # Get header rows (0-indexed, so Row 1 = index 0, Row 3 = index 2)
        main_headers = df_raw.iloc[0].fillna('')  # Row 1
        sub_headers = df_raw.iloc[2].fillna('')   # Row 3
        
        # Create intelligent column names
        smart_cols = []
        for i, (main_header, sub_header) in enumerate(zip(main_headers, sub_headers)):
            main_header = str(main_header).strip()
            sub_header = str(sub_header).strip()
            
            # Skip completely empty columns
            if main_header in ['nan', 'NULL', ''] and sub_header in ['nan', 'NULL', '']:
                if i == 0:
                    col_name = "Respondent"  # First column is always respondent
                else:
                    col_name = f"Empty_Col_{i}"
            else:
                # Create meaningful column names based on headers
                if i == 0:
                    col_name = "Respondent"
                elif i == 1 and "age" in main_header.lower():
                    col_name = "Age (Years)"
                elif i == 2 and "area" in main_header.lower():
                    col_name = "Areas Covered"
                elif i == 3 and "company" in main_header.lower():
                    col_name = "Company"
                elif i == 4 and "employment" in main_header.lower():
                    col_name = "Employment Status"
                else:
                    # Use main header as base
                    if main_header and main_header != 'nan':
                        col_name = main_header
                        
                        # Add sub-header if it provides additional context
                        if sub_header and sub_header != 'nan' and sub_header != main_header:
                            # Special cases for benefit details
                            if "days per month" in sub_header.lower():
                                col_name = f"{main_header} (Days)"
                            elif "egp/month" in sub_header.lower() or "egp" in sub_header.lower():
                                col_name = f"{main_header} (EGP)"
                            elif len(sub_header) < 30:  # Only add short, meaningful sub-headers
                                col_name = f"{main_header} ({sub_header})"
                    elif sub_header and sub_header != 'nan':
                        col_name = sub_header
                    else:
                        col_name = f"Question_{i+1}"
                
                # Clean and shorten long names
                col_name = col_name.replace('\n', ' ').replace('\r', ' ')
                if len(col_name) > 50:
                    # Apply smart shortening
                    if "benefit" in col_name.lower() and "direct employee" in col_name.lower():
                        col_name = "Benefits (Direct Employee)"
                    elif "deliveries" in col_name.lower() and "day" in col_name.lower():
                        col_name = "Deliveries per Day"
                    elif "income" in col_name.lower() or "salary" in col_name.lower():
                        col_name = "Net Income (EGP)"
                    elif "vehicle" in col_name.lower() and "type" in col_name.lower():
                        col_name = "Vehicle Type"
                    elif "working" in col_name.lower() and "hours" in col_name.lower():
                        col_name = "Working Hours per Day"
                    else:
                        col_name = col_name[:47] + "..."
            
            smart_cols.append(col_name)
        
        # Extract data starting from row 4 (index 3)
        data_df = df_raw.iloc[3:].copy()
        
        # Ensure we have the right number of columns
        if len(smart_cols) != len(data_df.columns):
            # Adjust if mismatch
            smart_cols = smart_cols[:len(data_df.columns)]
            if len(smart_cols) < len(data_df.columns):
                for i in range(len(smart_cols), len(data_df.columns)):
                    smart_cols.append(f"Extra_Col_{i}")
        
        # Ensure all column names are unique
        seen_names = set()
        unique_cols = []
        for col_name in smart_cols:
            original_name = col_name
            counter = 1
            while col_name in seen_names:
                col_name = f"{original_name}_{counter}"
                counter += 1
            seen_names.add(col_name)
            unique_cols.append(col_name)
        
        # Apply column names and clean up
        data_df.columns = unique_cols
        data_df = data_df.reset_index(drop=True)
        data_df = data_df.dropna(how='all')
        
        # Convert obvious numeric columns with better handling of mixed data
        numeric_indicators = ['age', 'year', 'egp', 'days', 'hours', 'deliveries', 'income', 'salary', 'allowance']
        for col in data_df.columns:
            col_lower = col.lower()
            if any(indicator in col_lower for indicator in numeric_indicators):
                try:
                    # Try to convert to numeric, keeping original if it fails
                    numeric_series = pd.to_numeric(data_df[col], errors='coerce')
                    # Only convert if more than 50% of values are valid numbers
                    if numeric_series.count() > len(data_df) * 0.5:
                        data_df[col] = numeric_series
                except:
                    pass
        
        # Handle problematic mixed columns that cause PyArrow issues
        # Aggressively clean the specific problematic column
        for col in data_df.columns:
            try:
                if 'working with your current' in col.lower() or 'how long' in col.lower():
                    # This is the problematic column - clean it aggressively
                    def clean_duration_value(val):
                        if pd.isna(val):
                            return None
                        val_str = str(val).strip()
                        if val_str.lower() in ['nan', 'none', '']:
                            return None
                        # Extract number from mixed text like "14 months" or "5 Years"
                        import re
                        numbers = re.findall(r'\d+\.?\d*', val_str)
                        if numbers:
                            try:
                                return float(numbers[0])
                            except:
                                return val_str
                        return val_str
                    
                    data_df[col] = data_df[col].apply(clean_duration_value)
                
                # Also check for other mixed columns
                elif data_df[col].dtype == 'object':
                    sample_values = data_df[col].dropna().head(10)
                    has_mixed_types = False
                    
                    for val in sample_values:
                        val_str = str(val)
                        if any(pattern in val_str.lower() for pattern in ['months', 'years', 'days']) and any(char.isdigit() for char in val_str):
                            has_mixed_types = True
                            break
                    
                    if has_mixed_types:
                        # Convert to string consistently
                        data_df[col] = data_df[col].astype(str)
                        data_df[col] = data_df[col].replace('nan', None)
            except Exception as e:
                continue
        
        return data_df
        
    except Exception as e:
        st.error(f"Error loading Excel file: {str(e)}")
        return pd.DataFrame()

# ---------- Data Loading ----------
st.subheader("📊 Data Source")

DEFAULT_CSV_PATH = "Vans_data_cleaned.csv"  # Use the cleaned CSV file
DEFAULT_XLSX_PATH = "Vans_data_raw_new.xlsx"  # Use the corrected file
FALLBACK_XLSX_PATH = "Vans data for dashboard.xlsx"  # Keep as fallback
data_choice = st.radio(
    "Choose data source:",
    ["📁 Use included sample file", "📤 Upload your own Excel file"],
    horizontal=True
)

df_all = pd.DataFrame()

if data_choice == "📁 Use included sample file":
    # Try cleaned CSV first (avoids PyArrow issues)
    if os.path.exists(DEFAULT_CSV_PATH):
        try:
            df_all = pd.read_csv(DEFAULT_CSV_PATH)
            if not df_all.empty:
                st.success(f"✅ Loaded clean Vans survey data: {len(df_all):,} respondents, {len(df_all.columns)} questions")
            else:
                df_all = pd.DataFrame()
        except Exception as e:
            st.warning(f"⚠️ Issue loading cleaned CSV: {str(e)}")
            df_all = pd.DataFrame()
    
    # Fallback to Excel if CSV fails
    if df_all.empty and os.path.exists(DEFAULT_XLSX_PATH):
        df_all = load_excel_file(DEFAULT_XLSX_PATH)
        if not df_all.empty:
            st.info(f"✅ Loaded Excel data: {len(df_all):,} respondents, {len(df_all.columns)} questions")
        else:
            st.warning("⚠️ Issue with Excel file, trying fallback...")
            if os.path.exists(FALLBACK_XLSX_PATH):
                df_all = load_excel_file(FALLBACK_XLSX_PATH)
                if not df_all.empty:
                    st.info(f"✅ Loaded fallback data: {len(df_all):,} respondents, {len(df_all.columns)} questions")
    
    # Final fallback
    if df_all.empty:
        st.info("📁 Data files not found. Please upload your own file below.")
        data_choice = "📤 Upload your own Excel file"

if data_choice == "📤 Upload your own Excel file" or df_all.empty:
    uploaded_file = st.file_uploader(
        "Choose Excel (.xlsx) or CSV file",
        type=["xlsx", "csv"],
        help="Upload your Excel or CSV file with delivery/van operation data"
    )
    
    if uploaded_file is not None:
        if uploaded_file.name.endswith('.csv'):
            df_all = pd.read_csv(uploaded_file)
        else:
            data_bytes = io.BytesIO(uploaded_file.read())
            df_all = load_excel_file(data_bytes)
        
        if not df_all.empty:
            st.success(f"✅ File uploaded successfully: {len(df_all):,} records, {len(df_all.columns)} columns")
    else:
        st.info("👆 Please upload an Excel file to continue")
        st.stop()

if df_all.empty:
    st.error("❌ No data available. Please upload a valid Excel file.")
    st.stop()

# Ensure we have valid data
if len(df_all) == 0 or len(df_all.columns) == 0:
    st.error("❌ Invalid data structure. Please check your Excel file.")
    st.stop()

# Clean and prepare data
df_all.columns = [str(c).strip() for c in df_all.columns]

# Remove problematic columns with minimal data
problematic_cols = []
for col in df_all.columns:
    try:
        # Remove if completely empty
        if df_all[col].isna().all() or (df_all[col].astype(str).str.strip() == '').all():
            problematic_cols.append(col)
        # Remove Question_1 specifically if it has very few valid responses
        elif col == 'Question_1':
            valid_responses = df_all[col].dropna()
            valid_responses = valid_responses[valid_responses.astype(str).str.strip() != '']
            if len(valid_responses) < 5:  # Less than 5 valid responses
                problematic_cols.append(col)
        # Remove columns with only 1-2 unique values and mostly empty
        else:
            non_empty = df_all[col].dropna()
            non_empty = non_empty[non_empty.astype(str).str.strip() != '']
            if len(non_empty) < 3 and df_all[col].nunique() <= 2:  # Very sparse data
                problematic_cols.append(col)
    except:
        continue

if problematic_cols:
    df_all = df_all.drop(problematic_cols, axis=1)
    st.info(f"📝 Removed {len(problematic_cols)} sparse/empty columns: {', '.join(problematic_cols[:3])}{'...' if len(problematic_cols) > 3 else ''}")

df_view = df_all.copy()

# ---------- Sidebar Filters ----------
with st.sidebar:
    st.markdown("### 🔍 Data Filters")
    
    # Show data info
    st.info(f"**Total Records:** {len(df_all):,}")
    
    # Categorical filters - find relevant columns dynamically
    potential_filter_cols = []
    for col in df_all.columns:
        col_lower = col.lower()
        if any(keyword in col_lower for keyword in ['company', 'employment', 'area', 'insurance', 'status']):
            try:
                if df_all[col].dtype == 'object' and df_all[col].nunique() < 20:  # Only categorical with reasonable unique values
                    potential_filter_cols.append(col)
            except Exception:
                # If there's an issue accessing the column, skip it
                continue
    
    filter_columns = potential_filter_cols[:4]  # Limit to first 4 relevant columns
    
    for col in filter_columns:
        if col in df_all.columns:
            unique_vals = sorted([str(v) for v in df_all[col].dropna().unique() if pd.notna(v)])
            if unique_vals:
                selected = st.multiselect(
                    f"Filter by {col}:",
                    options=unique_vals,
                    default=unique_vals,
                    key=f"filter_{col}"
                )
                if selected:
                    df_view = df_view[df_view[col].astype(str).isin(selected)]
    
    # Age filter
    if "Age (Years)" in df_all.columns:
        age_col = df_all["Age (Years)"]
        if pd.api.types.is_numeric_dtype(age_col):
            min_age, max_age = int(age_col.min()), int(age_col.max())
            if min_age < max_age:
                age_range = st.slider(
                    "Age Range:",
                    min_value=min_age,
                    max_value=max_age,
                    value=(min_age, max_age),
                    key="age_filter"
                )
                df_view = df_view[
                    (df_view["Age (Years)"] >= age_range[0]) & 
                    (df_view["Age (Years)"] <= age_range[1])
                ]
    
    # Show filtered count
    if len(df_view) != len(df_all):
        st.success(f"**Filtered:** {len(df_view):,} records")

# ---------- Key Performance Indicators ----------
st.subheader("📈 Key Performance Indicators")

kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

# Find relevant columns dynamically
deliveries_col = None
insurance_col = None
income_col = None
employment_col = None
age_col = None

for col in df_view.columns:
    col_lower = col.lower()
    if 'deliveries' in col_lower or 'delivery' in col_lower:
        deliveries_col = col
    elif 'insurance' in col_lower and 'medical' in col_lower:
        insurance_col = col
    elif 'income' in col_lower or 'salary' in col_lower:
        income_col = col
    elif 'employment' in col_lower and 'status' in col_lower:
        employment_col = col
    elif 'age' in col_lower:
        age_col = col

# Column detection complete

# KPI 1: Survey Responses
with kpi_col1:
    st.metric(
        "📊 Total Responses",
        f"{len(df_view):,}",
        delta=f"of {len(df_all):,} total"
    )

# KPI 2: Average Age or Insurance
with kpi_col2:
    if age_col:
        try:
            # More robust age calculation
            age_series = df_view[age_col]
            
            # Convert to numeric if not already (handle any string ages)
            if not pd.api.types.is_numeric_dtype(age_series):
                age_series = pd.to_numeric(age_series, errors='coerce')
            
            # Calculate mean of non-null values
            valid_ages = age_series.dropna()
            
            if len(valid_ages) > 0:
                avg_age = valid_ages.mean()
                st.metric(
                    "👥 Average Age",
                    f"{avg_age:.1f} years"
                )
            else:
                st.metric("👥 Average Age", "No valid data")
        except Exception as e:
            st.metric("👥 Average Age", f"Calculation error")
    elif insurance_col:
        yes_responses = df_view[insurance_col].astype(str).str.contains('Yes|yes', na=False).mean() * 100
        st.metric(
            "🏥 Medical Insurance",
            f"{yes_responses:.1f}% Yes"
        )
    else:
        st.metric("📋 Data Coverage", f"{len(df_view.columns)} questions")

# KPI 3: Deliveries or Income
with kpi_col3:
    if deliveries_col and pd.api.types.is_numeric_dtype(df_view[deliveries_col]):
        avg_deliveries = df_view[deliveries_col].mean()
        st.metric(
            "📦 Avg Deliveries",
            f"{avg_deliveries:.1f}/day"
        )
    elif income_col and pd.api.types.is_numeric_dtype(df_view[income_col]):
        avg_income = df_view[income_col].mean()
        st.metric(
            "💰 Avg Income",
            f"{avg_income:,.0f} EGP"
        )
    else:
        companies = df_view.select_dtypes(include=['object']).iloc[:, 2:5]  # Look at likely company columns
        if not companies.empty:
            unique_companies = companies.iloc[:, 0].nunique()
            st.metric("🏢 Companies", f"{unique_companies}")
        else:
            st.metric("📊 Questions", f"{len(df_view.columns)}")

# KPI 4: Most Common Response
with kpi_col4:
    if employment_col and not df_view[employment_col].empty:
        mode_employment = df_view[employment_col].mode()[0] if len(df_view[employment_col].mode()) > 0 else "N/A"
        count = df_view[employment_col].value_counts().iloc[0] if not df_view[employment_col].value_counts().empty else 0
        st.metric(
            "👥 Top Employment",
            str(mode_employment)[:20],
            delta=f"{count} responses"
        )
    else:
        # Find any categorical column with reasonable distribution
        for col in df_view.select_dtypes(include=['object']).columns:
            if df_view[col].nunique() < 10 and df_view[col].nunique() > 1:
                mode_val = df_view[col].mode()[0] if len(df_view[col].mode()) > 0 else "N/A"
                count = df_view[col].value_counts().iloc[0] if not df_view[col].value_counts().empty else 0
                st.metric(
                    f"📈 Most Common",
                    str(mode_val)[:15],
                    delta=f"{count} responses"
                )
                break
        else:
            st.metric("✅ Data Quality", f"{df_view.notna().sum().sum():,} answers")

# ---------- Interactive Data Analysis ----------
st.subheader("🔍 Interactive Data Analysis")

analysis_tab1, analysis_tab2, analysis_tab3 = st.tabs(["📊 Custom Analysis", "🔖 Quick Presets", "📋 Individual Responses"])

with analysis_tab1:
    st.write("**Create custom data summaries:**")
    
    # Add spacing for better visual separation
    st.write("")
    
    # Get numeric and categorical columns with comprehensive detection
    numeric_cols = []
    categorical_cols = []
    
    for col in df_view.columns:
        try:
            col_lower = col.lower()
            non_null_count = df_view[col].count()
            unique_count = df_view[col].nunique()
            
            # Enhanced numeric detection - include all numeric fields that could be useful for analysis
            if pd.api.types.is_numeric_dtype(df_view[col]) and non_null_count > 0:
                numeric_cols.append(col)
            elif df_view[col].dtype == 'object' and non_null_count > 0:
                # Comprehensive survey field detection - include ALL relevant survey categories
                is_important_field = any(keyword in col_lower for keyword in [
                    # Core demographics and employment
                    'company', 'employment', 'area', 'age', 'education', 'experience',
                    # Benefits and compensation
                    'insurance', 'medical', 'benefit', 'salary', 'income', 'bonus', 'allowance',
                    'incentive', 'overtime', 'holiday', 'leave', 'vacation', 'sick',
                    # Operations and delivery
                    'delivery', 'deliveries', 'vehicle', 'transport', 'fuel', 'maintenance',
                    'route', 'area', 'zone', 'district', 'region', 'location',
                    # Costs and expenses
                    'cost', 'expense', 'fee', 'charge', 'payment', 'fuel', 'gas', 'petrol',
                    'repair', 'service', 'maintenance', 'insurance',
                    # Work conditions and support
                    'support', 'training', 'equipment', 'uniform', 'safety', 'security',
                    'working', 'schedule', 'shift', 'hours', 'time',
                    # Performance and satisfaction
                    'performance', 'rating', 'satisfaction', 'feedback', 'complaint',
                    'issue', 'problem', 'challenge', 'difficulty',
                    # Status and classification
                    'status', 'type', 'category', 'classification', 'level', 'grade',
                    # Communication and technology
                    'phone', 'mobile', 'app', 'system', 'technology', 'communication',
                    # Personal and family
                    'family', 'children', 'dependents', 'married', 'single',
                    # Geographic and demographic
                    'city', 'governorate', 'address', 'residence', 'home',
                    # Survey responses and ratings
                    'yes', 'no', 'agree', 'disagree', 'satisfied', 'dissatisfied',
                    'good', 'bad', 'excellent', 'poor', 'fair'
                ])
                
                # Include if it's important OR has reasonable unique count (more generous limits)
                if is_important_field or (1 <= unique_count <= 50):
                    categorical_cols.append(col)
        except Exception:
            # If there's any issue accessing the column, still try to include it
            try:
                if df_view[col].count() > 0:
                    categorical_cols.append(col)
            except:
                continue
    
    # Also try to convert numeric-looking text columns
    additional_numeric = []
    for col in categorical_cols[:]:  # Use slice copy to avoid modifying during iteration
        try:
            # Try to convert to numeric
            numeric_version = pd.to_numeric(df_view[col], errors='coerce')
            valid_numeric_count = numeric_version.count()
            
            # If more than 50% of values can be converted to numeric, treat as numeric
            if valid_numeric_count > len(df_view) * 0.5:
                additional_numeric.append(col)
                categorical_cols.remove(col)
        except:
            continue
    
    numeric_cols.extend(additional_numeric)
    
    if len(numeric_cols) > 0 and len(categorical_cols) > 0:
        # Enhanced 3-dropdown layout for more detailed analysis
        st.write("**Enhanced Multi-Dimensional Analysis:**")
        
        # First row: Primary analysis settings
        col1, col2, col3 = st.columns([1.2, 1.2, 0.8])
        
        with col1:
            # Primary grouping column
            display_categorical = []
            for col in categorical_cols:
                if len(col) > 30:
                    display_name = col[:27] + "..."
                else:
                    display_name = col
                display_categorical.append(display_name)
            
            selected_idx = st.selectbox(
                "📂 Primary Group by:",
                range(len(categorical_cols) + 1),
                format_func=lambda x: "None" if x == 0 else display_categorical[x-1],
                help="Select the main categorical column to group the analysis by"
            )
            group_by = "None" if selected_idx == 0 else categorical_cols[selected_idx-1]
            
        with col2:
            # Numeric column to analyze
            display_numeric = []
            for col in numeric_cols:
                if len(col) > 30:
                    display_name = col[:27] + "..."
                else:
                    display_name = col
                display_numeric.append(display_name)
            
            analyze_idx = st.selectbox(
                "📊 Analyze:",
                range(len(numeric_cols)),
                format_func=lambda x: display_numeric[x],
                help="Select a numeric column to analyze"
            )
            analyze_col = numeric_cols[analyze_idx]
            
        with col3:
            agg_function = st.selectbox(
                "🔢 Function:", 
                ["mean", "sum", "count", "min", "max", "std"],
                help="Select the aggregation function to apply"
            )
        
        # Second row: Secondary analysis options
        st.write("")
        col4, col5, col6 = st.columns([1.2, 1.2, 0.8])
        
        with col4:
            # Secondary grouping (optional)
            secondary_selected_idx = st.selectbox(
                "📂 Secondary Group by (Optional):",
                range(len(categorical_cols) + 1),
                format_func=lambda x: "None" if x == 0 else display_categorical[x-1],
                help="Select an additional categorical column for cross-tabulation analysis"
            )
            secondary_group_by = "None" if secondary_selected_idx == 0 else categorical_cols[secondary_selected_idx-1]
            
        with col5:
            # Filter options
            filter_options = ["No Filter", "Top 5 Values", "Bottom 5 Values", "Above Average", "Below Average"]
            result_filter = st.selectbox(
                "🔍 Result Filter:",
                filter_options,
                help="Apply filters to the analysis results"
            )
            
        with col6:
            # Chart type selection
            chart_types = ["Bar Chart", "Line Chart", "Scatter Plot", "Box Plot"]
            chart_type = st.selectbox(
                "📈 Chart Type:",
                chart_types,
                help="Select visualization type for the results"
            )
        
        if group_by != "None" and analyze_col:
            try:
                # Ensure the analyze column is properly numeric
                df_analysis = df_view.copy()
                if analyze_col in df_analysis.columns:
                    # Convert to numeric, handling any text values
                    df_analysis[analyze_col] = pd.to_numeric(df_analysis[analyze_col], errors='coerce')
                
                # Remove rows where analyze_col is NaN after conversion
                required_cols = [analyze_col, group_by]
                if secondary_group_by != "None" and secondary_group_by != group_by:
                    required_cols.append(secondary_group_by)
                
                df_analysis = df_analysis.dropna(subset=required_cols)
                
                # Check if we have data after cleaning
                if len(df_analysis) == 0:
                    st.warning(f"⚠️ No valid numeric data found in '{analyze_col}' column after filtering.")
                else:
                    # Perform primary analysis
                    if secondary_group_by != "None" and secondary_group_by != group_by:
                        # Multi-dimensional analysis with secondary grouping
                        if agg_function == "mean":
                            result = df_analysis.groupby([group_by, secondary_group_by])[analyze_col].mean().reset_index()
                        elif agg_function == "sum":
                            result = df_analysis.groupby([group_by, secondary_group_by])[analyze_col].sum().reset_index()
                        elif agg_function == "count":
                            result = df_analysis.groupby([group_by, secondary_group_by])[analyze_col].count().reset_index()
                        elif agg_function == "min":
                            result = df_analysis.groupby([group_by, secondary_group_by])[analyze_col].min().reset_index()
                        elif agg_function == "max":
                            result = df_analysis.groupby([group_by, secondary_group_by])[analyze_col].max().reset_index()
                        else:  # std
                            result = df_analysis.groupby([group_by, secondary_group_by])[analyze_col].std().reset_index()
                        
                        result.columns = [group_by, secondary_group_by, f"{agg_function.title()} of {analyze_col}"]
                        
                    else:
                        # Single dimension analysis
                        if agg_function == "mean":
                            result = df_analysis.groupby(group_by)[analyze_col].mean().reset_index()
                        elif agg_function == "sum":
                            result = df_analysis.groupby(group_by)[analyze_col].sum().reset_index()
                        elif agg_function == "count":
                            result = df_analysis.groupby(group_by)[analyze_col].count().reset_index()
                        elif agg_function == "min":
                            result = df_analysis.groupby(group_by)[analyze_col].min().reset_index()
                        elif agg_function == "max":
                            result = df_analysis.groupby(group_by)[analyze_col].max().reset_index()
                        else:  # std
                            result = df_analysis.groupby(group_by)[analyze_col].std().reset_index()
                        
                        result.columns = [group_by, f"{agg_function.title()} of {analyze_col}"]
                    
                    # Apply result filters
                    if result_filter != "No Filter" and len(result) > 0:
                        value_col = result.columns[-1]  # Last column is the calculated value
                        if result_filter == "Top 5 Values":
                            result = result.nlargest(5, value_col)
                        elif result_filter == "Bottom 5 Values":
                            result = result.nsmallest(5, value_col)
                        elif result_filter == "Above Average":
                            avg_val = result[value_col].mean()
                            result = result[result[value_col] > avg_val]
                        elif result_filter == "Below Average":
                            avg_val = result[value_col].mean()
                            result = result[result[value_col] < avg_val]
                    
                    # Debug info
                    if secondary_group_by != "None" and secondary_group_by != group_by:
                        st.caption(f"📊 Multi-dimensional Analysis: {len(df_analysis)} records → {len(result)} combinations")
                    else:
                        st.caption(f"📊 Analysis: {len(df_analysis)} records → {len(result)} groups")
                    
                    # Add some spacing for better alignment
                    st.write("")
                    
                    # Display results in improved 3-column layout
                    col1, col2, col3 = st.columns([1.2, 1.8, 1])
                    
                    with col1:
                        st.write("**📊 Results Table**")
                        # Add padding to align with other sections
                        st.write("")
                        st.dataframe(result, use_container_width=True, height=280)
                    
                    with col2:
                        if len(result) > 0:
                            # Get the value column (last column)
                            y_col = result.columns[-1]
                            
                            # Create shorter, cleaner title to prevent cramming
                            short_analyze_col = analyze_col[:20] + "..." if len(analyze_col) > 20 else analyze_col
                            short_group_by = group_by[:15] + "..." if len(group_by) > 15 else group_by
                            
                            st.write("**📈 Visualization**")
                            # Add padding for alignment
                            st.write("")
                            
                            # Handle multi-dimensional vs single-dimensional visualization
                            if secondary_group_by != "None" and secondary_group_by != group_by:
                                # Multi-dimensional chart
                                if chart_type == "Bar Chart":
                                    fig = px.bar(
                                        result,
                                        x=group_by,
                                        y=y_col,
                                        color=secondary_group_by,
                                        title=f"{agg_function.title()} of {short_analyze_col}<br>by {short_group_by} & {secondary_group_by[:15]}",
                                        barmode='group'
                                    )
                                elif chart_type == "Line Chart":
                                    fig = px.line(
                                        result,
                                        x=group_by,
                                        y=y_col,
                                        color=secondary_group_by,
                                        title=f"{agg_function.title()} of {short_analyze_col}<br>by {short_group_by} & {secondary_group_by[:15]}",
                                        markers=True
                                    )
                                else:  # Default to bar for multi-dimensional
                                    fig = px.bar(
                                        result,
                                        x=group_by,
                                        y=y_col,
                                        color=secondary_group_by,
                                        title=f"{agg_function.title()} of {short_analyze_col}<br>by {short_group_by} & {secondary_group_by[:15]}",
                                        barmode='group'
                                    )
                            else:
                                # Single-dimensional chart with different chart types
                                if chart_type == "Bar Chart":
                                    fig = px.bar(
                                        result,
                                        x=group_by,
                                        y=y_col,
                                        title=f"{agg_function.title()} of {short_analyze_col}<br>by {short_group_by}",
                                        color=y_col,
                                        color_continuous_scale="viridis",
                                        text=y_col
                                    )
                                elif chart_type == "Line Chart":
                                    fig = px.line(
                                        result,
                                        x=group_by,
                                        y=y_col,
                                        title=f"{agg_function.title()} of {short_analyze_col}<br>by {short_group_by}",
                                        markers=True
                                    )
                                elif chart_type == "Scatter Plot":
                                    # For scatter, use index as x if only one grouping
                                    fig = px.scatter(
                                        result,
                                        x=group_by,
                                        y=y_col,
                                        title=f"{agg_function.title()} of {short_analyze_col}<br>by {short_group_by}",
                                        size=y_col,
                                        color=y_col
                                    )
                                else:  # Box Plot - need original data
                                    try:
                                        fig = px.box(
                                            df_analysis,
                                            x=group_by,
                                            y=analyze_col,
                                            title=f"Distribution of {short_analyze_col}<br>by {short_group_by}"
                                        )
                                    except:
                                        # Fallback to bar chart if box plot fails
                                        fig = px.bar(
                                            result,
                                            x=group_by,
                                            y=y_col,
                                            title=f"{agg_function.title()} of {short_analyze_col}<br>by {short_group_by}",
                                            color=y_col,
                                            color_continuous_scale="viridis"
                                        )
                            
                            # Common formatting for all chart types
                            if chart_type == "Bar Chart" and secondary_group_by == "None":
                                # Add text labels for single-dimension bar charts
                                if agg_function in ["mean", "std"]:
                                    fig.update_traces(
                                        texttemplate='%{text:.2f}',
                                        textposition='outside',
                                        textfont_size=10
                                    )
                                else:
                                    fig.update_traces(
                                        texttemplate='%{text:.0f}',
                                        textposition='outside', 
                                        textfont_size=10
                                    )
                            
                            # Update layout for better appearance
                            fig.update_layout(
                                xaxis_tickangle=-45,
                                yaxis_title=f"{agg_function.title()} Value",
                                title_font_size=14,
                                margin=dict(t=60, b=80, l=60, r=20),
                                height=320,
                                xaxis_title_font_size=12,
                                yaxis_title_font_size=12
                            )
                            
                            # Handle long category names
                            fig.update_xaxes(
                                tickangle=-45,
                                tickfont_size=10,
                                title_standoff=25
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("No data available for the selected combination.")
                    
                    with col3:
                        st.write("**📋 Key Statistics**")
                        # Add padding for alignment with other sections
                        st.write("")
                        
                        if len(result) > 0:
                            y_col = f"{agg_function.title()} of {analyze_col}"
                            
                            # Calculate and display key statistics
                            values = result[y_col].dropna()
                            
                            if len(values) > 0:
                                # Overall statistics
                                if agg_function == "mean":
                                    overall_stat = values.mean()
                                    stat_label = "Overall Average"
                                elif agg_function == "sum":
                                    overall_stat = values.sum()
                                    stat_label = "Grand Total"
                                elif agg_function == "count":
                                    overall_stat = values.sum()
                                    stat_label = "Total Count"
                                elif agg_function == "min":
                                    overall_stat = values.min()
                                    stat_label = "Minimum Value"
                                elif agg_function == "max":
                                    overall_stat = values.max()
                                    stat_label = "Maximum Value"
                                else:  # std
                                    overall_stat = values.mean()
                                    stat_label = "Average Std Dev"
                                
                                # Display key metrics
                                if agg_function in ["mean", "std"]:
                                    st.metric(stat_label, f"{overall_stat:.2f}")
                                else:
                                    st.metric(stat_label, f"{overall_stat:.0f}")
                                
                                # Additional insights
                                st.metric("Groups Found", len(result))
                                
                                if len(values) > 1:
                                    highest_idx = values.idxmax()
                                    lowest_idx = values.idxmin()
                                    
                                    highest_group = result.loc[highest_idx, group_by]
                                    lowest_group = result.loc[lowest_idx, group_by]
                                    
                                    st.write("**🏆 Highest:**")
                                    st.write(f"{str(highest_group)[:15]}...")
                                    if agg_function in ["mean", "std"]:
                                        st.write(f"Value: {values[highest_idx]:.2f}")
                                    else:
                                        st.write(f"Value: {values[highest_idx]:.0f}")
                                    
                                    st.write("**📉 Lowest:**")
                                    st.write(f"{str(lowest_group)[:15]}...")
                                    if agg_function in ["mean", "std"]:
                                        st.write(f"Value: {values[lowest_idx]:.2f}")
                                    else:
                                        st.write(f"Value: {values[lowest_idx]:.0f}")
                                
                                # Range information
                                if len(values) > 1:
                                    range_val = values.max() - values.min()
                                    if agg_function in ["mean", "std"]:
                                        st.metric("Range", f"{range_val:.2f}")
                                    else:
                                        st.metric("Range", f"{range_val:.0f}")
                            else:
                                st.info("No statistics available")
                        else:
                            st.info("Select analysis options to view statistics")
                    
            except Exception as e:
                st.error(f"Analysis error: {str(e)}")
    else:
        if len(numeric_cols) == 0:
            st.info("📊 No numeric columns found for analysis. Upload data with numeric values (age, income, etc.)")
        elif len(categorical_cols) == 0:
            st.info("📂 No categorical columns found for grouping. Upload data with text categories (company, status, etc.)")
        else:
            st.info("Need both numeric and categorical columns for analysis")

with analysis_tab2:
    # Generate comprehensive preset options based on available data
    preset_options = ["None"]
    
    # Core employment and demographic analysis
    employment_presets = [
        "Employment Status × Medical Insurance",
        "Company × Employment Status", 
        "Age Groups × Employment Status",
        "Education Level × Employment Status",
        "Experience × Employment Status"
    ]
    
    # Financial and compensation analysis
    financial_presets = [
        "Company × Average Income/Salary",
        "Employment Status × Average Income",
        "Areas Covered × Average Income",
        "Experience × Income Analysis",
        "Fuel Costs by Company",
        "Maintenance Costs by Vehicle Type",
        "Insurance Costs Analysis"
    ]
    
    # Operational and delivery analysis
    operational_presets = [
        "Company × Average Deliveries",
        "Employment Status × Deliveries per Day",
        "Areas Coverage × Delivery Performance",
        "Vehicle Type × Delivery Efficiency",
        "Working Hours × Delivery Count",
        "Route Analysis by Region"
    ]
    
    # Benefits and support analysis
    benefits_presets = [
        "Benefits Package by Company",
        "Medical Insurance Coverage Analysis",
        "Training Support by Employment Status",
        "Overtime Policies × Companies",
        "Holiday/Leave Benefits Analysis",
        "Safety Equipment Provision"
    ]
    
    # Satisfaction and performance analysis
    satisfaction_presets = [
        "Job Satisfaction by Company",
        "Performance Ratings Analysis",
        "Work-Life Balance Assessment",
        "Support Systems Effectiveness",
        "Communication Quality Analysis"
    ]
    
    # Cost and expense analysis
    cost_presets = [
        "Fuel Expenses by Company",
        "Maintenance Costs Breakdown",
        "Operating Expenses Analysis",
        "Cost per Delivery Analysis",
        "Expense Categories Comparison"
    ]
    
    # Combine all presets
    all_presets = (
        employment_presets + financial_presets + operational_presets + 
        benefits_presets + satisfaction_presets + cost_presets
    )
    preset_options.extend(all_presets)
    
    selected_preset = st.selectbox("Select comprehensive preset analysis:", preset_options)
    
    if selected_preset != "None":
        # Try to find matching columns for the selected preset
        preset_executed = False
        
        # Employment and demographics
        if "Employment Status × Medical Insurance" == selected_preset:
            emp_col = next((col for col in df_view.columns if "employment" in col.lower()), None)
            ins_col = next((col for col in df_view.columns if "insurance" in col.lower() and "medical" in col.lower()), None)
            if emp_col and ins_col:
                try:
                    crosstab = pd.crosstab(df_view[emp_col], df_view[ins_col], margins=True)
                    st.dataframe(crosstab, use_container_width=True)
                    preset_executed = True
                except Exception as e:
                    st.error(f"Analysis error: {str(e)}")
        
        elif "Company × Average Deliveries" == selected_preset:
            company_col = next((col for col in df_view.columns if "company" in col.lower()), None)
            delivery_col = next((col for col in df_view.columns if "deliver" in col.lower() and pd.api.types.is_numeric_dtype(df_view[col])), None)
            if company_col and delivery_col:
                try:
                    company_deliveries = df_view.groupby(company_col)[delivery_col].mean().reset_index()
                    st.dataframe(company_deliveries, use_container_width=True)
                    fig = px.bar(company_deliveries, x=company_col, y=delivery_col, 
                               title=f"Average {delivery_col} by {company_col}")
                    st.plotly_chart(fig, use_container_width=True)
                    preset_executed = True
                except Exception as e:
                    st.error(f"Analysis error: {str(e)}")
        
        elif "Fuel Costs by Company" == selected_preset:
            company_col = next((col for col in df_view.columns if "company" in col.lower()), None)
            fuel_col = next((col for col in df_view.columns if "fuel" in col.lower() and pd.api.types.is_numeric_dtype(df_view[col])), None)
            if company_col and fuel_col:
                try:
                    fuel_analysis = df_view.groupby(company_col)[fuel_col].agg(['mean', 'sum', 'count']).reset_index()
                    fuel_analysis.columns = [company_col, 'Average Fuel Cost', 'Total Fuel Cost', 'Count']
                    st.dataframe(fuel_analysis, use_container_width=True)
                    fig = px.bar(fuel_analysis, x=company_col, y='Average Fuel Cost',
                               title="Average Fuel Costs by Company")
                    st.plotly_chart(fig, use_container_width=True)
                    preset_executed = True
                except Exception as e:
                    st.error(f"Analysis error: {str(e)}")
        
        elif "Age Groups × Employment Status" == selected_preset:
            age_col = next((col for col in df_view.columns if "age" in col.lower() and pd.api.types.is_numeric_dtype(df_view[col])), None)
            emp_col = next((col for col in df_view.columns if "employment" in col.lower()), None)
            if age_col and emp_col:
                try:
                    # Create age groups
                    df_temp = df_view.copy()
                    df_temp['Age Group'] = pd.cut(df_temp[age_col], bins=[0, 25, 35, 45, 55, 100], 
                                                labels=['18-25', '26-35', '36-45', '46-55', '55+'])
                    crosstab = pd.crosstab(df_temp['Age Group'], df_temp[emp_col], margins=True)
                    st.dataframe(crosstab, use_container_width=True)
                    preset_executed = True
                except Exception as e:
                    st.error(f"Analysis error: {str(e)}")
        
        # Generic fallback for other presets
        elif not preset_executed:
            # Try to extract analysis type from preset name
            if "×" in selected_preset or "by" in selected_preset.lower():
                # Extract potential column keywords from preset name
                preset_words = selected_preset.lower().replace("×", " ").replace("by", " ").split()
                potential_cols = []
                for word in preset_words:
                    matching_cols = [col for col in df_view.columns if word in col.lower() or any(keyword in col.lower() for keyword in [word])]
                    potential_cols.extend(matching_cols)
                
                if len(potential_cols) >= 2:
                    # Try basic cross-tabulation or groupby analysis
                    try:
                        col1, col2 = potential_cols[0], potential_cols[1]
                        if df_view[col1].dtype == 'object' and df_view[col2].dtype == 'object':
                            # Cross-tabulation for categorical data
                            crosstab = pd.crosstab(df_view[col1], df_view[col2], margins=True)
                            st.dataframe(crosstab, use_container_width=True)
                            preset_executed = True
                        elif df_view[col1].dtype == 'object' and pd.api.types.is_numeric_dtype(df_view[col2]):
                            # Group by analysis
                            grouped = df_view.groupby(col1)[col2].agg(['mean', 'count']).reset_index()
                            st.dataframe(grouped, use_container_width=True)
                            fig = px.bar(grouped, x=col1, y='mean', title=f"Average {col2} by {col1}")
                            st.plotly_chart(fig, use_container_width=True)
                            preset_executed = True
                    except Exception as e:
                        st.error(f"Analysis error: {str(e)}")
        
        if not preset_executed:
            st.info(f"📊 Preset '{selected_preset}' requires specific data columns that may not be available in your dataset. Try the Custom Analysis tab for flexible analysis options.")

with analysis_tab3:
    st.write("**View individual survey responses with filtering:**")
    
    # Add response-level filters
    col1, col2, col3 = st.columns(3)
    
    # Get filterable columns (include categorical, numeric ranges, and important survey fields)
    filterable_cols = []
    numeric_range_cols = []
    
    for col in df_view.columns:
        try:
            col_lower = col.lower()
            unique_count = df_view[col].nunique()
            non_null_count = df_view[col].count()
            
            # Always include key survey fields regardless of unique count
            is_key_field = any(keyword in col_lower for keyword in [
                'company', 'employment', 'area', 'age', 'insurance', 'status',
                'fuel', 'cost', 'expense', 'income', 'salary', 'benefit',
                'delivery', 'maintenance', 'vehicle', 'transport', 'overtime',
                'leave', 'holiday', 'incentive', 'bonus', 'education', 'experience'
            ])
            
            if df_view[col].dtype == 'object':
                # Include categorical fields with reasonable unique values OR key survey fields
                if (2 <= unique_count <= 30) or (is_key_field and unique_count <= 50):
                    filterable_cols.append(col)
            elif pd.api.types.is_numeric_dtype(df_view[col]) and non_null_count > 0:
                # Include numeric fields for range filtering
                if is_key_field or any(keyword in col_lower for keyword in [
                    'age', 'cost', 'expense', 'income', 'salary', 'delivery', 'hour', 'day', 'year'
                ]):
                    numeric_range_cols.append(col)
        except Exception as e:
            continue
    
    active_filters = {}
    active_numeric_filters = {}
    
    # Combine all filterable columns for selection
    all_filter_options = filterable_cols + [f"{col} (Range)" for col in numeric_range_cols]
    
    if len(all_filter_options) > 0:
        with col1:
            filter_col1 = st.selectbox("Filter by:", ["None"] + all_filter_options, key="response_filter1")
            if filter_col1 != "None":
                if filter_col1.endswith(" (Range)"):
                    # Numeric range filter
                    actual_col = filter_col1.replace(" (Range)", "")
                    col_data = df_view[actual_col].dropna()
                    if len(col_data) > 0:
                        min_val, max_val = float(col_data.min()), float(col_data.max())
                        if min_val < max_val:
                            range_vals = st.slider(
                                f"Select {actual_col} range:",
                                min_value=min_val,
                                max_value=max_val,
                                value=(min_val, max_val),
                                key="range1"
                            )
                            active_numeric_filters[actual_col] = range_vals
                else:
                    # Categorical filter
                    unique_vals1 = sorted(df_view[filter_col1].dropna().astype(str).unique())
                    selected_vals1 = st.multiselect(f"Select {filter_col1}:", unique_vals1, default=unique_vals1, key="values1")
                    if selected_vals1:
                        active_filters[filter_col1] = selected_vals1
        
        with col2:
            if len(all_filter_options) > 1:
                used_cols = [filter_col1] if filter_col1 != "None" else []
                remaining_options = [opt for opt in all_filter_options if opt not in used_cols]
                filter_col2 = st.selectbox("Also filter by:", ["None"] + remaining_options, key="response_filter2")
                if filter_col2 != "None":
                    if filter_col2.endswith(" (Range)"):
                        # Numeric range filter
                        actual_col = filter_col2.replace(" (Range)", "")
                        col_data = df_view[actual_col].dropna()
                        if len(col_data) > 0:
                            min_val, max_val = float(col_data.min()), float(col_data.max())
                            if min_val < max_val:
                                range_vals = st.slider(
                                    f"Select {actual_col} range:",
                                    min_value=min_val,
                                    max_value=max_val,
                                    value=(min_val, max_val),
                                    key="range2"
                                )
                                active_numeric_filters[actual_col] = range_vals
                    else:
                        # Categorical filter
                        unique_vals2 = sorted(df_view[filter_col2].dropna().astype(str).unique())
                        selected_vals2 = st.multiselect(f"Select {filter_col2}:", unique_vals2, default=unique_vals2, key="values2")
                        if selected_vals2:
                            active_filters[filter_col2] = selected_vals2
        
        with col3:
            if len(all_filter_options) > 2:
                used_cols = [col for col in [filter_col1, filter_col2] if col != "None"]
                remaining_options = [opt for opt in all_filter_options if opt not in used_cols]
                filter_col3 = st.selectbox("Additional filter:", ["None"] + remaining_options, key="response_filter3")
                if filter_col3 != "None":
                    if filter_col3.endswith(" (Range)"):
                        # Numeric range filter
                        actual_col = filter_col3.replace(" (Range)", "")
                        col_data = df_view[actual_col].dropna()
                        if len(col_data) > 0:
                            min_val, max_val = float(col_data.min()), float(col_data.max())
                            if min_val < max_val:
                                range_vals = st.slider(
                                    f"Select {actual_col} range:",
                                    min_value=min_val,
                                    max_value=max_val,
                                    value=(min_val, max_val),
                                    key="range3"
                                )
                                active_numeric_filters[actual_col] = range_vals
                    else:
                        # Categorical filter
                        unique_vals3 = sorted(df_view[filter_col3].dropna().astype(str).unique())
                        selected_vals3 = st.multiselect(f"Select {filter_col3}:", unique_vals3, default=unique_vals3, key="values3")
                        if selected_vals3:
                            active_filters[filter_col3] = selected_vals3
    
    # Apply filters to get filtered responses
    filtered_responses = df_view.copy()
    
    # Apply categorical filters
    for filter_col, filter_vals in active_filters.items():
        filtered_responses = filtered_responses[filtered_responses[filter_col].astype(str).isin(filter_vals)]
    
    # Apply numeric range filters
    for filter_col, (min_val, max_val) in active_numeric_filters.items():
        filtered_responses = filtered_responses[
            (filtered_responses[filter_col] >= min_val) & 
            (filtered_responses[filter_col] <= max_val)
        ]
    
    # Display filtering summary
    st.write(f"**Showing {len(filtered_responses)} of {len(df_view)} survey responses**")
    
    if len(active_filters) > 0 or len(active_numeric_filters) > 0:
        filter_parts = []
        
        # Categorical filters
        for col, vals in active_filters.items():
            filter_parts.append(f"{col}: {len(vals)} selected")
        
        # Numeric range filters  
        for col, (min_val, max_val) in active_numeric_filters.items():
            filter_parts.append(f"{col}: {min_val:.1f}-{max_val:.1f}")
        
        if filter_parts:
            filter_summary = ", ".join(filter_parts)
            st.caption(f"Active filters: {filter_summary}")
    
    # Column selection for display
    st.write("**Select columns to display:**")
    
    # Smart default column selection - include more survey fields
    default_cols = []
    priority_keywords = ['respondent', 'age', 'company', 'employment', 'area']
    secondary_keywords = ['income', 'deliveries', 'fuel', 'cost', 'expense', 'insurance', 'benefit', 'salary']
    
    # First pass: high priority columns
    for col in filtered_responses.columns:
        col_lower = col.lower()
        if any(keyword in col_lower for keyword in priority_keywords):
            default_cols.append(col)
    
    # Second pass: secondary important columns
    for col in filtered_responses.columns:
        if col not in default_cols:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in secondary_keywords):
                default_cols.append(col)
    
    # Limit to first 10 columns to avoid overwhelming display
    default_cols = default_cols[:10]
    
    selected_columns = st.multiselect(
        "Choose columns to show in responses:",
        options=filtered_responses.columns.tolist(),
        default=default_cols if default_cols else filtered_responses.columns.tolist()[:6],
        key="response_columns"
    )
    
    if selected_columns:
        # Display options
        col1, col2, col3 = st.columns(3)
        with col1:
            page_size = st.selectbox("Responses per page:", [10, 25, 50, 100], index=1)
        with col2:
            show_index = st.checkbox("Show row numbers", value=True)
        with col3:
            sort_column = st.selectbox("Sort by:", ["None"] + selected_columns)
        
        # Prepare display dataframe
        display_df = filtered_responses[selected_columns].copy()
        
        # Apply sorting
        if sort_column != "None":
            try:
                display_df = display_df.sort_values(sort_column)
            except:
                pass
        
        # Pagination
        total_responses = len(display_df)
        total_pages = (total_responses - 1) // page_size + 1 if total_responses > 0 else 0
        
        if total_pages > 1:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                page = st.selectbox(f"Page (1 to {total_pages}):", range(1, total_pages + 1))
            
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            display_df = display_df.iloc[start_idx:end_idx]
        
        # Display the responses
        if len(display_df) > 0:
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=not show_index
            )
            
            # Download option for filtered responses
            csv = filtered_responses.to_csv(index=False)
            st.download_button(
                label=f"📥 Download Filtered Responses ({len(filtered_responses)} records)",
                data=csv,
                file_name=f"survey_responses_filtered_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No responses match the current filters.")
    else:
        st.info("Please select at least one column to display.")

# ---------- Visualizations ----------
st.subheader("📊 Data Visualizations")

viz_tab1, viz_tab2, viz_tab3 = st.tabs(["📈 Distribution Charts", "📊 Comparison Charts", "🗺️ Correlation Analysis"])

with viz_tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        # Employment Status Distribution
        employment_col = None
        for col in df_view.columns:
            if "employment" in col.lower() and not col.endswith(('_1', '_2', '_3', '_4', '_5', '_6')):
                employment_col = col
                break
        
        if employment_col and len(df_view[employment_col].dropna()) > 0:
            try:
                fig = px.pie(
                    df_view,
                    names=employment_col,
                    title="Employment Status Distribution",
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error creating employment chart: {str(e)}")
        else:
            st.info("No valid employment status data found for visualization")
    
    with col2:
        # Age Distribution
        age_col = None
        for col in df_view.columns:
            if "age" in col.lower() and not col.endswith(('_1', '_2', '_3', '_4', '_5', '_6')):
                age_col = col
                break
        
        if age_col and pd.api.types.is_numeric_dtype(df_view[age_col]):
            try:
                fig = px.histogram(
                    df_view,
                    x=age_col,
                    nbins=15,
                    title="Age Distribution",
                    color_discrete_sequence=["#667eea"]
                )
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error creating age chart: {str(e)}")
        else:
            st.info("No valid age data found for visualization")

with viz_tab2:
    st.write("**Compare key metrics across different dimensions:**")
    st.write("")
    
    # Enhanced comparison charts with multiple options
    chart_row1_col1, chart_row1_col2 = st.columns(2)
    
    with chart_row1_col1:
        # Fix deliveries by company detection
        company_col = None
        deliveries_col = None
        
        # Better column detection for company
        for col in df_view.columns:
            if "company" in col.lower():
                company_col = col
                break
        
        # Better column detection for deliveries - look for the actual column name pattern
        for col in df_view.columns:
            col_lower = col.lower()
            if ("deliveries" in col_lower and "per day" in col_lower) or ("average" in col_lower and "deliveries" in col_lower):
                deliveries_col = col
                break
        
        if company_col and deliveries_col:
            try:
                # Convert to numeric for analysis
                df_chart = df_view.copy()
                df_chart[deliveries_col] = pd.to_numeric(df_chart[deliveries_col], errors='coerce')
                
                # Remove NaN values
                df_chart = df_chart.dropna(subset=[deliveries_col, company_col])
                
                if len(df_chart) > 0:
                    fig = px.box(
                        df_chart,
                        x=company_col,
                        y=deliveries_col,
                        title="Daily Deliveries by Company",
                        color=company_col
                    )
                    fig.update_layout(xaxis_tickangle=-45, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No valid deliveries data after cleaning")
            except Exception as e:
                st.error(f"Error creating deliveries chart: {str(e)}")
        else:
            st.info("Deliveries or company data not found for comparison")
    
    with chart_row1_col2:
        # Working Hours by Employment Status
        employment_col = None
        hours_col = None
        
        for col in df_view.columns:
            if "employment" in col.lower() and "status" in col.lower():
                employment_col = col
                break
        
        for col in df_view.columns:
            col_lower = col.lower()
            if ("working" in col_lower and "hours" in col_lower) or ("hours" in col_lower and "per day" in col_lower):
                hours_col = col
                break
        
        if employment_col and hours_col:
            try:
                df_chart = df_view.copy()
                df_chart[hours_col] = pd.to_numeric(df_chart[hours_col], errors='coerce')
                df_chart = df_chart.dropna(subset=[hours_col, employment_col])
                
                if len(df_chart) > 0:
                    fig = px.violin(
                        df_chart,
                        x=employment_col,
                        y=hours_col,
                        title="Working Hours by Employment Status",
                        color=employment_col
                    )
                    fig.update_layout(xaxis_tickangle=-45, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No valid working hours data after cleaning")
            except Exception as e:
                st.error(f"Error creating working hours chart: {str(e)}")
        else:
            st.info("Working hours or employment data not found")
    
    # Second row of comparison charts
    chart_row2_col1, chart_row2_col2 = st.columns(2)
    
    with chart_row2_col1:
        # Fuel Costs by Company
        fuel_cost_col = None
        
        for col in df_view.columns:
            col_lower = col.lower()
            if ("fuel" in col_lower and "cost" in col_lower) or ("fuel" in col_lower and "egp" in col_lower):
                fuel_cost_col = col
                break
        
        if company_col and fuel_cost_col:
            try:
                df_chart = df_view.copy()
                df_chart[fuel_cost_col] = pd.to_numeric(df_chart[fuel_cost_col], errors='coerce')
                df_chart = df_chart.dropna(subset=[fuel_cost_col, company_col])
                
                if len(df_chart) > 0:
                    fig = px.bar(
                        df_chart.groupby(company_col)[fuel_cost_col].mean().reset_index(),
                        x=company_col,
                        y=fuel_cost_col,
                        title="Average Monthly Fuel Costs by Company",
                        color=company_col
                    )
                    fig.update_layout(xaxis_tickangle=-45, showlegend=False)
                    fig.update_traces(texttemplate='%{y:.0f} EGP', textposition='outside')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No valid fuel cost data after cleaning")
            except Exception as e:
                st.error(f"Error creating fuel costs chart: {str(e)}")
        else:
            st.info("Fuel cost data not found for comparison")
    
    with chart_row2_col2:
        # Vehicle Type Distribution
        vehicle_col = None
        
        for col in df_view.columns:
            col_lower = col.lower()
            if "vehicle" in col_lower and "type" in col_lower:
                vehicle_col = col
                break
        
        if vehicle_col:
            try:
                df_chart = df_view.dropna(subset=[vehicle_col])
                if len(df_chart) > 0:
                    vehicle_counts = df_chart[vehicle_col].value_counts()
                    fig = px.pie(
                        values=vehicle_counts.values,
                        names=vehicle_counts.index,
                        title="Vehicle Type Distribution"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No valid vehicle type data")
            except Exception as e:
                st.error(f"Error creating vehicle type chart: {str(e)}")
        else:
            st.info("Vehicle type data not found")
    
    # Third row - Additional comparison charts
    chart_row3_col1, chart_row3_col2 = st.columns(2)
    
    with chart_row3_col1:
        # Success Rate by Company
        success_rate_col = None
        
        for col in df_view.columns:
            col_lower = col.lower()
            if ("success" in col_lower and "rate" in col_lower) or ("delivery" in col_lower and "success" in col_lower):
                success_rate_col = col
                break
        
        if company_col and success_rate_col:
            try:
                df_chart = df_view.copy()
                df_chart[success_rate_col] = pd.to_numeric(df_chart[success_rate_col], errors='coerce')
                df_chart = df_chart.dropna(subset=[success_rate_col, company_col])
                
                if len(df_chart) > 0:
                    avg_success = df_chart.groupby(company_col)[success_rate_col].mean().reset_index()
                    fig = px.bar(
                        avg_success,
                        x=company_col,
                        y=success_rate_col,
                        title="Average Delivery Success Rate by Company",
                        color=company_col
                    )
                    fig.update_layout(xaxis_tickangle=-45, showlegend=False)
                    fig.update_traces(texttemplate='%{y:.1f}%', textposition='outside')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No valid success rate data after cleaning")
            except Exception as e:
                st.error(f"Error creating success rate chart: {str(e)}")
        else:
            st.info("Success rate data not found for comparison")
    
    with chart_row3_col2:
        # Age Distribution by Company
        age_col = None
        
        for col in df_view.columns:
            if "age" in col.lower():
                age_col = col
                break
        
        if company_col and age_col:
            try:
                df_chart = df_view.copy()
                df_chart[age_col] = pd.to_numeric(df_chart[age_col], errors='coerce')
                df_chart = df_chart.dropna(subset=[age_col, company_col])
                
                if len(df_chart) > 0:
                    fig = px.box(
                        df_chart,
                        x=company_col,
                        y=age_col,
                        title="Age Distribution by Company",
                        color=company_col
                    )
                    fig.update_layout(xaxis_tickangle=-45, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No valid age data after cleaning")
            except Exception as e:
                st.error(f"Error creating age distribution chart: {str(e)}")
        else:
            st.info("Age data not found for comparison")

with viz_tab3:
    # Correlation heatmap
    numeric_columns = df_view.select_dtypes(include=[np.number]).columns
    if len(numeric_columns) > 1:
        correlation_matrix = df_view[numeric_columns].corr()
        
        fig = px.imshow(
            correlation_matrix,
            title="Correlation Matrix",
            color_continuous_scale="RdBu",
            aspect="auto"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Need at least 2 numeric columns for correlation analysis")

# ---------- Data Export and Summary ----------
st.subheader("📋 Data Summary & Export")

summary_col1, summary_col2 = st.columns([2, 1])

with summary_col1:
    # Data summary statistics
    if not df_view.empty:
        st.write("**Statistical Summary:**")
        numeric_summary = df_view.describe()
        st.dataframe(numeric_summary, use_container_width=True)

with summary_col2:
    st.write("**Dataset Information:**")
    st.metric("📊 Total Records", f"{len(df_view):,}")
    st.metric("📋 Columns", len(df_view.columns))
    if len(df_all) > 0:
        st.metric("🔍 Filtered Data", f"{(len(df_view)/len(df_all)*100):.1f}%")
    else:
        st.metric("🔍 Filtered Data", "100%")
    
    # Download button for filtered data
    csv = df_view.to_csv(index=False)
    st.download_button(
        label="📥 Download Filtered Data (CSV)",
        data=csv,
        file_name=f"vans_data_filtered_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )

# ---------- Raw Data Viewer ----------
with st.expander("🔍 View Raw Data", expanded=False):
    st.dataframe(df_view, use_container_width=True)
    
    # Column information
    try:
        col_info = pd.DataFrame({
            'Column Name': df_view.columns,
            'Data Type': df_view.dtypes.astype(str),
            'Non-Null Count': df_view.count(),
            'Null Count': df_view.isnull().sum(),
            'Unique Values': df_view.nunique()
        })
    except Exception:
        # Fallback column info if dtypes fails
        col_info = pd.DataFrame({
            'Column Name': df_view.columns,
            'Data Type': ['Mixed' for _ in df_view.columns],
            'Non-Null Count': [len(df_view) for _ in df_view.columns],
            'Null Count': [0 for _ in df_view.columns],
            'Unique Values': [len(df_view) for _ in df_view.columns]
        })
    
    st.write("**Column Information:**")
    st.dataframe(col_info, use_container_width=True)

# ---------- Footer ----------
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem;">
    <p>🚐 <strong>Vans Data Interactive Dashboard</strong> | Built with Streamlit</p>
    <p>📊 Analyze • 🔍 Filter • 📈 Visualize • 📥 Export</p>
</div>
""", unsafe_allow_html=True)