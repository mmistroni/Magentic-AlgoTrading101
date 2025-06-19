# spreadsheet_utils.py

import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import List, Any, Optional

# --- Configuration Loading ---
# Load environment variables (requires `python-dotenv` if not already loaded by your main process)
# For this utility file, we assume env vars are already set when it's imported.
# If running this file directly, you'd need `from dotenv import load_dotenv; load_dotenv()` here.
SERVICE_ACCOUNT_FILE = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
if not SERVICE_ACCOUNT_FILE:
    raise EnvironmentError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set.")

# Parse scopes from environment variable. If multiple, separate by comma.
_raw_scopes = os.getenv('GOOGLE_SHEETS_SCOPES', 'https://www.googleapis.com/auth/spreadsheets.readonly')
SCOPES = [s.strip() for s in _raw_scopes.split(',')]

# --- Sheets Service Initialization (Modular and Cached) ---
_sheets_service_instance = None # To store the initialized service object

def get_sheets_service():
    """
    Authenticates with Google Sheets API using the service account file.
    Returns a cached Google Sheets API service object.
    Raises EnvironmentError or Exception if authentication fails.
    """
    global _sheets_service_instance
    if _sheets_service_instance is None:
        try:
            creds = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES)
            _sheets_service_instance = build('sheets', 'v4', credentials=creds)
            print("Google Sheets service initialized.")
        except Exception as e:
            raise Exception(f"Failed to initialize Google Sheets service: {e}")
    return _sheets_service_instance

# --- API Interaction Functions (Specific and Reusable) ---

def read_sheet_range(spreadsheet_id: str, range_name: str) -> Optional[List[List[Any]]]:
    """
    Reads data from a specified range in a Google Spreadsheet.

    Args:
        spreadsheet_id: The ID of the Google Spreadsheet.
        range_name: The A1 notation of the range (e.g., 'Sheet1!A1:D10').

    Returns:
        A list of lists representing the data, or None if no data is found or an error occurs.
    """
    if not spreadsheet_id or not range_name:
        print("Error: Spreadsheet ID and range name must be provided for read_sheet_range.")
        return None

    try:
        service = get_sheets_service()
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        values = result.get('values', [])
        if not values:
            print(f"No data found in range '{range_name}' of spreadsheet ID '{spreadsheet_id}'.")
            return None
        return values
    except HttpError as err:
        print(f"Google API Error reading range '{range_name}': {err.reason} (Code: {err.resp.status})")
        return None
    except Exception as e:
        print(f"An unexpected error occurred reading range '{range_name}': {e}")
        return None

def get_cell_value(spreadsheet_id: str, cell_address: str) -> Optional[str]:
    """
    Retrieves the value from a specific cell in a Google Spreadsheet.

    Args:
        spreadsheet_id: The ID of the Google Spreadsheet.
        cell_address: The A1 notation of the cell (e.g., 'B1', 'Sheet1!C3').

    Returns:
        The value from the cell as a string, or None if the cell is empty or an error occurs.
    """
    if not spreadsheet_id or not cell_address:
        print("Error: Spreadsheet ID and cell address must be provided for get_cell_value.")
        return None

    try:
        service = get_sheets_service()
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=cell_address,
            valueRenderOption='FORMATTED_VALUE' # Get value as it appears in the sheet
        ).execute()
        values = result.get('values', [])
        if values and values[0]:
            return str(values[0][0]) # Return as string
        else:
            print(f"No value found in cell '{cell_address}' of spreadsheet ID '{spreadsheet_id}'.")
            return None
    except HttpError as err:
        print(f"Google API Error accessing cell '{cell_address}': {err.reason} (Code: {err.resp.status})")
        return None
    except Exception as e:
        print(f"An unexpected error occurred accessing cell '{cell_address}': {e}")
        return None

def write_sheet_data(spreadsheet_id: str, range_name: str, data: List[List[Any]]) -> bool:
    """
    Writes data to a specified range in a Google Spreadsheet.

    Args:
        spreadsheet_id: The ID of the Google Spreadsheet.
        range_name: The A1 notation of the range to write to (e.g., 'Sheet1!A1:B2').
        data: A list of lists representing the data to write.
              Example: [['Header1', 'Header2'], ['Value1', 'Value2']]

    Returns:
        True if the write operation was successful, False otherwise.
    """
    if not spreadsheet_id or not range_name or not data:
        print("Error: Spreadsheet ID, range name, and data must be provided for write_sheet_data.")
        return False

    try:
        service = get_sheets_service()
        body = {'values': data}
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='USER_ENTERED', # USER_ENTERED parses values like a user would
            body=body
        ).execute()
        updated_cells = result.get('updatedCells', 'unknown number of')
        print(f"Successfully wrote {updated_cells} cells to {range_name}.")
        return True
    except HttpError as err:
        print(f"Google API Error writing to range '{range_name}': {err.reason} (Code: {err.resp.status})")
        if err.resp.status == 403:
            print("Ensure your service account has 'Editor' permission for this spreadsheet.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred writing to range '{range_name}': {e}")
        return False