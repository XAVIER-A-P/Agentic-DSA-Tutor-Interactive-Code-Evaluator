import os
import uuid
from typing import TypedDict, Annotated, Sequence
from operator import add

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver

from langchain_core.messages import AnyMessage, HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_groq import ChatGroq

# Assuming these exist in your project structure
from agents.challenge_generator import challenge_generator
from agents.code_evaluator import code_evaluator
from agents.theory_expert import answer_textbook_query

load_dotenv()

def get_database_url():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL is missing. Please add your Supabase PostgreSQL External Database URL to .env")
    if "sslmode=" not in database_url:
        separator = "&" if "?" in database_url else "?"
        database_url = f"{database_url}{separator}sslmode=require"
    return database_url

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing. Please add it to your .env file.")

# ============================================================
# State
# ============================================================
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add]  # Append-only chat history
    current_topic: str          # e.g., "Singly Linked Lists"
    generated_challenge: dict   # Storage for active challenge
    student_code: str           # Code submitted by user
    execution_result: str       # Output from Sandbox
    complexity_analysis: str    # Big-O assessment
    next_agent: str             # Routing pointer
    llm_calls: int              # How many times LLMs have been called

# ============================================================
# Nodes (Fixed API key parameter names)
# ============================================================
def theory_expert_node(state: AgentState):
    llm = ChatGroq(
        model="openai/gpt-oss-120b",
        temperature=0.2,
        api_key=GROQ_API_KEY
    )
    llm_with_tools = llm.bind_tools([answer_textbook_query])
    response = llm_with_tools.invoke(state["messages"])
    return {
        "messages": [response],
        "next_agent": "Supervisor",
        "llm_calls": state.get("llm_calls", 0) + 1
    }

def challenge_generator_node(state: AgentState):
    llm = ChatGroq(
        model="openai/gpt-oss-120b",
        temperature=0.7,
        api_key=GROQ_API_KEY
    )
    prompt = f"You are a Curriculum Designer. Based on the topic '{state.get('current_topic', 'DSA')}', generate a LeetCode-style challenge. Provide a description, function signature, and 3 test cases."
    response = llm.invoke(prompt)
    return {
        "messages": [response],
        "generated_challenge": {"prompt": response.content},
        "next_agent": "Supervisor",
        "llm_calls": state.get("llm_calls", 0) + 1
    }

def code_evaluator_node(state: AgentState):
    llm = ChatGroq(
        model="openai/gpt-oss-120b",
        temperature=0.0,
        api_key=GROQ_API_KEY
    )
    llm_with_tools = llm.bind_tools([code_evaluator])
    response = llm_with_tools.invoke(
        f"Evaluate this code: {state.get('student_code', '')} against this challenge: {state.get('generated_challenge', {})}"
    )
    return {
        "messages": [response],
        "next_agent": "Supervisor",
        "llm_calls": state.get("llm_calls", 0) + 1
    }

# ============================================================
# Router Logic (Routes *after* the node executes)
# ============================================================
def supervisor_router(state: AgentState):
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
# Build Graph (Fixed Routing Topology)
# ============================================================
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("TheoryExpert", theory_expert_node)
workflow.add_node("ChallengeGenerator", challenge_generator_node)
workflow.add_node("CodeEvaluator", code_evaluator_node)

# START routes directly to the conditional router
workflow.add_conditional_edges(
    START,
    supervisor_router,
    {
        "TheoryExpert": "TheoryExpert",
        "ChallengeGenerator": "ChallengeGenerator",
        "CodeEvaluator": "CodeEvaluator",
        END: END
    }
)

# Every agent loops back to the supervisor router for the next turn
workflow.add_conditional_edges(
    "TheoryExpert",
    supervisor_router,
    {"TheoryExpert": "TheoryExpert", "ChallengeGenerator": "ChallengeGenerator", "CodeEvaluator": "CodeEvaluator", END: END}
)
workflow.add_conditional_edges(
    "ChallengeGenerator",
    supervisor_router,
    {"TheoryExpert": "TheoryExpert", "ChallengeGenerator": "ChallengeGenerator", "CodeEvaluator": "CodeEvaluator", END: END}
)
workflow.add_conditional_edges(
    "CodeEvaluator",
    supervisor_router,
    {"TheoryExpert": "TheoryExpert", "ChallengeGenerator": "ChallengeGenerator", "CodeEvaluator": "CodeEvaluator", END: END}
)

# ============================================================
# DB Checkpointer Setup & Single Compile
# ============================================================
DATABASE_URL = get_database_url()
_conn = psycopg.connect(DATABASE_URL, autocommit=True, row_factory=dict_row)
checkpointer = PostgresSaver(_conn)
checkpointer.setup()

tutor_workflow = workflow.compile(checkpointer=checkpointer)

# ============================================================
# FastAPI Execution Handler (Fixed State Handling)
# ============================================================
def run_DSA_tutor_agent(user_input: str, thread_id: str | None = None):
    if not thread_id:
        thread_id = f"user_{uuid.uuid4().hex}"
        
    config = {"configurable": {"thread_id": thread_id}}
    
    # Check if thread already has memory history
    state_history = tutor_workflow.get_state(config)
    
    # Extract structural state tokens from input if needed (e.g., matching custom fields)
    update_payload = {}
    if "submit" in user_input.lower() or "run code" in user_input.lower():
        update_payload["student_code"] = user_input # Or parse out code blocks cleanly
    else:
        update_payload["current_topic"] = user_input
        
    # Standard messaging update format
    update_payload["messages"] = [HumanMessage(content=user_input)]
    
    # Run workflow (Persisted attributes are maintained by LangGraph via PostgresSaver)
    result = tutor_workflow.invoke(update_payload, config=config)
    
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
