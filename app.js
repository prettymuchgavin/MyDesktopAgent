/**
 * My Desktop Agent - Interactive Website Scripts
 * Provides interactive simulations, skills explorer, Telegram bot simulator, and utilities.
 */

document.addEventListener('DOMContentLoaded', () => {
  initMobileMenu();
  initHeroSimulation();
  initTelegramSimulator();
});

/* ==========================================================================
   Mobile Menu Toggle
   ========================================================================== */
function initMobileMenu() {
  const menuBtn = document.getElementById('mobileMenuBtn');
  const drawer = document.getElementById('mobileDrawer');

  if (!menuBtn || !drawer) return;

  menuBtn.addEventListener('click', () => {
    drawer.classList.toggle('open');
    const icon = menuBtn.querySelector('i');
    if (drawer.classList.contains('open')) {
      icon.classList.remove('fa-bars');
      icon.classList.add('fa-xmark');
    } else {
      icon.classList.remove('fa-xmark');
      icon.classList.add('fa-bars');
    }
  });

  // Close drawer when clicking any nav link
  drawer.querySelectorAll('.mobile-nav-link, a').forEach(link => {
    link.addEventListener('click', () => {
      drawer.classList.remove('open');
      const icon = menuBtn.querySelector('i');
      icon.classList.remove('fa-xmark');
      icon.classList.add('fa-bars');
    });
  });
}

/* ==========================================================================
   Hero Desktop Agent Simulator
   ========================================================================== */
const simScenarios = [
  {
    goal: '"Research top 5 AI agent papers from arXiv, summarize key findings, and draft into LibreOffice report."',
    windowTitle: 'Q3_AI_Research_Report.docx - LibreOffice Writer',
    typing: 'Key Finding: Multimodal agents with machine-speed terminal tooling achieve 4.2x faster task completion than pure visual clicking.',
    steps: [
      { text: 'Execute DuckDuckGo fast search for arXiv multimodal agents', sub: 'Tool: terminal.web_search("site:arxiv.org AI desktop agent") • 0.32s', status: 'done' },
      { text: 'Extract text & synthesize 5 key architectural findings', sub: 'Model: Gemma-4 Local Vision / Groq Cloud • 420 tokens', status: 'done' },
      { text: 'Focus LibreOffice Writer and paste formatted summary', sub: 'GUI: focus_window("LibreOffice") & clipboard_paste()', status: 'active' },
      { text: 'Capture completion screenshot and send Telegram confirmation', sub: 'Bot: telegram.send_photo(user_id=7482910, caption="Task complete")', status: 'pending' }
    ],
    logs: [
      { ts: '14:43:50', tag: 'INFO', color: 'text-blue-400', msg: 'Initialized Ollama vision pipeline.' },
      { ts: '14:43:52', tag: 'TOOL', color: 'text-emerald', msg: 'web_search() returned 8 abstracts in 318ms.' },
      { ts: '14:43:54', tag: 'ACTION', color: 'text-purple-400', msg: 'Generated Bézier curve: (820, 410) → (1420, 680)' },
      { ts: '14:43:56', tag: 'VOICE', color: 'text-amber-400', msg: 'Kokoro TTS: "Pasting summarized research into document..."' }
    ],
    cursorPositions: [
      { top: '35%', left: '45%' },
      { top: '55%', left: '60%' },
      { top: '65%', left: '30%' }
    ]
  },
  {
    goal: '"Organize messy Downloads folder: group PDFs, images, and archives into categorized project directories."',
    windowTitle: 'Downloads - File Explorer',
    typing: 'Organized 38 items: 14 PDFs → /Documents/Invoices, 18 PNGs → /Pictures/Screenshots, 6 ZIPs → /Archives.',
    steps: [
      { text: 'Scan C:\\Users\\gavin\\Downloads for unorganized files', sub: 'Tool: terminal.pwsh("Get-ChildItem -Path Downloads") • 0.08s', status: 'done' },
      { text: 'Classify files by mime-type & creation metadata', sub: 'Local RAG Classifier: 38 files analyzed • 0.12s', status: 'done' },
      { text: 'Move files to target directories atomically', sub: 'Tool: Move-Item with collision safety checks', status: 'active' },
      { text: 'Notify user via Push-to-Talk audio completion chime', sub: 'Audio: Kokoro TTS playback finished', status: 'pending' }
    ],
    logs: [
      { ts: '15:10:02', tag: 'INFO', color: 'text-blue-400', msg: 'Reading file system metadata...' },
      { ts: '15:10:03', tag: 'SAFETY', color: 'text-emerald', msg: 'Safety gate verified: No system files targeted.' },
      { ts: '15:10:04', tag: 'TOOL', color: 'text-emerald', msg: 'Created folder: C:\\Users\\gavin\\Documents\\Invoices' },
      { ts: '15:10:05', tag: 'VOICE', color: 'text-amber-400', msg: 'Kokoro TTS: "38 files successfully categorized."' }
    ],
    cursorPositions: [
      { top: '25%', left: '20%' },
      { top: '40%', left: '70%' },
      { top: '75%', left: '50%' }
    ]
  }
];

let currentScenarioIndex = 0;
let isSimPaused = false;
let simInterval = null;

function initHeroSimulation() {
  renderSimScenario(0);
  startCursorAnimation();
}

function renderSimScenario(index) {
  const sc = simScenarios[index];
  const goalEl = document.getElementById('activeGoalTitle');
  const typingEl = document.getElementById('simTypingText');
  const checklistEl = document.getElementById('checklistItems');
  const logLinesEl = document.getElementById('logLines');
  const stepCounterEl = document.getElementById('stepCounter');

  if (goalEl) goalEl.textContent = sc.goal;
  if (typingEl) typingEl.textContent = sc.typing;

  if (checklistEl) {
    checklistEl.innerHTML = sc.steps.map(step => {
      let icon = '<i class="fa-regular fa-circle"></i>';
      if (step.status === 'done') icon = '<i class="fa-solid fa-check"></i>';
      if (step.status === 'active') icon = '<i class="fa-solid fa-spinner fa-spin"></i>';

      return `
        <div class="checklist-item ${step.status} flex items-start gap-3">
          <div class="check-icon">${icon}</div>
          <div class="check-body">
            <div class="check-task">${step.text}</div>
            <div class="check-sub font-mono">${step.sub}</div>
          </div>
        </div>
      `;
    }).join('');
  }

  if (stepCounterEl) {
    stepCounterEl.textContent = `Step 3 of ${sc.steps.length}`;
  }

  if (logLinesEl) {
    logLinesEl.innerHTML = sc.logs.map(log => `
      <div class="log-line text-slate-400">
        <span class="log-ts">[${log.ts}]</span> 
        <span class="${log.color}">${log.tag}</span> ${log.msg}
      </div>
    `).join('');
  }
}

function startCursorAnimation() {
  const cursor = document.getElementById('aiCursor');
  const ripple = document.getElementById('clickRipple');
  if (!cursor) return;

  let posIdx = 0;
  clearInterval(simInterval);

  simInterval = setInterval(() => {
    if (isSimPaused) return;

    const sc = simScenarios[currentScenarioIndex];
    posIdx = (posIdx + 1) % sc.cursorPositions.length;
    const target = sc.cursorPositions[posIdx];

    cursor.style.top = target.top;
    cursor.style.left = target.left;

    // Trigger click ripple
    setTimeout(() => {
      if (ripple) {
        ripple.classList.remove('clicked');
        void ripple.offsetWidth; // trigger reflow
        ripple.classList.add('clicked');
      }
    }, 600);

  }, 3000);
}

function toggleSimPause() {
  isSimPaused = !isSimPaused;
  const pauseBtn = document.getElementById('simPauseBtn');
  if (!pauseBtn) return;

  if (isSimPaused) {
    pauseBtn.innerHTML = '<i class="fa-solid fa-play"></i> Resume';
    pauseBtn.style.color = 'var(--accent-emerald)';
  } else {
    pauseBtn.innerHTML = '<i class="fa-solid fa-pause"></i> Pause';
    pauseBtn.style.color = '';
  }
}

function cycleSimTask() {
  currentScenarioIndex = (currentScenarioIndex + 1) % simScenarios.length;
  renderSimScenario(currentScenarioIndex);
}

/* ==========================================================================
   Interactive 3-Step Workflow Switcher
   ========================================================================== */
function switchWorkflowStep(stepNumber) {
  // Update tabs
  const tabs = document.querySelectorAll('.workflow-tab');
  tabs.forEach((tab, index) => {
    if (index === stepNumber - 1) {
      tab.classList.add('active');
    } else {
      tab.classList.remove('active');
    }
  });

  // Update panes
  const panes = document.querySelectorAll('.step-pane');
  panes.forEach((pane, index) => {
    if (index === stepNumber - 1) {
      pane.classList.add('active');
    } else {
      pane.classList.remove('active');
    }
  });
}

/* ==========================================================================
   Skills Ecosystem Explorer
   ========================================================================== */
const skillsData = {
  reddit: {
    filename: 'skills/reddit_deep_research.md',
    content: `# 🧠 Skill: Reddit Deep Research & Sentiment Synthesizer

## Description
Search Reddit discussions for a target topic, scrape community sentiment, extract consensus recommendations, and output a concise executive report.

## Required Tools
- \`terminal.web_search(query)\`
- \`terminal.extract_url_text(url)\`
- \`knowledge.save_report(filename, content)\`

## Execution Rules:
1. Search via DuckDuckGo: \`site:reddit.com <topic> "recommendations"\`
2. Read the top 3 discussion threads.
3. Ignore promotional spam and bot comments.
4. Synthesize a 3-bullet summary:
   - Consensus Recommendation
   - Known Drawbacks / Caveats
   - Best Alternative Mentioned
5. Output results to \`data/reports/reddit_<topic>.md\`
6. Speak completion summary via Kokoro TTS.`
  },
  pdf: {
    filename: 'skills/invoice_organizer.md',
    content: `# 📄 Skill: Invoice PDF Extractor & Financial Organizer

## Description
Scans new PDF documents in Downloads, extracts invoice metadata (vendor, date, total amount), standardizes filename, and moves to accounting directory.

## Required Tools
- \`filesystem.scan_directory("Downloads", "*.pdf")\`
- \`vision.ocr_document(filepath)\`
- \`filesystem.move_and_rename(src, dest)\`

## Execution Rules:
1. Scan for PDFs containing keywords "Invoice", "Receipt", or "Total:".
2. Parse Vendor Name, Date (YYYY-MM-DD), and Amount ($XX.XX).
3. Generate new canonical filename:
   \`Invoice_{YYYY-MM-DD}_{Vendor}_{Amount}.pdf\`
4. Move sanitized file to \`C:\\Users\\gavin\\Documents\\Accounting\\Invoices\\2026\`.
5. Append metadata row to \`invoices_ledger.csv\`.`
  },
  morning: {
    filename: 'skills/morning_briefing_cron.md',
    content: `# ☀️ Skill: Daily 08:30 AM Morning Briefing

## Description
Automated background schedule that gathers local weather, top 3 tech headlines, and your calendar agenda, delivering a 1-page digest to Telegram.

## Trigger Schedule
- Cron: \`30 8 * * 1-5\` (Monday through Friday at 08:30 AM)

## Required Tools
- \`terminal.fetch_weather("CurrentLocation")\`
- \`terminal.web_search("top AI & technology news today")\`
- \`telegram.send_message(user_id=7482910, text=briefing)\`

## Execution Rules:
1. Fetch weather forecast & high/low temperatures.
2. Query DuckDuckGo for top tech breakthroughs in last 24h.
3. Compile a crisp 4-bullet morning brief.
4. Push directly to authenticated Telegram chat with interactive [📸 Screenshot] button.`
  }
};

let currentActiveSkillKey = 'reddit';

function loadSkillContent(skillKey) {
  currentActiveSkillKey = skillKey;
  const data = skillsData[skillKey];
  if (!data) return;

  const fnameEl = document.getElementById('currentSkillFilename');
  const codeEl = document.getElementById('skillCodeDisplay');

  if (fnameEl) {
    fnameEl.innerHTML = `<i class="fa-brands fa-markdown text-blue-400"></i> <span>${data.filename}</span>`;
  }
  if (codeEl) {
    codeEl.innerHTML = `<code>${escapeHtml(data.content)}</code>`;
  }

  // Update button active state
  document.querySelectorAll('.skill-file-item').forEach(btn => btn.classList.remove('active'));
  event.currentTarget.classList.add('active');
}

function copyActiveSkill(btn) {
  const data = skillsData[currentActiveSkillKey];
  if (!data) return;

  navigator.clipboard.writeText(data.content).then(() => {
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-check text-emerald"></i> Copied!';
    setTimeout(() => {
      btn.innerHTML = originalText;
    }, 2000);
  });
}

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

/* ==========================================================================
   Telegram Mobile Simulator
   ========================================================================== */
function initTelegramSimulator() {
  // Simulator ready
}

function handleTgSimClick(action) {
  const chatBody = document.getElementById('tgChatBody');
  if (!chatBody) return;

  const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  if (action === 'screenshot') {
    appendUserTgMsg('/screen', timeStr);
    setTimeout(() => {
      appendBotTgMsg(`
        📸 <b>Desktop Snapshot [Display 1]</b><br>
        <i>Resolution: 2560x1440 • 32ms capture</i><br>
        <div style="background:#111a2e; border-radius:6px; padding:8px; margin-top:6px; border:1px solid #334155; text-align:center;">
          <i class="fa-solid fa-desktop text-emerald" style="font-size:24px;"></i><br>
          <span style="font-size:10px; color:#94a3b8;">[Live View: LibreOffice + Terminal]</span>
        </div>
      `, timeStr, ['📸 Refresh', '⏸️ Pause', '⏹️ Stop']);
    }, 600);
  } else if (action === 'pause') {
    appendUserTgMsg('[⏸️ Pause Task]', timeStr);
    setTimeout(() => {
      appendBotTgMsg(`
        ⏸️ <b>Task Paused</b><br>
        Agent controls suspended. Press Resume when ready.
      `, timeStr, ['▶️ Resume', '⏹️ Stop']);
    }, 400);
  } else if (action === 'stop') {
    appendUserTgMsg('[⏹️ Stop Task]', timeStr);
    setTimeout(() => {
      appendBotTgMsg(`
        🛑 <b>Task Aborted</b><br>
        Agent has returned to idle standby.
      `, timeStr, ['📸 Screenshot', '📊 Status']);
    }, 400);
  } else if (action === 'Resume' || action === '▶️ Resume') {
    appendUserTgMsg('[▶️ Resume]', timeStr);
    setTimeout(() => {
      appendBotTgMsg(`
        ▶️ <b>Task Resumed</b><br>
        Continuing execution on Display 1.
      `, timeStr, ['📸 Screenshot', '⏸️ Pause', '⏹️ Stop']);
    }, 400);
  } else if (action === 'Refresh' || action === '📸 Refresh') {
    handleTgSimClick('screenshot');
  } else if (action === 'Status' || action === '📊 Status') {
    appendUserTgMsg('/status', timeStr);
    setTimeout(() => {
      appendBotTgMsg(`
        🤖 <b>System Status:</b> Idle Standby<br>
        ━━━━━━━━━━━━━━━<br>
        🖥️ Display: 2 Monitors Active<br>
        🧠 Model: Ollama Local (Llama 3.2 Vision)<br>
        🔒 Security: Whitelisted User ID Verified
      `, timeStr, ['📸 Screenshot']);
    }, 400);
  }
}

function handleTgSimSend() {
  const input = document.getElementById('tgSimInput');
  if (!input || !input.value.trim()) return;

  const userText = input.value.trim();
  input.value = '';
  const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  appendUserTgMsg(userText, timeStr);

  setTimeout(() => {
    if (userText.toLowerCase().includes('/screen')) {
      handleTgSimClick('screenshot');
    } else if (userText.toLowerCase().includes('/status')) {
      appendBotTgMsg(`
        🤖 <b>Active Task:</b> Custom Instruction<br>
        ━━━━━━━━━━━━━━━<br>
        ✅ 1. Screen perception parsed (40ms)<br>
        ⏳ 2. Executing instruction: "${userText}"<br>
        ⬜ 3. Final verification & snapshot
      `, timeStr, ['📸 Screenshot', '⏸️ Pause', '⏹️ Stop']);
    } else {
      appendBotTgMsg(`
        🤖 <b>Received Goal:</b> "${userText}"<br>
        Starting autonomous execution now.
      `, timeStr, ['📸 Screenshot', '⏸️ Pause', '⏹️ Stop']);
    }
  }, 500);
}

function appendUserTgMsg(text, timeStr) {
  const chatBody = document.getElementById('tgChatBody');
  const msgEl = document.createElement('div');
  msgEl.className = 'tg-msg tg-user-msg';
  msgEl.innerHTML = `
    <div class="tg-msg-text">${escapeHtml(text)}</div>
    <div class="tg-msg-time">${timeStr}</div>
  `;
  chatBody.appendChild(msgEl);
  chatBody.scrollTop = chatBody.scrollHeight;
}

function appendBotTgMsg(htmlContent, timeStr, buttons = []) {
  const chatBody = document.getElementById('tgChatBody');
  const msgEl = document.createElement('div');
  msgEl.className = 'tg-msg tg-bot-msg';

  let buttonsHtml = '';
  if (buttons.length > 0) {
    buttonsHtml = `
      <div class="tg-inline-keyboard flex flex-wrap gap-1 mt-2">
        ${buttons.map(b => `<button class="tg-btn" onclick="handleTgSimClick('${b.replace(/[^a-zA-Z]/g, '')}')">${b}</button>`).join('')}
      </div>
    `;
  }

  msgEl.innerHTML = `
    <div class="tg-msg-text font-mono text-xs">${htmlContent}</div>
    ${buttonsHtml}
    <div class="tg-msg-time">${timeStr}</div>
  `;
  chatBody.appendChild(msgEl);
  chatBody.scrollTop = chatBody.scrollHeight;
}

/* ==========================================================================
   Quickstart Tabs
   ========================================================================== */
function switchQsTab(tabKey) {
  const tabs = document.querySelectorAll('.qs-tab');
  tabs.forEach(t => t.classList.remove('active'));
  event.currentTarget.classList.add('active');

  const panes = {
    clone: 'qsPaneClone',
    deps: 'qsPaneDeps',
    setup: 'qsPaneSetup',
    run: 'qsPaneRun'
  };

  document.querySelectorAll('.qs-pane').forEach(p => p.classList.remove('active'));
  const activePane = document.getElementById(panes[tabKey]);
  if (activePane) activePane.classList.add('active');
}

function copyAllSteps(btn) {
  const fullScript = `# 1. Clone repository
git clone https://github.com/prettymuchgavin/MyDesktopAgent.git
cd MyDesktopAgent

# 2. Install dependencies
pip install -r requirements.txt

# 3. Interactive setup wizard
python setup.py

# 4. Launch Desktop Agent & Web Dashboard
python main.py`;

  navigator.clipboard.writeText(fullScript).then(() => {
    const original = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-check text-emerald"></i> Copied Full Script!';
    setTimeout(() => {
      btn.innerHTML = original;
    }, 2000);
  });
}

/* ==========================================================================
   Clipboard Utility
   ========================================================================== */
function copySnippet(text, btn) {
  navigator.clipboard.writeText(text).then(() => {
    const tooltip = btn.querySelector('.tooltip');
    if (tooltip) {
      tooltip.classList.add('show');
      setTimeout(() => {
        tooltip.classList.remove('show');
      }, 1800);
    } else {
      const original = btn.innerHTML;
      btn.innerHTML = '<i class="fa-solid fa-check text-emerald"></i>';
      setTimeout(() => {
        btn.innerHTML = original;
      }, 1800);
    }
  });
}

/* ==========================================================================
   FAQ Accordion
   ========================================================================== */
function toggleFaq(btn) {
  const item = btn.parentElement;
  const isActive = item.classList.contains('active');

  // Close all other items
  document.querySelectorAll('.faq-item').forEach(el => {
    el.classList.remove('active');
  });

  if (!isActive) {
    item.classList.add('active');
  }
}
