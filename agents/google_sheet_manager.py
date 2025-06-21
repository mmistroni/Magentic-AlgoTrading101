import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta

# Define the API scopes (permissions)
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

class GoogleSheetManager:
    """
    Manages interactions with a Google Sheet, including reading, appending, inserting data,
    and performing calculations.

    It expects Google Service Account credentials to be provided as a JSON string
    via the 'GOOGLE_SHEET_CREDENTIALS' environment variable.
    """

    def __init__(self):
        """
        Initializes the GoogleSheetManager by authenticating with Google Sheets API.
        Requires 'GOOGLE_SHEET_CREDENTIALS' environment variable to be set
        with the service account JSON key string.
        """
        self.service = self._authenticate()
        if self.service:
            print("GoogleSheetManager initialized and authenticated successfully.")
        else:
            print("GoogleSheetManager failed to initialize due to authentication error.")
            # In a production environment, you might raise an exception here
            # to prevent further operations if authentication fails.

    def _authenticate(self):
        """
        Authenticates with Google using a service account provided via environment variable
        and builds the Google Sheets API service object.

        Returns:
            googleapiclient.discovery.Resource: The authenticated Google Sheets API service object,
                                               or None if authentication fails.
        """
        try:
            credentials_json_str = os.getenv('GOOGLE_SHEET_CREDENTIALS')
            if not credentials_json_str:
                print("Environment variable 'GOOGLE_SHEET_CREDENTIALS' is not set.")
                return None

            try:
                credentials_info = json.loads(credentials_json_str)
            except json.JSONDecodeError:
                print("Environment variable 'GOOGLE_SHEET_CREDENTIALS' contains invalid JSON.")
                return None

            creds = service_account.Credentials.from_service_account_info(
                credentials_info, scopes=SCOPES
            )

            service = build('sheets', 'v4', credentials=creds)
            return service
        except HttpError as err:
            print(f"An API error occurred during service account authentication: {err}")
            print(f"Details: {err.content.decode('utf-8')}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred during authentication: {type(e).__name__}: {e}")
            return None

    def _ensure_authenticated(self):
        """Helper to ensure the service is authenticated before performing operations."""
        if not self.service:
            print("Error: Google Sheets service is not authenticated. Cannot proceed.")
            return False
        return True

    def _get_data_from_sheet(self, spreadsheet_id: str, range_name: str) -> Optional[List[List[Any]]]:
        """
        Internal method to read raw data from a specified range in a Google Sheet.

        Args:
            spreadsheet_id (str): The ID of the Google Spreadsheet.
            range_name (str): The A1 notation or R1C1 notation of the range to retrieve.

        Returns:
            Optional[List[List[Any]]]: A list of lists representing the data, or None on error.
        """
        if not self._ensure_authenticated():
            return None
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range=range_name).execute()
            values = result.get("values", [])
            if not values:
                print(f"No data found in range '{range_name}' of spreadsheet '{spreadsheet_id}'.")
            return values
        except HttpError as err:
            print(f"HTTP Error reading data from '{range_name}': {err}")
            print(f"Details: {err.content.decode('utf-8')}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred while reading data from '{range_name}': {type(e).__name__}: {e}")
            return None

    def _get_sheet_id_by_name(self, spreadsheet_id: str, sheet_name: str) -> Optional[int]:
        """
        Gets the numerical sheet ID for a given sheet name. Required for batchUpdate operations.
        Args:
            spreadsheet_id (str): The ID of the Google Spreadsheet.
            sheet_name (str): The name of the sheet.
        Returns:
            Optional[int]: The numerical ID of the sheet, or None if not found or error.
        """
        if not self._ensure_authenticated():
            return None
        try:
            spreadsheet_metadata = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheets = spreadsheet_metadata.get('sheets', [])
            for sheet in sheets:
                properties = sheet.get('properties', {})
                if properties.get('title') == sheet_name:
                    return properties.get('sheetId')
            print(f"Sheet '{sheet_name}' not found in spreadsheet '{spreadsheet_id}'.")
            return None
        except HttpError as err:
            print(f"HTTP Error getting sheet ID for '{sheet_name}': {err}")
            print(f"Details: {err.content.decode('utf-8')}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred getting sheet ID: {type(e).__name__}: {e}")
            return None

    def insert_empty_row(self, spreadsheet_id: str, sheet_name: str, insert_at_row_index: int, num_rows: int = 1) -> bool:
        """
        Inserts one or more empty rows into a Google Sheet at a specified index.
        Note: This shifts existing rows down.
        Args:
            spreadsheet_id (str): The ID of the Google Spreadsheet.
            sheet_name (str): The name of the sheet within the spreadsheet (e.g., "Sheet1").
            insert_at_row_index (int): The 1-based index where new rows will be inserted.
                                       For example, 1 to insert at the very top, 7 to insert before row 7.
            num_rows (int): The number of rows to insert (default is 1).
        Returns:
            bool: True if rows were successfully inserted, False otherwise.
        """
        if not self._ensure_authenticated():
            return False

        sheet_id = self._get_sheet_id_by_name(spreadsheet_id, sheet_name)
        if sheet_id is None:
            return False

        try:
            requests = [{
                'insertDimension': {
                    'range': {
                        'sheetId': sheet_id,
                        'dimension': 'ROWS',
                        'startIndex': insert_at_row_index - 1, # API uses 0-based index
                        'endIndex': insert_at_row_index - 1 + num_rows
                    },
                    'inheritFromBefore': False # Inherit formatting from cells below (False) or above (True)
                }
            }]
            body = {'requests': requests}
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id, body=body).execute()
            print(f"Successfully inserted {num_rows} empty row(s) at row {insert_at_row_index} in '{sheet_name}'.")
            return True
        except HttpError as err:
            print(f"HTTP Error inserting row: {err}")
            print(f"Details: {err.content.decode('utf-8')}")
            return False
        except Exception as e:
            print(f"An unexpected error occurred while inserting row: {type(e).__name__}: {e}")
            return False

    def calculate_column_sum(self, spreadsheet_id: str, range_name: str, column_index: int) -> Union[int, float, None]:
        """
        Calculates the sum of numeric values in a specific column within a given range.

        Args:
            spreadsheet_id (str): The ID of the spreadsheet.
            range_name (str): The A1 notation of the range to read (e.g., "Sheet1!A1:D5").
                              The sum will be calculated within this range.
            column_index (int): The 0-based index of the column to sum.
                                 If range_name is a single column (e.g., 'Sheet1!C:C'), this should be 0.
                                 If range_name is multiple columns (e.g., 'Sheet1!A:D'), this should be
                                 the appropriate index for that wider range (e.g., 2 for column C).

        Returns:
            Union[int, float, None]: The sum of the column values if successful,
                                     0 if no numeric data is found, or None if an error occurs.
        """
        data = self._get_data_from_sheet(spreadsheet_id, range_name)
        if data is None:
            return None

        total_sum: Union[int, float] = 0.0
        found_numeric_value = False

        for row_idx, row in enumerate(data):
            if column_index < len(row):
                cell_value = row[column_index]
                try:
                    numeric_value = float(str(cell_value).replace(',', ''))
                    total_sum += numeric_value
                    found_numeric_value = True
                except ValueError:
                    print(f"Warning: Value '{cell_value}' at row {row_idx+1}, column {column_index+1} "
                          f"in range '{range_name}' is not numeric. Skipping.")
                except Exception as e:
                    print(f"An unexpected error occurred processing cell value '{cell_value}': {type(e).__name__}: {e}")
            else:
                print(f"Warning: Row {row_idx+1} in range '{range_name}' does not have a column at index {column_index}. Skipping.")

        if not found_numeric_value:
            print(f"No numeric values found in column {column_index+1} of range '{range_name}'. Sum is 0.")
            return 0

        return total_sum

    def append_row(self, spreadsheet_id: str, sheet_name: str, start_row_for_append: int, data_to_append: List[List[Any]]) -> Optional[str]:
        """
        Appends one or more rows to a Google Sheet after a specific header row.

        Args:
            spreadsheet_id (str): The ID of the spreadsheet.
            sheet_name (str): The name of the sheet within the spreadsheet (e.g., "Sheet1").
            start_row_for_append (int): The row number *after* which you want to append.
                                      For example, if data should start after headers in row 3, use 4.
            data_to_append (List[List[Any]]): A list of lists representing the rows to append.
                                            Example: [['2025-06-07', 'Groceries', 150]]

        Returns:
            Optional[str]: The updated range string (e.g., 'Sheet1!A10:C11') if successful,
                           or None if an error occurs.
        """
        if not self._ensure_authenticated():
            return None
        try:
            range_name = f'{sheet_name}!A{start_row_for_append}:Z' # Use a wide range for append

            body = {
                'values': data_to_append
            }

            result = self.service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()

            updates = result.get('updates', {})
            updated_cells = updates.get('updatedCells')
            updated_range = updates.get('updatedRange')

            if updated_cells is not None and updated_range:
                print(f"{updated_cells} cells appended successfully.")
                print(f"Updated range: {updated_range}")
                return updated_range
            else:
                print(f"Could not confirm data append. Response: {result}")
                return None

        except HttpError as err:
            print(f"HTTP Error appending data: {err}")
            print(f"Details: {err.content.decode('utf-8')}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred while appending data: {type(e).__name__}: {e}")
            return None

    def read_sheet_data(self, spreadsheet_id: str, range_name: str) -> Optional[List[List[Any]]]:
        """
        Reads data from a specified range in a Google Sheet.

        Args:
            spreadsheet_id (str): The ID of the Google Spreadsheet.
            range_name (str): The A1 notation or R1C1 notation of the range to retrieve.

        Returns:
            Optional[List[List[Any]]]: A list of lists representing the data, or None on error.
        """
        return self._get_data_from_sheet(spreadsheet_id, range_name)

    def _get_single_cell_value(self, spreadsheet_id: str, cell_address: str) -> Optional[Any]:
        """
        Internal helper to get a single cell value.
        Args:
            spreadsheet_id (str): The ID of the Google Spreadsheet.
            cell_address (str): The A1 notation of the cell (e.g., 'Sheet1!B1').
        Returns:
            Optional[Any]: The value of the cell, or None if not found or an error occurs.
        """
        data = self._get_data_from_sheet(spreadsheet_id, cell_address)
        if data and data[0] and len(data[0]) > 0:
            return data[0][0]
        return None

    def get_budget_from_b1(self, spreadsheet_id: str, sheet_name: str = 'Sheet1') -> Optional[float]:
        """
        Retrieves the budget value from cell B1 of the specified sheet.
        Args:
            spreadsheet_id (str): The ID of the Google Spreadsheet.
            sheet_name (str): The name of the sheet (default is 'Sheet1').
        Returns:
            Optional[float]: The budget as a float, or None if not found or not numeric.
        """
        cell_value = self._get_single_cell_value(spreadsheet_id, f'{sheet_name}!B1')
        if cell_value is not None:
            try:
                return float(str(cell_value).replace(',', ''))
            except ValueError:
                print(f"Warning: Budget value '{cell_value}' in B1 is not numeric.")
        return None

    def get_start_date_from_b3(self, spreadsheet_id: str, sheet_name: str = 'Sheet1') -> Optional[str]:
        """
        Retrieves the start date string from cell B3 of the specified sheet.
        Args:
            spreadsheet_id (str): The ID of the Google Spreadsheet.
            sheet_name (str): The name of the sheet (default is 'Sheet1').
        Returns:
            Optional[str]: The start date string, or None if not found.
        """
        return self._get_single_cell_value(spreadsheet_id, f'{sheet_name}!B3')

    def get_end_date_from_b4(self, spreadsheet_id: str, sheet_name: str = 'Sheet1') -> Optional[str]:
        """
        Retrieves the end date string from cell B4 of the specified sheet.
        Args:
            spreadsheet_id (str): The ID of the Google Spreadsheet.
            sheet_name (str): The name of the sheet (default is 'Sheet1').
        Returns:
            Optional[str]: The end date string, or None if not found.
        """
        return self._get_single_cell_value(spreadsheet_id, f'{sheet_name}!B4')

    def get_current_budget(self, spreadsheet_id: str, sheet_name: str = 'Sheet1') -> Optional[float]:
        """
        Retrieves the total budget value from cell B1 of the specified Google Sheet.
        This is a public wrapper around get_budget_from_b1.
        Args:
            spreadsheet_id (str): The ID of the Google Spreadsheet.
            sheet_name (str): The name of the sheet (default is 'Sheet1').
        Returns:
            Optional[float]: The budget as a float, or None if not found or not numeric.
        """
        return self.get_budget_from_b1(spreadsheet_id, sheet_name)

    def get_total_expenses(self, spreadsheet_id: str, sheet_name: str = 'Sheet1', start_expense_row: int = 7) -> Union[int, float, None]:
        """
        Calculates the total sum of all expenses in column C, starting from a specified row.
        Assumes expenses are in column C.
        Args:
            spreadsheet_id (str): The ID of the Google Spreadsheet.
            sheet_name (str): The name of the sheet (default is 'Sheet1').
            start_expense_row (int): The 1-based row number where expense data starts.
                                     (e.g., 7 if headers are up to row 6).
        Returns:
            Union[int, float, None]: The total sum of expenses, 0 if no numeric data, or None on error.
        """
        # Range for column C from start_expense_row to end (inclusive)
        expense_range = f'{sheet_name}!C{start_expense_row}:C'
        # Column index is 0 because we are retrieving only column C's data
        return self.calculate_column_sum(spreadsheet_id, expense_range, 0)

    def get_remaining_budget(self, spreadsheet_id: str, sheet_name: str = 'Sheet1', start_expense_row: int = 7) -> Union[int, float, None]:
        """
        Calculates the remaining budget by subtracting total expenses from the total budget.
        Args:
            spreadsheet_id (str): The ID of the Google Spreadsheet.
            sheet_name (str): The name of the sheet (default is 'Sheet1').
            start_expense_row (int): The 1-based row number where expense data starts.
        Returns:
            Union[int, float, None]: The remaining budget, or None if data cannot be retrieved.
        """
        budget = self.get_current_budget(spreadsheet_id, sheet_name) # Call the newly added public method
        total_expenses = self.get_total_expenses(spreadsheet_id, sheet_name, start_expense_row)

        if budget is None:
            print("Could not retrieve total budget from B1.")
            return None
        if total_expenses is None:
            print("Could not retrieve total expenses.")
            return None

        return budget - total_expenses

    def get_daily_remaining_budget(self, spreadsheet_id: str, sheet_name: str = 'Sheet1', start_expense_row: int = 7) -> Optional[str]:
        """
        Calculates and formats the daily remaining budget.
        If remaining budget is positive, returns "<remaining budget> (number of days left)".
        If remaining budget is negative, returns "<remaining budget>".
        Args:
            spreadsheet_id (str): The ID of the Google Spreadsheet.
            sheet_name (str): The name of the sheet (default is 'Sheet1').
            start_expense_row (int): The 1-based row number where expense data starts.
        Returns:
            Optional[str]: A formatted string representing the daily remaining budget,
                           or None if data cannot be retrieved or dates are invalid.
        """
        remaining_budget = self.get_remaining_budget(spreadsheet_id, sheet_name, start_expense_row)
        start_date_str = self.get_start_date_from_b3(spreadsheet_id, sheet_name)
        end_date_str = self.get_end_date_from_b4(spreadsheet_id, sheet_name)

        if remaining_budget is None:
            return None
        if start_date_str is None or end_date_str is None:
            print("Could not retrieve start or end dates from B3/B4.")
            return None

        # If remaining budget is negative, return it directly
        if remaining_budget < 0:
            return f"{remaining_budget:.2f}"

        # If remaining budget is positive, proceed with daily calculation and formatting
        try:
            start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d')

            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow = today + timedelta(days=1)

            if end_date_obj < tomorrow:
                # If the period has already ended or is today, and budget is not negative,
                # consider 0 days left or a specific message.
                print(f"End date ({end_date_obj.strftime('%Y-%m-%d')}) is already past or is today. No remaining days for daily budget calculation.")
                return f"{remaining_budget:.2f} (0 days left - Period ended.)"


            num_remaining_days = (end_date_obj - tomorrow).days + 1
            if num_remaining_days <= 0:
                return f"{remaining_budget:.2f} (0 days left - No valid remaining days.)"

            return f"{remaining_budget:.2f} ({num_remaining_days} days left)"

        except ValueError:
            print(f"Warning: Date format not recognized. Start: '{start_date_str}', End: '{end_date_str}'. "
                  "Expected format like 'YYYY-MM-DD'.")
            return None
        except Exception as e:
            print(f"An unexpected error occurred during daily budget calculation: {type(e).__name__}: {e}")
            return None

    def get_all_expenses(self, spreadsheet_id: str, sheet_name: str = 'Sheet1', start_expense_row: int = 7, expense_columns: str = 'A:C') -> Optional[List[List[Any]]]:
        """
        Reads and returns all expense data from the specified sheet and columns, starting from a given row.
        Args:
            spreadsheet_id (str): The ID of the Google Spreadsheet.
            sheet_name (str): The name of the sheet (default is 'Sheet1').
            start_expense_row (int): The 1-based row number where expense data starts.
            expense_columns (str): The A1 notation of the columns covering expense data (e.g., 'A:C').
        Returns:
            Optional[List[List[Any]]]: A list of lists representing all expense data, or None on error.
        """
        # The range is constructed as 'SheetName!StartColumnRow:EndColumn'
        expense_range = f'{sheet_name}!{expense_columns.split(":")[0]}{start_expense_row}:{expense_columns.split(":")[1]}'
        return self.read_sheet_data(spreadsheet_id, expense_range)
