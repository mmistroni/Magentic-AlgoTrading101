# sheet_manager.py
import os
import json
from typing import List, Dict, Any, Optional, Union
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.cloud import secretmanager_v1beta1 as secretmanager # Import here if get_secret is internal

# Helper Function: Safely Get Secrets from Secret Manager
def get_secret(project_id: str, secret_id: str, version_id: str = 'latest') -> Optional[str]:
    """Retrieves a secret value from Google Cloud Secret Manager."""
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        print(f"Error accessing secret '{secret_id}' in project '{project_id}': {e}")
        return None

# --- MODIFIED GoogleSheetManager Class (from previous response) ---
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

class GoogleSheetManager:
    """
    Manages direct interactions with the Google Sheets API, including authentication
    using service account credentials fetched from Secret Manager.
    NOTE: This class's methods are NOT directly exposed as ADK tools.
          Instead, separate wrapper functions (decorated with @tool) will call these methods.
    """
    def __init__(self, project_id: str, credentials_secret_id: str):
        self.project_id = project_id
        self.credentials_secret_id = credentials_secret_id
        self.service = self._authenticate()
        if not self.service:
            raise RuntimeError("GoogleSheetManager authentication failed. Check credentials and service account permissions.")
        print("GoogleSheetManager initialized successfully and authenticated.")

    def _authenticate(self):
        # ... (rest of your _authenticate method, which uses the get_secret helper)
        try:
            credentials_json_str = get_secret(self.project_id, self.credentials_secret_id) # Use the get_secret helper
            if not credentials_json_str:
                print("Authentication failed: No credentials found in Secret Manager.")
                return None

            creds_info = json.loads(credentials_json_str)
            creds = service_account.Credentials.from_service_account_info(
                creds_info, scopes=SCOPES
            )
            return build('sheets', 'v4', credentials=creds)
        except (json.JSONDecodeError, HttpError) as e:
            print(f"Authentication HTTP/JSON decoding error: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred during authentication: {type(e).__name__}: {e}")
            return None

    # --- All your other methods (insert_empty_row_internal, calculate_column_sum_internal, etc.) ---
    # Make sure to keep the "_internal" suffix and REMOVE any @tool decorators here!
    # Copy all methods from your previously provided GoogleSheetManager, ensuring they are _internal

    def _ensure_authenticated(self):
        """Helper to ensure the service is authenticated before performing operations."""
        if not self.service:
            print("Error: Google Sheets service is not authenticated. Cannot proceed.")
            return False
        return True

    def _get_data_from_sheet(self, spreadsheet_id: str, range_name: str) -> Optional[List[List[Any]]]:
        # ... (copy as is)
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
            print(f"HTTP Error reading data from '{range_name}': {err.content.decode('utf-8')}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred while reading data from '{range_name}': {type(e).__name__}: {e}")
            return None

    def _get_single_cell_value(self, spreadsheet_id: str, cell_range: str) -> Optional[str]:
        # ... (copy as is)
        data = self._get_data_from_sheet(spreadsheet_id, cell_range)
        return data[0][0] if data and data[0] else None

    def _get_sheet_id_by_name(self, spreadsheet_id: str, sheet_name: str) -> Optional[int]:
        # ... (copy as is)
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
            print(f"HTTP Error getting sheet ID for '{sheet_name}': {err.content.decode('utf-8')}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred getting sheet ID: {type(e).__name__}: {e}")
            return None


    # --- All your other methods (insert_empty_row_internal, calculate_column_sum_internal, etc.) ---
    # Make sure to keep the "_internal" suffix and REMOVE any @tool decorators here!
    # Copy all methods from your previously provided GoogleSheetManager, ensuring they are _internal

    def insert_empty_row_internal(self, spreadsheet_id: str, sheet_name: str, insert_at_row_index: int, num_rows: int = 1) -> bool:
        # ... (copy logic from previous response)
        if not self._ensure_authenticated():
            return False
        sheet_id = self._get_sheet_id_by_name(spreadsheet_id, sheet_name)
        if sheet_id is None: return False
        try:
            requests = [{
                'insertDimension': {
                    'range': {
                        'sheetId': sheet_id,
                        'dimension': 'ROWS',
                        'startIndex': insert_at_row_index - 1,
                        'endIndex': insert_at_row_index - 1 + num_rows
                    },
                    'inheritFromBefore': False
                }
            }]
            body = {'requests': requests}
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id, body=body).execute()
            print(f"Successfully inserted {num_rows} empty row(s) at row {insert_at_row_index} in '{sheet_name}'.")
            return True
        except HttpError as err:
            print(f"HTTP Error inserting row: {err.content.decode('utf-8')}"); return False
        except Exception as e:
            print(f"An unexpected error occurred while inserting row: {type(e).__name__}: {e}"); return False

    def calculate_column_sum_internal(self, spreadsheet_id: str, range_name: str, column_index: int) -> Union[int, float, None]:
        # ... (copy logic from previous response)
        data = self._get_data_from_sheet(spreadsheet_id, range_name)
        if data is None: return None
        total_sum: Union[int, float] = 0.0
        found_numeric_value = False
        for row in data:
            if column_index < len(row):
                try:
                    numeric_value = float(str(row[column_index]).replace(',', ''))
                    total_sum += numeric_value
                    found_numeric_value = True
                except ValueError: pass
                except Exception as e: print(f"An unexpected error occurred processing cell value: {type(e).__name__}: {e}")
        return total_sum if found_numeric_value else 0.0

    def append_row_internal(self, spreadsheet_id: str, sheet_name: str, start_row_for_append: int, data_to_append: List[List[Any]]) -> Optional[str]:
        # ... (copy logic from previous response)
        if not self._ensure_authenticated(): return None
        try:
            range_name = f'{sheet_name}!A{start_row_for_append}'
            body = {'values': data_to_append}
            result = self.service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            updates = result.get('updates', {})
            updated_range = updates.get('updatedRange')
            if updated_range: print(f"Appended to: {updated_range}"); return updated_range
            else: print(f"Could not confirm data append. Response: {result}"); return None
        except HttpError as err:
            print(f"HTTP Error appending data: {err.content.decode('utf-8')}"); return None
        except Exception as e:
            print(f"An unexpected error occurred while appending data: {type(e).__name__}: {e}"); return None

    def read_sheet_data_internal(self, spreadsheet_id: str, range_name: str) -> Optional[List[List[Any]]]:
        # ... (copy logic from previous response)
        return self._get_data_from_sheet(spreadsheet_id, range_name)

    def get_budget_amount_internal(self, spreadsheet_id: str, sheet_name: str = 'Sheet1') -> Optional[float]:
        # ... (copy logic from previous response)
        cell_value = self._get_single_cell_value(spreadsheet_id, f'{sheet_name}!B1')
        if cell_value is not None:
            try: return float(str(cell_value).replace(',', ''))
            except ValueError: print(f"Warning: Budget value '{cell_value}' in B1 is not numeric."); return None
        return None

    def get_start_date_internal(self, spreadsheet_id: str, sheet_name: str = 'Sheet1') -> Optional[str]:
        # ... (copy logic from previous response)
        return self._get_single_cell_value(spreadsheet_id, f'{sheet_name}!B3')

    def get_end_date_internal(self, spreadsheet_id: str, sheet_name: str = 'Sheet1') -> Optional[str]:
        # ... (copy logic from previous response)
        return self._get_single_cell_value(spreadsheet_id, f'{sheet_name}!B4')

    def get_total_expenses_sum_internal(self, spreadsheet_id: str, sheet_name: str = 'Sheet1', start_expense_row: int = 7) -> Union[int, float, None]:
        # ... (copy logic from previous response)
        expense_range = f'{sheet_name}!C{start_expense_row}:C'
        return self.calculate_column_sum_internal(spreadsheet_id, expense_range, 0)

    def get_remaining_budget_value_internal(self, spreadsheet_id: str, sheet_name: str = 'Sheet1', start_expense_row: int = 7) -> Union[int, float, None]:
        # ... (copy logic from previous response)
        budget = self.get_budget_amount_internal(spreadsheet_id, sheet_name)
        total_expenses = self.get_total_expenses_sum_internal(spreadsheet_id, sheet_name, start_expense_row)
        if budget is None: print("Could not retrieve total budget for remaining budget calculation."); return None
        if total_expenses is None: print("Could not retrieve total expenses for remaining budget calculation."); return None
        return budget - total_expenses

    def get_remaining_days_in_period_internal(self, spreadsheet_id: str, sheet_name: str = 'Sheet1') -> Optional[int]:
        # ... (copy logic from previous response)
        start_date_str = self.get_start_date_internal(spreadsheet_id, sheet_name)
        end_date_str = self.get_end_date_internal(spreadsheet_id, sheet_name)
        if start_date_str is None or end_date_str is None:
            print("Could not retrieve start or end dates from B3/B4 for remaining days calculation.")
            return None
        try:
            start_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d')
            # Current date for calculation (as of the environment context)
            current_date_str = "2025-07-06" # Today is Sunday, July 6, 2025
            today = datetime.strptime(current_date_str, '%Y-%m-%d')

            if end_date_obj < today: return 0 # Period has already ended
            return (end_date_obj - today).days + 1 # +1 to include current day
        except ValueError:
            print(f"Warning: Date format not recognized. Start: '{start_date_str}', End: '{end_date_str}'. Expected 'YYYY-MM-DD'.")
            return None
        except Exception as e:
            print(f"An unexpected error occurred during remaining days calculation: {type(e).__name__}: {e}"); return None


    def get_daily_remaining_budget_str_internal(self, spreadsheet_id: str, sheet_name: str = 'Sheet1', start_expense_row: int = 7) -> Optional[str]:
        # ... (copy logic from previous response)
        remaining_budget = self.get_remaining_budget_value_internal(spreadsheet_id, sheet_name, start_expense_row)
        num_remaining_days = self.get_remaining_days_in_period_internal(spreadsheet_id, sheet_name)
        if remaining_budget is None: return None
        if remaining_budget < 0: return f"£{remaining_budget:.2f}"
        if num_remaining_days is None: return None
        if num_remaining_days <= 0: return f"£{remaining_budget:.2f} (0 days left - Period ended or invalid dates.)"
        else:
            daily_budget = remaining_budget / num_remaining_days
            return f"£{remaining_budget:.2f} (£{daily_budget:.2f} per day for {num_remaining_days} days left)"


    def get_all_expenses_data_internal(self, spreadsheet_id: str, sheet_name: str = 'Sheet1', start_expense_row: int = 7, expense_columns: str = 'A:C') -> Optional[List[List[Any]]]:
        # ... (copy logic from previous response)
        expense_range = f'{sheet_name}!{expense_columns.split(":")[0]}{start_expense_row}:{expense_columns.split(":")[1]}'
        return self.read_sheet_data_internal(spreadsheet_id, expense_range)