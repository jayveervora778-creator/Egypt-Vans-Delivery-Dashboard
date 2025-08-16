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

@st.cache_data(show_spinner="Loading data...")
def load_excel_file(path_or_bytes):
    """Load Excel file with survey data structure support"""
    try:
        # Simple approach - try different loading methods
        
        # Method 1: Try standard pandas Excel loading with headers
        try:
            df = pd.read_excel(path_or_bytes, header=1)
            # Look for respondent data
            respondent_rows = df[df.iloc[:, 1].astype(str).str.contains('Respondent', na=False)]
            if len(respondent_rows) > 0:
                # Get the index of first respondent
                start_idx = respondent_rows.index[0]
                # Extract data from that point
                data_df = df.iloc[start_idx:].copy()
                # Clean column names
                new_cols = []
                for col in data_df.columns:
                    if pd.notna(col) and not str(col).startswith('Unnamed'):
                        clean_name = str(col).strip()
                        if len(clean_name) > 40:
                            if "age" in clean_name.lower():
                                clean_name = "Age (Years)"
                            elif "company" in clean_name.lower():
                                clean_name = "Company"
                            elif "employment" in clean_name.lower():
                                clean_name = "Employment Status"
                            elif "areas" in clean_name.lower():
                                clean_name = "Areas Covered"
                            else:
                                clean_name = clean_name[:40] + "..."
                        new_cols.append(clean_name)
                    else:
                        new_cols.append(f"Column_{len(new_cols)}")
                
                # Ensure all column names are unique
                seen_names = set()
                unique_cols = []
                for col_name in new_cols:
                    original_name = col_name
                    counter = 1
                    while col_name in seen_names:
                        col_name = f"{original_name}_{counter}"
                        counter += 1
                    seen_names.add(col_name)
                    unique_cols.append(col_name)
                
                data_df.columns = unique_cols
                data_df = data_df.reset_index(drop=True)
                data_df = data_df.dropna(how='all')
                
                return data_df
        except Exception:
            pass
        
        # Method 2: Load without headers and process manually
        df_raw = pd.read_excel(path_or_bytes, header=None)
        
        # Find the data start (look for "Respondent")
        data_start_row = None
        for idx in range(min(10, len(df_raw))):  # Only check first 10 rows
            for col_idx in range(min(5, len(df_raw.columns))):  # Only check first 5 columns
                cell_value = df_raw.iloc[idx, col_idx]
                if pd.notna(cell_value) and 'Respondent' in str(cell_value):
                    data_start_row = idx
                    break
            if data_start_row is not None:
                break
        
        if data_start_row is not None:
            # Extract data
            data_df = df_raw.iloc[data_start_row:].copy()
            
            # Simple column naming with uniqueness guarantee
            simple_cols = []
            for i in range(len(data_df.columns)):
                if i == 0:
                    simple_cols.append("ID")
                elif i == 1:
                    simple_cols.append("Respondent")
                elif i == 2:
                    simple_cols.append("Age (Years)")
                elif i == 3:
                    simple_cols.append("Areas Covered") 
                elif i == 4:
                    simple_cols.append("Company")
                elif i == 5:
                    simple_cols.append("Employment Status")
                else:
                    simple_cols.append(f"Question_{i}")
            
            # Ensure all column names are unique
            seen_names = set()
            unique_cols = []
            for col_name in simple_cols:
                original_name = col_name
                counter = 1
                while col_name in seen_names:
                    col_name = f"{original_name}_{counter}"
                    counter += 1
                seen_names.add(col_name)
                unique_cols.append(col_name)
            
            simple_cols = unique_cols
            
            data_df.columns = simple_cols
            data_df = data_df.reset_index(drop=True)
            data_df = data_df.dropna(how='all')
            
            # Only convert clearly numeric columns
            if "Age (Years)" in data_df.columns:
                try:
                    data_df["Age (Years)"] = pd.to_numeric(data_df["Age (Years)"], errors='coerce')
                except:
                    pass
            
            return data_df
        
        # Method 3: Fallback - return empty DataFrame with error
        st.error("Could not process Excel file structure")
        return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Error loading Excel file: {str(e)}")
        return pd.DataFrame()

# ---------- Data Loading ----------
st.subheader("📊 Data Source")

DEFAULT_XLSX_PATH = "Vans data for dashboard.xlsx"
DEFAULT_CSV_PATH = "Vans data for dashboard.csv"
data_choice = st.radio(
    "Choose data source:",
    ["📁 Use included sample file", "📤 Upload your own Excel file"],
    horizontal=True
)

df_all = pd.DataFrame()

if data_choice == "📁 Use included sample file":
    if os.path.exists(DEFAULT_XLSX_PATH):
        df_all = load_excel_file(DEFAULT_XLSX_PATH)
        if not df_all.empty:
            st.success(f"✅ Loaded Vans survey data: {len(df_all):,} respondents, {len(df_all.columns)} questions")
    else:
        st.info("📁 Original data file not found. Please upload your own file below.")
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

# KPI 1: Survey Responses
with kpi_col1:
    st.metric(
        "📊 Total Responses",
        f"{len(df_view):,}",
        delta=f"of {len(df_all):,} total"
    )

# KPI 2: Average Age or Insurance
with kpi_col2:
    if age_col and pd.api.types.is_numeric_dtype(df_view[age_col]):
        avg_age = df_view[age_col].mean()
        st.metric(
            "👥 Average Age",
            f"{avg_age:.1f} years"
        )
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

analysis_tab1, analysis_tab2 = st.tabs(["📊 Custom Analysis", "🔖 Quick Presets"])

with analysis_tab1:
    st.write("**Create custom data summaries:**")
    
    # Get numeric and categorical columns safely
    numeric_cols = []
    categorical_cols = []
    
    for col in df_view.columns:
        try:
            if pd.api.types.is_numeric_dtype(df_view[col]):
                numeric_cols.append(col)
            elif df_view[col].dtype == 'object':
                categorical_cols.append(col)
        except Exception:
            # If there's any issue accessing the column, treat it as categorical
            categorical_cols.append(col)
    
    if len(numeric_cols) > 0 and len(categorical_cols) > 0:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            group_by = st.selectbox("📂 Group by:", ["None"] + categorical_cols)
        with col2:
            analyze_col = st.selectbox("📊 Analyze:", numeric_cols)
        with col3:
            agg_function = st.selectbox("🔢 Function:", ["mean", "sum", "count", "min", "max", "std"])
        
        if group_by != "None" and analyze_col:
            try:
                # Perform aggregation
                if agg_function == "mean":
                    result = df_view.groupby(group_by)[analyze_col].mean().reset_index()
                elif agg_function == "sum":
                    result = df_view.groupby(group_by)[analyze_col].sum().reset_index()
                elif agg_function == "count":
                    result = df_view.groupby(group_by)[analyze_col].count().reset_index()
                elif agg_function == "min":
                    result = df_view.groupby(group_by)[analyze_col].min().reset_index()
                elif agg_function == "max":
                    result = df_view.groupby(group_by)[analyze_col].max().reset_index()
                else:  # std
                    result = df_view.groupby(group_by)[analyze_col].std().reset_index()
                
                result.columns = [group_by, f"{agg_function.title()} of {analyze_col}"]
                
                # Display results
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.dataframe(result, use_container_width=True)
                
                with col2:
                    fig = px.bar(
                        result,
                        x=group_by,
                        y=f"{agg_function.title()} of {analyze_col}",
                        title=f"{agg_function.title()} of {analyze_col} by {group_by}",
                        color=f"{agg_function.title()} of {analyze_col}",
                        color_continuous_scale="viridis"
                    )
                    fig.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig, use_container_width=True)
                    
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
    preset_options = [
        "None",
        "Employment Status × Medical Insurance",
        "Company × Average Deliveries",
        "Age Groups × Employment Status",
        "Areas Covered × Average Income",
        "Company × Employee Count"
    ]
    
    selected_preset = st.selectbox("Select preset analysis:", preset_options)
    
    if selected_preset != "None":
        if selected_preset == "Employment Status × Medical Insurance":
            if "Employment Status" in df_view.columns and "Medical Insurance" in df_view.columns:
                crosstab = pd.crosstab(
                    df_view["Employment Status"],
                    df_view["Medical Insurance"],
                    margins=True
                )
                st.dataframe(crosstab, use_container_width=True)
                
        elif selected_preset == "Company × Average Deliveries":
            if "Company" in df_view.columns and "Deliveries per day" in df_view.columns:
                company_deliveries = df_view.groupby("Company")["Deliveries per day"].mean().reset_index()
                st.dataframe(company_deliveries, use_container_width=True)
                
                fig = px.bar(company_deliveries, x="Company", y="Deliveries per day")
                st.plotly_chart(fig, use_container_width=True)

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
    col1, col2 = st.columns(2)
    
    with col1:
        # Deliveries by Company
        company_col = None
        deliveries_col = None
        
        for col in df_view.columns:
            if "company" in col.lower() and not col.endswith(('_1', '_2', '_3', '_4', '_5', '_6')):
                company_col = col
            elif "deliveries" in col.lower() and not col.endswith(('_1', '_2', '_3', '_4', '_5', '_6')):
                deliveries_col = col
        
        if company_col and deliveries_col and len(df_view[company_col].dropna()) > 0:
            try:
                fig = px.box(
                    df_view,
                    x=company_col,
                    y=deliveries_col,
                    title="Deliveries per Day by Company"
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error creating company/deliveries chart: {str(e)}")
        else:
            st.info("No valid company or deliveries data found for visualization")
    
    with col2:
        # Income by Employment Status
        income_col = None
        employment_col = None
        
        for col in df_view.columns:
            if "income" in col.lower() and not col.endswith(('_1', '_2', '_3', '_4', '_5', '_6')):
                income_col = col
            elif "employment" in col.lower() and not col.endswith(('_1', '_2', '_3', '_4', '_5', '_6')):
                employment_col = col
        
        if income_col and employment_col and len(df_view[income_col].dropna()) > 0:
            try:
                fig = px.violin(
                    df_view,
                    x=employment_col,
                    y=income_col,
                    title="Income Distribution by Employment Status"
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error creating income chart: {str(e)}")
        else:
            st.info("No valid income or employment data found for visualization")

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