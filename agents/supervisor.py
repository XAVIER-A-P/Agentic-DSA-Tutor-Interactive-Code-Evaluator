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
from agents.challenge_generator import challenge_generator
from agents.code_evaluator import code_evaluator
from agents.theory_expert import answer_textbook_query

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

def theory_expert_node(state: AgentState):
    # Initialize the LLM with specified parameters
    llm = ChatGroq(
        model="openai/gpt-oss-120b", 
        temperature=0.2, 
        groq_api_key=os.getenv("GROQ_API_KEY")
    )

    llm_with_tools = llm.bind_tools([answer_textbook_query])
    
    # Process the last message from user or supervisor
    response = llm_with_tools.invoke(state["messages"])
    
    return {
        "messages": [response],
        "next_agent": "Supervisor"
    }


# ============================================================
# Challenge Generator Agent
# ============================================================

def challenge_generator_node(state: AgentState):
        # Initialize the LLM with specified parameters
    llm = ChatGroq(
        model="openai/gpt-oss-120b", 
        temperature=0.7, 
        groq_api_key=os.getenv("GROQ_API_KEY")
    )
    
    prompt = f"""You are a Curriculum Designer. Based on the topic '{state['current_topic']}', 
    generate a LeetCode-style challenge. Provide a description, function signature, and 3 test cases."""
    
    response = llm.invoke(prompt)
    
    return {
        "messages": [response],
        "generated_challenge": {"prompt": response.content},
        "next_agent": "Supervisor"
    }


# ============================================================
# Code Evaluator Agent
# ============================================================

def code_evaluator_node(state: AgentState):
        # Initialize the LLM with specified parameters
    llm = ChatGroq(
        model="openai/gpt-oss-120b", 
        temperature=0.0,  # Zero variance for evaluating code 
        groq_api_key=os.getenv("GROQ_API_KEY")
    )
    llm_with_tools = llm.bind_tools([code_evaluator])
    
    # Evaluate correctness and Big-O efficiency
    response = llm_with_tools.invoke(
        f"Evaluate this code: {state['student_code']} against this challenge: {state['generated_challenge']}"
    )
    
    return {
        "messages": [response],
        "next_agent": "Supervisor"
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



# ============================================================
# Build Graph
# ============================================================   

# Construct the Workflow Graph
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("TheoryExpert", theory_expert_node)
workflow.add_node("ChallengeGenerator", challenge_generator_node)
workflow.add_node("CodeEvaluator", code_evaluator_node)

# Set Entry Point based on conditional router logic
workflow.set_conditional_entry_point(
    supervisor_router,
    {
        "TheoryExpert": "TheoryExpert",
        "ChallengeGenerator": "ChallengeGenerator",
        "CodeEvaluator": "CodeEvaluator",
        END: END
    }
)

# Wire Nodes back to router evaluation
workflow.add_edge("TheoryExpert", END)
workflow.add_edge("ChallengeGenerator", END)
workflow.add_edge("CodeEvaluator", END)

# Compile Graph
app = workflow.compile()


# ============================================================
# PostgreSQL Checkpointer
# ============================================================ 

DATABASE_URL = get_database_url()

_conn = psycopg.connect(
    DATABASE_URL,
    autocommit=True,
    row_factory=dict_row
)

checkpointer = PostgresSaver(_conn)
checkpointer.setup()

tutor_workflow = workflow.compile(checkpointer=checkpointer)


# ============================================================
# Function for FastAPI
# ============================================================ 

def run_DSA_tutor_agent(user_input: str, thread_id: str | None = None):
    if not thread_id:
        thread_id = f"user_{uuid.uuid4().hex}"

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    result = tutor_workflow.invoke(
        {
            "messages":[
                HumanMessage(content=user_input)
            ],
            "current_topic": user_input,                              
            "generated_challenge": {},                      
            "student_code": "",                                
            "execution_result": "",                        
            "complexity_analysis": "",                       
            "next_agent": "",                                  
            "llm_calls": 0
        },
        config=config
    )

    final_answer = result["messages"][-1].content

    return {
        "thread_id": thread_id,
        "answer": final_answer,
        "generated_challenge": result.get("generated_challenge", {}),
        "student_code": result.get("student_code", ""),
        "execution_result": result.get("execution_result", ""),
        "complexity_analysis": result.get("complexity_analysis", ""),
        "next_agent": result.get("next_agent", ""),
        "llm_calls": result.get("llm_calls", 0)
    }
