/**
 * Frontend Orchestration Core Engine
 * Coordinates UI states and bridges payloads smoothly to the FastAPI /api/DSA_tutor endpoint.
 */
document.addEventListener("DOMContentLoaded", () => {
    // Render Icons
    lucide.createIcons();

    // DOM Nodes Mapping
    const topicQueryForm = document.getElementById("topicQueryForm");
    const topicInput = document.getElementById("topicInput");
    const answerSpace = document.getElementById("answerSpace");
    const ragStatus = document.getElementById("ragStatus");
    const challengeSpace = document.getElementById("challengeSpace");
    const codeEditor = document.getElementById("codeEditor");
    const resetStubsBtn = document.getElementById("resetStubsBtn");
    const submitSolutionBtn = document.getElementById("submitSolutionBtn");
    const consoleLogs = document.getElementById("consoleLogs");
    const runtimeBadge = document.getElementById("runtimeBadge");
    const threadIdDisplay = document.getElementById("threadIdDisplay");
    const nextAgentBadge = document.getElementById("nextAgentBadge");
    const llmCallsDisplay = document.getElementById("llmCallsDisplay");
    const askBtn = document.getElementById("askBtn");

    // Tracks persistent multi-agent graph variables across loops
    let currentThreadId = null;

    // Intercept keyboard Tab entries inside code window for standard indent spacing
    codeEditor.addEventListener("keydown", (e) => {
        if (e.key === "Tab") {
            e.preventDefault();
            const start = codeEditor.selectionStart;
            const end = codeEditor.selectionEnd;
            codeEditor.value = codeEditor.value.substring(0, start) + "    " + codeEditor.value.substring(end);
            codeEditor.selectionStart = codeEditor.selectionEnd = start + 4;
        }
    });

    /**
     * Unified Pipeline to dispatch data inputs straight into backend schema targets
     * @param {string} incomingMessage - Target text prompt or source code structure string
     */
    async function postToDSATutor(incomingMessage) {
        try {
            // Apply workspace interactive layout processing locks
            askBtn.disabled = true;
            submitSolutionBtn.disabled = true;
            ragStatus.innerText = "PROCESSING LOOP";
            ragStatus.className = "text-[10px] px-2 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-800 font-mono animate-pulse";

            const response = await fetch("/api/DSA_tutor", {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                body: JSON.stringify({
                    message: incomingMessage,
                    thread_id: currentThreadId
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP Network error occurred: ${response.status}`);
            }

            const data = await response.json();

            if (!data.success) {
                showConsoleError(data.error || "Unknown Multi-Agent processing loop failure.");
                return;
            }

            // Sync state session identifiers tracking checkpointer structures
            if (data.thread_id) {
                currentThreadId = data.thread_id;
                threadIdDisplay.innerText = currentThreadId;
            }
            
            if (data.next_agent) {
                nextAgentBadge.innerText = data.next_agent;
            }

            if (data.llm_calls !== undefined) {
                llmCallsDisplay.innerText = `Calls: ${data.llm_calls}`;
            }

            // 1. Process and Populate: AI Knowledge Answer Space
            if (data.answer) {
                ragStatus.innerText = "SYNC COMPLETE";
                ragStatus.className = "text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-mono";
                
                let renderHtml = `<div class="text-slate-300 text-xs space-y-3 leading-relaxed">`;
                renderHtml += `<p class="whitespace-pre-line">${escapeHTML(data.answer)}</p>`;
                
                // Incorporate dynamic time-complexity metrics if verified by analyzer pass
                if (data.complexity_analysis) {
                    renderHtml += `
                        <div class="mt-4 p-3 bg-slate-900 border border-slate-800 rounded-lg font-mono">
                            <div class="text-xs font-bold text-indigo-400 mb-1">Big-O Syntactic Inspection Profile:</div>
                            <p class="text-[11px] text-slate-300 whitespace-pre-wrap">${escapeHTML(data.complexity_analysis)}</p>
                        </div>`;
                }
                renderHtml += `</div>`;
                answerSpace.innerHTML = renderHtml;
            }

            // 2. Process and Populate: Challenge prompt statement workspace
            if (data.generated_challenge) {
                challengeSpace.innerHTML = `<div class="whitespace-pre-wrap text-xs font-mono text-slate-200">${escapeHTML(data.generated_challenge)}</div>`;
            }

            // 3. Populate default initial boilerplate signature fields into code area if currently clear
            if (data.student_code && !codeEditor.value.trim()) {
                codeEditor.value = data.student_code;
            }

            // 4. Process and Populate: Live evaluation output log stream metrics
            if (data.execution_result) {
                runtimeBadge.innerText = "EVALUATION FINISHED";
                runtimeBadge.className = "text-[10px] px-2 py-0.5 rounded bg-blue-950 text-blue-400 border border-blue-800 font-mono font-bold";
                
                consoleLogs.innerHTML = `
                    <div class="text-emerald-400 font-mono text-xs whitespace-pre-wrap">${escapeHTML(data.execution_result)}</div>
                `;
            }

        } catch (error) {
            showConsoleError(error.message);
        } exportFinally: {
            askBtn.disabled = false;
            submitSolutionBtn.disabled = false;
            if (ragStatus.innerText === "PROCESSING LOOP") {
                ragStatus.innerText = "STANDBY";
                ragStatus.className = "text-[10px] px-2 py-0.5 rounded bg-slate-900 text-slate-500 font-mono";
            }
        }
    }

    /**
     * Prints clean error metrics to terminal window
     * @param {string} errorMsg - Summary error logs message
     */
    function showConsoleError(errorMsg) {
        runtimeBadge.innerText = "SYSTEM ERROR";
        runtimeBadge.className = "text-[10px] px-2 py-0.5 rounded bg-rose-950 text-rose-400 border border-rose-800 font-mono font-bold";
        consoleLogs.innerHTML = `<div class="text-rose-400 font-semibold">&gt; Runtime Call Exception:</div>
                                 <div class="text-rose-500/80 font-mono text-xs mt-1">${escapeHTML(errorMsg)}</div>`;
    }

    /**
     * Standard security string encoder helper preventing visual markup injections
     */
    function escapeHTML(str) {
        if (!str) return '';
        return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    // Connect form text input fields to RAG tracking routines
    topicQueryForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const userInputText = topicInput.value.trim();
        if (!userInputText) return;
        postToDSATutor(userInputText);
    });

    // Connect standard solution button inputs to sandbox execution loops
    submitSolutionBtn.addEventListener("click", () => {
        const payloadScript = codeEditor.value.trim();
        if (!payloadScript) {
            alert("The code workspace editor is empty. Enter functional scripts before processing code evaluation.");
            return;
        }
        
        runtimeBadge.innerText = "SANDBOX RUNNING";
        runtimeBadge.className = "text-[10px] px-2 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-800 font-mono animate-pulse";
        consoleLogs.innerHTML = `<div class="text-indigo-400 animate-pulse">&gt; Dispatching application text vector variables to non-networked container sandboxes...</div>`;
        
        // Pipe active text fields straight to standard post utility routes
        postToDSATutor(payloadScript);
    });

    // Reset code areas back to default environment states
    resetStubsBtn.addEventListener("click", () => {
        codeEditor.value = "";
        consoleLogs.innerHTML = `<div class="text-slate-600">// Sandbox container runtime inactive. Execution logs from background validation pipelines will render inside this console.</div>`;
        runtimeBadge.innerText = "Awaiting Signal";
        runtimeBadge.className = "text-[10px] px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-500 uppercase tracking-wider font-bold";
    });
});
