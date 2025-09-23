from google.adk.agents import LlmAgent
from google.adk.agents import SequentialAgent, ParallelAgent
from .prompts import TRIPPLANNER_AGENT_INSTRUCTIONS
from .flight_agent import fagent
from .sightseeing_agent import sagent
from .hotel_agent import hagent
from google.adk.tools import agent_tool
# Coordinator Agent


#1. Create a parallel agent for concurrent tasks
plan_parallel = ParallelAgent(
    name="ParallelTripAgent",
    sub_agents=[fagent, hagent]
)  


# 2. Create a summary agent to gather results
trip_summary = LlmAgent(
    model='gemini-2.0-flash',
    name="TripSummaryAgent",
    instruction="Summarize the trip details from the flight, hotel, and sightseeing agents...",
    output_key="trip_summary")

# please help me plan a visit to paris in november for a honeymoon, book flights from london heathrow and book a 5 night stay in a hotel close to eiffel tower
root_agent = SequentialAgent(
    name="PlanTripWorkflow",
    sub_agents=[sagent, plan_parallel, trip_summary]
)
