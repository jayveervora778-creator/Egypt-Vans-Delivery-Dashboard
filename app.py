
import os, io, tempfile, datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.io as pio
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(page_title="Vans Interactive Dashboard", layout="wide")
APP_TITLE = "📊 Vans Data Interactive Dashboard"

# ---------- Auth (optional) ----------
PASSWORD = os.getenv("STREAMLIT_DASH_PASSWORD", "")
if PASSWORD:
    def login():
        with st.form("login", clear_on_submit=False):
            pwd = st.text_input("Password", type="password")
            ok = st.form_submit_button("Enter")
        return ok, pwd
    st.title(APP_TITLE)
    ok, pwd = login()
    if not ok or pwd != PASSWORD:
        st.info("Enter the password to access the dashboard.")
        st.stop()

st.title(APP_TITLE)
st.caption("Slice, dice, visualize, and export Vans dataset.")

DEFAULT_PATH = "Vans data for dashboard.xlsx"

def _flatten_columns(columns):
    flattened = []
    for col in columns:
        if isinstance(col, tuple) or isinstance(col, list):
            parts = [str(x) for x in col if str(x) != "nan"]
            flattened.append(" - ".join(parts).strip())
        else:
            flattened.append(str(col).strip())
    return flattened

@st.cache_data(show_spinner=False)
def load_excel_any(path_or_bytes):
    xls = pd.ExcelFile(path_or_bytes)
    frames = []
    for sheet in xls.sheet_names:
        try:
            df = pd.read_excel(path_or_bytes, sheet_name=sheet, header=[0,1,2])
            df.columns = _flatten_columns(df.columns.values)
        except Exception:
            df = pd.read_excel(path_or_bytes, sheet_name=sheet, header=0)
            df.columns = _flatten_columns(df.columns.values)
        df.columns = [c.replace("Unnamed: ", "").strip() for c in df.columns]
        frames.append(df)
    return pd.concat(frames, ignore_index=True)

choice = st.radio("Data source:", ["Use included file", "Upload your own"], horizontal=True)

if choice == "Use included file":
    if not os.path.exists(DEFAULT_PATH):
        st.error("Included file not found.")
        st.stop()
    df_all = load_excel_any(DEFAULT_PATH)
else:
    up = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"])
    if up is None:
        st.stop()
    else:
        data = io.BytesIO(up.read())
        df_all = load_excel_any(data)

# Clean cols
df_all.columns = [str(c).strip() for c in df_all.columns]
df_view = df_all.copy()

# ---------- Global Filters ----------
with st.sidebar:
    st.header("🔎 Global Filters")
    for c in ["Company", "Employment Status", "Areas Covered"]:
        if c in df_all.columns:
            vals = sorted([v for v in df_all[c].dropna().unique()])
            sel = st.multiselect(f"{c} filter", options=vals, default=vals)
            df_view = df_view[df_view[c].isin(sel)]
    if "Age (Years)" in df_all.columns:
        min_age, max_age = int(df_all["Age (Years)"].min()), int(df_all["Age (Years)"].max())
        age_range = st.slider("Age Range", min_age, max_age, (min_age, max_age))
        df_view = df_view[df_view["Age (Years)"].between(age_range[0], age_range[1])]

# ---------- KPI Metrics ----------
st.subheader("📌 Key Metrics")
col1, col2, col3, col4 = st.columns(4)
if "Deliveries per day" in df_view.columns:
    col1.metric("Avg Deliveries/day", round(df_view["Deliveries per day"].mean(),1))
if "Medical Insurance" in df_view.columns:
    pct = (df_view["Medical Insurance"].eq("Yes").mean()*100)
    col2.metric("% with Medical Insurance", f"{pct:.1f}%")
if "Net Income (Gross - All Expenses) (EGP)" in df_view.columns:
    col3.metric("Avg Net Income", f"{df_view['Net Income (Gross - All Expenses) (EGP)'].mean():,.0f} EGP")
if "Employment Status" in df_view.columns:
    mode = df_view["Employment Status"].mode()[0] if not df_view["Employment Status"].empty else "N/A"
    col4.metric("Most Common Employment", mode)

# ---------- Data Preview ----------
st.subheader("📋 Data Preview")
st.write(f"**Showing {len(df_view):,} records** (filtered from {len(df_all):,} total)")

# Show basic info
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Records", f"{len(df_view):,}")
with col2:
    st.metric("Total Columns", len(df_view.columns))
with col3:
    st.metric("Data Coverage", f"{(len(df_view)/len(df_all)*100):.1f}%")

# Show first few rows
with st.expander("View Sample Data", expanded=False):
    st.dataframe(df_view.head(10), use_container_width=True)

# ---------- Interactive Data Analysis ----------
st.subheader("📊 Interactive Data Analysis")

# Custom pivot table functionality
st.write("**Create your own data summary:**")
col1, col2, col3 = st.columns(3)

with col1:
    index_col = st.selectbox("Group by (Rows):", ["None"] + list(df_view.columns))
with col2:
    value_col = st.selectbox("Analyze (Values):", ["None"] + [col for col in df_view.columns if df_view[col].dtype in ['int64', 'float64']])
with col3:
    agg_func = st.selectbox("Function:", ["mean", "sum", "count", "min", "max"])

if index_col != "None" and value_col != "None":
    try:
        if agg_func == "count":
            pivot_result = df_view.groupby(index_col)[value_col].count().reset_index()
        elif agg_func == "mean":
            pivot_result = df_view.groupby(index_col)[value_col].mean().reset_index()
        elif agg_func == "sum":
            pivot_result = df_view.groupby(index_col)[value_col].sum().reset_index()
        elif agg_func == "min":
            pivot_result = df_view.groupby(index_col)[value_col].min().reset_index()
        else:  # max
            pivot_result = df_view.groupby(index_col)[value_col].max().reset_index()
            
        pivot_result.columns = [index_col, f"{agg_func.title()} of {value_col}"]
        
        st.subheader(f"📋 {agg_func.title()} of {value_col} by {index_col}")
        st.dataframe(pivot_result, use_container_width=True)
        
        # Create a chart from pivot result
        fig = px.bar(pivot_result, 
                    x=index_col, 
                    y=f"{agg_func.title()} of {value_col}",
                    title=f"{agg_func.title()} of {value_col} by {index_col}")
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Analysis error: {e}")
else:
    st.info("👆 Select both 'Group by' and 'Analyze' fields to create a summary table.")

# ---------- Quick Preset Analysis ----------
st.subheader("🔖 Quick Analysis Presets")
preset = st.selectbox("Select a preset analysis:", [
    "None",
    "Employment Status × Medical Insurance",
    "Company × Avg Deliveries",
    "Areas Covered × Avg Net Income",
    "Company × Count of Employees",
    "Employment Status × Avg Income",
    "Age Groups × Employment Status"
])

if preset != "None":
    st.info(f"Showing preset: '{preset}'")
    
    if preset == "Employment Status × Medical Insurance" and "Employment Status" in df_view.columns and "Medical Insurance" in df_view.columns:
        cross_tab = pd.crosstab(df_view["Employment Status"], df_view["Medical Insurance"], margins=True)
        st.dataframe(cross_tab, use_container_width=True)
        
    elif preset == "Company × Avg Deliveries" and "Company" in df_view.columns and "Deliveries per day" in df_view.columns:
        company_deliveries = df_view.groupby("Company")["Deliveries per day"].mean().reset_index()
        st.dataframe(company_deliveries, use_container_width=True)
        
    elif preset == "Areas Covered × Avg Net Income" and "Areas Covered" in df_view.columns and "Net Income (Gross - All Expenses) (EGP)" in df_view.columns:
        area_income = df_view.groupby("Areas Covered")["Net Income (Gross - All Expenses) (EGP)"].mean().reset_index()
        st.dataframe(area_income, use_container_width=True)
        
    elif preset == "Company × Count of Employees" and "Company" in df_view.columns:
        company_count = df_view["Company"].value_counts().reset_index()
        company_count.columns = ["Company", "Count"]
        st.dataframe(company_count, use_container_width=True)
        
    elif preset == "Employment Status × Avg Income" and "Employment Status" in df_view.columns and "Net Income (Gross - All Expenses) (EGP)" in df_view.columns:
        emp_income = df_view.groupby("Employment Status")["Net Income (Gross - All Expenses) (EGP)"].mean().reset_index()
        st.dataframe(emp_income, use_container_width=True)
        
    elif preset == "Age Groups × Employment Status" and "Age (Years)" in df_view.columns and "Employment Status" in df_view.columns:
        df_view_copy = df_view.copy()
        df_view_copy["Age Group"] = pd.cut(df_view_copy["Age (Years)"], bins=[0, 25, 35, 45, 100], labels=["18-25", "26-35", "36-45", "46+"])
        age_emp = pd.crosstab(df_view_copy["Age Group"], df_view_copy["Employment Status"], margins=True)
        st.dataframe(age_emp, use_container_width=True)

# ---------- Visual Analytics ----------
st.subheader("📈 Visual Analytics")

charts = []

if "Employment Status" in df_view.columns:
    fig = px.pie(df_view, names="Employment Status", title="Employment Status Share")
    st.plotly_chart(fig, use_container_width=True)
    charts.append(("pie.png", fig))

if "Company" in df_view.columns and "Deliveries per day" in df_view.columns:
    fig = px.bar(df_view, x="Company", y="Deliveries per day",
                 title="Deliveries per Day by Company", barmode="group")
    st.plotly_chart(fig, use_container_width=True)
    charts.append(("deliveries.png", fig))

if "Age (Years)" in df_view.columns:
    fig = px.histogram(df_view, x="Age (Years)", nbins=10, title="Age Distribution")
    st.plotly_chart(fig, use_container_width=True)
    charts.append(("age.png", fig))

if "Net Income (Gross - All Expenses) (EGP)" in df_view.columns and "Employment Status" in df_view.columns:
    fig = px.box(df_view, x="Employment Status",
                 y="Net Income (Gross - All Expenses) (EGP)", title="Net Income by Employment Status")
    st.plotly_chart(fig, use_container_width=True)
    charts.append(("income.png", fig))

if "Fuel Expenses (EGP)" in df_view.columns and "Company" in df_view.columns:
    df_exp = df_view.groupby("Company")[["Fuel Expenses (EGP)", "Maintenance Costs (EGP)",
                                         "Financing/Lease (EGP)", "Other Expenses (licenses, permits, fines, etc....)"]].mean().reset_index()
    df_exp = df_exp.melt(id_vars="Company", var_name="Expense Type", value_name="Avg Expense")
    fig = px.bar(df_exp, x="Company", y="Avg Expense", color="Expense Type", barmode="stack",
                 title="Average Expenses by Company")
    st.plotly_chart(fig, use_container_width=True)
    charts.append(("expenses.png", fig))

# ---------- PDF Export ----------
st.subheader("📑 Export")
if st.button("⬇️ Export Dashboard to PDF"):
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "dashboard_snapshot.pdf")
        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        styles = getSampleStyleSheet()
        flow = []

        flow.append(Paragraph("Vans Data Dashboard Snapshot", styles['Title']))
        flow.append(Paragraph(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), styles['Normal']))
        flow.append(Spacer(1,12))

        # KPIs
        if "Deliveries per day" in df_view.columns:
            flow.append(Paragraph(f"Avg Deliveries/day: {round(df_view['Deliveries per day'].mean(),1)}", styles['Normal']))
        if "Medical Insurance" in df_view.columns:
            pct = df_view["Medical Insurance"].eq("Yes").mean()*100
            flow.append(Paragraph(f"% with Medical Insurance: {pct:.1f}%", styles['Normal']))
        if "Net Income (Gross - All Expenses) (EGP)" in df_view.columns:
            flow.append(Paragraph(f"Avg Net Income: {df_view['Net Income (Gross - All Expenses) (EGP)'].mean():,.0f} EGP", styles['Normal']))
        flow.append(Spacer(1,12))

        # Save and add charts
        for fname, fig in charts:
            outpath = os.path.join(tmpdir, fname)
            pio.write_image(fig, outpath, format="png")
            flow.append(Image(outpath, width=400, height=250))
            flow.append(Spacer(1,12))

        doc.build(flow)
        with open(pdf_path,"rb") as f:
            st.download_button("Download PDF", data=f, file_name="dashboard_snapshot.pdf", mime="application/pdf")
