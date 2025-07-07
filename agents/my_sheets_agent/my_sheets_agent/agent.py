# agent.py
import os
import yaml # NEW: Import yaml library to parse config.yaml
from datetime import datetime
from typing import List, Any, Optional, Union

# Import ADK components
from google.adk.agents import LlmAgent # Changed from Agent to LlmAgent for consistency with ADK
from google.adk.tools import tool, Tool

# Import your GoogleSheetManager and get_secret helper
from google_sheet_manager import GoogleSheetManager, get_secret

# --- Module-Level Configuration and Initialization (Runs ONCE per Cloud Function Cold Start) ---

CONFIG_FILE_PATH = 'config.yaml' # Define the path to your config file

# 1. Load configuration from config.yaml
print(f"[{datetime.now()}] Loading configuration from {CONFIG_FILE_PATH}...")
config = {}
try:
    with open(CONFIG_FILE_PATH, 'r') as f:
        config = yaml.safe_load(f)
    if not config:
        raise ValueError("Config file is empty or invalid.")
    print("Configuration loaded successfully.")
except FileNotFoundError:
    print(f"FATAL ERROR: Configuration file not found at {CONFIG_FILE_PATH}. Agent cannot proceed.")
    exit(1) # Exit if critical config is missing
except yaml.YAMLError as e:
    print(f"FATAL ERROR: Error parsing YAML file {CONFIG_FILE_PATH}: {e}. Agent cannot proceed.")
    exit(1) # Exit if critical config is malformed
except ValueError as e:
    print(f"FATAL ERROR: Configuration error in {CONFIG_FILE_PATH}: {e}. Agent cannot proceed.")
    exit(1) # Exit if critical config is problematic

# 2. Extract configuration values from the loaded YAML
# Use .get() with a default or check for None and exit for critical values
YOUR_GCP_PROJECT_ID = config.get('gcp_project_id')
if not YOUR_GCP_PROJECT_ID:
    print("FATAL ERROR: 'gcp_project_id' not found in config.yaml. Agent cannot proceed.")
    exit(1)

GOOGLE_SHEET_CREDS_SECRET_ID = config.get('service_account_creds_secret_id')
MY_SPREADSHEET_ID_SECRET_ID = config.get('spreadsheet_id_secret_id')

if not GOOGLE_SHEET_CREDS_SECRET_ID:
    print("FATAL ERROR: 'service_account_creds_secret_id' not found in config.yaml. Agent cannot proceed.")
    exit(1)
if not MY_SPREADSHEET_ID_SECRET_ID:
    print("FATAL ERROR: 'spreadsheet_id_secret_id' not found in config.yaml. Agent cannot proceed.")
    exit(1)

# Non-sensitive sheet structure constants (with defaults from config.yaml or hardcoded fallback)
DEFAULT_SHEET_NAME = config.get('default_sheet_name', 'Expenses')
DEFAULT_START_EXPENSE_ROW = config.get('default_start_expense_row', 7)


# 3. Retrieve actual secrets from Secret Manager using the IDs from config.yaml
print(f"[{datetime.now()}] Attempting to retrieve secrets from Secret Manager...")

MY_SPREADSHEET_ID = get_secret(YOUR_GCP_PROJECT_ID, MY_SPREADSHEET_ID_SECRET_ID)
if not MY_SPREADSHEET_ID:
    print(f"FATAL ERROR: Could not retrieve Spreadsheet ID from Secret Manager secret '{MY_SPREADSHEET_ID_SECRET_ID}'. Agent will not function.")
    exit(1) # Exit if a crucial secret cannot be retrieved

SERVICE_ACCOUNT_JSON_STRING = get_secret(YOUR_GCP_PROJECT_ID, GOOGLE_SHEET_CREDS_SECRET_ID)
if not SERVICE_ACCOUNT_JSON_STRING:
    print(f"FATAL ERROR: Could not retrieve service account JSON from Secret Manager secret '{GOOGLE_SHEET_CREDS_SECRET_ID}'. Agent will not function.")
    exit(1) # Exit if a crucial secret cannot be retrieved


# 4. Initialize the GoogleSheetManager instance with resolved secrets
print(f"[{datetime.now()}] Initializing GoogleSheetManager with resolved credentials...")
sheet_manager_instance = None
try:
    # Pass the actual spreadsheet ID and the service account JSON string
    # This assumes your GoogleSheetManager's __init__ now accepts these directly
    sheet_manager_instance = GoogleSheetManager(MY_SPREADSHEET_ID, SERVICE_ACCOUNT_JSON_STRING)
except RuntimeError as e:
    print(f"CRITICAL ERROR: GoogleSheetManager failed to initialize: {e}. Sheet-related tools will be unavailable.")


# --- Define ADK Tools (Wrapper Functions) ---
adk_agent_tools = [] # This list will hold the functions provided to the ADK Agent

# Only define and add tools if the sheet_manager_instance was successfully created and authenticated
if sheet_manager_instance and sheet_manager_instance.service:
    # --- Expense Tools ---
    @tool
    def add_expense(date_str: str, description: str, amount: float) -> Optional[str]:
        """
        Adds a new expense record to the budget Google Sheet.
        Args:
            date_str (str): The date of the expense in 'YYYY-MM-DD' format (e.g., '2025-07-07').
            description (str): A brief description of the expense (e.g., 'Groceries', 'Coffee').
            amount (float): The monetary amount of the expense (e.g., 20.50).
        Returns:
            Optional[str]: The updated range string (e.g., 'Expenses!A10:C11') if successful, or None on error.
        """
        data_to_append = [[f'="{date_str}"', description, amount]]
        return sheet_manager_instance.append_row_internal(
            spreadsheet_id=MY_SPREADSHEET_ID,
            sheet_name=DEFAULT_SHEET_NAME,
            start_row_for_append=DEFAULT_START_EXPENSE_ROW,
            data_to_append=data_to_append
        )
    adk_agent_tools.append(add_expense)

    @tool
    def list_all_expenses_data() -> Optional[List[List[Any]]]:
        """
        Retrieves and returns all expense records from the budget Google Sheet.
        Each record is a list, typically [Date, Description, Amount].
        Returns:
            Optional[List[List[Any]]]: A list of expense records, or None if an error occurs.
        """
        expense_columns = 'A:C' # Adjust these columns if your expenses span different columns
        return sheet_manager_instance.get_all_expenses_data_internal(
            spreadsheet_id=MY_SPREADSHEET_ID,
            sheet_name=DEFAULT_SHEET_NAME,
            start_expense_row=DEFAULT_START_EXPENSE_ROW,
            expense_columns=expense_columns
        )
    adk_agent_tools.append(list_all_expenses_data)

    # --- Budget Calculation Tools ---
    @tool
    def get_current_budget_total() -> Optional[float]:
        """
        Retrieves the total budget amount from the Google Sheet (assumed from cell B1).
        Returns:
            Optional[float]: The budget amount as a float, or None if not found or not numeric.
        """
        return sheet_manager_instance.get_budget_amount_internal(
            spreadsheet_id=MY_SPREADSHEET_ID,
            sheet_name=DEFAULT_SHEET_NAME
        )
    adk_agent_tools.append(get_current_budget_total)

    @tool
    def calculate_remaining_budget_value() -> Union[int, float, None]:
        """
        Calculates the remaining budget by subtracting total expenses from the total budget.
        Returns:
            Union[int, float, None]: The remaining budget value, or None if data cannot be retrieved.
        """
        return sheet_manager_instance.get_remaining_budget_value_internal(
            spreadsheet_id=MY_SPREADSHEET_ID,
            sheet_name=DEFAULT_SHEET_NAME,
            start_expense_row=DEFAULT_START_EXPENSE_ROW
        )
    adk_agent_tools.append(calculate_remaining_budget_value)

    @tool
    def get_days_left_in_budget_period() -> Optional[int]:
        """
        Calculates and returns the number of remaining days in the current budget period.
        The period is defined by start/end dates in cells B3/B4 of the Google Sheet (YYYY-MM-DD format).
        Returns:
            Optional[int]: The number of days remaining (including today), or 0 if the period has ended, or None on error.
        """
        return sheet_manager_instance.get_remaining_days_in_period_internal(
            spreadsheet_id=MY_SPREADSHEET_ID,
            sheet_name=DEFAULT_SHEET_NAME
        )
    adk_agent_tools.append(get_days_left_in_budget_period)

    @tool
    def get_daily_budget_breakdown_string() -> Optional[str]:
        """
        Provides a detailed breakdown of the remaining budget, including remaining amount,
        estimated daily allowance, and days left in the period.
        Returns:
            Optional[str]: A formatted string (e.g., '£150.00 (£30.00 per day for 5 days left)'),
                           or just the remaining amount if over budget, or None on error.
        """
        return sheet_manager_instance.get_daily_remaining_budget_str_internal(
            spreadsheet_id=MY_SPREADSHEET_ID,
            sheet_name=DEFAULT_SHEET_NAME,
            start_expense_row=DEFAULT_START_EXPENSE_ROW
        )
    adk_agent_tools.append(get_daily_budget_breakdown_string)

    # --- General Sheet Interaction Tools (if you want these exposed) ---
    @tool
    def insert_new_empty_row(insert_at_row_index: int, num_rows: int = 1) -> bool:
        """
        Inserts one or more empty rows into the Google Sheet at a specified 1-based index.
        This shifts existing rows down. Useful for creating space.

        Args:
            insert_at_row_index (int): The 1-based index where new rows will be inserted.
                                       For example, 1 to insert at the very top, 7 to insert before row 7.
            num_rows (int): The number of rows to insert (default is 1).
        Returns:
            bool: True if rows were successfully inserted, False otherwise.
        """
        return sheet_manager_instance.insert_empty_row_internal(
            spreadsheet_id=MY_SPREADSHEET_ID,
            sheet_name=DEFAULT_SHEET_NAME,
            insert_at_row_index=insert_at_row_index,
            num_rows=num_rows
        )
    adk_agent_tools.append(insert_new_empty_row)

    @tool
    def calculate_column_total(range_name: str, column_index: int) -> Union[int, float, None]:
        """
        Calculates the sum of numeric values in a specific column within a given range of a Google Sheet.

        Args:
            range_name (str): The A1 notation of the range to read (e.g., "Sheet1!A1:D5", or "Sheet1!C:C").
                              The sum will be calculated within this specified range.
            column_index (int): The 0-based index of the column to sum *relative to the given range*.
                                 If range_name is a single column (e.g., 'Sheet1!C:C'), this should be 0.
                                 If range_name is multiple columns (e.g., 'Sheet1!A:D'), this should be
                                 the appropriate index for that wider range (e.g., 2 for column C).
        Returns:
            Union[int, float, None]: The sum of the column values if successful,
                                     0 if no numeric data is found, or None if an error occurs.
        """
        return sheet_manager_instance.calculate_column_sum_internal(
            spreadsheet_id=MY_SPREADSHEET_ID,
            range_name=range_name,
            column_index=column_index
        )
    adk_agent_tools.append(calculate_column_total)

    @tool
    def read_sheet_range(range_name: str) -> Optional[List[List[Any]]]:
        """
        Reads all data from a specified range in the Google Sheet.

        Args:
            range_name (str): The A1 notation or R1C1 notation of the range to retrieve (e.g., "Sheet1!A1:C10" or "Sheet1!A:C").

        Returns:
            Optional[List[List[Any]]]: A list of lists representing the data, or an empty list if no data, or None on error.
        """
        return sheet_manager_instance.read_sheet_data_internal(
            spreadsheet_id=MY_SPREADSHEET_ID,
            range_name=range_name
        )
    adk_agent_tools.append(read_sheet_range)

else:
    print("WARNING: GoogleSheetManager not ready. Agent will not have access to Google Sheet tools.")


# --- Initialize the ADK Agent Instance ---
LLM_MODEL_NAME = "gemini-1.5-flash-latest"

budget_agent = LlmAgent( # Changed from Agent to LlmAgent
    name="BudgetManager",
    description="An intelligent AI assistant specialized in managing personal budgets within a Google Sheet. It can add new expenses, retrieve financial summaries, list past transactions, and provide insights into daily spending.",
    model=LLM_MODEL_NAME,
    tools=adk_agent_tools, # Provide the list of pre-configured wrapper tools here
    system_prompt=(
        "You are a helpful, accurate, and detailed personal budget manager. "
        "Your primary goal is to assist the user by interacting with their Google Sheet using the available tools. "
        "Always prioritize using the specific tools provided to answer questions about budget, expenses, or daily limits. "
        "When asked to add an expense, always confirm you have the date (default to today, {current_date}, if not specified), "
        "a clear description of the expense, and the exact monetary amount. "
        "Provide clear and concise responses based on the tool outputs. "
        "Be proactive in offering budget insights and help the user stay on track. "
        "The current date is {current_date}."
    ).format(current_date=datetime.now().strftime('%Y-%m-%d')), # Inject current date into prompt for context
)