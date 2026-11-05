# import os
# from typing import Annotated, Sequence, TypedDict
# from operator import add
# from langchain_core.messages import BaseMessage
# from langchain_openai import ChatOpenAI
# from langgraph.graph import StateGraph, END

# # Define Global State
# class AgentState(TypedDict):
#     messages: Annotated[Sequence[BaseMessage], add] # Append-only chat history
#     current_topic: str                               # e.g., "Singly Linked Lists"
#     generated_challenge: dict                        # Storage for active challenge
#     student_code: str                                # Code submitted by user
#     execution_result: str                            # Output from Sandbox
#     complexity_analysis: str                         # Big-O assessment
#     next_agent: str                                  # Routing pointer


############################################################################################################################



import os
from dotenv import load_dotenv

load_dotenv()

from typing import TypedDict, Annotated, Sequence
import operator
import uuid

import psycopg
from psycopg.rows import dict_row

from operator import add
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import (
    AnyMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
    BaseMessage,
)

from langchain_groq import ChatGroq
from challenge_generator import challenge_generator
from code_evaluator import code_evaluator
from theory_expert import answer_textbook_query

def get_database_url():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError(
            "DATABASE_URL is missing. please add your superbase PostgreSQL External Databas_URL to .env"
        )

    if "sslmode=" not in database_url:
        separator = "&" if "?" in database_url else "?"
        database_url = f"{database_url}{separator}sslmode=require"

    return database_url


GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing. Please add it to your .env file.")


# ============================================================
# LLM
# ============================================================

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=GROQ_API_KEY
)


# ============================================================
# State
# ============================================================

# Define Global State
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add] # Append-only chat history
    current_topic: str                               # e.g., "Singly Linked Lists"
    generated_challenge: dict                        # Storage for active challenge
    student_code: str                                # Code submitted by user
    execution_result: str                            # Output from Sandbox
    complexity_analysis: str                         # Big-O assessment
    next_agent: str                                  # Routing pointer
    llm_calls: int                                   # How many times llms have been called (Count)

    
# ============================================================
# Theory Expert Agent
# ============================================================

def theory_expert_agent(state: AgentState):
    query = state["current_topic"]
    textbook_theory = answer_textbook_query(query)

    return {
        "generated_challenge": textbook_theory,
        "messages": [
            AIMessage(content="Textbook theory featched.")
        ],
        "llm_calls": state.get("llm_calls", 0) + 1
    }


# ============================================================
# Challenge Generator Agent
# ============================================================

def challenge_agent(state: AgentState):
    query = f"Generate leetcode style python coding questions for {state['current_topic']}"
    coding_question = challenge_generator(query)

    return {
        "generated_challenge": coding_question,
        "messages": [
            AIMessage(content="Coding challenge fetched.")
        ],
        "llm_calls": state.get("llm_calls", 0) + 1
    }


# ============================================================
# Code Evaluator Agent
# ============================================================

def evaluator_agent(state: AgentState):
    query =  f"Evaluate this code: {state['student_code']} against this challenge: {state['generated_challenge']}"
    code = code_evaluator(query)

    # return {
    #     "student_code": code,
    #     "messages": [
    #         AIMessage(content="Coding challenge fetched.")
    #     ],
    #     "llm_calls": state.get("llm_calls", 0) + 1
    # }

    response = llm.invoke([
        SystemMessage(content="You are an expert code evaluater."),
        HumanMessage(content=query)
    ])

    return {
        "student_code": response.content,
        "messages": [response],
        "llm_call": state.get("llm_calls", 0) + 1
    }


# ============================================================
# Supervisor Agent
# ============================================================    

def supervisor_router(state: AgentState):
    # Pure routing logic based on user intent or current system progress
    last_message = state["messages"][-1].content.lower()
    
    if "explain" in last_message or "what is" in last_message:
        return "TheoryExpert"
    elif "give me a challenge" in last_message or "next problem" in last_message:
        return "ChallengeGenerator"
    elif "submit" in last_message or "run code" in last_message:
        return "CodeEvaluator"
    else:
        return END


