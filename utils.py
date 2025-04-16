import pandas as pd
import gspread
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials

def format_name(name):
    """Format name to capitalize only the first letter of each word."""
    if pd.isna(name):
        return name
    # Split the name into words and capitalize only the first letter
    return ' '.join(word.lower().capitalize() for word in str(name).split())

def read_file(file, has_headers):
    """Read file based on its extension."""
    try:
        if file.name.endswith('.csv'):
            return pd.read_csv(file, header=0 if has_headers else None)
        elif file.name.endswith('.xlsx'):
            return pd.read_excel(file, header=0 if has_headers else None)
        elif file.name.endswith('.txt'):
            # First try comma separator
            try:
                df = pd.read_csv(file, sep=',', header=0 if has_headers else None)
                # Check if we got more than one column
                if len(df.columns) > 1:
                    return df
            except:
                pass
            
            # If comma didn't work, try tab separator
            return pd.read_csv(file, sep='\t', header=0 if has_headers else None)
        else:
            raise ValueError("Unsupported file format. Please upload CSV, XLSX, or TXT file.")
    except Exception as e:
        raise ValueError(f"Error reading file: {str(e)}")

def save_to_gsheets(df, worksheet):
    """Append dataframe to Google Sheets."""
    try:
        # Get the last row with data
        last_row = len(worksheet.get_all_values())
        
        # Replace NaN values with empty strings
        df_clean = df.fillna('')
        
        # Append new records starting from the next row
        worksheet.append_rows(
            df_clean.values.tolist(),
            value_input_option='RAW',
            insert_data_option='INSERT_ROWS',
            table_range=f'A{last_row + 1}'
        )
        return True
    except Exception as e:
        st.error(f"Error saving to Google Sheets: {str(e)}")
        return False

def get_google_sheets_connection():
    """Setup Google Sheets connection."""
    scope = ['https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive']
    credentials_dict = {
        "type": "service_account",
        "project_id": "third-hangout-387516",
        "private_key_id": st.secrets["private_key_id"],
        "private_key": st.secrets["google_credentials"],
        "client_email": "apollo-miner@third-hangout-387516.iam.gserviceaccount.com",
        "client_id": "114223947184571105588",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/apollo-miner%40third-hangout-387516.iam.gserviceaccount.com",
        "universe_domain": "googleapis.com"
    }
    
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
    return gspread.authorize(credentials)

def clear_session_state():
    """Clear all session state variables except password_correct."""
    for key in list(st.session_state.keys()):
        if key != "password_correct":
            del st.session_state[key] 