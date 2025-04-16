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
    # YYYY-MM-DD (without time)
    (r'^\d{4}-\d{2}-\d{2}$', '%Y-%m-%d'),
    # YYYY-MM-DD HH:MM:SS
    (r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', '%Y-%m-%d %H:%M:%S'),
    # MM/DD/YYYY
    (r'\d{1,2}/\d{1,2}/\d{4}', '%m/%d/%Y'),
    # DD/MM/YYYY
    (r'\d{1,2}/\d{1,2}/\d{4}', '%d/%m/%Y'),
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
    
    date_str = str(date_sample).strip()
    
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

def save_to_gsheets_with_error_handling(df, worksheet, sheet_key, sheet_name):
    """Save to Google Sheets with detailed error handling."""
    try:
        # Replace NaN values with empty strings
        df_clean = df.fillna('')
        
        # We need to convert the dataframe to a list of lists before converting date objects
        rows = df_clean.values.tolist()
        
        # Convert all date/datetime objects to strings in the rows
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                # Check if the value is a date or datetime object
                if hasattr(val, 'strftime'):  # Both date and datetime have strftime
                    rows[i][j] = val.strftime('%Y-%m-%d')
        
        # Get the last row with data
        last_row = len(worksheet.get_all_values())
        
        # Check worksheet access
        st.write(f"Preparing to write {len(df_clean)} rows to {sheet_name} worksheet...")
        
        # Append new records starting from the next row
        worksheet.append_rows(
            rows,
            value_input_option='RAW',
            insert_data_option='INSERT_ROWS',
            table_range=f'A{last_row + 1}'
        )
        
        st.success(f"✅ Successfully saved data to Google Sheet: {sheet_key}, worksheet: {sheet_name}")
        return True
    except Exception as e:
        st.error(f"❌ Error saving to Google Sheets: {str(e)}")
        # Include more detailed error information
        import traceback
        st.code(traceback.format_exc())
        return False

def process_donation_data(df, donor_name_col, donation_date_col, facility_col, donor_account_col=None, donor_phone_col=None):
    """Process donation data for scheduling."""
    try:
        # Fetch center hours from GitHub
        try:
            st.info("📅 Fetching center hours from OLGAM API...")
            response = requests.get("https://olgamlife.github.io/chatbot/hoursolgam.json", timeout=10)
            response.raise_for_status()  # Raise error for bad responses
            center_hours = response.json()
            st.success("✅ Successfully fetched center hours")
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Error fetching center hours: {str(e)}")
            st.warning("⚠️ Will use fallback scheduling (2 days after donation)")
            # Create empty dict as fallback
            center_hours = {}
            
        # Show the facility codes in the data vs. known centers
        unique_facilities = df[facility_col].dropna().unique().tolist()
        st.write(f"Facility codes in data: {', '.join(unique_facilities)}")
        mapped_centers = [f"{code} → {get_center_name(code)}" for code in unique_facilities]
        st.write(f"Mapped to centers: {', '.join(mapped_centers)}")
        
        # Auto-detect date format from the first non-null value
        date_format = None
        for date_val in df[donation_date_col]:
            if not pd.isna(date_val):
                date_format = detect_date_format(str(date_val).strip())
                if date_format:
                    break
        
        # Process DataFrame
        if date_format:
            st.info(f"📅 Detected date format: {date_format}")
            try:
                df['Donation Date'] = pd.to_datetime(df[donation_date_col], format=date_format, errors='coerce')
                
                # Show helpful information for debugging
                if df['Donation Date'].isna().all():
                    st.error("❌ Failed to parse any dates with the detected format. Trying alternative formats...")
                    # Try without a specific format as fallback
                    df['Donation Date'] = pd.to_datetime(df[donation_date_col], errors='coerce')
            except Exception as e:
                st.error(f"❌ Error parsing dates: {str(e)}. Trying alternative approach...")
                # Fallback to pandas auto-detection
                df['Donation Date'] = pd.to_datetime(df[donation_date_col], errors='coerce')
        else:
            # Fallback to pandas auto-detection
            st.warning("⚠️ Could not detect date format. Trying pandas auto-detection...")
            df['Donation Date'] = pd.to_datetime(df[donation_date_col], errors='coerce')
        
        # Check for invalid dates and notify user
        invalid_dates = df['Donation Date'].isna().sum()
        if invalid_dates > 0:
            st.warning(f"⚠️ {invalid_dates} dates could not be parsed. Please check your data.")
            
            # If all dates failed, show sample data to help debugging
            if invalid_dates == len(df):
                st.error("❌ All dates failed to parse! Sample of your data:")
                st.write(df[donation_date_col].head(3).tolist())
                return False, None, None
        
        # Continue with processing
        df['Donor Name'] = df[donor_name_col]
        df['Facility'] = df[facility_col]
        # Add donor account and phone if provided
        if donor_account_col:
            df['Donor Account'] = df[donor_account_col]
        if donor_phone_col:
            df['Donor Phone'] = df[donor_phone_col]
        df['First_Name'] = df['Donor Name'].apply(extract_first_name)
        df['Center_Name'] = df['Facility'].apply(get_center_name)
        
        # Show more debugging information
        st.write("Processing center data and calculating next donation dates...")
        
        df['Next_Donation_Date'] = df.apply(
            lambda row: get_next_open_date(row['Donation Date'], row['Facility'], center_hours) 
            if not pd.isna(row['Donation Date']) else pd.NaT, 
            axis=1
        )
        
        # Convert date.date to string to avoid serialization issues
        df['Date_to_Send'] = df['Next_Donation_Date'].dt.strftime('%Y-%m-%d')
        
        # Create the output dataframe with all necessary columns
        output_columns = ['Donor Name', 'First_Name']
        
        # Add optional columns if they exist
        if 'Donor Account' in df.columns:
            output_columns.append('Donor Account')
        if 'Donor Phone' in df.columns:
            output_columns.append('Donor Phone')
            
        # Add remaining columns
        output_columns.extend(['Facility', 'Center_Name', 'Donation Date', 
                              'Next_Donation_Date', 'Date_to_Send'])
        
        # Output for Google Sheet
        processed_df = df[output_columns]
        
        # Show summary of processed data
        valid_donations = processed_df['Donation Date'].notna().sum()
        valid_next_dates = processed_df['Next_Donation_Date'].notna().sum()
        
        st.write(f"Successfully processed {valid_donations} donations")
        st.write(f"Scheduled {valid_next_dates} next donation dates")
        
        # Get Google Sheets connection
        try:
            st.info("📊 Connecting to Google Sheets...")
            gc = get_google_sheets_connection()
            workbook = gc.open_by_key(SPREADSHEET_KEY)
            st.success("✅ Successfully connected to Google Sheets")
            
            # Try to get the worksheet, if it doesn't exist, create it
            try:
                worksheet = workbook.worksheet(WORKSHEET_NAME)
                st.write(f"Found existing worksheet: {WORKSHEET_NAME}")
            except:
                st.write(f"Creating new worksheet: {WORKSHEET_NAME}")
                worksheet = workbook.add_worksheet(WORKSHEET_NAME, rows=1000, cols=10)
                
                # Add headers that include the new columns
                headers = ['Donor Name', 'First Name']
                if 'Donor Account' in df.columns:
                    headers.append('Donor Account')
                if 'Donor Phone' in df.columns:
                    headers.append('Donor Phone')
                
                headers.extend(['Facility', 'Center Name', 'Donation Date',
                              'Next Donation Date', 'Date to Send'])
                
                worksheet.append_row(headers)
            
            # Save to Google Sheets using enhanced error handling
            if save_to_gsheets_with_error_handling(processed_df, worksheet, SPREADSHEET_KEY, WORKSHEET_NAME):
                return True, processed_df, WORKSHEET_NAME
            else:
                return False, processed_df, WORKSHEET_NAME
                
        except Exception as e:
            st.error(f"❌ Error connecting to Google Sheets: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
            return False, processed_df, WORKSHEET_NAME
        
    except Exception as e:
        st.error(f"Error processing donation data: {str(e)}")
        # Show more detailed error for debugging
        import traceback
        st.code(traceback.format_exc())
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
           - **Donor Account Column**: The column containing donor account numbers
           - **Donor Phone Column**: The column containing donor phone numbers
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
    
    # Get column names from dataframe
    columns = df.columns.tolist()
    
    # Define patterns for automatic column detection
    donor_name_patterns = ['donor name', 'donor', 'name', 'full name']
    donor_account_patterns = ['donor #', 'donor account', 'account', 'donor number', 'donor id', 'id']
    donor_phone_patterns = ['donor phone', 'phone', 'phone number', 'contact', 'telephone']
    donation_date_patterns = ['donation date', 'date', 'donation time', 'draw date']
    facility_patterns = ['facility', 'center', 'location', 'center code', 'facility code']
    
    # Find default column indices
    donor_name_default = find_column_by_pattern(columns, donor_name_patterns)
    donor_account_default = find_column_by_pattern(columns, donor_account_patterns)
    donor_phone_default = find_column_by_pattern(columns, donor_phone_patterns)
    donation_date_default = find_column_by_pattern(columns, donation_date_patterns)
    facility_default = find_column_by_pattern(columns, facility_patterns)
    
    col1, col2 = st.columns(2)
    
    with col1:
        donor_name_col = st.selectbox(
            "Donor Name Column", 
            columns,
            index=donor_name_default
        )
        donor_account_col = st.selectbox(
            "Donor Account Column", 
            columns,
            index=donor_account_default
        )
        donor_phone_col = st.selectbox(
            "Donor Phone Column", 
            columns,
            index=donor_phone_default
        )
    
    with col2:
        donation_date_col = st.selectbox(
            "Donation Date Column", 
            columns,
            index=donation_date_default
        )
        facility_col = st.selectbox(
            "Facility Code Column", 
            columns,
            index=facility_default
        )
        
        # Show examples of the current date format
        if donation_date_col in df.columns:
            st.markdown("#### Date Preview")
            date_samples = df[donation_date_col].head(3).to_string(index=False)
            st.text(f"Example dates from your file:\n{date_samples}")
            
            # Try to detect and show the format
            for date_val in df[donation_date_col]:
                if not pd.isna(date_val):
                    detected_format = detect_date_format(str(date_val).strip())
                    if detected_format:
                        st.success(f"✅ Date format will be auto-detected")
                        break
    
    if st.button("Process Donation Data"):
        with st.spinner("Processing donation data and updating Google Sheets..."):
            success, processed_df, worksheet_name = process_donation_data(
                df, donor_name_col, donation_date_col, facility_col, donor_account_col, donor_phone_col
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

# Example usage
if __name__ == "__main__":
    render_donation_scheduler_ui(pd.DataFrame({
        'Donor Name': ['John Doe', 'Jane Smith'],
        'Donor Account': ['123456789', '987654321'],
        'Donor Phone': ['555-1234', '555-5678'],
        'Donation Date': ['2024-05-01', '2024-05-02'],
        'Facility': ['OLX', 'OLW']
    })) 