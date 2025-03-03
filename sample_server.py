from fastapi import FastAPI
from langchain.llms import OpenAI
from langchain.chains import LLMChain
from pydantic import BaseModel

app = FastAPI()

# Initialize OpenAI LLM
llm = OpenAI(model_name="text-davinci-003", temperature = 0)
qa_chain = LLMChain(llm=llm)

class Question(BaseModel):
    content: str

@app.post("/ask")
async def ask_question(question: Question):
    answer = qa_chain.run(question.content)
    return {"question": question.content, "answer": answer}



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

