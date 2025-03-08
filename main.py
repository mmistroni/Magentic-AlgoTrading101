from fastapi import FastAPI, Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from perplexity_tools import agent_executor
from fastapi.responses import StreamingResponse

app = FastAPI()
api_key_header = APIKeyHeader(name="X-API-Key")

class QueryInput(BaseModel):
    input: str

class QueryOutput(BaseModel):
    response: str

def get_api_key(api_key: str = Depends(api_key_header)):
    # In a real application, you would validate the API key here
    return api_key

@app.post("/query", response_model=QueryOutput)
async def query_endpoint(input_data: QueryInput):##, api_key: str = Depends(get_api_key)):
    
    async def event_generator():
        async for chunk in agent_executor.astream({'input': input_data.input, 'agent_scratchpad': ''}):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
    
    # It should be a streaming respo
    return QueryOutput(response=response)




if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
