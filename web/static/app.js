// My Desktop Agent Web Interface Logic
document.addEventListener("DOMContentLoaded", () => {
    // --- DOM Element References ---
    const sidebar = document.getElementById("sidebar");
    const btnToggleSidebar = document.getElementById("btnToggleSidebar");
    const sidebarAgentName = document.getElementById("sidebarAgentName");
    const statusDot = document.getElementById("statusDot");
    const statusText = document.getElementById("statusText");
    const topBarModelName = document.getElementById("topBarModelName");
    const topBarTelegramStatus = document.getElementById("topBarTelegramStatus");

    // Top Action Buttons
    const btnQuickStart = document.getElementById("btnQuickStart");
    const btnQuickStop = document.getElementById("btnQuickStop");
    
    // Bento Metrics
    const agentStateLabel = document.getElementById("agentStateLabel");
    const agentStateSub = document.getElementById("agentStateSub");
    const selectMonitor = document.getElementById("selectMonitor");
    const visionIntervalDisplay = document.getElementById("visionIntervalDisplay");
    const activeSkillsCount = document.getElementById("activeSkillsCount");
    const skillsMiniList = document.getElementById("skillsMiniList");
    const skillsFullList = document.getElementById("skillsFullList");

    // Task & Chat Elements
    const taskHeaderTitle = document.getElementById("taskHeaderTitle");
    const taskStatusBadge = document.getElementById("taskStatusBadge");
    const btnPauseTask = document.getElementById("btnPauseTask");
    const btnStopTask = document.getElementById("btnStopTask");
    const planChecklistContainer = document.getElementById("planChecklistContainer");
    const planStepsList = document.getElementById("planStepsList");
    const stepCounter = document.getElementById("stepCounter");
    const dynamicChatMessages = document.getElementById("dynamicChatMessages");
    const taskChatFeed = document.getElementById("taskChatFeed");
    const taskGoalInput = document.getElementById("taskGoalInput");
    const btnExecuteTask = document.getElementById("btnExecuteTask");
    const btnVoiceInput = document.getElementById("btnVoiceInput");

    // Config Elements
    const cfgStreamerName = document.getElementById("cfgStreamerName");
    const cfgPersonaPrompt = document.getElementById("cfgPersonaPrompt");
    const btnEnhancePrompt = document.getElementById("btnEnhancePrompt");
    const enhanceStatusHint = document.getElementById("enhanceStatusHint");
    const cfgTextModel = document.getElementById("cfgTextModel");
    const cfgVisionModel = document.getElementById("cfgVisionModel");
    const cfgTTSEngine = document.getElementById("cfgTTSEngine");
    const cfgVisionInterval = document.getElementById("cfgVisionInterval");
    const cfgEnableInputs = document.getElementById("cfgEnableInputs");
    const cfgEnableTools = document.getElementById("cfgEnableTools");
    const btnSaveConfig = document.getElementById("btnSaveConfig");

    // Knowledge Search & MCP
    const knowledgeSearchInput = document.getElementById("knowledgeSearchInput");
    const btnSearchKnowledge = document.getElementById("btnSearchKnowledge");
    const knowledgeSearchResults = document.getElementById("knowledgeSearchResults");
    const mcpServerCountBadge = document.getElementById("mcpServerCountBadge");
    const mcpServersList = document.getElementById("mcpServersList");
    const fullLogViewer = document.getElementById("fullLogViewer");
    const btnClearLogs = document.getElementById("btnClearLogs");

    let activeConfig = {};
    let installedModels = [];
    let isTaskRunning = false;
    let isConfigFormInitialized = false;
    let lastRenderedStep = -1;

    // --- 1. Tab Switching Navigation ---
    const navTabBtns = document.querySelectorAll(".nav-tab-btn");
    const tabPanes = document.querySelectorAll(".tab-pane");

    navTabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetId = btn.getAttribute("data-tab");
            
            navTabBtns.forEach(b => {
                b.classList.remove("active", "bg-secondary-container", "text-on-secondary-container", "font-bold");
                b.classList.add("text-on-surface-variant");
            });
            btn.classList.add("active", "bg-secondary-container", "text-on-secondary-container", "font-bold");
            btn.classList.remove("text-on-surface-variant");

            tabPanes.forEach(pane => {
                if (pane.id === targetId) {
                    pane.classList.remove("hidden");
                    pane.classList.add("flex");
                } else {
                    pane.classList.add("hidden");
                    pane.classList.remove("flex");
                }
            });
        });
    });

    if (btnToggleSidebar) {
        btnToggleSidebar.addEventListener("click", () => {
            sidebar.classList.toggle("-translate-x-full");
        });
    }

    // --- 2. Initial Status & Configuration Load ---
    async function loadStatus() {
        try {
            const statusRes = await fetch("/api/status");
            const statusData = await statusRes.json();
            
            if (statusData.config) {
                activeConfig = statusData.config;
            }

            try {
                const modelsRes = await fetch("/api/models");
                const modelsData = await modelsRes.json();
                installedModels = modelsData.models || [];
            } catch (mErr) {
                console.warn("Could not fetch models:", mErr);
            }

            const currentText = activeConfig.ollama?.text_model || statusData.text_model || "gemma4:31b-cloud";
            const currentVision = activeConfig.ollama?.vision_model || statusData.vision_model || "gemma4:31b-cloud";

            if (!isConfigFormInitialized) {
                populateModelDropdowns(installedModels, currentText, currentVision);
                populateConfigForm(activeConfig, true);
                isConfigFormInitialized = true;
            }

            updateUIState(statusData);
            loadMonitors();
            loadSkills();
            loadMCPServers();
        } catch (err) {
            console.error("Failed to load status:", err);
        }
    }

    function updateUIState(status) {
        const isRunning = status.is_running;
        if (sidebarAgentName) sidebarAgentName.textContent = activeConfig.agent?.name || "My Desktop Agent";
        if (topBarModelName) topBarModelName.textContent = activeConfig.ollama?.text_model || status.text_model || "gemma4:31b-cloud";

        if (statusText) statusText.textContent = isRunning ? "Active & Running" : "Standby (OFF)";
        if (statusDot) {
            if (isRunning) {
                statusDot.className = "w-2 h-2 rounded-full bg-emerald-400 agent-active-glow";
            } else {
                statusDot.className = "w-2 h-2 rounded-full bg-slate-500";
            }
        }

        if (btnQuickStart) btnQuickStart.disabled = isRunning;
        if (btnQuickStop) btnQuickStop.disabled = !isRunning;

        if (agentStateLabel) agentStateLabel.textContent = isRunning ? "Active" : "Optimal";
        if (agentStateSub) agentStateSub.textContent = isRunning ? "Observing Screen" : "Standby Mode";

        // Task State
        const taskState = status.task_state || {};
        const isTaskActive = taskState.state === "IN_PROGRESS";
        isTaskRunning = isTaskActive;

        if (taskStatusBadge) {
            taskStatusBadge.textContent = taskState.state || "STANDBY";
            if (taskState.state === "IN_PROGRESS") {
                taskStatusBadge.className = "px-2.5 py-0.5 rounded-full bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 text-xs font-bold uppercase tracking-wider";
            } else if (taskState.state === "PAUSED") {
                taskStatusBadge.className = "px-2.5 py-0.5 rounded-full bg-amber-500/20 border border-amber-500/30 text-amber-400 text-xs font-bold uppercase tracking-wider";
            } else {
                taskStatusBadge.className = "px-2.5 py-0.5 rounded-full bg-primary-container/20 border border-primary-container/30 text-primary text-xs font-bold uppercase tracking-wider";
            }
        }

        if (btnPauseTask) btnPauseTask.disabled = !isTaskActive;
        if (btnStopTask) btnStopTask.disabled = !isTaskActive;

        if (taskState.goal && taskHeaderTitle) {
            taskHeaderTitle.textContent = `Task: "${taskState.goal}"`;
        }

        // Render plan checklist if task is active
        if (taskState.plan_steps && taskState.plan_steps.length > 0) {
            renderPlanChecklist(taskState.plan_steps, taskState.current_step_idx);
        }
    }

    function renderPlanChecklist(steps, currentIdx) {
        if (!planChecklistContainer || !planStepsList) return;
        planChecklistContainer.style.display = "block";
        if (stepCounter) stepCounter.textContent = `Step ${Math.min(currentIdx + 1, steps.length)} of ${steps.length}`;

        planStepsList.innerHTML = "";
        steps.forEach((step, idx) => {
            const isCompleted = idx < currentIdx;
            const isCurrent = idx === currentIdx;

            const item = document.createElement("div");
            item.className = `flex items-start gap-2.5 p-2 rounded-lg text-xs transition-all ${
                isCurrent 
                    ? "bg-primary-container/10 border border-primary/30 text-primary font-semibold shadow-sm" 
                    : (isCompleted ? "text-on-surface-variant line-through opacity-70" : "text-on-surface")
            }`;

            const icon = document.createElement("span");
            icon.className = "material-symbols-outlined text-sm shrink-0 mt-0.5";
            icon.textContent = isCompleted ? "check_circle" : (isCurrent ? "radio_button_checked" : "radio_button_unchecked");
            if (isCompleted) icon.classList.add("text-emerald-400");
            else if (isCurrent) icon.classList.add("text-primary");

            const label = document.createElement("span");
            label.className = "flex-1";
            label.textContent = `${idx + 1}. ${step}`;

            item.appendChild(icon);
            item.appendChild(label);
            planStepsList.appendChild(item);
        });
    }

    function populateModelDropdowns(models, selectedText, selectedVision) {
        if (!cfgTextModel || !cfgVisionModel) return;
        cfgTextModel.innerHTML = "";
        cfgVisionModel.innerHTML = "";

        const allModels = Array.from(new Set([...models, selectedText, selectedVision, "gemma4:31b-cloud", "gemma4:latest", "llama3.2-vision:latest", "qwen2.5:3b", "gpt-4o-mini"]));
        
        allModels.forEach(m => {
            if (!m) return;
            const opt1 = document.createElement("option");
            opt1.value = m;
            opt1.textContent = m;
            if (m === selectedText) opt1.selected = true;
            cfgTextModel.appendChild(opt1);

            const opt2 = document.createElement("option");
            opt2.value = m;
            opt2.textContent = m;
            if (m === selectedVision) opt2.selected = true;
            cfgVisionModel.appendChild(opt2);
        });
    }

    function populateConfigForm(cfg, force = false) {
        if (!cfg) return;
        if (!force && isConfigFormInitialized) {
            return;
        }
        const agent = cfg.agent || {};
        const desktop = cfg.desktop_agent || {};

        if (cfgStreamerName) cfgStreamerName.value = agent.name || "My Desktop Agent";
        if (cfgPersonaPrompt) cfgPersonaPrompt.value = agent.persona_prompt || "";
        if (cfgVisionInterval) {
            cfgVisionInterval.value = desktop.vision_interval_sec || 2.0;
            if (visionIntervalDisplay) visionIntervalDisplay.textContent = `${desktop.vision_interval_sec || 2.0}s`;
        }
        if (cfgEnableInputs) cfgEnableInputs.checked = desktop.enable_desktop_inputs ?? true;
        if (cfgEnableTools) cfgEnableTools.checked = cfg.tools?.enable_terminal_commands ?? true;

        if (cfgTTSEngine && cfg.tts?.engine) cfgTTSEngine.value = cfg.tts.engine;
    }

    // --- 3. Monitors Selector ---
    async function loadMonitors() {
        try {
            const res = await fetch("/api/monitors");
            const data = await res.json();
            if (selectMonitor && data.monitors && data.monitors.length > 0) {
                selectMonitor.innerHTML = "";
                data.monitors.forEach(m => {
                    const opt = document.createElement("option");
                    opt.value = m.index;
                    opt.textContent = m.name;
                    if (m.index === data.active_monitor) opt.selected = true;
                    selectMonitor.appendChild(opt);
                });
                selectMonitor.onchange = async () => {
                    await fetch("/api/monitors/switch", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ index: parseInt(selectMonitor.value) })
                    });
                };
            }
        } catch (e) {
            console.warn("Could not load monitors:", e);
        }
    }

    // --- 4. Markdown Skills Loader ---
    async function loadSkills() {
        try {
            const res = await fetch("/api/skills");
            const data = await res.json();
            const skills = data.skills || [];
            
            if (activeSkillsCount) activeSkillsCount.textContent = `${skills.length} Skills`;

            if (skillsMiniList) {
                skillsMiniList.innerHTML = "";
                skills.forEach(s => {
                    const btn = document.createElement("div");
                    btn.className = "flex items-center gap-2 p-1.5 rounded-lg text-xs text-on-surface hover:bg-surface-container transition-colors";
                    btn.innerHTML = `<span class="material-symbols-outlined text-primary text-sm">description</span><span class="truncate font-serif">${s.name}</span>`;
                    skillsMiniList.appendChild(btn);
                });
            }

            if (skillsFullList) {
                skillsFullList.innerHTML = "";
                skills.forEach(s => {
                    const card = document.createElement("div");
                    card.className = "p-4 rounded-xl bg-surface-container border border-outline-variant flex flex-col gap-2";
                    card.innerHTML = `
                        <div class="flex justify-between items-start">
                            <h4 class="font-bold text-sm text-primary font-serif">${s.name}</h4>
                            <span class="text-[10px] px-2 py-0.5 rounded bg-surface-container-high text-on-surface-variant font-mono">${s.filename}</span>
                        </div>
                        <p class="text-xs text-on-surface-variant">${s.description || "Autonomous workflow guidelines"}</p>
                    `;
                    skillsFullList.appendChild(card);
                });
            }
        } catch (e) {
            console.warn("Could not load skills:", e);
        }
    }

    // --- 4b. MCP Servers & Tools ---
    async function loadMCPServers() {
        if (!mcpServersList) return;
        try {
            const res = await fetch("/api/mcp/servers");
            const data = await res.json();
            const servers = data.servers || [];
            const tools = data.tools || [];
            
            if (mcpServerCountBadge) {
                mcpServerCountBadge.textContent = `${servers.length} Servers (${tools.length} Tools)`;
            }

            mcpServersList.innerHTML = "";
            if (servers.length === 0) {
                mcpServersList.innerHTML = `
                    <div class="p-4 rounded-xl bg-surface-container border border-outline-variant/60 text-xs text-on-surface-variant">
                        <p class="font-bold text-on-surface mb-1">No MCP Servers Configured</p>
                        <p>To connect external MCP tools (like GitHub, Filesystem, Postgres, etc.), configure them under <code class="text-primary font-mono">mcp_servers</code> in your <code class="text-primary font-mono">config.yaml</code>.</p>
                    </div>
                `;
                return;
            }

            servers.forEach(s => {
                const card = document.createElement("div");
                card.className = "p-4 rounded-xl bg-surface-container border border-outline-variant flex flex-col gap-2";
                const statusBadge = s.connected 
                    ? `<span class="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 text-[10px] font-bold">🟢 Connected</span>`
                    : `<span class="px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-400 text-[10px] font-bold">🔴 Connecting / Disconnected</span>`;
                
                const toolsList = s.tools && s.tools.length > 0
                    ? s.tools.map(t => `<span class="px-2 py-0.5 rounded bg-surface-container-high text-[11px] font-mono text-primary">${t}</span>`).join(" ")
                    : `<span class="text-xs text-on-surface-variant italic">No tools discovered</span>`;

                card.innerHTML = `
                    <div class="flex justify-between items-center">
                        <div class="flex items-center gap-2">
                            <span class="material-symbols-outlined text-primary text-sm">extension</span>
                            <h4 class="font-bold text-sm text-on-surface font-serif">${s.name}</h4>
                            <span class="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-surface text-on-surface-variant">${s.transport}</span>
                        </div>
                        ${statusBadge}
                    </div>
                    <div class="pt-1 flex flex-wrap gap-1 items-center">
                        <span class="text-xs text-on-surface-variant mr-1 font-bold">Tools:</span>
                        ${toolsList}
                    </div>
                `;
                mcpServersList.appendChild(card);
            });
        } catch (e) {
            console.warn("Could not load MCP servers:", e);
        }
    }

    // --- 5. Task Execution & Chat Timeline ---
    function appendChatMessage(sender, text, isUser = false, toolDetails = null) {
        if (!dynamicChatMessages) return;

        const msgDiv = document.createElement("div");
        msgDiv.className = isUser 
            ? "flex flex-col items-end gap-1 max-w-[85%] self-end"
            : "flex flex-col items-start gap-1 max-w-[85%] self-start";

        if (!isUser) {
            const header = document.createElement("div");
            header.className = "flex items-center gap-2 mb-0.5";
            header.innerHTML = `
                <div class="w-6 h-6 rounded-full bg-primary-container flex items-center justify-center shrink-0 shadow-sm border border-primary/20">
                    <span class="material-symbols-outlined text-on-primary-container text-xs">smart_toy</span>
                </div>
                <span class="text-xs font-bold text-primary">${sender}</span>
            `;
            msgDiv.appendChild(header);
        }

        const bubble = document.createElement("div");
        bubble.className = isUser
            ? "bg-surface-container-highest text-on-surface px-4 py-2.5 rounded-xl rounded-tr-none border border-outline-variant/60 text-sm shadow-sm font-serif"
            : "bg-surface-container-low text-on-surface px-4 py-2.5 rounded-xl rounded-tl-none border border-outline-variant text-sm shadow-sm font-serif w-full";

        bubble.innerHTML = `<p class="leading-relaxed">${text}</p>`;

        if (toolDetails) {
            const toolBox = document.createElement("div");
            toolBox.className = "mt-2 p-2 rounded-lg bg-surface border border-outline-variant font-mono text-[11px] text-on-surface-variant overflow-x-auto";
            toolBox.innerHTML = `<strong>⚡ Tool Execution:</strong> <pre class="mt-1">${JSON.stringify(toolDetails, null, 2)}</pre>`;
            bubble.appendChild(toolBox);
        }

        msgDiv.appendChild(bubble);
        dynamicChatMessages.appendChild(msgDiv);

        if (taskChatFeed) {
            taskChatFeed.scrollTop = taskChatFeed.scrollHeight;
        }
    }

    async function startTaskWithGoal(goal) {
        const g = goal.trim();
        if (!g) return;

        appendChatMessage("You", g, true);
        taskGoalInput.value = "";

        try {
            const res = await fetch("/api/task/start", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ goal: g })
            });
            const data = await res.json();
            if (data.status === "started") {
                const name = activeConfig.agent?.name || "My Desktop Agent";
                appendChatMessage(name, `Task accepted: "${g}". Initializing execution plan...`);
                loadStatus();
            }
        } catch (e) {
            appendChatMessage("System", `Error starting task: ${e}`);
        }
    }

    if (btnExecuteTask) {
        btnExecuteTask.addEventListener("click", () => startTaskWithGoal(taskGoalInput.value));
    }

    if (taskGoalInput) {
        taskGoalInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                startTaskWithGoal(taskGoalInput.value);
            }
        });
    }

    // Quick Task Chips
    document.querySelectorAll(".task-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            const goal = chip.getAttribute("data-goal");
            if (goal) startTaskWithGoal(goal);
        });
    });

    if (btnPauseTask) {
        btnPauseTask.addEventListener("click", async () => {
            await fetch("/api/task/pause", { method: "POST" });
            loadStatus();
        });
    }

    if (btnStopTask) {
        btnStopTask.addEventListener("click", async () => {
            await fetch("/api/task/stop", { method: "POST" });
            loadStatus();
        });
    }

    if (btnQuickStart) {
        btnQuickStart.addEventListener("click", async () => {
            await fetch("/api/start", { method: "POST" });
            loadStatus();
        });
    }

    if (btnQuickStop) {
        btnQuickStop.addEventListener("click", async () => {
            await fetch("/api/stop", { method: "POST" });
            loadStatus();
        });
    }

    // --- 6. AI Prompt Enhancer ---
    if (btnEnhancePrompt) {
        btnEnhancePrompt.addEventListener("click", async () => {
            const currentPrompt = cfgPersonaPrompt.value.trim();
            const agentName = cfgStreamerName.value.trim() || "My Desktop Agent";

            btnEnhancePrompt.disabled = true;
            btnEnhancePrompt.innerHTML = `<span>⏳ Expanding System Prompt...</span>`;
            if (enhanceStatusHint) enhanceStatusHint.textContent = "AI Prompt Architect is structuring and enriching your persona...";

            try {
                const res = await fetch("/api/enhance_prompt", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ prompt: currentPrompt, agent_name: agentName })
                });
                const data = await res.json();
                if (data.status === "success" && data.enhanced_prompt) {
                    cfgPersonaPrompt.value = data.enhanced_prompt;
                    if (activeConfig && activeConfig.agent) {
                        activeConfig.agent.persona_prompt = data.enhanced_prompt;
                    }
                    if (enhanceStatusHint) enhanceStatusHint.textContent = "✨ Enhanced prompt loaded! Click 'Save Changes' to permanently save.";
                } else {
                    alert("Could not enhance prompt: " + (data.detail || "Unknown error"));
                }
            } catch (err) {
                alert("Error enhancing prompt: " + err);
            } finally {
                btnEnhancePrompt.disabled = false;
                btnEnhancePrompt.innerHTML = `<span>✨ Make My System Prompt Better</span>`;
            }
        });
    }

    // --- 7. Save Config ---
    if (btnSaveConfig) {
        btnSaveConfig.addEventListener("click", async () => {
            const newCfg = { ...activeConfig };
            newCfg.agent = newCfg.agent || {};
            newCfg.desktop_agent = newCfg.desktop_agent || {};
            newCfg.ollama = newCfg.ollama || {};
            newCfg.tts = newCfg.tts || {};
            newCfg.tools = newCfg.tools || {};

            newCfg.agent.name = cfgStreamerName.value.trim();
            newCfg.agent.persona_prompt = cfgPersonaPrompt.value.trim();
            newCfg.ollama.text_model = cfgTextModel.value;
            newCfg.ollama.vision_model = cfgVisionModel.value;
            newCfg.desktop_agent.vision_interval_sec = parseFloat(cfgVisionInterval.value);
            newCfg.desktop_agent.enable_desktop_inputs = cfgEnableInputs.checked;
            newCfg.tools.enable_terminal_commands = cfgEnableTools.checked;
            newCfg.tts.engine = cfgTTSEngine.value;

            try {
                const res = await fetch("/api/update_config", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ config: newCfg })
                });
                const result = await res.json();
                alert(result.message || "Configurations saved successfully!");
                activeConfig = newCfg;
                populateConfigForm(newCfg, true);
                loadStatus();
            } catch (err) {
                alert("Error saving config: " + err);
            }
        });
    }

    // --- 8. Knowledge Base Search ---
    if (btnSearchKnowledge && knowledgeSearchInput) {
        btnSearchKnowledge.addEventListener("click", async () => {
            const q = knowledgeSearchInput.value.trim();
            if (!q) return;
            try {
                const res = await fetch("/api/knowledge/search", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ query: q })
                });
                const data = await res.json();
                const results = data.results || [];
                
                knowledgeSearchResults.innerHTML = "";
                if (results.length === 0) {
                    knowledgeSearchResults.innerHTML = `<p class="text-xs text-on-surface-variant">No matching excerpts found in local documents.</p>`;
                    return;
                }
                results.forEach(r => {
                    const item = document.createElement("div");
                    item.className = "p-3 rounded-lg bg-surface border border-outline-variant text-xs space-y-1";
                    item.innerHTML = `
                        <div class="flex justify-between items-center text-primary font-bold">
                            <span>📄 ${r.document}</span>
                            <span class="text-[10px] text-on-surface-variant font-mono">Score: ${r.score}</span>
                        </div>
                        <p class="text-on-surface font-serif">${r.text}</p>
                    `;
                    knowledgeSearchResults.appendChild(item);
                });
            } catch (e) {
                console.error("Knowledge search error:", e);
            }
        });
    }

    // --- 9. WebSocket Activity & Terminal Logs ---
    function connectWebSocket() {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${protocol}//${window.location.host}/ws/logs`;
        const ws = new WebSocket(wsUrl);

        ws.onmessage = (event) => {
            const raw = event.data;
            if (fullLogViewer) {
                const logLine = document.createElement("div");
                logLine.textContent = raw;
                if (raw.includes("[ERROR]")) logLine.className = "text-rose-400";
                else if (raw.includes("[WARN]")) logLine.className = "text-amber-400";
                else if (raw.includes("⚡ Tool") || raw.includes("💻 Running")) logLine.className = "text-cyan-400 font-semibold";
                else if (raw.includes("🎉 Task")) logLine.className = "text-emerald-400 font-bold";
                else logLine.className = "text-on-surface-variant";
                fullLogViewer.appendChild(logLine);
                fullLogViewer.scrollTop = fullLogViewer.scrollHeight;
            }

            // If action narration received in log, render in chat
            if (raw.includes("Analyzing desktop to advance task") || raw.includes("Task completed")) {
                loadStatus();
            }
        };

        ws.onclose = () => setTimeout(connectWebSocket, 3000);
    }

    if (btnClearLogs) {
        btnClearLogs.addEventListener("click", () => {
            if (fullLogViewer) fullLogViewer.innerHTML = "";
        });
    }

    // Periodic status poll
    setInterval(loadStatus, 2500);

    // Initial Start
    loadStatus();
    connectWebSocket();
});
