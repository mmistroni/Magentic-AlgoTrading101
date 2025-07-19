# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test deployment of Academic Research Agent to Agent Engine."""

import os

from absl import app, flags
from dotenv import load_dotenv
from vertexai import agent_engines
from adk_gsheet_agent.sheet_tool_provider import SheetToolProvider
from adk_gsheet_agent.google_sheet_manager import GoogleSheetManager

def main(argv: list[str]) -> None:  # pylint: disable=unused-argument

    load_dotenv()

    project_id = 'datascience-projects'
    location = 'us-central1'
    bucket = 'adk_short_bot'

    print('foobar')    

    spreasheet_id = os.getenv('BUDGET_SPREADSHEET_ID')
    credentials = os.getenv('GOOGLE_SHEET_CREDENTIALS')

    manager = GoogleSheetManager(spreasheet_id, credentials)
    res = manager.get_all_expenses_data_internal(spreasheet_id, 'Sheet1', 7)
    for item in res:
        print(res)



if __name__ == "__main__":
    app.run(main)