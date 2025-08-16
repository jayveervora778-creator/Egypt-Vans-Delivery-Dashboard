#!/usr/bin/env python3
"""
Script to clean the Excel data and create a PyArrow-safe version
"""
import pandas as pd
import numpy as np

def clean_mixed_column(series):
    """Clean mixed data types in a column"""
    cleaned = []
    for val in series:
        if pd.isna(val):
            cleaned.append(None)
        else:
            val_str = str(val).strip()
            if val_str.lower() in ['nan', 'none', '']:
                cleaned.append(None)
            else:
                # Keep as string to avoid type conflicts
                cleaned.append(val_str)
    return cleaned

def main():
    print("Loading and cleaning Excel data...")
    
    # Load raw data
    df_raw = pd.read_excel('Vans_data_raw_new.xlsx', header=None)
    
    # Extract headers
    main_headers = df_raw.iloc[0].fillna('')
    sub_headers = df_raw.iloc[2].fillna('')
    
    # Create column names
    smart_cols = []
    for i, (main_header, sub_header) in enumerate(zip(main_headers, sub_headers)):
        main_header = str(main_header).strip()
        sub_header = str(sub_header).strip()
        
        if main_header in ['nan', 'NULL', ''] and sub_header in ['nan', 'NULL', '']:
            if i == 0:
                col_name = 'Respondent'
            else:
                col_name = f'Empty_Col_{i}'
        else:
            if i == 0:
                col_name = 'Respondent'
            elif i == 1 and 'age' in main_header.lower():
                col_name = 'Age (Years)'
            elif i == 2 and 'area' in main_header.lower():
                col_name = 'Areas Covered'
            elif i == 3 and 'company' in main_header.lower():
                col_name = 'Company'
            elif i == 4 and 'employment' in main_header.lower():
                col_name = 'Employment Status'
            else:
                if main_header and main_header != 'nan':
                    col_name = main_header
                    if sub_header and sub_header != 'nan' and sub_header != main_header:
                        if 'days per month' in sub_header.lower():
                            col_name = f'{main_header} (Days)'
                        elif 'egp/month' in sub_header.lower() or 'egp' in sub_header.lower():
                            col_name = f'{main_header} (EGP)'
                        elif len(sub_header) < 30:
                            col_name = f'{main_header} ({sub_header})'
                elif sub_header and sub_header != 'nan':
                    col_name = sub_header
                else:
                    col_name = f'Question_{i+1}'
            
            col_name = col_name.replace('\n', ' ').replace('\r', ' ')
            if len(col_name) > 50:
                col_name = col_name[:47] + '...'
        
        smart_cols.append(col_name)
    
    # Extract data starting from row 4
    data_df = df_raw.iloc[3:].copy()
    data_df.columns = smart_cols[:len(data_df.columns)]
    data_df = data_df.reset_index(drop=True)
    data_df = data_df.dropna(how='all')
    
    print(f"Data loaded: {len(data_df)} rows, {len(data_df.columns)} columns")
    
    # Clean problematic columns
    problematic_patterns = ['working with your current', 'how long']
    
    for col in data_df.columns:
        col_lower = col.lower()
        
        # Clean the specific problematic column
        if any(pattern in col_lower for pattern in problematic_patterns):
            print(f"Cleaning problematic column: {col}")
            data_df[col] = clean_mixed_column(data_df[col])
        
        # Convert obvious numeric columns
        elif any(indicator in col_lower for indicator in ['age', 'year', 'egp', 'days', 'hours', 'deliveries', 'income', 'salary', 'allowance']):
            try:
                numeric_series = pd.to_numeric(data_df[col], errors='coerce')
                if numeric_series.count() > len(data_df) * 0.5:
                    data_df[col] = numeric_series
            except:
                pass
    
    # Save cleaned data
    print("Saving cleaned data...")
    data_df.to_csv('Vans_data_cleaned.csv', index=False)
    print("Cleaned data saved as 'Vans_data_cleaned.csv'")
    
    # Check age column
    age_col = next((col for col in data_df.columns if 'age' in col.lower()), None)
    if age_col:
        print(f"\nAge column: {age_col}")
        print(f"Age data type: {data_df[age_col].dtype}")
        print(f"Age sample: {data_df[age_col].head(5).tolist()}")
        print(f"Age mean: {data_df[age_col].mean():.2f}")

if __name__ == "__main__":
    main()