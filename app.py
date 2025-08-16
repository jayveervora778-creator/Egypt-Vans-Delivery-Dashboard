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
    """Load Excel file with multi-sheet and multi-header support"""
    try:
        xls = pd.ExcelFile(path_or_bytes)
        frames = []
        
        for sheet in xls.sheet_names:
            try:
                # Try multi-level headers first
                df = pd.read_excel(path_or_bytes, sheet_name=sheet, header=[0,1,2])
                df.columns = _flatten_columns(df.columns.values)
            except Exception:
                try:
                    # Try single header
                    df = pd.read_excel(path_or_bytes, sheet_name=sheet, header=0)
                    df.columns = _flatten_columns(df.columns.values)
                except Exception:
                    # Skip problematic sheets
                    continue
            
            # Clean column names
            df.columns = [c.replace("Unnamed: ", "").strip() for c in df.columns]
            df.columns = [c if c else f"Column_{i}" for i, c in enumerate(df.columns)]
            
            frames.append(df)
        
        if frames:
            result = pd.concat(frames, ignore_index=True)
            return result
        else:
            st.error("No valid data found in Excel file")
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
            st.success(f"✅ Loaded sample data: {len(df_all):,} records")
    elif os.path.exists(DEFAULT_CSV_PATH):
        df_all = pd.read_csv(DEFAULT_CSV_PATH)
        if not df_all.empty:
            st.success(f"✅ Loaded sample data: {len(df_all):,} records")
    else:
        st.info("📁 Sample file not found. Please upload your own file below.")
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

# Clean and prepare data
df_all.columns = [str(c).strip() for c in df_all.columns]
df_view = df_all.copy()

# ---------- Sidebar Filters ----------
with st.sidebar:
    st.markdown("### 🔍 Data Filters")
    
    # Show data info
    st.info(f"**Total Records:** {len(df_all):,}")
    
    # Categorical filters
    filter_columns = ["Company", "Employment Status", "Areas Covered", "Medical Insurance"]
    
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

# KPI 1: Average Deliveries
with kpi_col1:
    if "Deliveries per day" in df_view.columns:
        avg_deliveries = df_view["Deliveries per day"].mean()
        st.metric(
            "📦 Avg Deliveries/Day",
            f"{avg_deliveries:.1f}",
            delta=f"vs {df_all['Deliveries per day'].mean():.1f} overall"
        )
    else:
        st.metric("📦 Avg Deliveries/Day", "N/A")

# KPI 2: Medical Insurance Coverage
with kpi_col2:
    if "Medical Insurance" in df_view.columns:
        insurance_pct = (df_view["Medical Insurance"].eq("Yes").mean() * 100)
        overall_pct = (df_all["Medical Insurance"].eq("Yes").mean() * 100)
        st.metric(
            "🏥 Medical Insurance",
            f"{insurance_pct:.1f}%",
            delta=f"{insurance_pct - overall_pct:.1f}pp"
        )
    else:
        st.metric("🏥 Medical Insurance", "N/A")

# KPI 3: Average Net Income
with kpi_col3:
    income_col = "Net Income (Gross - All Expenses) (EGP)"
    if income_col in df_view.columns:
        avg_income = df_view[income_col].mean()
        overall_income = df_all[income_col].mean()
        st.metric(
            "💰 Avg Net Income",
            f"{avg_income:,.0f} EGP",
            delta=f"{avg_income - overall_income:,.0f} EGP"
        )
    else:
        st.metric("💰 Avg Net Income", "N/A")

# KPI 4: Most Common Employment
with kpi_col4:
    if "Employment Status" in df_view.columns and not df_view["Employment Status"].empty:
        mode_employment = df_view["Employment Status"].mode()[0]
        count = df_view["Employment Status"].value_counts().iloc[0]
        st.metric(
            "👥 Top Employment",
            mode_employment,
            delta=f"{count} workers"
        )
    else:
        st.metric("👥 Top Employment", "N/A")

# ---------- Interactive Data Analysis ----------
st.subheader("🔍 Interactive Data Analysis")

analysis_tab1, analysis_tab2 = st.tabs(["📊 Custom Analysis", "🔖 Quick Presets"])

with analysis_tab1:
    st.write("**Create custom data summaries:**")
    
    # Get numeric and categorical columns
    numeric_cols = [col for col in df_view.columns if pd.api.types.is_numeric_dtype(df_view[col])]
    categorical_cols = [col for col in df_view.columns if df_view[col].dtype == 'object']
    
    if numeric_cols and categorical_cols:
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
        if "Employment Status" in df_view.columns:
            fig = px.pie(
                df_view,
                names="Employment Status",
                title="Employment Status Distribution",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Age Distribution
        if "Age (Years)" in df_view.columns:
            fig = px.histogram(
                df_view,
                x="Age (Years)",
                nbins=15,
                title="Age Distribution",
                color_discrete_sequence=["#667eea"]
            )
            st.plotly_chart(fig, use_container_width=True)

with viz_tab2:
    col1, col2 = st.columns(2)
    
    with col1:
        # Deliveries by Company
        if "Company" in df_view.columns and "Deliveries per day" in df_view.columns:
            fig = px.box(
                df_view,
                x="Company",
                y="Deliveries per day",
                title="Deliveries per Day by Company"
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Income by Employment Status
        income_col = "Net Income (Gross - All Expenses) (EGP)"
        if income_col in df_view.columns and "Employment Status" in df_view.columns:
            fig = px.violin(
                df_view,
                x="Employment Status",
                y=income_col,
                title="Income Distribution by Employment Status"
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

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
    st.metric("🔍 Filtered Data", f"{(len(df_view)/len(df_all)*100):.1f}%")
    
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
    col_info = pd.DataFrame({
        'Column Name': df_view.columns,
        'Data Type': df_view.dtypes.astype(str),
        'Non-Null Count': df_view.count(),
        'Null Count': df_view.isnull().sum(),
        'Unique Values': df_view.nunique()
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