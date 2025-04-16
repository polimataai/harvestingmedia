import streamlit as st
import pandas as pd
from utils import format_name, save_to_gsheets, get_google_sheets_connection

SPREADSHEET_KEY = "1qWLg1vQHvJQG2hFHrUpO8y6bC8_xDdkLG2ErY_aGxkw"
WORKSHEET_NAME = "Certo_Market_MKT_Report"

def process_certo_market_visits(df, name_col, email_col, phone_col, reg_date_col, first_order_col, spent_col):
    """Process data for Certo Market Visits Report."""
    # Convert dates to string format before creating DataFrame
    processed_df = pd.DataFrame({
        'Name': df[name_col].apply(format_name),
        'Email': df[email_col].str.lower(),
        'Phone': df[phone_col],
        'Registered Date': pd.to_datetime(df[reg_date_col]).dt.strftime('%Y-%m-%d'),
        'First Order Date': pd.to_datetime(df[first_order_col]).dt.strftime('%Y-%m-%d'),
        'Spent $': df[spent_col]
    })
    
    # Get Google Sheets connection
    gc = get_google_sheets_connection()
    workbook = gc.open_by_key(SPREADSHEET_KEY)
    worksheet = workbook.worksheet(WORKSHEET_NAME)
    
    # Clear the worksheet and add headers
    worksheet.clear()
    headers = ['Name', 'Email', 'Phone', 'Registered Date', 'First Order Date', 'Spent $']
    worksheet.append_row(headers)
    
    # Save to Google Sheets
    return save_to_gsheets(processed_df, worksheet), processed_df, WORKSHEET_NAME

def render_certo_market_visits_ui(df):
    """Render UI for Certo Market Visits Report process."""
    st.markdown("### Map Columns")
    st.markdown("Please select which columns contain the required information:")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        name_col = st.selectbox("Name Column", df.columns.tolist())
        email_col = st.selectbox("Email Column", df.columns.tolist())
    
    with col2:
        phone_col = st.selectbox("Phone Column", df.columns.tolist())
        reg_date_col = st.selectbox("Registration Date Column", df.columns.tolist())
    
    with col3:
        first_order_col = st.selectbox("First Order Date Column", df.columns.tolist())
        spent_col = st.selectbox("Spent Amount Column", df.columns.tolist())
    
    if st.button("Process Data"):
        with st.spinner("Processing data and updating Google Sheets..."):
            success, processed_df, worksheet_name = process_certo_market_visits(
                df, name_col, email_col, phone_col, reg_date_col, first_order_col, spent_col
            )
            
            if success:
                st.success(f"✅ Data successfully processed and saved to {worksheet_name}!")
                
                # Display statistics
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Records", len(processed_df))
                with col2:
                    st.metric("Unique Emails", len(processed_df['Email'].unique()))
            else:
                st.error("❌ Failed to save data to Google Sheets.") 