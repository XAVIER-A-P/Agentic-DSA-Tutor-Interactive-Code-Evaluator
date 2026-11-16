"use strict";

let editor = null;
let currentThreadId = null;
let activeTutorController = null;

const STARTER_CODE = [
  "# Write your Python solution here",
  "",
  "def solve():",
  "    # Read input, solve, and print the result",
  "    pass",
  "",
  "if __name__ == '__main__':",
  "    solve()",
  ""
].join("\n");

const $ = (id) => document.getElementById(id);

function setPill(el, text) {
  if (!el) return;
  el.textContent = text;
  el.className = "pill";
}

function escapeHTML(value) {
  const map = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  };
  return String(value ?? "").replace(/[&<>"']/g, (c) => map[c]);
}

/* Parse tutor Markdown with Marked, then sanitize before inserting into the DOM. */


function renderMarkdown(markdown) {
    const source = String(markdown ?? "");

    if (!source.trim()) return "";

    if (!window.marked || typeof window.marked.parse !== "function") {
        console.error("Marked.js failed to load.");
        return `<pre>${escapeHTML(source)}</pre>`;
    }

    const html = window.marked.parse(source, {
        gfm: true,
        breaks: true
    });

    if (!window.DOMPurify ||
        typeof window.DOMPurify.sanitize !== "function") {
        console.error("DOMPurify failed to load.");
        return `<pre>${escapeHTML(source)}</pre>`;
    }

    return window.DOMPurify.sanitize(html);
}


/* Theory, generated challenge, and complexity details share one Tutor response view. */

function formatStructuredContent(value) {
    if (value === null || value === undefined) {
        return "Not provided";
    }

    if (typeof value === "string" || typeof value === "number" ||
        typeof value === "boolean") {
        return String(value);
    }

    if (Array.isArray(value)) {
        return value.map(item => {
            return "- " + formatStructuredContent(item);
        }).join("\n");
    }

    if (typeof value === "object") {
        return Object.entries(value)
            .map(([key, item]) => {
                const heading = key
                    .replace(/_/g, " ")
                    .replace(/\b\w/g, char => char.toUpperCase());

                if (item && typeof item === "object") {
                    return `### ${heading}\n\n${formatStructuredContent(item)}`;
                }

                return `**${heading}:** ${formatStructuredContent(item)}`;
            })
            .join("\n\n");
    }

    return String(value);
}

function showTutorResponse(data) {
    const parts = [];

    if (data.answer) {
        parts.push(formatStructuredContent(data.answer));
    }

    if (data.generated_challenge) {
        parts.push(
            "## Generated Coding Challenge\n\n" +
            formatStructuredContent(data.generated_challenge)
        );
    }

    if (data.complexity_analysis) {
        parts.push(
            "## Complexity Analysis\n\n" +
            formatStructuredContent(data.complexity_analysis)
        );
    }

    const answerContent = $("answerContent");

    answerContent.innerHTML = parts.length
        ? renderMarkdown(parts.join("\n\n---\n\n"))
        : '<p class="console-muted">The tutor did not return a response for this request.</p>';
}

function showConsole(message, kind = "") {
  const cls = kind ? ` class="${escapeHTML(kind)}"` : "";
  $("consoleOutput").innerHTML = `<span${cls}>${escapeHTML(message)}</span>`;
}

async function apiRequest(url, body, signal) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json"
    },
    body: JSON.stringify(body),
    signal
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || data.error || `Request failed (${response.status})`);
  }
  return data;
}

async function checkHealth() {
  try {
    const response = await fetch("/health");
    $("apiStatus").textContent = response.ok ? "Online" : "Offline";
  } catch {
    $("apiStatus").textContent = "Offline";
  }
}

async function askTutor(message) {
  // Cancel any in-flight tutor request before starting a new one
  if (activeTutorController) {
    activeTutorController.abort();
  }
  const controller = new AbortController();
  activeTutorController = controller;

  $("askBtn").disabled = true;
  setPill($("agentStatus"), "WORKING");
  $("answerContent").innerHTML =
    '<div class="empty-state"><h3>Working on your request…</h3><p>Your DSA agents are preparing a response.</p></div>';

  try {
    const data = await apiRequest(
      "/api/DSA_tutor",
      { message, thread_id: currentThreadId },
      controller.signal
    );

    // Ignore response if this request was aborted (e.g., user clicked New Session)
    if (controller.signal.aborted) return;

    currentThreadId = data.thread_id || currentThreadId;
    $("threadId").textContent = currentThreadId || "Active";
    showTutorResponse(data);
    $("llmCalls").textContent = data.llm_calls ?? 0;
    $("nextAgent").textContent = data.next_agent || "—";

    if (data.student_code && editor && !editor.getValue().trim()) {
      editor.setValue(data.student_code);
    }
    if (data.execution_result) {
      showConsole(data.execution_result);
    }

    setPill($("agentStatus"), "COMPLETE");
  } catch (error) {
    if (error.name === "AbortError") return;
    $("answerContent").textContent = error.message;
    setPill($("agentStatus"), "ERROR");
  } finally {
    if (activeTutorController === controller) {
      activeTutorController = null;
      $("askBtn").disabled = false;
    }
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
    ]
      .filter(Boolean)
      .join("\n\n");

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
  const starter = "# Write your Python solution here\n\ndef solve():\n    # Read input, solve, and print the result\n    pass\n\nif __name__ == '__main__':\n    solve()\n";
  if (window.require) {
    require.config({
      paths: { vs: "https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs" }
    });

    require(["vs/editor/editor.main"], () => {
      editor = monaco.editor.create($("editor"), {
        value: starter,
        language: "python",
        theme: "vs-dark",
        automaticLayout: true,
        minimap: { enabled: false },
        fontSize: 13,
        lineHeight: 22,
        tabSize: 4,
        scrollBeyondLastLine: false,
        roundedSelection: false,
        padding: { top: 14, bottom: 14 }
      });
    });
  } else {
    $("editor").innerHTML = '<textarea id="fallbackEditor" spellcheck="false"></textarea>';
    $("fallbackEditor").value = starter;
    $("fallbackEditor").style.cssText =
      "width:100%;height:100%;background:#090e19;color:#c7f0d8;border:0;padding:16px;font:13px monospace;resize:none";

    editor = {
      getValue:()=>$("fallbackEditor").value,
      setValue: v => {
        $("fallbackEditor").value=v;
      }
    };
  }
}

document.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) {
    lucide.createIcons();
  }

  initEditor();
  checkHealth();

  $("tutorForm").addEventListener("submit", (e) => {
    e.preventDefault();
    const message = $("promptInput").value.trim();
    if (message) {
      askTutor(message);
    }
  });

  $("runCodeBtn").addEventListener("click", runCode);

  $("resetCodeBtn").addEventListener("click", () => {
    if (editor) {
      editor.setValue(STARTER_CODE);
    }
  });

  $("newSessionBtn").addEventListener("click", () => {
    if (activeTutorController) {
      activeTutorController.abort();
      activeTutorController = null;
    }

    currentThreadId = null;
    $("askBtn").disabled = false;
    $("threadId").textContent = "New session";
    $("answerContent").innerHTML =
      '<div class="empty-state"><h3>New learning session</h3><p>Ask a theory question or request a coding challenge.</p></div>';
    setPill($("agentStatus"), "READY");
  });

  $("copyResponseBtn").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText($("answerContent").innerText);
      $("copyResponseBtn").textContent = "Copied";
      setTimeout(() => {
        $("copyResponseBtn").innerHTML = '<i data-lucide="copy"></i> Copy';
        if (window.lucide) {
          lucide.createIcons();
        }
      }, 1200);
    } catch {
      $("copyResponseBtn").textContent = "Copy unavailable";
    }
  });
});
