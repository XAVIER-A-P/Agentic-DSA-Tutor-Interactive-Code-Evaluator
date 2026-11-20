
from __future__ import annotations

import ast

from agents.llm_client_test import (
    get_llm_client,
    get_model_name,
    response_text,
)


def inspect_code_structure(code: str) -> dict:
    """Inspect Python syntax, loops, nesting and recursion."""

    try:
        tree = ast.parse(code)

    except SyntaxError as exc:
        return {
            "valid_syntax": False,
            "syntax_error": (
                f"{exc.msg} (line {exc.lineno})"
            ),
            "loop_count": 0,
            "max_loop_depth": 0,
            "recursive_functions": [],
        }

    loop_count = 0
    max_loop_depth = 0

    def visit(node: ast.AST, depth: int = 0):
        nonlocal loop_count, max_loop_depth

        for child in ast.iter_child_nodes(node):

            if isinstance(
                child,
                (ast.For, ast.AsyncFor, ast.While)
            ):
                loop_count += 1

                next_depth = depth + 1

                max_loop_depth = max(
                    max_loop_depth,
                    next_depth,
                )

                visit(child, next_depth)

            else:
                visit(child, depth)

    visit(tree)

    recursive = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):

            for child in ast.walk(node):

                if (
                    isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Name)
                    and child.func.id == node.name
                ):
                    recursive.append(node.name)
                    break

    return {
        "valid_syntax": True,
        "syntax_error": None,
        "loop_count": loop_count,
        "max_loop_depth": max_loop_depth,
        "recursive_functions": sorted(set(recursive)),
    }


def fallback_analysis(info: dict) -> str:

    if not info["valid_syntax"]:
        return (
            "## Complexity Analysis\n\n"
            "**Syntax error:** "
            f"`{info['syntax_error']}`\n\n"
            "Fix the syntax error before complexity analysis."
        )

    recursive = info["recursive_functions"]
    depth = info["max_loop_depth"]

    if recursive:
        estimate = (
            "Recursion detected. A recurrence-relation "
            "analysis is required. Recursion alone does "
            "not determine Big-O complexity."
        )

    elif depth == 0:
        estimate = (
            "No explicit loops or self-recursive functions "
            "were detected. This does not prove O(1), "
            "because called functions may depend on input size."
        )

    elif depth == 1:
        estimate = (
            "One maximum level of explicit iteration was "
            "detected. O(n) may apply if the loop scales "
            "linearly with input size."
        )

    else:
        estimate = (
            f"{depth} nested levels of iteration were detected. "
            f"O(n^{depth}) may apply if each level scales with n."
        )

    return f"""
## Complexity Analysis

### Time Complexity

{estimate}

### Space Complexity

Inspect additional containers, copied data, and recursion depth.
Static loop counting cannot determine auxiliary space by itself.

### Static Code Inspection

- Explicit loops: {info['loop_count']}
- Maximum nested loop depth: {depth}
- Recursive functions: {
    ', '.join(recursive) if recursive else 'None detected'
}

**Note:** This is a heuristic report, not a formal complexity proof.
"""


def analyze_complexity(code: str) -> str:

    info = inspect_code_structure(code)

    if not info["valid_syntax"]:
        return fallback_analysis(info)

    prompt = f"""
Analyze the following Python code's time and space complexity.

```python
{code}
```

AST observations:

{info}

Write a Markdown report using:

## Complexity Analysis

### Time Complexity

### Space Complexity

### Code Observations

Requirements:

1. Explain the assumptions about input size.
2. Analyze loops and recursion.
3. Consider data structures and library operations.
4. Discuss best, average and worst cases when meaningful.
5. Distinguish input storage from auxiliary space.
6. Do not assume nested loops automatically mean O(n^k).
7. Do not invent operations that are not in the code.
8. Explain when exact complexity cannot be determined.
"""

    try:

        response = get_llm_client().chat.completions.create(
            model=get_model_name(),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a rigorous algorithms analyst. "
                        "Never invent complexity claims."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.1,
            max_tokens=1800,
        )

        answer = response_text(response)

        return answer or fallback_analysis(info)

    except Exception:

        return fallback_analysis(info)
