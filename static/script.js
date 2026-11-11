"use strict";

let editor;
let currentThreadId = null;
const $ = (id) => document.getElementById(id);

function setPill(element, text, kind = "") {
  element.textContent = text;
  element.className = "pill" + (kind ? ` ${kind}` : "");
}
function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[c]);
}
function showConsole(message, kind = "") {
  $("consoleOutput").innerHTML = `<span class="${kind}">${escapeHTML(message)}</span>`;
}
async function apiRequest(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Accept": "application/json" },
    body: JSON.stringify(body)
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || data.error || `Request failed (${response.status})`);
  return data;
}

async function checkHealth() {
  try {
    const response = await fetch("/health");
    if (!response.ok) throw new Error("offline");
    $("apiStatus").textContent = "Online";
  } catch {
    $("apiStatus").textContent = "Offline";
  }
}

async function askTutor(message) {
  $("askBtn").disabled = true;
  setPill($("agentStatus"), "WORKING");
  try {
    const data = await apiRequest("/api/DSA_tutor", { message, thread_id: currentThreadId });
    currentThreadId = data.thread_id || currentThreadId;
    $("threadId").textContent = currentThreadId || "Active";
    $("answerContent").textContent = data.answer || "The agent returned no explanation.";
    $("challengeContent").textContent = data.generated_challenge || "No challenge was generated for this request.";
    $("llmCalls").textContent = data.llm_calls ?? 0;
    $("nextAgent").textContent = data.next_agent || "—";
    if (data.student_code && (!editor || !editor.getValue().trim())) editor.setValue(data.student_code);
    if (data.execution_result) showConsole(data.execution_result);
    setPill($("agentStatus"), "COMPLETE");
  } catch (error) {
    $("answerContent").textContent = error.message;
    setPill($("agentStatus"), "ERROR");
  } finally {
    $("askBtn").disabled = false;
  }
}

async function runCode() {
  const code = editor ? editor.getValue() : "";
  if (!code.trim()) {
    showConsole("Enter Python code before running.", "console-error");
    return;
  }
  $("runCodeBtn").disabled = true;
  setPill($("executionStatus"), "RUNNING");
  $("runHint").textContent = "Container starting...";
  showConsole("Starting isolated Docker execution...");
  try {
    const data = await apiRequest("/api/execute", { code });
    $("runtimeValue").textContent = `${data.execution_time_ms} ms`;
    $("exitValue").textContent = data.return_code ?? "timeout";
    setPill($("executionStatus"), data.status);
    $("runHint").textContent = "Execution finished";
    const output = [
      data.stdout ? `STDOUT\n${data.stdout}` : "",
      data.stderr ? `STDERR\n${data.stderr}` : "",
      !data.stdout && !data.stderr ? "(No output)" : ""
    ].filter(Boolean).join("\n\n");
    showConsole(output, data.status === "Accepted" ? "console-success" : "console-error");
  } catch (error) {
    setPill($("executionStatus"), "ERROR");
    $("runHint").textContent = "Execution failed";
    showConsole(error.message, "console-error");
  } finally {
    $("runCodeBtn").disabled = false;
  }
}

function initEditor() {
  const starter = `# Write your Python solution here\n\ndef solve():\n    # Example: read input and print your answer\n    pass\n\n\nif __name__ == "__main__":\n    solve()\n`;
  if (window.require) {
    require.config({ paths: { vs: "https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs" } });
    require(["vs/editor/editor.main"], () => {
      editor = monaco.editor.create($("editor"), {
        value: starter, language: "python", theme: "vs-dark",
        automaticLayout: true, minimap: { enabled: false },
        fontSize: 13, lineHeight: 22, tabSize: 4,
        scrollBeyondLastLine: false, roundedSelection: false,
        padding: { top: 14, bottom: 14 }
      });
    });
  } else {
    $("editor").innerHTML = '<textarea id="fallbackEditor" spellcheck="false"></textarea>';
    $("fallbackEditor").value = starter;
    $("fallbackEditor").style.cssText = "width:100%;height:100%;background:#090e19;color:#c7f0d8;border:0;padding:16px;font:13px monospace;resize:none";
    editor = { getValue: () => $("fallbackEditor").value, setValue: (v) => $("fallbackEditor").value = v };
  }
}

document.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) lucide.createIcons();
  initEditor();
  checkHealth();
  $("tutorForm").addEventListener("submit", (event) => {
    event.preventDefault();
    const message = $("promptInput").value.trim();
    if (message) askTutor(message);
  });
  $("runCodeBtn").addEventListener("click", runCode);
  $("resetCodeBtn").addEventListener("click", () => {
    if (editor) editor.setValue("# Write your Python solution here\n\ndef solve():\n    pass\n\nif __name__ == '__main__':\n    solve()\n");
  });
  $("newSessionBtn").addEventListener("click", () => {
    currentThreadId = null;
    $("threadId").textContent = "New session";
    $("answerContent").textContent = "New session started. Ask your tutor a question.";
    $("challengeContent").textContent = "Your generated problem will appear here.";
    setPill($("agentStatus"), "READY");
  });
  $("copyChallengeBtn").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText($("challengeContent").textContent);
      $("copyChallengeBtn").textContent = "Copied";
      setTimeout(() => $("copyChallengeBtn").textContent = "Copy", 1200);
    } catch { $("copyChallengeBtn").textContent = "Copy unavailable"; }
  });
});
