#!/usr/bin/env python3
"""
Simple test to check just the age calculation without any dataframe display
"""
import streamlit as st
import pandas as pd
import numpy as np

st.title("🧪 Age KPI Test")

# Load ultra-clean data directly
try:
    df = pd.read_csv('Vans_data_ultra_clean.csv')
    st.write(f"✅ Loaded data: {len(df)} rows, {len(df.columns)} columns")
    
    # Find age column
    age_col = None
    for col in df.columns:
        if 'age' in col.lower():
            age_col = col
            break
    
    if age_col:
        st.write(f"🎯 Found age column: {age_col}")
        st.write(f"📊 Data type: {df[age_col].dtype}")
        
        # Calculate age statistics
        valid_ages = df[age_col].dropna()
        st.write(f"📋 Valid age count: {len(valid_ages)}")
        st.write(f"📈 Age range: {valid_ages.min()} to {valid_ages.max()}")
        
        avg_age = valid_ages.mean()
        st.write(f"🎯 **AVERAGE AGE: {avg_age:.1f} years**")
        
        # Show the KPI metric
        st.metric("👥 Average Age", f"{avg_age:.1f} years")
        
        # Show sample ages
        st.write("📝 Sample ages:")
        st.write(valid_ages.head(10).tolist())
        
    else:
        st.error("❌ No age column found")
        st.write("Available columns:")
        st.write(df.columns.tolist())

except Exception as e:
    st.error(f"❌ Error: {e}")
    import traceback
    st.write(traceback.format_exc())