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


