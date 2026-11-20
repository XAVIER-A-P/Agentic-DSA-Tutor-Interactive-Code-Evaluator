
from __future__ import annotations

from agents.llm_client_test import (
    get_llm_client,
    get_model_name,
    response_text,
)


def generate_challenge(
    topic: str,
    difficulty: str = "Intermediate",
) -> str:

    topic = (
        (topic or "").strip()
        or "Data Structures and Algorithms"
    )

    difficulty = (difficulty or "Intermediate").strip()

    allowed = {"Beginner", "Intermediate", "Advanced"}

    if difficulty not in allowed:
        difficulty = "Intermediate"

    prompt = f"""
Create one original, technically correct Python coding challenge.

Topic: {topic}
Difficulty: {difficulty}

Return Markdown using these sections:

# Challenge Title

## Problem Description

## Input Format

## Output Format

## Constraints

## Examples

## Starter Code

## Concepts Tested

## Hints

Requirements:

1. Include at least two internally consistent examples.
2. Explain all input and output requirements.
3. Provide realistic constraints.
4. Make the challenge solvable using Python.
5. Provide useful starter code.
6. Include three progressive hints.
7. Do not reveal the complete solution.
8. Do not invent textbook citations.
9. Do not claim hidden tests exist.
10. Ensure the problem matches the requested difficulty.
"""

    response = get_llm_client().chat.completions.create(
        model=get_model_name(),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an experienced Data Structures "
                    "and Algorithms instructor and coding "
                    "problem author."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.5,
        max_tokens=2600,
    )

    result = response_text(response)

    if not result:
        raise RuntimeError(
            "The model returned an empty challenge."
        )

    return result
