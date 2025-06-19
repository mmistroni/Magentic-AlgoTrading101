import google.auth
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import List, Dict, Any, Optional, Union
import os
import json


# Define the API scopes (permissions) your agent needs
# For read/write access to Google Sheets:
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
# For read-only access:
# SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']


def get_sheets_service_with_service_account():
    """Authenticates using a service account and returns a Google Sheets API service object."""
    try:
        # Create credentials from the service account key file
        credentials_json_str = os.getenv('GOOGLE_SHEET_CREDENTIALS')

        credentials_info = json.loads(credentials_json_str)
        creds = service_account.Credentials.from_service_account_info(
            credentials_info, scopes=SCOPES)

        # Build the Sheets API service object
        service = build('sheets', 'v4', credentials=creds)
        print("Successfully authenticated with service account.")
        return service
    except HttpError as err:
        print(f"An API error occurred during service account authentication: {err}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def calculate_column_sum(self, spreadsheet_id: str, range_name: str, column_index: int) -> Optional[Union[int, float]]:
        """
        Calculates the sum of numeric values in a specific column within a given range.

        Args:
            spreadsheet_id (str): The ID of the spreadsheet.
            range_name (str): The A1 notation of the range to read (e.g., "Sheet1!A1:D5").
                              The sum will be calculated within this range.
            column_index (int): The 0-based index of the column to sum.
                                 (e.g., 0 for column A, 1 for column B, etc.).

        Returns:
            Optional[Union[int, float]]: The sum of the column values if successful,
                                         or None if an error occurs or no numeric data is found.
        """
        service = get_sheets_service_with_service_account()
        range_name: str = f'Sheet1!C{7}:Z'
        if data is None:
            print(f"Could not read data from range '{range_name}' to calculate sum.")
            return None

        total_sum: Union[int, float] = 0
        found_numeric_value = False

        for row_idx, row in enumerate(data):
            if column_index < len(row):
                cell_value = row[column_index]
                try:
                    # Attempt to convert to float, as it handles both ints and decimals
                    numeric_value = float(cell_value)
                    total_sum += numeric_value
                    found_numeric_value = True
                except ValueError:
                    # If conversion fails, it's not a valid number. Skip or log.
                    print(f"Warning: Value '{cell_value}' at row {row_idx+1}, column {column_index+1} "
                          f"in range '{range_name}' is not numeric. Skipping.")
                except Exception as e:
                    print(f"An unexpected error occurred processing cell value '{cell_value}': {type(e).__name__}: {e}")
            else:
                print(f"Warning: Row {row_idx+1} in range '{range_name}' does not have a column at index {column_index}. Skipping.")

        if not found_numeric_value:
            print(f"No numeric values found in column {column_index+1} of range '{range_name}'. Sum is 0.")

        return total_sum if found_numeric_value else 0 # Return 0 if no numeric values were found

def find_last_row_index(self, spreadsheet_id: str, sheet_name: str, reference_column: str = 'A') -> int:
    """
    Finds the index of the last row containing data in a specified reference column.

    Args:
        spreadsheet_id (str): The ID of the spreadsheet.
        sheet_name (str): The name of the sheet within the spreadsheet (e.g., "Sheet1").
        reference_column (str): The column to check for data (e.g., 'A', 'B', 'C').
                                The function will read the entire column to find the last row.

    Returns:
        int: The 1-based index of the last row containing data in the reference column.
                Returns 0 if the column is entirely empty or if an error occurs.
    """
    full_column_range = f"{sheet_name}!{reference_column}:{reference_column}"
    data = self.read_data(spreadsheet_id, full_column_range)

    if data is None:
        print(f"Could not read data from column '{reference_column}' to find last row index.")
        return 0
    else:
        # The length of the returned data list is the number of rows with content.
        # Since rows are 1-based in Google Sheets, this length is the last row index.
        last_row = len(data)
        print(f"Last row with data in column '{reference_column}' is: {last_row}")
        return last_row


def append_row_after_headers(spreadsheet_id, sheet_name, start_row_for_append, data_to_append):
    """
    Appends a row to a Google Sheet after a specific header row.

    Args:
        spreadsheet_id: The ID of the spreadsheet.
        sheet_name: The name of the sheet within the spreadsheet (e.g., "Sheet1").
        start_row_for_append: The row number *after* which you want to append.
                              For example, if headers are in row 3, use 4.
        data_to_append: A list of lists representing the rows to append.
                        Example: [['2025-06-07', 'Groceries', 150]]
    """
    try:
        service = get_sheets_service_with_service_account()

        # The range where data will be appended.
        # This tells the API to find the next empty row starting from `start_row_for_append`.
        range_name = f'{sheet_name}!A{start_row_for_append}:Z'

        body = {
            'values': data_to_append
        }

        result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='USER_ENTERED', # Use 'USER_ENTERED' if you have formulas or dates
            insertDataOption='INSERT_ROWS', # This is important to ensure new rows are inserted
            body=body
        ).execute()

        print(f"{result.get('updates').get('updatedCells')} cells appended.")
        print(f"Updated range: {result.get('updates').get('updatedRange')}")

    except Exception as err:
        print(f"An error occurred: {err}")




# --- Example Usage ---
if __name__ == "__main__":
    service = get_sheets_service_with_service_account()

    if service:
        # Replace with the actual ID of your Google Spreadsheet
        # You can find this in the spreadsheet's URL:
        # https://docs.google.com/spreadsheets/d/YOUR_SPREADSHEET_ID_HERE/edit
        #https://docs.google.com/spreadsheets/d/1uVb4olpIX_9jzF0hn-rdUoOh9XRU4Wnc/edit?gid=1137654152#gid=1137654152
        SPREADSHEET_ID =  os.getenv('BUDGET_SPREADSHEET_ID')#"1hGkQHbYKtDfsQvAsgTT6eZe9sPjuxA3MrTVZV1O7RLE" # <<< IMPORTANT: Update this ID!
        RANGE_NAME = "Sheet1!A1:D5" # Example range

        try:
            # Read data from the spreadsheet
            result = service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
            
            
            
            values = result.get("values", [])

            if not values:
                print("No data found in the spreadsheet.")
            else:
                print("\nData from spreadsheet:")
                for row in values:
                    print(row)

            print('Writing values.......')
            # Example of writing data (if you used the full 'spreadsheets' scope)
            values_to_write = [['2025-06-07', 'Food', 33.22], 
                               ['2025-06-08', 'Lunch', 15.12]]
            body = {'values': values_to_write}
            # result = service.spreadsheets().values().update(
            #      spreadsheetId=SPREADSHEET_ID, range="Sheet1!E1",
            #      valueInputOption="RAW", body=body).execute()
            # print(f"\n{result.get('updatedCells')} cells updated.")

            HEADER_ROW_NUMBER = 6 # <<< CONFIRM THIS IN YOUR SPREADSHEET
            START_ROW_FOR_APPEND = HEADER_ROW_NUMBER + 1
            append_row_after_headers(SPREADSHEET_ID, 'Sheet1', START_ROW_FOR_APPEND, values_to_write)
        
            values_to_write2 = [['2025-06-08', 'Food', 13.22], 
                               ['2025-06-08', 'Lunch', 125.12]]
            
            append_row_after_headers(SPREADSHEET_ID, 'Sheet1', START_ROW_FOR_APPEND, values_to_write2)


            SUM_ENTIRE_COLUMN_C_RANGE = "Sheet1!C:C"
            COLUMN_TO_SUM_INDEX_FOR_FULL_COLUMN = 0 # When range is a single column, its index is 0

            print(f"Attempting to sum the entire column C in range '{SUM_ENTIRE_COLUMN_C_RANGE}'...")
            column_sum_full_column = sheets_connector.calculate_column_sum(
                SPREADSHEET_ID, SUM_ENTIRE_COLUMN_C_RANGE, COLUMN_TO_SUM_INDEX_FOR_FULL_COLUMN
            )


        
        
        except HttpError as err:
            print(f"Failed to interact with spreadsheet: {err}")
        except Exception as e:
            print(f"An unexpected error occurred during spreadsheet interaction: {e}")
    else:
        print("Could not obtain Google Sheets service.")