import streamlit as st
import pandas as pd
from utils import format_name, save_to_gsheets, get_google_sheets_connection

SPREADSHEET_KEY = "1qWLg1vQHvJQG2hFHrUpO8y6bC8_xDdkLG2ErY_aGxkw"
WORKSHEET_NAME = "Certo_Market"

def process_certo_market(df, email_col, first_name_col, phone_col):
    """Process data for Certo Market."""
    processed_df = pd.DataFrame({
        'Email': df[email_col].str.lower(),
        'First Name': df[first_name_col].apply(format_name),
        'Phone': df[phone_col]
    })
    
    # Get Google Sheets connection
    gc = get_google_sheets_connection()
    workbook = gc.open_by_key(SPREADSHEET_KEY)
    worksheet = workbook.worksheet(WORKSHEET_NAME)
    
    # Save to Google Sheets
    return save_to_gsheets(processed_df, worksheet), processed_df, WORKSHEET_NAME

def render_certo_market_ui(df):
    """Render UI for Certo Market process."""
    st.markdown("### Map Columns")
    st.markdown("Please select which columns contain the required information:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        email_col = st.selectbox("Email Column", df.columns.tolist())
        first_name_col = st.selectbox("First Name Column", df.columns.tolist())
    
    with col2:
        phone_col = st.selectbox("Phone Column", df.columns.tolist())
    
    if st.button("Process Data"):
        with st.spinner("Processing data and updating Google Sheets..."):
            success, processed_df, worksheet_name = process_certo_market(
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
            else:
                st.error("❌ Failed to save data to Google Sheets.") 