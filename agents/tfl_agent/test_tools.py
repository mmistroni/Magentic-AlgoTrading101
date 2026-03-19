import asyncio
import os
from tfl_agent.tools import get_tfl_route  # Assuming your function is in tools.py

async def test_main():
    # Set your API key if it's not already in the env
    # os.environ['TFL_API_KEY'] = 'your_actual_key_here'
    
    print("🧪 Starting TfL Route Test...")
    
    # Test for 'Tomorrow' at 05:45
    # Replace with a valid YYYYMMDD date for tomorrow
    test_date = "20260320" 
    
    try:
        results = await get_tfl_route(travel_date=test_date, travel_time="0545")
        
        if not results:
            print("❌ No routes found. Check your API key or Station IDs.")
            return

        print(f"✅ Found {len(results)} routes!\n")
        
        for i, journey in enumerate(results, 1):
            print(f"--- Option {i} ---")
            print(f"Path: {journey.legs_summary}")
            print(f"Duration: {journey.duration} mins")
            print(f"Disrupted: {journey.is_disrupted}")
            if journey.is_disrupted:
                print(f"Messages: {journey.disruption_messages}")
            print(f"Fare: £{journey.total_fare}\n")
            
    except Exception as e:
        print(f"💥 Test Failed with error: {e}")

if __name__ == "__main__":
    # This is the magic line that starts the event loop
    asyncio.run(test_main())