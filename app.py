import streamlit as st
import pandas as pd

from auth import check_password
from utils import read_file, clear_session_state
from certo_market import render_certo_market_ui
from ferreira import render_ferreira_ui
from certo_market_visits import render_certo_market_visits_ui
from donation_scheduler import render_donation_scheduler_ui
from key_food import render_key_food_ui
from market_place import render_market_place_ui

# Basic page configuration
st.set_page_config(
    page_title="Harvesting Media - Data Processor 2.0",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def format_name(name):
    """Format name to capitalize only the first letter of each word."""
    if pd.isna(name):
        return name
    # Split the name into words and capitalize only the first letter
    return ' '.join(word.lower().capitalize() for word in str(name).split())

def on_process_change():
    """Handle process selection change."""
    clear_session_state()

def main():
    if not check_password():
        st.error("⚠️ Password incorrect. Please try again.")
        return

    # Header
    st.title("🌾 Harvesting Media")
    st.subheader("Data Processor")
    
    # Initialize session state for process if not exists
    if 'previous_process' not in st.session_state:
        st.session_state['previous_process'] = None
    
    # Process selection
    process = st.selectbox(
        "Select Process",
        ["Certo Market", "Ferreira", "Certo Market Visits Report", "Donation Scheduler", 
         "Key Food Valley Stream", "The Market Place"],
        help="Choose which process to run",
        key="process"
    )
    
    # Check if process changed
    if st.session_state['previous_process'] is not None and st.session_state['previous_process'] != process:
        clear_session_state()
        st.session_state['process'] = process
        st.rerun()
    
    # Update previous process
    st.session_state['previous_process'] = process
    
    # File uploader with format detection
    file_extensions = ['csv', 'xlsx', 'txt']
    file_type_message = ""
    
    # Adjust file uploader based on process
    if process == "Key Food Valley Stream":
        file_extensions = ['csv']
        file_type_message = "(CSV format)"
    elif process == "The Market Place":
        file_extensions = ['xlsx']
        file_type_message = "(XLSX format)"
    
    uploaded_file = st.file_uploader(f"Choose a file {file_type_message}", type=file_extensions)
    
    if uploaded_file is not None:
        try:
            # Ask if file has headers
            has_headers = st.checkbox("File has headers", value=True)
            
            # Read the file
            df = read_file(uploaded_file, has_headers)
            
            # If no headers, generate column names
            if not has_headers:
                df.columns = [f'Column {i+1}' for i in range(len(df.columns))]
            
            # Show the first few rows of the data
            st.markdown("### Preview of Data")
            st.dataframe(df.head())
            
            # Route to the appropriate process UI
            if process == "Certo Market":
                render_certo_market_ui(df)
            elif process == "Ferreira":
                render_ferreira_ui(df)
            elif process == "Certo Market Visits Report":
                render_certo_market_visits_ui(df)
            elif process == "Donation Scheduler":
                render_donation_scheduler_ui(df)
            elif process == "Key Food Valley Stream":
                render_key_food_ui(df)
            elif process == "The Market Place":
                render_market_place_ui(df)
                
        except Exception as e:
            st.error(f"❌ Error processing file: {str(e)}")

if __name__ == "__main__":
    main() 