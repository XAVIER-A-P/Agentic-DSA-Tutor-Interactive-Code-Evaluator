/**
 * Frontend Core State Engine
 * Emulates the LangGraph cyclical multi-agent environment, routing phases,
 * and background Docker container sandboxed execution.
 */

document.addEventListener("DOMContentLoaded", () => {
    // Initialise Lucide Icon Sets
    lucide.createIcons();

    // DOM References
    const chatTimeline = document.getElementById("chatTimeline");
    const agentInputForm = document.getElementById("agentInputForm");
    const userInput = document.getElementById("userInput");
    const codeEditor = document.getElementById("codeEditor");
    const submitCodeBtn = document.getElementById("submitCodeBtn");
    const consoleLogs = document.getElementById("consoleLogs");
    const runtimeBadge = document.getElementById("runtimeBadge");
    const redisCheckpoint = document.getElementById("redisCheckpoint");

    // Internal Application State Mocking Frame
    let currentChallenge = null;
    let checkpointCounter = 101;

    // Agent Definitions Mapping Architecture Specifications
    const AGENTS = {
        ROUTER: { name: "Supervisor Router", icon: "git-branch", color: "text-amber-400 bg-amber-400/10 border-amber-500/20" },
        GENERATOR: { name: "Challenge Generator", icon: "file-plus", color: "text-indigo-400 bg-indigo-400/10 border-indigo-500/20" },
        EVALUATOR: { name: "Code Evaluator", icon: "shield", color: "text-cyan-400 bg-cyan-400/10 border-cyan-500/20" },
        THEORY: { name: "Theory Expert (RAG)", icon: "book-open", color: "text-emerald-400 bg-emerald-400/10 border-emerald-500/20" }
    };

    /**
     * Renders modular multi-agent updates onto the timeline display
     */
    function appendAgentMessage(agent, text, isCode = false) {
        const messageDiv = document.createElement("div");
        messageDiv.className = "flex gap-3 animate-fade-in";

        const contentHTML = isCode 
            ? `<pre class="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs font-mono text-emerald-400 overflow-x-auto whitespace-pre-wrap w-full">${escapeHTML(text)}</pre>`
            : `<p class="text-xs text-slate-300 leading-relaxed whitespace-pre-line">${text}</p>`;

        messageDiv.innerHTML = `
            <div class="w-7 h-7 rounded-lg shrink-0 flex items-center justify-center border ${agent.color}">
                <i data-lucide="${agent.icon}" class="w-3.5 h-3.5"></i>
            </div>
            <div class="flex-1 space-y-1">
                <div class="flex items-center justify-between">
                    <span class="text-[11px] font-semibold text-slate-400 tracking-wide">${agent.name}</span>
                    <span class="text-[9px] text-slate-600 font-mono">${new Date().toLocaleTimeString()}</span>
                </div>
                ${contentHTML}
            </div>
        `;
        
        chatTimeline.appendChild(messageDiv);
        lucide.createIcons();
        chatTimeline.scrollTop = chatTimeline.scrollHeight;
    }

    /**
     * Appends pure standard user message blocks
     */
    function appendUserMessage(text) {
        const messageDiv = document.createElement("div");
        messageDiv.className = "flex gap-3 justify-end";
        messageDiv.innerHTML = `
            <div class="flex-1 space-y-1 text-right max-w-[85%] ml-auto">
                <div class="text-[11px] font-semibold text-slate-400 tracking-wide">Student</div>
                <div class="bg-indigo-600/10 border border-indigo-500/20 px-3 py-2 rounded-lg text-xs text-slate-200 inline-block text-left">
                    ${escapeHTML(text)}
                </div>
            </div>
        `;
        chatTimeline.appendChild(messageDiv);
        chatTimeline.scrollTop = chatTimeline.scrollHeight;
    }

    /**
     * Form Helper Utilities
     */
    window.fillSamplePrompt = function(promptText) {
        userInput.value = promptText;
        userInput.focus();
    };

    function escapeHTML(str) {
        return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    function updateCheckpoint() {
        checkpointCounter += 1;
        redisCheckpoint.innerText = `chk_tx_${checkpointCounter}`;
    }

    /**
     * Input Router Logic Flow Handling (Phase 2 & Phase 3 Simulation)
     */
    agentInputForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const query = userInput.value.trim();
        if (!query) return;

        appendUserMessage(query);
        userInput.value = "";

        // Trigger Phase 2: Orchestration State Loop Transitions
        setTimeout(() => {
            appendAgentMessage(AGENTS.ROUTER, `Intercepted target prompt query. Updating centralized LangGraph session tracking vector context. Routing task trajectory directly to the Assignment Engine.`);
            updateCheckpoint();
        }, 600);

        // Trigger Phase 3: Simulated Problem Synthesis & Embedding Evaluation
        if (query.toLowerCase().includes("binary search tree") || query.toLowerCase().includes("bst")) {
            setTimeout(() => {
                appendAgentMessage(AGENTS.GENERATOR, `Scanning base textbook vectors on node configuration mechanics. Instantiating medium tier challenge prompt framework...`);
            }, 1600);

            setTimeout(() => {
                currentChallenge = "bst";
                const problemPrompt = `### Challenge: Validate Binary Search Tree Accuracy\n\nImplement an analytical verification algorithm determining if a given binary root construct fulfills structural constraint laws matching traditional text patterns (Left Child < Root < Right Child).`;
                appendAgentMessage(AGENTS.GENERATOR, problemPrompt);
                
                // Inject scaffolding signature code straight into IDE component window
                codeEditor.value = `def is_valid_bst(root):\n    # TODO: Implement complexity boundaries within O(N) constraints\n    # The structural testing environment will isolate metrics securely\n    pass\n`;
                updateCheckpoint();
            }, 2800);
        } else {
            // General Architectural Fallback Path
            setTimeout(() => {
                appendAgentMessage(AGENTS.THEORY, `Query directed to Qdrant indexes. Extraction completed: Textbook insights dictate that functional application structures scale explicitly relative to depth limitations during processing execution patterns.`);
                updateCheckpoint();
            }, 1800);
        }
    });

    /**
     * Code Submission Pipeline Handling (Phase 4 Execution Lifecycle simulation)
     */
    submitCodeBtn.addEventListener("click", () => {
        const activeScript = codeEditor.value.trim();
        if (!activeScript) {
            alert("The IDE workspace context appears empty. Input functional structures before executing scripts.");
            return;
        }

        // Set UI UI State indicators to Sandbox Active Mode
        submitCodeBtn.disabled = true;
        submitCodeBtn.innerText = "Running Test Harness...";
        runtimeBadge.innerText = "Queued (Celery)";
        runtimeBadge.className = "text-[10px] uppercase font-bold tracking-wider text-amber-500";
        
        consoleLogs.innerHTML = `<div class="text-indigo-400 animate-pulse">&gt; Dispatching code payloads to non-networked container layers...</div>`;

        // Execution Pipeline Step 1: Routing & State Logging
        setTimeout(() => {
            appendAgentMessage(AGENTS.EVALUATOR, `Extracting algorithmic signatures. Packaging environment verification sequence payloads inside strict Docker execution sandboxes.`);
            consoleLogs.innerHTML += `<div class="text-slate-400">&gt; Worker picked up message frame. Initializing ephemeral container sandbox environment...</div>`;
            runtimeBadge.innerText = "Executing";
            updateCheckpoint();
        }, 1000);

        // Execution Pipeline Step 2: Running Complexity Verification Scans
        setTimeout(() => {
            consoleLogs.innerHTML += `<div class="text-slate-400">&gt; Running code execution vectors against local test modules...</div>`;
            appendAgentMessage(AGENTS.EVALUATOR, `Executing Parallel Analytical Inspection: Processing static code structure scans via localized abstract trees to check for Big-O code compliance standard levels.`);
        }, 2200);

        // Execution Pipeline Step 3: Returning Outputs & Re-adjusting System Flags (Phase 5 State Sync)
        setTimeout(() => {
            // Reset submission control parameters
            submitCodeBtn.disabled = false;
            submitCodeBtn.innerHTML = `<i data-lucide="play" class="w-3.5 h-3.5 fill-current"></i> Submit to Sandbox`;
            lucide.createIcons();

            // Evaluate payload conditions for tailored response tracking
            if (activeScript.includes("pass") || activeScript.length < 120) {
                runtimeBadge.innerText = "Failed Structural Standards";
                runtimeBadge.className = "text-[10px] uppercase font-bold tracking-wider text-rose-500";

                consoleLogs.innerHTML += `
                    <div class="text-rose-400 font-semibold">&gt; TestSuite Status: FAILED</div>
                    <div class="text-rose-500/80">AssertionError: The verification modules returned empty structures. Stub structures require implementation features.</div>
                `;

                appendAgentMessage(AGENTS.THEORY, `Compilation diagnostics failure flagged inside internal memory loops. cross-referencing Textbook Chapter 4 (Tree Configurations):\n\nEnsure that you trace node boundaries explicitly down the stack utilizing infinity indicators as dynamic parameter caps. Code structures currently resolve to constant computational patterns.`);
                        } else {
                runtimeBadge.innerText = "Pass (Success)";
                runtimeBadge.className = "text-[10px] uppercase font-bold tracking-wider text-emerald-500";
                consoleLogs.innerHTML += `
                <div class="text-emerald-400 font-semibold">&gt; TestSuite Status: SUCCESS</div>
                <div class="text-slate-300">All test metrics passed inside sandboxed matrix successfully.</div>
                `; 
                appendAgentMessage(AGENTS.EVALUATOR, `Verification sequence finished cleanly. Code structural parameters match required O(N) evaluation bounds.`);
                updateCheckpoint();
            }
        }, 3500);
    });
});
