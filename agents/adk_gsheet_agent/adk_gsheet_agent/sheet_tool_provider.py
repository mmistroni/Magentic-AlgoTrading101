# adk_gsheet_agent/sheet_tool_provider.py (REVERTED to ORIGINAL working version for FunctionTool)

from typing import List, Any, Optional, Union
from google.adk.tools import FunctionTool # Essential for FunctionTool
from datetime import datetime
from adk_gsheet_agent.google_sheet_manager import GoogleSheetManager

class SheetToolProvider:
    """
    Provides ADK tool functions for Google Sheet operations.
    Each tool is a method of this class, allowing them to explicitly
    access shared dependencies (GoogleSheetManager, spreadsheet IDs, etc.)
    through the class instance.
    """
    def __init__(self, sheet_manager: GoogleSheetManager, spreadsheet_id: str, default_sheet_name: str, default_start_expense_row: int):
        if not sheet_manager or not sheet_manager.service:
            raise ValueError("GoogleSheetManager instance must be valid and authenticated.")

        self.sheet_manager = sheet_manager
        self.spreadsheet_id = spreadsheet_id
        self.default_sheet_name = default_sheet_name
        self.default_start_expense_row = default_start_expense_row
        self.current_date = datetime.now().strftime('%Y-%m-%d') # Capture current date at init for tool context

    # --- Expense Tools ---
    # These methods are designed to be wrapped by FunctionTool
    def add_expense(self, date_str: Optional[str] = None, description: str = "", amount: float = 0.0) -> Optional[str]:
        """
        Adds a new expense record to the budget Google Sheet.
        Args:
            date_str (str): The date of the expense in 'YYYY-MM-DD' format (e.g., '2025-07-07').
                            Defaults to today's date if not specified.
            description (str): A brief description of the expense (e.g., 'Groceries', 'Coffee').
            amount (float): The monetary amount of the expense (e.g., 20.50).
        Returns:
            Optional[str]: The updated range string (e.g., 'Expenses!A10:C11') if successful, or None on error.
        """
        print(f"[{datetime.now()}] Tool: add_expense called with date={date_str}, desc='{description}', amount={amount}")
        if not date_str:
            date_str = self.current_date

        data_to_append = [[f'="{date_str}"', description, amount]]
        return self.sheet_manager.append_row_internal(
            spreadsheet_id=self.spreadsheet_id,
            sheet_name=self.default_sheet_name,
            start_row_for_append=self.default_start_expense_row,
            data_to_append=data_to_append
        )

    def list_all_expenses_data(self) -> Optional[List[List[Any]]]:
        """
        Retrieves and returns all expense records from the budget Google Sheet.
        Each record is a list, typically [Date, Description, Amount].
        This tool requires no input.
        Returns:
            Optional[List[List[Any]]]: A list of expense records, or None if an error occurs.
        """
        print(f"[{datetime.now()}] Tool: list_all_expenses_data called.")
        expense_columns = 'A:C' # Adjust these columns if your expenses span different columns
        return self.sheet_manager.get_all_expenses_data_internal(
            spreadsheet_id=self.spreadsheet_id,
            sheet_name=self.default_sheet_name,
            start_expense_row=self.default_start_expense_row,
            expense_columns=expense_columns
        )

    # --- Budget Calculation Tools ---
    def get_current_budget_total(self) -> Optional[float]:
        """
        Retrieves the total budget amount from the Google Sheet (assumed from cell B1).
        This tool requires no input.
        Returns:
            Optional[float]: The budget amount as a float, or None if not found or not numeric.
        """
        print(f"[{datetime.now()}] Tool: get_current_budget_total called.")
        return self.sheet_manager.get_budget_amount_internal(
            spreadsheet_id=self.spreadsheet_id,
            sheet_name=self.default_sheet_name
        )

    def calculate_remaining_budget_value(self) -> Union[int, float, None]:
        """
        Calculates the remaining budget by subtracting total expenses from the total budget.
        This tool requires no input.
        Returns:
            Union[int, float, None]: The remaining budget value, or None if data cannot be retrieved.
        """
        print(f"[{datetime.now()}] Tool: calculate_remaining_budget_value called.")
        return self.sheet_manager.get_remaining_budget_value_internal(
            spreadsheet_id=self.spreadsheet_id,
            sheet_name=self.default_sheet_name,
            start_expense_row=self.default_start_expense_row
        )

    def get_days_left_in_budget_period(self) -> Optional[int]:
        """
        Calculates and returns the number of remaining days in the current budget period.
        The period is defined by start/end dates in cells B3/B4 of the Google Sheet (YYYY-MM-DD format).
        This tool requires no input.
        Returns:
            Optional[int]: The number of days remaining (including today), or 0 if the period has ended, or None on error.
        """
        print(f"[{datetime.now()}] Tool: get_days_left_in_budget_period called.")
        return self.sheet_manager.get_remaining_days_in_period_internal(
            spreadsheet_id=self.spreadsheet_id,
            sheet_name=self.default_sheet_name
        )

    def get_daily_budget_breakdown_string(self) -> Optional[str]:
        """
        Provides a detailed breakdown of the remaining budget, including remaining amount,
        estimated daily allowance, and days left in the period.
        This tool requires no input.
        Returns:
            Optional[str]: A formatted string (e.g., '£150.00 (£30.00 per day for 5 days left)'),
                            or just the remaining amount if over budget, or None on error.
        """
        print(f"[{datetime.now()}] Tool: get_daily_budget_breakdown_string called.")
        return self.sheet_manager.get_daily_remaining_budget_str_internal(
            spreadsheet_id=self.spreadsheet_id,
            sheet_name=self.default_sheet_name,
            start_expense_row=self.default_start_expense_row
        )

    # --- General Sheet Interaction Tools ---
    def insert_new_empty_row(self, insert_at_row_index: int, num_rows: int = 1) -> bool:
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
        print(f"[{datetime.now()}] Tool: insert_new_empty_row called at index {insert_at_row_index} for {num_rows} rows.")
        return self.sheet_manager.insert_empty_row_internal(
            spreadsheet_id=self.spreadsheet_id,
            sheet_name=self.default_sheet_name,
            insert_at_row_index=insert_at_row_index,
            num_rows=num_rows
        )

    def calculate_column_total(self, range_name: str, column_index: int) -> Union[int, float, None]:
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
        print(f"[{datetime.now()}] Tool: calculate_column_total called for range '{range_name}', column index {column_index}.")
        return self.sheet_manager.calculate_column_sum_internal(
            spreadsheet_id=self.spreadsheet_id,
            range_name=range_name,
            column_index=column_index
        )

    def read_sheet_range(self, range_name: str) -> Optional[List[List[Any]]]:
        """
        Reads all data from a specified range in the Google Sheet.

        Args:
            range_name (str): The A1 notation or R1C1 notation of the range to retrieve (e.g., "Sheet1!A1:C10" or "Sheet1!A:C").

        Returns:
            Optional[List[List[Any]]]: A list of lists representing the data, or an empty list if no data, or None on error.
        """
        print(f"[{datetime.now()}] Tool: read_sheet_range called for range '{range_name}'.")
        return self.sheet_manager.read_sheet_data_internal(
            spreadsheet_id=self.spreadsheet_id,
            range_name=range_name
        )

    def get_all_tools(self) -> List[FunctionTool]: # Return type is FunctionTool
        """
        Returns a list of all FunctionTool instances from this class's methods.
        """
        tools = []
        # Manually create FunctionTool instances for each tool method.
        # This is the expected pattern when @tool_code is not directly importable.
        tools.append(FunctionTool(self.add_expense))
        tools.append(FunctionTool(self.list_all_expenses_data))
        tools.append(FunctionTool(self.get_current_budget_total))
        tools.append(FunctionTool(self.calculate_remaining_budget_value))
        tools.append(FunctionTool(self.get_days_left_in_budget_period))
        tools.append(FunctionTool(self.get_daily_budget_breakdown_string))
        tools.append(FunctionTool(self.insert_new_empty_row))
        tools.append(FunctionTool(self.calculate_column_total))
        tools.append(FunctionTool(self.read_sheet_range))

        return tools