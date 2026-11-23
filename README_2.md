# Agentic DSA Tutor — complete UI/API integration scaffold

This package adds a complete browser UI, FastAPI routes, a LangGraph adapter,
and a Docker-based Python runner. It is designed to sit beside your existing
`agents/` directory; it does not replace your supervisor or agent implementations.

## 1. Expected project structure

Copy these files into the root of your existing project. Keep your existing:

- `agents/supervisor.py`
- `agents/theory_expert.py`
- `agents/challenge_generator.py`
- Other agent modules and ingestion code

The resulting root should contain `app.py`, `agents/`, `services/`, `schemas/`,
`templates/`, and `static/`.

## 2. Python environment (Windows PowerShell)

```powershell
conda activate DSA_tutor
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Add your existing API keys and Supabase settings to `.env`. Do not commit `.env`.

## 3. Docker code runner

Install and start Docker Desktop. Pull the runner image:

```powershell
docker pull python:3.11-slim
docker run --rm python:3.11-slim python --version
```

The `/api/execute` route runs submitted Python in a disposable container with
network disabled, read-only root filesystem, memory/CPU/PID limits, dropped
Linux capabilities, and a short timeout.

This is a baseline for a portfolio/demo environment, not a guarantee against
all hostile code. For a public multi-user judge, use gVisor or Firecracker,
separate worker hosts, queueing, per-user rate limits, authentication, audit
logging, and strict resource quotas.

## 4. Start the app

```powershell
python app.py
```

Open http://127.0.0.1:8000

Health check: http://127.0.0.1:8000/health

## 5. Existing LangGraph contract

`services/agent_service.py` calls your current function exactly as supplied in
your earlier app code:

```python
run_DSA_tutor_agent(user_input=message, thread_id=thread_id)
```

It expects a dictionary. These keys are normalized:

- `thread_id`
- `answer`
- `generated_challenge`
- `student_code`
- `execution_result`
- `complexity_analysis`
- `next_agent`
- `llm_calls`
- optional `test_cases`

If your supervisor returns a different shape, edit only `services/agent_service.py`.

## 6. Important separation: tutor workflow vs code execution

The topic form calls `POST /api/tutor`, which invokes LangGraph.
The Run Code button calls `POST /api/execute`, which invokes the isolated
Docker runner directly. This avoids pretending that sending source code as a
natural-language prompt automatically executes it.

The runner currently executes the submitted script and captures stdout/stderr.
It does not yet compare output against generated test cases or calculate
algorithmic complexity. Those features require a known test-case schema and
an evaluator contract in your existing agents. The UI displays the actual
execution status and runtime rather than fabricating Accepted test results.

## 7. Production deployment checklist

Before exposing this publicly:

- Put the app behind HTTPS and a reverse proxy.
- Add authentication and per-user request limits.
- Move execution into isolated worker machines/containers with gVisor or Firecracker.
- Add a queue and concurrency limits.
- Pin and self-host frontend assets if CDN availability is not acceptable.
- Add structured logs, metrics, tracing, and error monitoring.
- Keep secrets in deployment environment variables / secret manager.
- Add automated API, agent, and sandbox tests.
- Review Docker daemon access: access to the Docker socket is highly privileged.
