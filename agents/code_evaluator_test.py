
from __future__ import annotations

from services.code_executor_test import execute_python


def normalize_output(value: str) -> str:

    return "\n".join(
        line.rstrip()
        for line in (value or "").strip().splitlines()
    )


def evaluate_code(
    code: str,
    stdin: str = "",
    expected_output: str | None = None,
    test_cases: list[dict] | None = None,
) -> dict:

    """
    Execute submitted Python code.

    Test case format:

    [
        {
            "input": "5",
            "expected_output": "25"
        }
    ]
    """

    if not isinstance(code, str) or not code.strip():

        return {
            "status": "Invalid Submission",
            "stdout": "",
            "stderr": "No Python code was provided.",
            "return_code": None,
            "execution_time_ms": 0.0,
            "output_matched": None,
            "tests_passed": 0,
            "tests_total": 0,
            "test_results": [],
        }

    # Single execution mode
    if test_cases is None:

        result = execute_python(
            code=code,
            stdin=stdin or "",
        )

        result.update({
            "output_matched": None,
            "tests_passed": 0,
            "tests_total": 0,
            "test_results": [],
        })

        if (
            expected_output is not None
            and result["status"] == "Accepted"
        ):

            matched = (
                normalize_output(result["stdout"])
                == normalize_output(expected_output)
            )

            result["output_matched"] = matched

            if not matched:
                result["status"] = "Wrong Answer"

        return result

    # Multiple test case mode
    if not isinstance(test_cases, list) or not test_cases:

        raise ValueError(
            "test_cases must be a non-empty list."
        )

    if len(test_cases) > 50:

        raise ValueError(
            "A maximum of 50 test cases is allowed."
        )

    test_results = []
    total_ms = 0.0
    passed = 0
    last_stderr = ""

    for index, case in enumerate(test_cases, start=1):

        if (
            not isinstance(case, dict)
            or "expected_output" not in case
        ):

            raise ValueError(
                f"Test case {index} must contain expected_output."
            )

        run = execute_python(
            code,
            str(case.get("input", "")),
        )

        total_ms += float(
            run.get("execution_time_ms", 0)
        )

        last_stderr = (
            run.get("stderr", "")
            or last_stderr
        )

        matched = (
            run.get("status") == "Accepted"
            and normalize_output(run.get("stdout", ""))
            == normalize_output(
                str(case["expected_output"])
            )
        )

        if matched:
            passed += 1

        test_results.append({
            "test_case": index,
            "status": (
                "Passed"
                if matched
                else (
                    run.get("status")
                    if run.get("status") != "Accepted"
                    else "Wrong Answer"
                )
            ),
            "stdout": run.get("stdout", ""),
            "stderr": run.get("stderr", ""),
            "expected_output": str(
                case["expected_output"]
            ),
            "execution_time_ms": run.get(
                "execution_time_ms", 0
            ),
        })

        if run.get("status") in {
            "Time Limit Exceeded",
            "Execution Environment Error",
        }:
            break

    total = len(test_results)

    all_passed = (
        total == len(test_cases)
        and passed == len(test_cases)
    )

    if all_passed:
        status = "Accepted"

    elif any(
        item["status"] == "Time Limit Exceeded"
        for item in test_results
    ):
        status = "Time Limit Exceeded"

    elif any(
        item["status"] == "Execution Environment Error"
        for item in test_results
    ):
        status = "Execution Environment Error"

    elif any(
        item["status"] == "Runtime Error"
        for item in test_results
    ):
        status = "Runtime Error"

    else:
        status = "Wrong Answer"

    first = test_results[0] if test_results else {}

    return {
        "status": status,
        "stdout": first.get("stdout", ""),
        "stderr": last_stderr,
        "return_code": 0 if status == "Accepted" else None,
        "execution_time_ms": round(total_ms, 2),
        "output_matched": all_passed,
        "tests_passed": passed,
        "tests_total": len(test_cases),
        "test_results": test_results,
    }
