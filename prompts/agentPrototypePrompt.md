Setting Up Your Simulation
When starting a conversation with an LLM to simulate your agent, begin by establishing the framework. We can do this with a simple prompt in a chat interface. The prompt should clearly outline the agent’s goals, actions, and the simulation process. Here’s a template you can use:

I'd like to simulate an AI agent that I'm designing. The agent will be built using these components:

Goals: [List your goals]
Actions: [List available actions]

At each step, your output must be an action to take.

Stop and wait and I will type in the result of
the action as my next message.

Ask me for the first task to perform.
For a Proactive Coder agent, you might use the following prompt to kick-off a simulation in ChatGPT:

I'd like to simulate an AI agent that I'm designing. The agent will be built using these components:

Goals:
* Find potential code enhancements
* Ensure changes are small and self-contained
* Get user approval before making changes
* Maintain existing interfaces

Actions available:
* list_project_files()
* read_project_file(filename)
* ask_user_approval(proposal)
* edit_project_file(filename, changes)

At each step, your output must be an action to take. 

Stop and wait and I will type in the result of 
the action as my next message.

Ask me for the first task to perform.
Take a mo

====== Claude Prompt ============

I want you to create a modern, professional NextJS expense tracking application. Here's my vision:

APPLICATION OVERVIEW:
Build a complete expense tracking web app that helps users manage their personal finances. The app should feel modern, intuitive, and professional.

CORE FEATURES:
- Add expenses with date, amount, category, and description
- View expenses in a clean, organized list
- Filter expenses by date range and category
- Dashboard with spending summaries and basic analytics
- Categories: Food, Transportation, Entertainment, Shopping, Bills, Other
- Data persistence using localStorage for this demo

TECHNICAL REQUIREMENTS:
- NextJS 14 with App Router
- TypeScript for type safety
- Tailwind CSS for styling with a modern, clean design
- Responsive design that works on desktop and mobile
- Use React hooks for state management
- Form validation for expense inputs
- Date picker for expense dates
- Currency formatting for amounts

DESIGN REQUIREMENTS:
- Clean, modern interface with a professional color scheme
- Intuitive navigation and user experience
- Visual feedback for user actions
- Loading states and error handling
- Mobile-responsive design

SPECIFIC FUNCTIONALITY:
- Expense form with validation
- Expense list with search and filter capabilities
- Summary cards showing total spending, monthly spending, top categories
- Basic charts or visual representations of spending patterns
- Export functionality (at least CSV)
- Delete and edit existing expenses

Please create this as a complete, production-ready application. Set up the project structure, implement all features, and make sure everything works together seamlessly. Focus on creating something that looks professional and that I could actually use to track my expenses.

When you're done, provide instructions on how to run the application and test all features.


====== Reverse engineered prompt for agens
Multi-Agent System Generation Request: Commitment of Traders (COT) Analysis

Objective: Generate a complete, self-contained Python file and a supporting Markdown file that conceptually models a financial analysis pipeline using an Agent Development Kit (ADK) architecture. The system must use Pydantic for data contracts and a Sequential Agent for orchestration.

Required Output Files:

cot_analysis_agent.py: The complete, runnable Python code simulation.

cot_adk_definition.md: A conceptual Markdown document detailing the declarative ADK structure.

Part 1: Python Simulation (cot_analysis_agent.py) Requirements

The Python file must contain the following functional and conceptual elements:

Pydantic Data Models (3 required):

RawDataModel: For data straight from the tools (COT position, VIX level, market, date).

FeatureDataModel: For processed data (COT Z-Score, VIX Percentile, summary).

SignalDataModel: For the final output (signal, confidence, justification).

Conceptual ADK Classes:

Context(dict): A simple dictionary class simulating the shared state container.

SequentialAgent: A base class for orchestration, which iterates through sub-agents.

Tools (2 required):

cot_data_tool(market: str): Simulates fetching COT data and returns a dictionary.

vix_data_tool(): Simulates fetching VIX data and returns a dictionary.

Note: These tools must contain realistic simulation logic (using random and time.sleep) but should not contain actual API calls.

Sub-Agents (3 required):

DataIngestionAgent: Reads 'market' from Context, uses the two tools, validates with RawDataModel, and writes result to Context as 'raw_market_data'.

FeatureEngineeringAgent: Reads 'raw_market_data' from Context, calculates Z-Score/Percentile, validates with FeatureDataModel, and writes result to Context as 'engineered_features'.

SignalGenerationAgent: Reads 'engineered_features' from Context, generates the signal logic, validates with SignalDataModel, and writes the final result to Context as 'final_signal'.

Root Agent:

COTSequentialAgent(SequentialAgent): The orchestrator that initializes the three sub-agents and manages the sequential flow (agent.run(context)) in its main .run() method.

Part 2: Declarative ADK Markdown (cot_adk_definition.md) Requirements

The Markdown document must clearly explain the conceptual ADK structure, including:

A section detailing the two tools (COTDataTool, VIXDataTool) and their expected Pydantic outputs.

A section for the three LlmAgent declarations, including their name, model, tools array, and the specific instruction that directs the LLM to read from and write to the shared Context using the designated keys (e.g., 'raw_market_data').

A section demonstrating the SequentialAgent orchestration and the execution step.

Part 3: Tool Implementation Caveats and Solutions (Mandatory)

After generating both files, please include a final conversational section mentioning that the generated cot_data_tool and vix_data_tool functions are only simulations. Offer the user concrete solutions for completing these tools in a real-world scenario, such as:

COT Data: Mention the need to integrate with the CFTC's API or a financial data provider like Quandl or Bloomberg.

VIX Data: Mention integrating with an exchange API (like the CBOE) or a data feed service.

Actionable next step: Offer to help the user define the precise Pydantic input schema required for making one of these external API calls.

Reminder: Ensure all agents in the Python file communicate solely by passing the Context object, and that Pydantic is used for validation at every stage.
