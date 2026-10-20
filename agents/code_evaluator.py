import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0.0,
    groq_api_key=os.getenv("GROQ_API_KEY")
)


def code_evaluator(prompt):
    # Evaluate correctness and Big-O efficiency
    response = llm.invoke(prompt)

    return{
        "messages": [response]
    }