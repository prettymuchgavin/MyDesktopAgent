# 🤖 Product Brief & Website Specification: My Desktop Agent
> **Purpose of this document:** Provide a complete, highly detailed breakdown of **My Desktop Agent** so an AI web designer / web developer can build a modern, high-converting product landing page or documentation website for this open-source application.

---

## 📌 1. Product Overview & Core Pitch

* **Product Name:** `My Desktop Agent`
* **Tagline:** *"The Autonomous AI Desktop Assistant That Sees Your Screen, Runs Terminal Tools, and Takes Action."*
* **Core Concept:** An open-source, high-agency Windows desktop AI companion that blends real-time computer vision, humanized keyboard/mouse automation, high-speed terminal tools (PowerShell, web search, local RAG), push-to-talk voice input, and complete Telegram mobile remote control.
* **Target Audience:** Developers, power users, entrepreneurs, creators, system administrators, and anyone who wants a proactive AI assistant that actually *does things* on their PC rather than just chatting in a browser tab.
* **License:** Open Source (MIT License)

---

## 🌟 2. Key Value Propositions (The "Why It's Different")

1. **High-Agency Execution (Not Just a Chatbot):**
   - Unlike standard chatbots (ChatGPT, Claude web) that can only give advice in text, My Desktop Agent actually opens applications, types documents in Google Docs/Notepad, runs build scripts, navigates browser tabs, and organizes files autonomously.
2. **Local Privacy or Cloud Superpowers:**
   - Works 100% offline and private using local **Ollama** models (e.g. `gemma4`, `llama3.2-vision`, `qwen2.5`) OR integrates seamlessly with high-speed cloud providers (**Groq**, **OpenRouter**, **OpenAI**, **Anthropic**, **Gemini**).
3. **Machine-Speed Tools + Organic GUI Hybrid:**
   - Performs tasks via instant **PowerShell commands**, **DuckDuckGo web search (<1s)**, and **local document retrieval** whenever possible, falling back to humanized visual mouse/keyboard clicks only when interacting with graphical canvases.
4. **Complete Telegram Remote Control:**
   - Control your home or office desktop from your phone anywhere in the world. Request real-time desktop screenshots, send task goals, and receive completion photos with interactive 1-tap buttons.
5. **Drop-in Markdown Skills Ecosystem (`skills/*.md`):**
   - Extend the agent's capabilities simply by dropping `.md` workflow guides into the `skills/` folder (inspired by OpenClaw and Cursor rules).

---

## 🚀 3. Comprehensive Feature Breakdown (For Website Bento Grid)

### 👁️ 1. Zero-Flicker Screen Perception & Multi-Monitor Support
- Captures and analyzes high-resolution screenshots on-demand without continuous hardware cursor flicker or GDI stutter.
- Multi-display switching: Target Display 1, Display 2, or full virtual desktop.
- Automatic fail-safe recovery if Windows sleeps or locks.

### 🖱️ 2. Humanized Desktop Mouse & Keyboard Automation
- Organic Bézier mouse curves, adaptive hover durations, and natural typing with clipboard paste acceleration for large text.
- Supports window focusing (`focus_window("Chrome")`), scrolling, and system shortcuts (`Ctrl+T`, `Alt+Tab`, `Win+R`).
- Global Emergency Freeze hotkey (`F12`) to instantly pause/resume AI controls.

### ⚡ 3. High-Speed Terminal & Tool Execution Engine
- Direct PowerShell and CMD execution with real-time stdout/stderr capture in milliseconds.
- Instant web search (<1 second) via DuckDuckGo without opening a browser window.
- Clean text extraction from public web URLs and REST APIs.

### 🎙️ 4. Push-to-Talk Voice & Natural Spoken Commentary
- Global hotkey: Press **`Alt + A`** or **`F8`** anywhere in Windows to speak tasks hands-free.
- Transcribes voice commands and speaks natural live commentary during task execution via ultra-low-latency local **Kokoro ONNX** or **ElevenLabs Cloud**.

### 📱 5. Telegram Mobile Companion
- Strict numeric User ID authorization whitelist to prevent unauthorized access.
- `/screen` command for instant desktop snapshots.
- `/status` to monitor active multi-step checklists.
- 1-tap interactive inline action buttons (`[📸 Screenshot]`, `[⏸️ Pause]`, `[⏹️ Stop]`, `[📊 Status]`).
- Automatic high-res completion screenshot sent directly to your phone when tasks finish.

### 📚 6. Local Document Knowledge Base (RAG)
- Drop any `.txt`, `.md`, `.json`, `.csv`, or code files into `data/knowledge/`.
- Automatic semantic chunking and BM25/TF-IDF similarity search so the agent references your personal notes and project specs in real-time.

### ⏰ 7. Scheduled Automations & Morning Briefings
- Set up recurring background cron routines (e.g. daily 08:30 AM morning briefing that fetches top news headlines, checks weather, and delivers a summary to Telegram).

### 🛡️ 8. Dangerous Command Safety Gate
- Built-in heuristic safety gate that intercepts and blocks destructive terminal commands (e.g. `rm -rf`, `format`, `rmdir /s`, `taskkill explorer.exe`) before execution.

---

## 🎨 4. Design, Typography & Brand Aesthetic Guidelines

* **Visual Vibe:** Modern, elegant, high-agency, dark obsidian utilitarian. Inspired by editorial typography blended with cybernetic minimalism.
* **Color Palette:**
  - **Background (Deep Obsidian):** `#0b1326`
  - **Surface Container (Card Background):** `#171f33` / `#131b2e`
  - **Surface High (Borders & Accents):** `#222a3e` / `#2d3449`
  - **Primary Text & Lavender Glow:** `#dbe1ff` / `#b5c4ff`
  - **Secondary Text (Slate Muted):** `#8d90a2` / `#c6c6d0`
  - **Accent Active / Glow Emerald:** `#34d399` / `#10b981`
  - **Magic Prompt Enhancer Gradient:** `linear-gradient(135deg, #a855f7 0%, #ec4899 50%, #3b82f6 100%)`
* **Typography:**
  - **Headings & Brand Title:** *Times New Roman* / Editorial Serif (Elegant, prestigious, distinct).
  - **Body Text & UI Labels:** *Inter*, *Roboto*, or clean Modern Sans-Serif.
  - **Code, Metrics & Terminal:** *JetBrains Mono* or *Consolas*.

---

## 📐 5. Recommended Website Structure & Page Wireframe

```
[ 1. Navigation Bar ]
Logo ("My Desktop Agent") | Features | How It Works | Skills | Documentation | GitHub Button [⭐ Star]

[ 2. Hero Section ]
- Big Serif Headline: "Your PC, Fully Autonomous."
- Subheadline: "An open-source desktop AI agent that observes your screen, executes terminal tools, controls applications, and listens to your voice or Telegram."
- Primary CTAs: [ 📥 Download / Quickstart ] [ 💻 View on GitHub ]
- Live Product Mockup / Video: Showcase the dark Obsidian & Times New Roman dashboard with live screen stream & dynamic plan checklist.

[ 3. Bento Grid of Capabilities ]
- Card 1: 👁️ Zero-Flicker Screen Vision (Multi-Monitor)
- Card 2: ⚡ Instant Terminal & Web Tools (<1s execution)
- Card 3: 📱 Telegram Remote Control with Inline Keyboards
- Card 4: 🎙️ Push-to-Talk Voice Input (`Alt+A`)
- Card 5: 🧩 Drop-in Markdown Skills (`skills/*.md`)
- Card 6: 🛡️ Dangerous Command Safety Gate

[ 4. How It Works (3-Step Interactive Workflow) ]
- Step 1: Input (Voice `Alt+A`, Dashboard Goal, or Telegram message).
- Step 2: Perception & Planning (Vision VLM analyzes desktop & generates dynamic checklist).
- Step 3: Fast Execution (Executes terminal commands, pastes text, clicks targets, sends completion photo).

[ 5. Drop-in Markdown Skills Showcase ]
- Code snippet comparison showing how simple `.md` files define entire agent workflows (like OpenClaw / Cursor rules).

[ 6. Local Privacy vs Cloud Flexibility ]
- Side-by-side comparison: Ollama 100% offline private execution vs Cloud API speed (Groq / OpenRouter / OpenAI).

[ 7. Comparison Table: My Desktop Agent vs Standard AI Chatbots ]
| Feature | Traditional Web Chatbot | My Desktop Agent |
| :--- | :--- | :--- |
| Direct Desktop Control | ❌ No (Text only) | ✅ Yes (Mouse, Keyboard, Apps) |
| Local Terminal & Filesystem | ❌ No | ✅ Yes (PowerShell, RAG, Web Search) |
| Sees Screen in Real-Time | ❌ Manual upload only | ✅ Continuous On-Demand Vision |
| Telegram Remote Control | ❌ No | ✅ Full Remote with Screenshots |
| Hands-Free Voice Input | ❌ Browser only | ✅ Global Hotkey (`Alt+A` / `F8`) |
| Offline / Local Models | ❌ No | ✅ Yes (Ollama / Local Kokoro ONNX) |

[ 8. Quick Start Section ]
- 3 terminal commands to get started:
  git clone ...
  pip install -r requirements.txt
  python setup.py

[ 9. FAQ Section ]
- Is it completely free and open source? (Yes, MIT License).
- Do I need an expensive GPU? (No, works with lightweight local 3B models or free cloud tiers).
- How is my desktop secured? (Strict Telegram User ID gate + destructive command safety filter).

[ 10. Footer ]
- Links: GitHub Repo, Releases, Documentation, License, Discord/Community.
```

---

## 💻 6. Quick Start Code Snippets (For Website Copy)

```bash
# 1. Clone the open-source repository
git clone https://github.com/your-username/my-desktop-agent.git
cd my-desktop-agent

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the interactive setup wizard
python setup.py

# 4. Launch Desktop Agent & Web Dashboard
python main.py
```

---

*This specification is ready to be provided to an AI web development tool, frontend engineer, or UI designer to build a landing page.*
