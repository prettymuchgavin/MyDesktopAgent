# 🤖 My Desktop Agent
> **An autonomous, local & cloud-powered AI desktop assistant that sees your screen, executes terminal tools, controls mouse/keyboard workflows, and responds to your voice or Telegram from anywhere.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![Ollama & Cloud](https://img.shields.io/badge/AI-Ollama%20%7C%20OpenRouter%20%7C%20Groq%20%7C%20OpenAI-purple.svg)](https://ollama.com)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows-0078D6.svg)](https://www.microsoft.com/windows)

---

## ✨ Features at a Glance

* **👁️ Real-Time Screen Perception (Non-Flickering VLM)**: Continuously observes desktop state across multiple monitors with automatic fail-safe recovery and zero cursor flicker.
* **🖱️ Autonomous Mouse & Keyboard Automation**: Humanized Bézier mouse trajectories, smart clipboard pasting, hotkeys, scrolling, and window switching.
* **⚡ High-Speed Direct Tools**: Instant PowerShell terminal command execution, DuckDuckGo web search (<1s), URL text extraction, and local filesystem operations.
* **🧩 Markdown Skills Ecosystem (`skills/*.md`)**: Drop-in `.md` skill guides (like OpenClaw / Cursor rules) with step-by-step instructions the agent dynamically references.
* **🎙️ Push-to-Talk Voice Input**: Press **`Alt + A`** or **`F8`** anywhere in Windows to speak tasks hands-free.
* **🔊 Natural Voice Generation**: Ultra-fast local Kokoro ONNX speech synthesis + ElevenLabs Cloud integration.
* **📱 Telegram Remote Control**: Complete remote control from your phone with strict User ID authentication, `/screen` snapshots, interactive inline buttons, and automated completion screenshots.
* **⏰ Scheduled Automations & Morning Briefings**: Recurring background cron routines that fetch news, summarize emails, and deliver daily reports.
* **🛡️ Dangerous Command Safety Gate**: Intercepts and blocks high-risk destructive terminal commands (e.g. `rm -rf`, `format`, `rmdir /s`).
* **🎨 Modern Obsidian & Times New Roman Dashboard**: A web control canvas with live stream viewport, dynamic plan checklist, terminal logs, and system tray minimization.

---

## 🚀 Quick Start

### 1. Prerequisites
- **Windows 10 / 11**
- **Python 3.10+** (64-bit recommended)
- *(Optional)* [Ollama](https://ollama.com) for 100% private local execution, or API keys for cloud providers (OpenRouter, Groq, OpenAI).

### 2. Installation
Clone the repository and install requirements:
```bash
git clone https://github.com/your-username/my-desktop-agent.git
cd my-desktop-agent
pip install -r requirements.txt
```

### 3. Interactive Setup Wizard
Run the setup wizard to choose your AI models, agent name, voice engine, and optional Telegram integration:
```bash
python setup.py
```
*(Or simply double-click `setup.bat`)*

### 4. Optional: Local Voice Weights (Kokoro ONNX)
To enable high-quality local voice synthesis:
```bash
python download_kokoro.py
```

### 5. Launch the Agent
You can run the agent in GUI mode or headless background mode:

```bash
# Standard Desktop GUI Mode:
python main.py

# Detached Background Worker Mode (System Tray):
python main.py --background
```

Open your browser at:
👉 **`http://localhost:8000`**

---

## 📱 Telegram Remote Setup

1. Open Telegram and message **`@BotFather`** to create a new bot and obtain your `bot_token`.
2. Message **`@userinfobot`** to find your numeric **User ID** (e.g., `123456789`).
3. Run `python setup.py` or edit `config.yaml` to add your token and numeric ID to `allowed_user_ids`.
4. Message your bot on Telegram:
   - Send any task prompt (e.g. *"Open Google Docs and write a project summary"*).
   - Use `/screen` for an instant desktop capture.
   - Use `/status` to check active plan steps.
   - Tap inline interactive buttons: `[📸 Screenshot]`, `[⏸️ Pause]`, `[⏹️ Stop]`.

---

## 🧩 Markdown Skills (`skills/`)

Create custom skills by simply dropping a `.md` file into the `skills/` directory:

```markdown
---
name: Web Research & Fact Gathering
description: Fast internet research, information synthesis, and summary reports.
triggers: search, research, google, news, find information
---

# Web Research Skill
1. Use `web_search` to query keywords in milliseconds.
2. Use `fetch_url` to inspect deep documentation.
3. Save findings to a local markdown file with `write_file`.
```

---

## ⌨️ Global Hotkeys

| Hotkey | Action |
| :--- | :--- |
| **`Alt + A`** or **`F8`** | **Push-to-Talk Voice Input** (Speak any desktop task out loud) |
| **`F12`** | **Emergency Pause / Resume** (Instantly freeze/unfreeze AI controls) |

---

## ⚙️ Configuration (`config.yaml`)

See [`config.example.yaml`](./config.example.yaml) for a fully documented configuration template.

---

## 🤝 Contributing

Contributions are welcome! Please check out [`CONTRIBUTING.md`](./CONTRIBUTING.md) for details on submitting Pull Requests and creating new Markdown skills.

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](./LICENSE) for more information.
