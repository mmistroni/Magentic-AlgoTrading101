import os
import yaml
from datetime import datetime
from typing import Optional, Tuple

# Assuming google_sheet_manager is in the same or a discoverable path
from adk_gsheet_agent.google_sheet_manager import GoogleSheetManager, get_secret

# --- Module-Level Configuration Constant ---
CONFIG_FILE_PATH = 'config.yaml'

def initialize_agent_dependencies() -> Tuple[Optional[GoogleSheetManager], str, str, int]:
    """
    Loads configuration from config.yaml, retrieves secrets from Secret Manager,
    and initializes the GoogleSheetManager. Exits the process if critical
    configurations or secrets are missing.

    This function runs ONCE per Cloud Function cold start.

    Returns:
        Tuple[Optional[GoogleSheetManager], str, str, int]:
            - Initialized GoogleSheetManager instance (None if initialization fails).
            - The resolved Google Spreadsheet ID.
            - The default sheet name for operations.
            - The default start row for expense data.
    """
    print(f"[{datetime.now()}] Starting agent dependency initialization...")
    # remeber to call gcloud auth application-default login
    # 1. Load configuration from config.yaml
    config = {}
    try:
        with open(CONFIG_FILE_PATH, 'r') as f:
            config = yaml.safe_load(f)
        if not config:
            raise ValueError("Config file is empty or invalid.")
        print(f"[{datetime.now()}] Configuration loaded successfully from {CONFIG_FILE_PATH}.")
    except FileNotFoundError:
        print(f"FATAL ERROR: Configuration file not found at {CONFIG_FILE_PATH}. Agent cannot proceed.")
        exit(1) # Critical error, terminate cold start
    except yaml.YAMLError as e:
        print(f"FATAL ERROR: Error parsing YAML file {CONFIG_FILE_PATH}: {e}. Agent cannot proceed.")
        exit(1) # Critical error, terminate cold start
    except ValueError as e:
        print(f"FATAL ERROR: Configuration error in {CONFIG_FILE_PATH}: {e}. Agent cannot proceed.")
        exit(1) # Critical error, terminate cold start

    # 2. Extract configuration values from the loaded YAML
    your_gcp_project_id = config.get('gcp_project_id')
    if not your_gcp_project_id:
        print("FATAL ERROR: 'gcp_project_id' not found in config.yaml. Agent cannot proceed.")
        exit(1) # Critical error, terminate cold start

    google_sheet_creds_secret_id = config.get('service_account_creds_secret_id')
    my_spreadsheet_id_secret_id = config.get('spreadsheet_id_secret_id')

    if not google_sheet_creds_secret_id:
        print("FATAL ERROR: 'service_account_creds_secret_id' not found in config.yaml. Agent cannot proceed.")
        exit(1) # Critical error, terminate cold start
    if not my_spreadsheet_id_secret_id:
        print("FATAL ERROR: 'spreadsheet_id_secret_id' not found in config.yaml. Agent cannot proceed.")
        exit(1) # Critical error, terminate cold start

    # Non-sensitive sheet structure constants with defaults
    default_sheet_name = config.get('default_sheet_name', 'Expenses')
    default_start_expense_row = config.get('default_start_expense_row', 7)


    # 3. Retrieve actual secrets from Secret Manager
    print(f"[{datetime.now()}] Attempting to retrieve secrets from Secret Manager for project '{your_gcp_project_id}'...")

    my_spreadsheet_id = get_secret(your_gcp_project_id, my_spreadsheet_id_secret_id)
    if not my_spreadsheet_id:
        print(f"FATAL ERROR: Could not retrieve Spreadsheet ID from Secret Manager secret '{my_spreadsheet_id_secret_id}'. Agent will not function.")
        exit(1) # Critical error, terminate cold start

    service_account_json_string = get_secret(your_gcp_project_id, google_sheet_creds_secret_id)
    if not service_account_json_string:
        print(f"FATAL ERROR: Could not retrieve service account JSON from Secret Manager secret '{google_sheet_creds_secret_id}'. Agent will not function.")
        exit(1) # Critical error, terminate cold start


    # 4. Initialize the GoogleSheetManager instance
    print(f"[{datetime.now()}] Initializing GoogleSheetManager with resolved credentials...")
    sheet_manager_instance = None
    try:
        sheet_manager_instance = GoogleSheetManager(my_spreadsheet_id, service_account_json_string)
        print(f"[{datetime.now()}] GoogleSheetManager initialized successfully.")
    except RuntimeError as e:
        print(f"CRITICAL ERROR: GoogleSheetManager failed to initialize: {e}. Sheet-related tools will be unavailable.")

    # Return the initialized manager and derived constants
    return sheet_manager_instance, my_spreadsheet_id, default_sheet_name, default_start_expense_row