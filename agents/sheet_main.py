import os
import json
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from datetime import date

# Import the GoogleSheetManager class from your conceptual 'google_sheet_manager.py' file.
# In a real environment, you would ensure 'google_sheet_manager.py' is in the same directory
# or on your Python path.
try:
    from google_sheet_manager import GoogleSheetManager
except ImportError:
    print("Error: 'google_sheet_manager' module not found.")
    print("Please ensure google_sheet_manager.py is accessible in your environment.")
    exit()

# --- Configuration (matching agent defaults) ---
MY_SPREADSHEET_ID = os.getenv('BUDGET_SPREADSHEET_ID', 'YOUR_SPREADSHEET_ID_HERE') # <--- CHANGE THIS!
DEFAULT_SHEET_NAME = 'Sheet1'
DEFAULT_START_EXPENSE_ROW = 7 # Assuming headers and budget info are in rows 1-6

if __name__ == "__main__":
    # IMPORTANT: Ensure GOOGLE_SHEET_CREDENTIALS environment variable is set
    # with the JSON content of your Google Service Account key file.

    print("--- Initializing GoogleSheetManager ---")
    sheet_manager = GoogleSheetManager()

    if not sheet_manager.service:
        print("Exiting as GoogleSheetManager could not be initialized (authentication failed).")
        exit()

    print("\n--- Direct Manager Workflow Started ---")

    # Task 1: Insert 3 specific rows of data
    print("\n--- Task 1: Inserting specific expense rows ---")
    # Date format from user is DD/MM/YYYY, converting to YYYY-MM-DD for consistency with date parsing functions
    # For dates to display correctly in Google Sheets, ensure the column is formatted as 'Date'.
    # In Google Sheets: Select the column (e.g., Column A), then go to Format -> Number -> Date.
    new_expense_rows = [
        [f"{date.today().strftime('%Y-%m-%d')}", 'Food', 11.0],
        [f"{date.today().strftime('%Y-%m-%d')}", 'Lunch', 50.0],
        [f"{date.today().strftime('%Y-%m-%d')}", 'Transport', 100.0]
    ]
    
    # Using append_row, which will add these rows at the first available row after DEFAULT_START_EXPENSE_ROW
    append_success = sheet_manager.append_row(
        spreadsheet_id=MY_SPREADSHEET_ID,
        sheet_name=DEFAULT_SHEET_NAME,
        start_row_for_append=DEFAULT_START_EXPENSE_ROW,
        data_to_append=new_expense_rows
    )
    if append_success:
        print("Expense rows inserted successfully.")
    else:
        print("Failed to insert expense rows.")


    # Task 2: Get current budget
    print("\n--- Task 2: Find Current Budget ---")
    current_budget = sheet_manager.get_current_budget(
        spreadsheet_id=MY_SPREADSHEET_ID,
        sheet_name=DEFAULT_SHEET_NAME
    )
    if current_budget is not None:
        print(f"Current Budget: {current_budget:.2f}")
    else:
        print("Could not retrieve current budget.")

    # Task 3: Get total expenses and remaining budget
    print("\n--- Task 3: Find Total Expenses and Remaining Budget ---")
    total_expenses = sheet_manager.get_total_expenses(
        spreadsheet_id=MY_SPREADSHEET_ID,
        sheet_name=DEFAULT_SHEET_NAME,
        start_expense_row=DEFAULT_START_EXPENSE_ROW
    )
    if total_expenses is not None:
        print(f"Total Expenses: {total_expenses:.2f}")
    else:
        print("Could not retrieve total expenses.")

    remaining_budget = sheet_manager.get_remaining_budget(
        spreadsheet_id=MY_SPREADSHEET_ID,
        sheet_name=DEFAULT_SHEET_NAME,
        start_expense_row=DEFAULT_START_EXPENSE_ROW
    )
    if remaining_budget is not None:
        print(f"Remaining Budget: {remaining_budget:.2f}")
    else:
        print("Could not retrieve remaining budget.")

    # Task 4: Calculate daily budget remaining
    print("\n--- Task 4: Calculate Daily Remaining Budget ---")
    daily_remaining_budget = sheet_manager.get_daily_remaining_budget(
        spreadsheet_id=MY_SPREADSHEET_ID,
        sheet_name=DEFAULT_SHEET_NAME,
        start_expense_row=DEFAULT_START_EXPENSE_ROW
    )
    # FIX: Removed :.2f as daily_remaining_budget is already a formatted string
    if daily_remaining_budget is not None:
        print(f"Daily Remaining Budget: {daily_remaining_budget}") 
    else:
        print("Could not calculate daily remaining budget.")

    # Task 5: Show all expenses
    print("\n--- Task 5: Show All Expenses ---")
    all_expenses = sheet_manager.get_all_expenses(
        spreadsheet_id=MY_SPREADSHEET_ID,
        sheet_name=DEFAULT_SHEET_NAME,
        start_expense_row=DEFAULT_START_EXPENSE_ROW,
        expense_columns='A:C' # Assuming date, description, amount are in A, B, C
    )
    if all_expenses:
        print("All Expenses:")
        for row in all_expenses:
            print(row)
    else:
        print("No expenses found or an error occurred.")

    print("\n--- Direct Manager Workflow Complete ---")
