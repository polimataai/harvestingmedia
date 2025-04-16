import streamlit as st
import pandas as pd
import requests
from datetime import timedelta
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

# Common date formats with their pandas format strings
DATE_FORMATS = {
    "MM/DD/YYYY (e.g., 01/31/2023)": "%m/%d/%Y",
    "DD/MM/YYYY (e.g., 31/01/2023)": "%d/%m/%Y",
    "YYYY-MM-DD (e.g., 2023-01-31)": "%Y-%m-%d",
    "MM-DD-YYYY (e.g., 01-31-2023)": "%m-%d-%Y",
    "DD-MM-YYYY (e.g., 31-01-2023)": "%d-%m-%Y",
    "YYYY/MM/DD (e.g., 2023/01/31)": "%Y/%m/%d",
}

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

def process_donation_data(df, donor_name_col, donation_date_col, facility_col, date_format=None):
    """Process donation data for scheduling."""
    try:
        # Fetch center hours from GitHub
        response = requests.get("https://olgamlife.github.io/chatbot/hoursolgam.json")
        center_hours = response.json()
        
        # Process DataFrame
        if date_format:
            df['Donation Date'] = pd.to_datetime(df[donation_date_col], format=date_format, errors='coerce')
        else:
            df['Donation Date'] = pd.to_datetime(df[donation_date_col], errors='coerce')
        
        # Check for invalid dates and notify user
        invalid_dates = df['Donation Date'].isna().sum()
        if invalid_dates > 0:
            st.warning(f"⚠️ {invalid_dates} dates could not be parsed. Please check the date format.")
        
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
    st.markdown("Please select which columns contain the required information:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        donor_name_col = st.selectbox("Donor Name Column", df.columns.tolist())
        donation_date_col = st.selectbox("Donation Date Column", df.columns.tolist())
        
        # Add date format selection
        date_format_description = st.selectbox(
            "Donation Date Format",
            list(DATE_FORMATS.keys()),
            help="Select the format of your donation dates"
        )
        date_format = DATE_FORMATS[date_format_description]
    
    with col2:
        facility_col = st.selectbox("Facility Code Column", df.columns.tolist())
        
        # Show examples of the current date format
        if donation_date_col in df.columns:
            st.markdown("#### Date Preview")
            st.text(f"Example dates from your file:\n{df[donation_date_col].head(3).to_string(index=False)}")
    
    if st.button("Process Donation Data"):
        with st.spinner("Processing donation data and updating Google Sheets..."):
            success, processed_df, worksheet_name = process_donation_data(
                df, donor_name_col, donation_date_col, facility_col, date_format
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