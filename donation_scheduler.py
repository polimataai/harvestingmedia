import streamlit as st
import pandas as pd
import requests
from datetime import timedelta
import re
from utils import save_to_gsheets, get_google_sheets_connection

SPREADSHEET_KEY = "1mlOhXY4aITLXXGS7IDrQfaZcg3MwxvI0vm3hDgswsB0"
WORKSHEET_NAME = "Donation_Schedule"

# Facility code → full center name mapping
FACILITY_MAPPING = {
    'OLX': 'BRONX',
    'OLW': 'PARKCHESTER',
    'OLL': 'HOWARD_BEACH',
    'OLK': 'BROWNSVILLE',
    'OLJ': 'JAMAICA',
    'OLF': 'FLATBUSH',
    'OLB': 'BROOKLYN',
    'HPF': 'FT_PIERCE',
    'OLG': 'EASTHARLEM',
    'OLH': 'FORDHAM',
}

# Date format patterns for automatic detection
DATE_PATTERNS = [
    # YYYY-MM-DD HH:MM:SS
    (r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', '%Y-%m-%d %H:%M:%S'),
    # MM/DD/YYYY
    (r'\d{1,2}/\d{1,2}/\d{4}', '%m/%d/%Y'),
    # DD/MM/YYYY
    (r'\d{1,2}/\d{1,2}/\d{4}', '%d/%m/%Y'),
    # YYYY-MM-DD
    (r'\d{4}-\d{2}-\d{2}', '%Y-%m-%d'),
    # MM-DD-YYYY
    (r'\d{1,2}-\d{1,2}-\d{4}', '%m-%d-%Y'),
    # YYYY/MM/DD
    (r'\d{4}/\d{1,2}/\d{1,2}', '%Y/%m/%d'),
]

def extract_first_name(full_name):
    """Extract first name from 'Last, First' format."""
    if isinstance(full_name, str) and ',' in full_name:
        return full_name.split(',')[1].strip().title()
    return ""

def get_center_name(facility_code):
    """Get full center name from facility code."""
    if pd.isna(facility_code):
        return "UNKNOWN"
    return FACILITY_MAPPING.get(facility_code.strip().upper(), "UNKNOWN")

def get_next_open_date(donation_date, facility_code, center_hours):
    """Get next open date for donation based on center hours."""
    center = get_center_name(facility_code).replace(" ", "_").upper()
    if center not in center_hours:
        return donation_date + timedelta(days=2)  # fallback if unknown
    
    open_days = [day for day, hours in center_hours[center].items() if "CLOSED" not in hours.upper()]
    check_date = donation_date + timedelta(days=2)
    while check_date.strftime('%A') not in open_days:
        check_date += timedelta(days=1)
    
    return check_date

def detect_date_format(date_sample):
    """Auto-detect date format from sample."""
    if pd.isna(date_sample):
        return None
    
    date_str = str(date_sample)
    
    # Check each pattern
    for pattern, date_format in DATE_PATTERNS:
        if re.match(pattern, date_str):
            # Try to parse with this format
            try:
                pd.to_datetime(date_str, format=date_format)
                return date_format
            except:
                continue
    
    # Default fallback
    return None

def process_donation_data(df, donor_name_col, donation_date_col, facility_col):
    """Process donation data for scheduling."""
    try:
        # Fetch center hours from GitHub
        response = requests.get("https://olgamlife.github.io/chatbot/hoursolgam.json")
        center_hours = response.json()
        
        # Auto-detect date format from the first non-null value
        date_format = None
        for date_val in df[donation_date_col]:
            if not pd.isna(date_val):
                date_format = detect_date_format(date_val)
                if date_format:
                    break
        
        # Process DataFrame
        if date_format:
            st.info(f"📅 Detected date format: {date_format}")
            df['Donation Date'] = pd.to_datetime(df[donation_date_col], format=date_format, errors='coerce')
        else:
            # Fallback to pandas auto-detection
            df['Donation Date'] = pd.to_datetime(df[donation_date_col], errors='coerce')
        
        # Check for invalid dates and notify user
        invalid_dates = df['Donation Date'].isna().sum()
        if invalid_dates > 0:
            st.warning(f"⚠️ {invalid_dates} dates could not be parsed. Please check your data.")
        
        df['Donor Name'] = df[donor_name_col]
        df['Facility'] = df[facility_col]
        df['First_Name'] = df['Donor Name'].apply(extract_first_name)
        df['Center_Name'] = df['Facility'].apply(get_center_name)
        df['Next_Donation_Date'] = df.apply(
            lambda row: get_next_open_date(row['Donation Date'], row['Facility'], center_hours) 
            if not pd.isna(row['Donation Date']) else pd.NaT, 
            axis=1
        )
        df['Date_to_Send'] = df['Next_Donation_Date'].dt.date  # For filtering in Google Sheets
        
        # Output for Google Sheet
        processed_df = df[['Donor Name', 'First_Name', 'Facility', 'Center_Name', 'Donation Date',
                    'Next_Donation_Date', 'Date_to_Send']]
        
        # Get Google Sheets connection
        gc = get_google_sheets_connection()
        workbook = gc.open_by_key(SPREADSHEET_KEY)
        
        # Try to get the worksheet, if it doesn't exist, create it
        try:
            worksheet = workbook.worksheet(WORKSHEET_NAME)
        except:
            worksheet = workbook.add_worksheet(WORKSHEET_NAME, rows=1000, cols=10)
            # Add headers
            headers = ['Donor Name', 'First Name', 'Facility', 'Center Name', 'Donation Date',
                      'Next Donation Date', 'Date to Send']
            worksheet.append_row(headers)
        
        # Save to Google Sheets
        return save_to_gsheets(processed_df, worksheet), processed_df, WORKSHEET_NAME
        
    except Exception as e:
        st.error(f"Error processing donation data: {str(e)}")
        return False, None, None

def render_donation_scheduler_ui(df):
    """Render UI for donation scheduler process."""
    st.markdown("### Map Columns")
    
    # Add helpful instructions
    with st.expander("Instructions for using the Donation Scheduler", expanded=True):
        st.markdown("""
        **How to use the Donation Scheduler:**
        
        1. Select the appropriate columns from your data:
           - **Donor Name Column**: The column containing donor names (typically in 'Last, First' format)
           - **Donation Date Column**: The column containing donation dates
           - **Facility Code Column**: The column containing facility codes (e.g., OLX, OLW)
        
        2. Click "Process Donation Data" to:
           - Extract first names from full names
           - Map facility codes to center names
           - Calculate the next available donation date based on center hours
           - Save results to Google Sheets
        
        The date format will be automatically detected from your data.
        """)
    
    st.markdown("Please select which columns contain the required information:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        donor_name_col = st.selectbox("Donor Name Column", df.columns.tolist())
        donation_date_col = st.selectbox("Donation Date Column", df.columns.tolist())
    
    with col2:
        facility_col = st.selectbox("Facility Code Column", df.columns.tolist())
        
        # Show examples of the current date format
        if donation_date_col in df.columns:
            st.markdown("#### Date Preview")
            date_samples = df[donation_date_col].head(3).to_string(index=False)
            st.text(f"Example dates from your file:\n{date_samples}")
            
            # Try to detect and show the format
            for date_val in df[donation_date_col]:
                if not pd.isna(date_val):
                    detected_format = detect_date_format(date_val)
                    if detected_format:
                        st.success(f"✅ Date format will be auto-detected")
                        break
    
    if st.button("Process Donation Data"):
        with st.spinner("Processing donation data and updating Google Sheets..."):
            success, processed_df, worksheet_name = process_donation_data(
                df, donor_name_col, donation_date_col, facility_col
            )
            
            if success and processed_df is not None:
                st.success(f"✅ Donation data successfully processed and saved to {worksheet_name}!")
                
                # Display statistics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Donations", len(processed_df))
                with col2:
                    st.metric("Unique Donors", len(processed_df['Donor Name'].unique()))
                with col3:
                    st.metric("Centers", len(processed_df['Center_Name'].unique()))
                
                # Show preview of processed data
                st.markdown("### Preview of Processed Data")
                st.dataframe(processed_df.head(10))
            else:
                st.error("❌ Failed to process donation data.") 