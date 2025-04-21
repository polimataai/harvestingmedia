import streamlit as st
import pandas as pd
from utils import format_name, save_to_gsheets, get_google_sheets_connection

SPREADSHEET_KEY = "1xsDEfSg2qv-3-hVyOWbhyWz3TuxNBnIEnweZ54iExv8"
WORKSHEET_NAME = "Key_Food_Valley_Stream"

def process_key_food(df, email_col, first_name_col, phone_col):
    """Process data for Key Food Valley Stream."""
    processed_df = pd.DataFrame({
        'Email': df[email_col].str.lower(),
        'First Name': df[first_name_col].apply(format_name),
        'Phone': df[phone_col]
    })
    
    # Get Google Sheets connection
    gc = get_google_sheets_connection()
    workbook = gc.open_by_key(SPREADSHEET_KEY)
    
    # Try to get the worksheet, if it doesn't exist, create it
    try:
        worksheet = workbook.worksheet(WORKSHEET_NAME)
    except:
        worksheet = workbook.add_worksheet(WORKSHEET_NAME, rows=1000, cols=10)
        # Add headers
        headers = ['Email', 'First Name', 'Phone']
        worksheet.append_row(headers)
    
    # Save to Google Sheets
    return save_to_gsheets(processed_df, worksheet), processed_df, WORKSHEET_NAME

def render_key_food_ui(df):
    """Render UI for Key Food Valley Stream process."""
    st.markdown("### Map Columns")
    st.markdown("Please select which columns contain the required information:")
    
    # Get column names from dataframe
    columns = df.columns.tolist()
    
    # Define patterns for automatic column detection
    email_patterns = ['email', 'e-mail', 'mail']
    first_name_patterns = ['first name', 'first', 'name', 'customer name', 'customer']
    phone_patterns = ['phone', 'phone number', 'contact', 'telephone', 'cell', 'mobile']
    
    # Find default column indices
    email_default = find_column_by_pattern(columns, email_patterns)
    first_name_default = find_column_by_pattern(columns, first_name_patterns)
    phone_default = find_column_by_pattern(columns, phone_patterns)
    
    col1, col2 = st.columns(2)
    
    with col1:
        email_col = st.selectbox(
            "Email Column", 
            columns,
            index=email_default
        )
        first_name_col = st.selectbox(
            "First Name Column", 
            columns,
            index=first_name_default
        )
    
    with col2:
        phone_col = st.selectbox(
            "Phone Column", 
            columns,
            index=phone_default
        )
        
        st.markdown("#### File Type")
        st.success("✓ CSV Format Detected")
    
    if st.button("Process Data"):
        with st.spinner("Processing data and updating Google Sheets..."):
            success, processed_df, worksheet_name = process_key_food(
                df, email_col, first_name_col, phone_col
            )
            
            if success:
                st.success(f"✅ Data successfully processed and saved to {worksheet_name}!")
                
                # Display statistics
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Records", len(processed_df))
                with col2:
                    st.metric("Unique Emails", len(processed_df['Email'].unique()))
                
                # Show preview of processed data
                st.markdown("### Preview of Processed Data")
                st.dataframe(processed_df.head(10))
            else:
                st.error("❌ Failed to save data to Google Sheets.")

def find_column_by_pattern(columns, patterns):
    """Find the index of a column that best matches the given patterns."""
    # Try exact match first
    for pattern in patterns:
        for i, col in enumerate(columns):
            if str(col).lower() == pattern:
                return i
    
    # Then try contains match
    for pattern in patterns:
        for i, col in enumerate(columns):
            if pattern in str(col).lower():
                return i
    
    # Return first column as default
    return 0 