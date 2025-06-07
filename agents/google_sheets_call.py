import google.auth
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import json
credentials_json_str = os.getenv('GOOGLE_SHEET_CREDENTIALS')

credentials_info = json.loads(credentials_json_str)



# Define the API scopes (permissions) your agent needs
# For read/write access to Google Sheets:
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
# For read-only access:
# SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']


def get_sheets_service_with_service_account():
    """Authenticates using a service account and returns a Google Sheets API service object."""
    try:
        # Create credentials from the service account key file
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
        SPREADSHEET_ID = "1hGkQHbYKtDfsQvAsgTT6eZe9sPjuxA3MrTVZV1O7RLE" # <<< IMPORTANT: Update this ID!
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
            values_to_write = [['07/06/2025', 'Food', 33.22], 
                               ['08/06/2025', 'Lunch', 15.12]]
            body = {'values': values_to_write}
            result = service.spreadsheets().values().update(
                 spreadsheetId=SPREADSHEET_ID, range="Sheet1!E1",
                 valueInputOption="RAW", body=body).execute()
            print(f"\n{result.get('updatedCells')} cells updated.")

        except HttpError as err:
            print(f"Failed to interact with spreadsheet: {err}")
        except Exception as e:
            print(f"An unexpected error occurred during spreadsheet interaction: {e}")
    else:
        print("Could not obtain Google Sheets service.")