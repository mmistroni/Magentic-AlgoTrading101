import json # NEW: Import the json module
import os
import tempfile # You can remove this import if no other part of your code uses it
from datetime import datetime
from typing import List, Any, Optional, Union
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.cloud import secretmanager

# Helper function to get secrets from Google Secret Manager
def get_secret(project_id: str, secret_id: str) -> Optional[str]:
    """Retrieves a secret from Google Secret Manager."""
    if not project_id or not secret_id:
        print("Project ID or Secret ID is missing for get_secret.")
        return None
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        print(f'----- attempting to retrieve SECRET {name}')
        response = client.access_secret_version(request={"name": name})
        secret_value = response.payload.data.decode("UTF-8")
        print(f"Successfully retrieved secret '{secret_id}'.")
        return secret_value
    except Exception as e:
        print(f"Error retrieving secret '{secret_id}': {e}")
        return None

class GoogleSheetManager:
    # Removed temp_creds_file from __init__ and __del__
    def __init__(self, spreadsheet_id: str, service_account_json_str: str):
        self.spreadsheet_id = spreadsheet_id
        self.service = None

        if not self.spreadsheet_id:
            raise ValueError("Spreadsheet ID must be provided to GoogleSheetManager.")
        if not service_account_json_str:
            raise ValueError("Service Account JSON string must be provided for authentication.")

        try:
            # NEW: Parse the JSON string directly into a dictionary
            credentials_info = json.loads(service_account_json_str)
            self.service = self._authenticate_from_info(credentials_info)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid service account JSON string provided: {e}")
        except Exception as e:
            raise RuntimeError(f"Error setting up GoogleSheetManager with provided credentials: {e}")

    # No __del__ method needed anymore as no temporary files are created

    # NEW: Authentication method that takes a dictionary directly
    def _authenticate_from_info(self, credentials_info: dict):
        """Authenticates with Google Sheets API using service account info."""
        try:
            # Define the scope of access for the Google Sheets API
            SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

            # Create credentials from the dictionary
            creds = service_account.Credentials.from_service_account_info(
                credentials_info, scopes=SCOPES
            )

            # Build the Sheets API service object
            service = build('sheets', 'v4', credentials=creds)
            print("Google Sheets API service built successfully from JSON info.")
            return service
        except Exception as e:
            raise RuntimeError(f"Error authenticating with Google Sheets API: {e}")

    # --- Utility Methods ---
    # (No changes needed for the methods below from previous version)

    def append_row_internal(self, spreadsheet_id: str, sheet_name: str,
                            start_row_for_append: int, data_to_append: List[List[Any]]) -> Optional[str]:
        """Appends a new row of data to the Google Sheet."""
        if not self.service:
            print("Service not initialized. Cannot append row.")
            return None
        try:
            # Determine the range to append to. For 'Expenses' sheet starting at row 7,
            # this might be something like 'Expenses!A7:C' or 'Expenses!A:C'.
            # The API automatically appends after the last row of data if range is like 'Sheet1!A:C'
            # Or you can specify a precise range like 'Sheet1!A7' to ensure it starts from there.
            # Using just sheet_name (e.g., 'Expenses') will append to the end of that sheet.
            range_name = sheet_name

            result = self.service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED', # Interprets values as user input (e.g., handles formulas, dates)
                insertDataOption='INSERT_ROWS', # Ensures new rows are inserted
                body={'values': data_to_append}
            ).execute()
            updated_range = result.get('updates', {}).get('updatedRange')
            print(f"Row appended. Updated range: {updated_range}")
            return updated_range
        except HttpError as err:
            print(f"HTTP error appending row: {err}")
            return None
        except Exception as e:
            print(f"Error appending row: {e}")
            return None

    def get_all_expenses_data_internal(self, spreadsheet_id: str, sheet_name: str,
                                       start_expense_row: int, expense_columns: str = 'A:C') -> Optional[List[List[Any]]]:
        """Retrieves all expense records from the specified sheet and columns, starting from a given row."""
        if not self.service:
            print("Service not initialized. Cannot retrieve expenses.")
            return None
        try:
            range_name = f"{sheet_name}!{expense_columns}"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range=range_name).execute()
            values = result.get('values', [])

            # Filter out rows before start_expense_row (1-based index)
            # Adjust for 0-based list index: start_expense_row - 1
            if values:
                return values[start_expense_row - 1:]
            return []
        except HttpError as err:
            print(f"HTTP error getting expenses: {err}")
            return None
        except Exception as e:
            print(f"Error getting expenses: {e}")
            return None

    def get_budget_amount_internal(self, spreadsheet_id: str, sheet_name: str, budget_cell: str = 'B1') -> Optional[float]:
        """Retrieves the total budget amount from a specific cell."""
        if not self.service:
            print("Service not initialized. Cannot get budget.")
            return None
        try:
            range_name = f"{sheet_name}!{budget_cell}"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range=range_name, valueRenderOption='UNFORMATTED_VALUE').execute()
            values = result.get('values', [])
            if values and values[0] and len(values[0]) > 0:
                try:
                    return float(values[0][0])
                except (ValueError, TypeError):
                    print(f"Could not convert '{values[0][0]}' to float for budget amount.")
                    return None
            return None
        except HttpError as err:
            print(f"HTTP error getting budget amount: {err}")
            return None
        except Exception as e:
            print(f"Error getting budget amount: {e}")
            return None

    def get_remaining_budget_value_internal(self, spreadsheet_id: str, sheet_name: str,
                                            start_expense_row: int, expense_columns: str = 'A:C') -> Union[int, float, None]:
        """Calculates the remaining budget."""
        total_budget = self.get_budget_amount_internal(spreadsheet_id, sheet_name)
        if total_budget is None:
            return None

        expenses_data = self.get_all_expenses_data_internal(spreadsheet_id, sheet_name, start_expense_row, expense_columns)
        if expenses_data is None:
            return None

        total_expenses = 0.0
        # Assuming amount is in the 3rd column (index 2) of the fetched data
        for row in expenses_data:
            if len(row) > 2: # Ensure there's a third column
                try:
                    total_expenses += float(row[2])
                except (ValueError, TypeError):
                    # Skip rows where amount is not a valid number
                    continue

        return total_budget - total_expenses

    def get_remaining_days_in_period_internal(self, spreadsheet_id: str, sheet_name: str,
                                              start_date_cell: str = 'B3', end_date_cell: str = 'B4') -> Optional[int]:
        """Calculates days left in the budget period based on start/end dates in sheet."""
        if not self.service:
            print("Service not initialized. Cannot get remaining days.")
            return None
        try:
            range_name = f"{sheet_name}!{start_date_cell}:{end_date_cell}"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range=range_name).execute()
            values = result.get('values', [])

            if not values or len(values) < 2 or not values[0] or not values[1]:
                print("Start or end date cells not found or invalid.")
                return None

            # Assuming dates are in YYYY-MM-DD format as strings
            start_date_str = values[0][0]
            end_date_str = values[1][0]

            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            today = datetime.now().date()

            if today > end_date:
                return 0 # Period has ended
            elif today < start_date:
                # If today is before the start of the period, calculate days from start to end
                return (end_date - start_date).days + 1
            else:
                return (end_date - today).days + 1
        except (ValueError, TypeError, IndexError) as e:
            print(f"Error parsing dates from sheet: {e}")
            return None
        except HttpError as err:
            print(f"HTTP error getting date range: {err}")
            return None
        except Exception as e:
            print(f"Error getting remaining days: {e}")
            return None

    def get_daily_remaining_budget_str_internal(self, spreadsheet_id: str, sheet_name: str,
                                                start_expense_row: int, expense_columns: str = 'A:C') -> Optional[str]:
        """Provides a formatted string for daily budget breakdown."""
        remaining_budget = self.calculate_remaining_budget_value(spreadsheet_id, sheet_name, start_expense_row, expense_columns)
        if remaining_budget is None:
            return None

        days_left = self.get_days_left_in_budget_period(spreadsheet_id, sheet_name)
        if days_left is None:
            return None

        if remaining_budget <= 0:
            return f"You are over budget by {abs(remaining_budget):.2f}." # Assuming currency formatting from sheet is not strictly needed for this output

        if days_left > 0:
            daily_allowance = remaining_budget / days_left
            return f"{remaining_budget:.2f} ({daily_allowance:.2f} per day for {days_left} days left)"
        else:
            return f"{remaining_budget:.2f} (Budget period has ended)."

    def insert_empty_row_internal(self, spreadsheet_id: str, sheet_name: str,
                                  insert_at_row_index: int, num_rows: int = 1) -> bool:
        """Inserts one or more empty rows into the Google Sheet at a specified 1-based index."""
        if not self.service:
            print("Service not initialized. Cannot insert rows.")
            return False
        try:
            requests = [{
                'insertDimension': {
                    'range': {
                        'sheetId': self._get_sheet_id_by_name(spreadsheet_id, sheet_name),
                        'dimension': 'ROWS',
                        'startIndex': insert_at_row_index - 1, # API is 0-based
                        'endIndex': insert_at_row_index - 1 + num_rows
                    },
                    'inheritFromBefore': False # Ensures new rows are truly empty
                }
            }]
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id, body={'requests': requests}).execute()
            print(f"Inserted {num_rows} empty row(s) at row {insert_at_row_index}.")
            return True
        except HttpError as err:
            print(f"HTTP error inserting rows: {err}")
            return False
        except Exception as e:
            print(f"Error inserting rows: {e}")
            return False

    def _get_sheet_id_by_name(self, spreadsheet_id: str, sheet_name: str) -> Optional[int]:
        """Helper to get sheet ID from its name."""
        if not self.service:
            print("Service not initialized. Cannot get sheet ID.")
            return None
        try:
            spreadsheet_metadata = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id, fields='sheets.properties').execute()
            for sheet in spreadsheet_metadata.get('sheets', []):
                if sheet.get('properties', {}).get('title') == sheet_name:
                    return sheet['properties']['sheetId']
            print(f"Sheet '{sheet_name}' not found in spreadsheet.")
            return None
        except HttpError as err:
            print(f"HTTP error getting sheet ID: {err}")
            return None
        except Exception as e:
            print(f"Error getting sheet ID: {e}")
            return None

    def calculate_column_sum_internal(self, spreadsheet_id: str, range_name: str, column_index: int) -> Union[int, float, None]:
        """
        Calculates the sum of numeric values in a specific column within a given range of a Google Sheet.
        """
        if not self.service:
            print("Service not initialized. Cannot calculate column sum.")
            return None
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range=range_name, valueRenderOption='UNFORMATTED_VALUE').execute()
            values = result.get('values', [])
            
            total_sum = 0.0
            for row in values:
                if len(row) > column_index:
                    try:
                        value = float(row[column_index])
                        total_sum += value
                    except (ValueError, TypeError):
                        # Skip values that cannot be converted to float
                        continue
            print(f"Calculated sum for column {column_index} in range {range_name}: {total_sum}")
            return total_sum
        except HttpError as err:
            print(f"HTTP error calculating column sum: {err}")
            return None
        except Exception as e:
            print(f"Error calculating column sum: {e}")
            return None

    def read_sheet_data_internal(self, spreadsheet_id: str, range_name: str) -> Optional[List[List[Any]]]:
        """
        Reads all data from a specified range in the Google Sheet.
        """
        if not self.service:
            print("Service not initialized. Cannot read sheet data.")
            return None
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range=range_name).execute()
            values = result.get('values', [])
            print(f"Successfully read data from range {range_name}. Rows: {len(values)}")
            return values
        except HttpError as err:
            print(f"HTTP error reading sheet data: {err}")
            return None
        except Exception as e:
            print(f"Error reading sheet data: {e}")
            return None