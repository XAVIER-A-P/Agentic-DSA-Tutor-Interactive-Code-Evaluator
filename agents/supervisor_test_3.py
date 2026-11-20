
from __future__ import annotations

import re
from typing import Literal, TypedDict

from langgraph.graph import END, StateGraph


class TutorState(TypedDict, total=False):

    user_input: str
    thread_id: str

    answer: str
    generated_challenge: str
    student_code: str

    execution_result: dict | None
    complexity_analysis: str

    next_agent: str
    llm_calls: int
    error: str


CODE_FENCE_RE = re.compile(
    r"```(?:python|py)?\s*\n(.*?)```",
    flags=re.IGNORECASE | re.DOTALL,
)


def extract_python_code(text: str) -> str:

    matches = CODE_FENCE_RE.findall(text or "")

    return "\n\n".join(
        item.strip()
        for item in matches
        if item.strip()
    )


def looks_like_python(text: str) -> bool:

    lines = (text or "").strip().splitlines()

    if not lines:
        return False

    indicators = (
        "def ",
        "class ",
        "import ",
        "from ",
        "print(",
        "for ",
        "while ",
        "if ",
        "elif ",
        "else:",
        "return ",
        "input(",
        " = ",
        " == ",
        " in ",
    )

    return any(
        any(token in line for token in indicators)
        for line in lines
    )


def extract_topic(user_input: str) -> str:

    pattern = (
        r"\b(?:on|about|covering)\s+(.+?)"
        r"(?:\s+(?:at|with)\s+"
        r"(?:beginner|easy|medium|intermediate|hard|advanced)"
        r"(?:\s+level)?)?[.!?]*$"
    )

    match = re.search(
        pattern,
        user_input,
        flags=re.IGNORECASE,
    )

    if match:

        topic = match.group(1).strip(" .?!")

        if topic:
            return topic

    return "Data Structures and Algorithms"


def extract_difficulty(user_input: str) -> str:

    lowered = user_input.lower()

    if any(
        word in lowered
        for word in ("beginner", "easy")
    ):
        return "Beginner"

    if any(
        word in lowered
        for word in ("advanced", "hard")
    ):
        return "Advanced"

    return "Intermediate"


def route_request(
    state: TutorState,
) -> Literal["challenge", "evaluate", "theory"]:

    text = state.get("user_input", "").strip()
    lowered = text.lower()

    if extract_python_code(text) or looks_like_python(text):
        return "evaluate"

    challenge_terms = (
        "generate a challenge",
        "create a challenge",
        "give me a challenge",
        "coding challenge",
        "coding problem",
        "practice problem",
    )

    if any(
        term in lowered
        for term in challenge_terms
    ):
        return "challenge"

    evaluation_terms = (
        "run this code",
        "execute this code",
        "evaluate my code",
        "check my code",
        "debug this code",
        "test my code",
        "analyze my code",
    )

    if any(
        term in lowered
        for term in evaluation_terms
    ):
        return "evaluate"

    return "theory"


# ============================================================
# ROUTER
# ============================================================

def router_node(state: TutorState) -> TutorState:

    return {
        "next_agent": route_request(state)
    }


# ============================================================
# CHALLENGE GENERATOR
# ============================================================

def challenge_node(state: TutorState) -> TutorState:

    from agents.challenge_generator_test import generate_challenge

    user_input = state.get("user_input", "")

    topic = extract_topic(user_input)
    difficulty = extract_difficulty(user_input)

    try:

        challenge = generate_challenge(
            topic=topic,
            difficulty=difficulty,
        )

        return {
            "answer": (
                f"I generated a {difficulty.lower()}-level "
                f"challenge about **{topic}**."
            ),
            "generated_challenge": challenge,
            "student_code": "",
            "execution_result": None,
            "complexity_analysis": "",
            "next_agent": "challenge_generator",
            "llm_calls": 1,
            "error": "",
        }

    except Exception as exc:

        return {
            "answer": (
                "Challenge generation failed. "
                "Check your LLM configuration."
            ),
            "generated_challenge": "",
            "student_code": "",
            "execution_result": None,
            "complexity_analysis": "",
            "next_agent": "challenge_generator",
            "llm_calls": 0,
            "error": str(exc),
        }


# ============================================================
# CODE EVALUATOR
# ============================================================

def format_execution_answer(result: dict) -> str:

    status = result.get("status", "Unknown")

    parts = [
        "## Code Execution Result",
        f"**Status:** {status}",
        (
            "**Execution time:** "
            f"{result.get('execution_time_ms', 0)} ms"
        ),
    ]

    if result.get("tests_total", 0):

        parts.append(
            f"**Test cases:** "
            f"{result.get('tests_passed', 0)}/"
            f"{result.get('tests_total', 0)} passed"
        )

    stdout = result.get("stdout", "")
    stderr = result.get("stderr", "")

    if stdout.strip():

        parts.extend([
            "",
            "### Standard Output",
            "```text",
            stdout.strip(),
            "```",
        ])

    if stderr.strip():

        parts.extend([
            "",
            "### Standard Error",
            "```text",
            stderr.strip(),
            "```",
        ])

    if status == "Accepted":

        parts.append(
            "\nYour program executed successfully."
        )

    elif status == "Wrong Answer":

        parts.append(
            "\nThe program ran, but its output did not "
            "match the expected output."
        )

    elif status == "Time Limit Exceeded":

        parts.append(
            "\nThe program exceeded the configured time limit."
        )

    elif status == "Runtime Error":

        parts.append(
            "\nThe program encountered a runtime error."
        )

    elif status == "Execution Environment Error":

        parts.append(
            "\nThe execution environment could not run "
            "the program. Check Docker."
        )

    if result.get("tests_total", 0):

        parts.append(
            "\n**Note:** Only the test cases supplied to "
            "the evaluator were checked. No hidden test "
            "suite is implied."
        )

    return "\n".join(parts)


def evaluation_node(state: TutorState) -> TutorState:

    from agents.code_evaluator_test import evaluate_code
    from agents.complexity_analyzer_test import analyze_complexity

    user_input = state.get("user_input", "")

    code = extract_python_code(user_input)

    if not code and looks_like_python(user_input):
        code = user_input.strip()

    if not code:

        return {
            "answer": (
                "Please submit your Python code inside a "
                "Markdown code block.\n\n"
                "Example:\n\n"
                "```python\n"
                "print('Hello')\n"
                "```"
            ),
            "generated_challenge": "",
            "student_code": "",
            "execution_result": None,
            "complexity_analysis": "",
            "next_agent": "code_evaluator",
            "llm_calls": 0,
            "error": "",
        }

    try:

        result = evaluate_code(code)

        try:

            complexity = analyze_complexity(code)
            llm_calls = 1

        except Exception as exc:

            complexity = (
                f"Complexity analysis failed: {exc}"
            )

            llm_calls = 0

        return {
            "answer": format_execution_answer(result),
            "generated_challenge": "",
            "student_code": code,
            "execution_result": result,
            "complexity_analysis": complexity,
            "next_agent": "code_evaluator",
            "llm_calls": llm_calls,
            "error": "",
        }

    except Exception as exc:

        return {
            "answer": "Code evaluation failed.",
            "generated_challenge": "",
            "student_code": code,
            "execution_result": {
                "status": "Evaluation Error",
                "stdout": "",
                "stderr": str(exc),
                "return_code": None,
                "execution_time_ms": 0.0,
            },
            "complexity_analysis": "",
            "next_agent": "code_evaluator",
            "llm_calls": 0,
            "error": str(exc),
        }


# ============================================================
# THEORY EXPERT
# ============================================================

def theory_node(state: TutorState) -> TutorState:

    # Lazy import: theory_expert loads the embedding model
    # when it is imported.
    from agents.theory_expert import answer_textbook_query

    question = state.get("user_input", "").strip()

    try:

        answer = answer_textbook_query(question)

        return {
            "answer": str(answer),
            "generated_challenge": "",
            "student_code": "",
            "execution_result": None,
            "complexity_analysis": "",
            "next_agent": "theory_expert",
            "llm_calls": 1,
            "error": "",
        }

    except Exception as exc:

        return {
            "answer": (
                "The textbook assistant could not complete "
                "the request. Check Supabase, the textbook "
                "index, and your LLM settings."
            ),
            "generated_challenge": "",
            "student_code": "",
            "execution_result": None,
            "complexity_analysis": "",
            "next_agent": "theory_expert",
            "llm_calls": 0,
            "error": str(exc),
        }


# ============================================================
# LANGGRAPH
# ============================================================

def build_tutor_graph():

    graph = StateGraph(TutorState)

    graph.add_node("router", router_node)

    graph.add_node(
        "challenge_generator",
        challenge_node,
    )

    graph.add_node(
        "code_evaluator",
        evaluation_node,
    )

    graph.add_node(
        "theory_expert",
        theory_node,
    )

    graph.set_entry_point("router")

    graph.add_conditional_edges(
        "router",
        lambda state: state["next_agent"],
        {
            "challenge": "challenge_generator",
            "evaluate": "code_evaluator",
            "theory": "theory_expert",
        },
    )

    graph.add_edge(
        "challenge_generator",
        END,
    )

    graph.add_edge(
        "code_evaluator",
        END,
    )

    graph.add_edge(
        "theory_expert",
        END,
    )

    return graph.compile()


tutor_graph = build_tutor_graph()


# ============================================================
# PUBLIC FUNCTION USED BY app.py
# ============================================================

def run_DSA_tutor_agent(
    user_input: str,
    thread_id: str,
) -> dict:

    safe_thread_id = str(thread_id or "default")

    if not user_input or not user_input.strip():

        return {
            "thread_id": safe_thread_id,
            "answer": (
                "Please enter a question or submit Python code."
            ),
            "generated_challenge": "",
            "student_code": "",
            "execution_result": None,
            "complexity_analysis": "",
            "next_agent": "none",
            "llm_calls": 0,
        }

    try:

        result = tutor_graph.invoke(
            {
                "user_input": user_input.strip(),
                "thread_id": safe_thread_id,
            },
            config={
                "configurable": {
                    "thread_id": safe_thread_id,
                }
            },
        )

        return {
            "thread_id": safe_thread_id,
            "answer": str(
                result.get("answer", "")
            ),
            "generated_challenge": str(
                result.get("generated_challenge", "")
            ),
            "student_code": str(
                result.get("student_code", "")
            ),
            "execution_result": result.get(
                "execution_result"
            ),
            "complexity_analysis": str(
                result.get("complexity_analysis", "")
            ),
            "next_agent": str(
                result.get("next_agent", "unknown")
            ),
            "llm_calls": int(
                result.get("llm_calls", 0)
            ),
        }

    except Exception as exc:

        return {
            "thread_id": safe_thread_id,
            "answer": (
                "The DSA Tutor encountered an unexpected "
                "backend error. Check the server terminal."
            ),
            "generated_challenge": "",
            "student_code": "",
            "execution_result": None,
            "complexity_analysis": "",
            "next_agent": "supervisor",
            "llm_calls": 0,
            "error": str(exc),
        }
