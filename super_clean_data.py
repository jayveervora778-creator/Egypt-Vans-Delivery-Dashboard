#!/usr/bin/env python3
"""
Super aggressive data cleaning to eliminate ALL PyArrow issues
"""
import pandas as pd
import numpy as np

def main():
    print("🧹 Super cleaning data to eliminate PyArrow issues...")
    
    # Load the existing cleaned data
    try:
        df = pd.read_csv('Vans_data_cleaned.csv')
        print(f"📊 Loaded {len(df)} rows, {len(df.columns)} columns")
    except Exception as e:
        print(f"❌ Error loading cleaned CSV: {e}")
        return
    
    # STEP 1: Force ALL columns to string initially (this eliminates mixed types)
    print("🔧 Converting all columns to strings...")
    df_safe = df.copy()
    for col in df_safe.columns:
        df_safe[col] = df_safe[col].astype(str)
        # Replace pandas nan representations with None
        df_safe[col] = df_safe[col].replace(['nan', 'None', '<NA>', 'NaN'], '')
    
    # STEP 2: Only convert clearly numeric columns back to numeric
    print("🔢 Converting safe numeric columns...")
    numeric_columns = ['Age (Years)']  # Start with age which we know should be numeric
    
    # Add other columns that are clearly numeric based on content
    for col in df_safe.columns:
        col_lower = col.lower()
        if any(word in col_lower for word in ['age', 'egp', 'days', 'hours']):
            if col not in numeric_columns:
                # Test if conversion is safe
                test_series = pd.to_numeric(df_safe[col], errors='coerce')
                valid_count = test_series.count()
                total_count = len(df_safe[col]) - (df_safe[col] == '').sum()
                
                if total_count > 0 and valid_count / total_count > 0.7:  # 70% must be valid numbers
                    numeric_columns.append(col)
                    print(f"✅ {col}: {valid_count}/{total_count} valid numbers")
    
    # Convert the safe numeric columns
    for col in numeric_columns:
        if col in df_safe.columns:
            df_safe[col] = pd.to_numeric(df_safe[col], errors='coerce')
            print(f"🔢 Converted {col} to numeric")
    
    # STEP 3: Handle the problematic columns explicitly
    problematic_patterns = ['working with your current', 'how long']
    for col in df_safe.columns:
        col_lower = col.lower()
        if any(pattern in col_lower for pattern in problematic_patterns):
            print(f"🚨 Fixing problematic column: {col}")
            # Force to string and clean
            df_safe[col] = df_safe[col].astype(str).replace('nan', '')
    
    # STEP 4: Verify age data
    age_col = next((col for col in df_safe.columns if 'age' in col.lower()), None)
    if age_col:
        print(f"\n📋 Age Column Analysis:")
        print(f"   Column: {age_col}")
        print(f"   Data type: {df_safe[age_col].dtype}")
        print(f"   Sample values: {df_safe[age_col].dropna().head(10).tolist()}")
        print(f"   Valid count: {df_safe[age_col].count()}")
        print(f"   Mean age: {df_safe[age_col].mean():.2f} years")
    
    # STEP 5: Save ultra-clean version
    output_file = 'Vans_data_ultra_clean.csv'
    df_safe.to_csv(output_file, index=False)
    print(f"💾 Saved ultra-clean data to: {output_file}")
    
    # STEP 6: Test PyArrow compatibility
    print("\n🧪 Testing PyArrow compatibility...")
    try:
        import pyarrow as pa
        table = pa.Table.from_pandas(df_safe)
        print("✅ PyArrow conversion successful!")
    except Exception as e:
        print(f"❌ PyArrow test failed: {e}")
        
        # Find the problematic column
        for col in df_safe.columns:
            try:
                test_df = df_safe[[col]]
                pa.Table.from_pandas(test_df)
            except Exception as col_error:
                print(f"🚨 Problematic column: {col} - {col_error}")
    
    print("🎉 Super cleaning complete!")

if __name__ == "__main__":
    main()