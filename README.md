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

The application supports four different data processing workflows:

1. **Certo Market**: Processes customer data for Certo Market
2. **Ferreira**: Processes customer data for Ferreira stores, including store number
3. **Certo Market Visits Report**: Processes marketing report data for Certo Market including registration dates, first order dates, and spent amounts
4. **Donation Scheduler**: Processes donation data to schedule follow-up appointments based on center availability and donor history

Each process has its own module with dedicated UI and data processing functions. 