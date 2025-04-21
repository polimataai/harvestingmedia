# Harvesting Media - Data Processor

A Streamlit application for processing and uploading data to Google Sheets for different Harvesting Media processes.

## Project Structure

The application has been refactored into a modular structure:

- **app.py**: Main application file that handles the UI setup, authentication, and routes to specific process modules
- **auth.py**: Contains the password authentication functionality
- **utils.py**: Contains utility functions used across different processes
- **certo_market.py**: Process module for Certo Market data
- **ferreira.py**: Process module for Ferreira data
- **certo_market_visits.py**: Process module for Certo Market Visits Report data
- **donation_scheduler.py**: Process module for scheduling follow-up donation appointments
- **key_food.py**: Process module for Key Food Valley Stream data
- **market_place.py**: Process module for The Market Place data

## Running the Application

1. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the Streamlit application:
   ```
   streamlit run app.py
   ```

## Processes

The application supports six different data processing workflows:

1. **Certo Market**: Processes customer data for Certo Market
2. **Ferreira**: Processes customer data for Ferreira stores, including store number
3. **Certo Market Visits Report**: Processes marketing report data for Certo Market including registration dates, first order dates, and spent amounts
4. **Donation Scheduler**: Processes donation data to schedule follow-up appointments based on center availability and donor history
5. **Key Food Valley Stream**: Processes customer data from CSV files for Key Food Valley Stream
6. **The Market Place**: Processes customer data from XLSX files for The Market Place

Each process has its own module with dedicated UI and data processing functions. 