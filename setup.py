import os
import sys
import time
import json
import yaml
import subprocess
import requests
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def print_banner():
    print("=" * 70)
    print("🤖  MY DESKTOP AGENT - INTERACTIVE TERMINAL SETUP WIZARD")
    print("=" * 70)
    print("Welcome! Let's customize your autonomous AI desktop assistant.\n")

def prompt_choice(prompt_text, options, default_idx=1):
    print(prompt_text)
    for idx, opt in enumerate(options, 1):
        def_tag = " (Default)" if idx == default_idx else ""
        print(f"  [{idx}] {opt}{def_tag}")
    while True:
        choice = input(f"\nSelect option [1-{len(options)}] (default {default_idx}): ").strip()
        if not choice:
            return default_idx - 1
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return int(choice) - 1
        print("Invalid choice, please enter a valid number.")

def setup_model_config():
    print("\n--------------------------------------------------")
    print("STEP 1: AI Model Configuration (Local vs Cloud)")
    print("--------------------------------------------------")
    
    mode_idx = prompt_choice(
        "Choose where your AI models should run:",
        ["Local (Ollama - 100% Private, Offline & Free)", "Cloud Provider (OpenRouter, OpenAI, Groq, Anthropic, Gemini)"],
        default_idx=1
    )
    
    ollama_cfg = {}
    
    if mode_idx == 0:
        # Local Ollama
        print("\n--- Local Ollama Setup ---")
        url = input("Enter your Ollama URL [default: http://localhost:11434]: ").strip()
        if not url:
            url = "http://localhost:11434"
        url = url.rstrip("/")
        
        print(f"Connecting to Ollama at {url}...")
        installed_models = []
        try:
            res = requests.get(f"{url}/api/tags", timeout=5)
            if res.status_code == 200:
                models_data = res.json().get("models", [])
                installed_models = [m.get("name") for m in models_data]
        except Exception as e:
            print(f"⚠️ Note: Could not query Ollama ({e}). Make sure Ollama is running.")

        if installed_models:
            print(f"\nFound {len(installed_models)} models in your local Ollama:")
            t_idx = prompt_choice("Select Text LLM model:", installed_models, default_idx=1)
            text_model = installed_models[t_idx]
            
            # Recommend vision model if available
            v_default = 1
            for idx, m in enumerate(installed_models, 1):
                if any(v in m.lower() for v in ["vision", "vl", "cloud", "gemma4"]):
                    v_default = idx
                    break
            v_idx = prompt_choice("Select Vision VLM model:", installed_models, default_idx=v_default)
            vision_model = installed_models[v_idx]
        else:
            text_model = input("Enter Ollama text model name [default: gemma4:31b-cloud]: ").strip() or "gemma4:31b-cloud"
            vision_model = input("Enter Ollama vision model name [default: gemma4:31b-cloud]: ").strip() or "gemma4:31b-cloud"

        ollama_cfg = {
            "provider": "ollama",
            "host": url,
            "text_model": text_model,
            "vision_model": vision_model,
            "temperature": 0.7
        }
    else:
        # Cloud Provider
        print("\n--- Cloud Provider Setup ---")
        providers = [
            "OpenRouter (Recommended - Access to all top models in one key)",
            "OpenAI (GPT-4o, GPT-4o-mini)",
            "Groq (Ultra-fast Llama 3.3 & Vision)",
            "Custom OpenAI-Compatible API Endpoint"
        ]
        p_idx = prompt_choice("Select Cloud Provider:", providers, default_idx=1)
        
        if p_idx == 0:
            provider_name = "openrouter"
            base_url = "https://openrouter.ai/api/v1"
            api_key = input("Enter your OpenRouter API Key (sk-or-...): ").strip()
            text_model = input("Text Model [default: openai/gpt-4o-mini]: ").strip() or "openai/gpt-4o-mini"
            vision_model = input("Vision Model [default: openai/gpt-4o-mini]: ").strip() or "openai/gpt-4o-mini"
        elif p_idx == 1:
            provider_name = "openai"
            base_url = "https://api.openai.com/v1"
            api_key = input("Enter your OpenAI API Key (sk-...): ").strip()
            text_model = input("Text Model [default: gpt-4o-mini]: ").strip() or "gpt-4o-mini"
            vision_model = input("Vision Model [default: gpt-4o-mini]: ").strip() or "gpt-4o-mini"
        elif p_idx == 2:
            provider_name = "groq"
            base_url = "https://api.groq.com/openai/v1"
            api_key = input("Enter your Groq API Key (gsk_...): ").strip()
            text_model = input("Text Model [default: llama-3.3-70b-versatile]: ").strip() or "llama-3.3-70b-versatile"
            vision_model = input("Vision Model [default: llama-3.2-11b-vision-preview]: ").strip() or "llama-3.2-11b-vision-preview"
        else:
            provider_name = "custom"
            base_url = input("Enter Base URL (e.g. https://api.together.xyz/v1): ").strip()
            api_key = input("Enter API Key: ").strip()
            text_model = input("Text Model name: ").strip()
            vision_model = input("Vision Model name: ").strip()

        ollama_cfg = {
            "provider": provider_name,
            "base_url": base_url,
            "api_key": api_key,
            "text_model": text_model,
            "vision_model": vision_model,
            "temperature": 0.7
        }

    return ollama_cfg

def setup_personality_config():
    print("\n--------------------------------------------------")
    print("STEP 2: Agent Personality & Directives")
    print("--------------------------------------------------")
    
    presets = [
        ("Helpful & Efficient Pro", "You are My Desktop Agent, a professional, focused, and efficient autonomous desktop productivity assistant. Keep answers direct and get tasks done quickly."),
        ("Friendly & Conversational Companion", "You are My Desktop Agent, a warm, polite, and conversational desktop companion. You speak naturally like a helpful friend while assisting with desktop tasks."),
        ("Tech Specialist / Coding Assistant", "You are My Desktop Agent, a precise technical specialist and software expert. You assist with technical workflows, code editing, terminal commands, and system tasks."),
        ("Creative & Brainstorming Partner", "You are My Desktop Agent, an imaginative and inspiring desktop assistant who excels at creative writing, brainstorming ideas, and drafting rich content."),
        ("Custom Personality (Write your own)", "")
    ]
    
    preset_names = [p[0] for p in presets]
    choice_idx = prompt_choice("Choose a personality preset:", preset_names, default_idx=1)
    
    name = input("\nWhat would you like to name your agent? [default: My Desktop Agent]: ").strip() or "My Desktop Agent"
    
    if choice_idx == 4:
        # Custom
        print("\nEnter your custom system persona prompt below:")
        prompt = input("> ").strip()
        if not prompt:
            prompt = f"You are {name}, an autonomous AI desktop assistant helping the user execute tasks on their computer."
    else:
        prompt = presets[choice_idx][1].replace("My Desktop Agent", name)

    enhance_choice = input("\n✨ Would you like to enhance this prompt with AI to make it more detailed? (y/n) [default: n]: ").strip().lower()
    if enhance_choice == "y":
        try:
            print("Enhancing prompt with AI...")
            from modules.llm_engine import OllamaEngine
            cfg_temp = load_config() if os.path.exists(CONFIG_PATH) else {}
            llm_temp = OllamaEngine(cfg_temp.get("ollama", {}))
            enhanced = llm_temp.enhance_system_prompt(prompt, name)
            if enhanced:
                prompt = enhanced
                print("\n✅ Enhanced System Prompt:")
                print(prompt)
        except Exception as e:
            print(f"Could not enhance prompt: {e}")

    return {"name": name, "persona_prompt": prompt}

def setup_voice_config():
    print("\n--------------------------------------------------")
    print("STEP 3: Voice & Speech Engine")
    print("--------------------------------------------------")
    
    has_voice = input("Do you want your desktop agent to speak out loud? (y/n) [default: y]: ").strip().lower()
    if has_voice == "n":
        return {
            "engine": "none",
            "sample_rate": 24000,
            "speed": 1.0,
            "voice": "af_sarah"
        }

    engines = [
        "Local Voice (Kokoro-TTS - Free, runs locally with ONNX, no API key needed)",
        "Cloud Voice (ElevenLabs - Ultra-realistic premium AI voice)"
    ]
    e_idx = prompt_choice("Select Voice Engine:", engines, default_idx=1)
    
    if e_idx == 0:
        return {
            "engine": "kokoro-onnx",
            "sample_rate": 24000,
            "speed": 1.1,
            "voice": "af_sarah"
        }
    else:
        print("\n--- ElevenLabs Configuration ---")
        api_key = input("Enter ElevenLabs API Key (xi-api-key): ").strip()
        voice_id = input("Enter Voice ID [default: 21m00Tcm4TlvDq8ikWAM]: ").strip() or "21m00Tcm4TlvDq8ikWAM"
        model_id = input("Enter Model ID [default: eleven_turbo_v2_5]: ").strip() or "eleven_turbo_v2_5"
        
        return {
            "engine": "elevenlabs",
            "sample_rate": 24000,
            "speed": 1.1,
            "voice": "af_sarah",
            "elevenlabs": {
                "api_key": api_key,
                "voice_id": voice_id,
                "model_id": model_id
            }
        }

def setup_telegram_config():
    print("\n--------------------------------------------------")
    print("STEP 4: Telegram Remote Chat & Background Activation")
    print("--------------------------------------------------")
    print("You can control your agent from your phone via Telegram (like OpenClaw)!")
    print("When running in the background, sending a message on Telegram will wake up")
    print("the agent and execute the requested desktop task autonomously.\n")

    enable_tg = input("Enable Telegram Remote Control & Chat? (y/n) [default: n]: ").strip().lower()
    if enable_tg != "y":
        return {
            "enabled": False,
            "bot_token": "",
            "allowed_user_ids": []
        }

    print("\n--- Telegram Setup Guide ---")
    print("1. Open Telegram and search for @BotFather")
    print("2. Send '/newbot' and follow instructions to get your HTTP API Bot Token.")
    bot_token = input("\nEnter your Telegram Bot Token (e.g. 123456789:ABC-DEF...): ").strip()

    print("\n--- Security: Trusted User ID Authorization ---")
    print("To prevent unauthorized strangers from controlling your PC, the agent only")
    print("responds to your specific Telegram User ID.")
    print("(You can find your numeric User ID by messaging @userinfobot on Telegram)\n")
    
    user_id = input("Enter your numeric Telegram User ID (e.g. 123456789): ").strip()
    allowed_ids = [user_id] if user_id else []

    return {
        "enabled": bool(bot_token),
        "bot_token": bot_token,
        "allowed_user_ids": allowed_ids
    }

def setup_global_command():
    print("\n--------------------------------------------------")
    print("STEP 5: Global System Command")
    print("--------------------------------------------------")
    
    enable_global = input("Enable global system command ('desktop-agent' and 'agent') to run from ANY terminal? (y/n) [default: y]: ").strip().lower()
    if enable_global == "n":
        print("Skipping global command creation.")
        return

    python_exe = sys.executable
    main_py_path = os.path.join(BASE_DIR, "main.py")
    
    # 1. Create a launcher .cmd script
    cmd_content = f'@echo off\r\n"{python_exe}" "{main_py_path}" %*\r\n'
    
    # Target directory on Windows: %LOCALAPPDATA%\Microsoft\WindowsApps (always in user PATH by default)
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    windows_apps_dir = os.path.join(local_app_data, "Microsoft", "WindowsApps") if local_app_data else None
    
    success = False
    if windows_apps_dir and os.path.exists(windows_apps_dir):
        try:
            for alias in ["desktop-agent.cmd", "agent.cmd", "desktop-agent.bat", "agent.bat"]:
                target_file = os.path.join(windows_apps_dir, alias)
                with open(target_file, "w", encoding="utf-8") as f:
                    f.write(cmd_content)
            success = True
            print(f"✅ Global commands 'desktop-agent' and 'agent' installed to {windows_apps_dir}!")
        except Exception as e:
            print(f"Could not write to WindowsApps directory: {e}")

    # Fallback: Add BASE_DIR to User PATH environment variable
    if not success:
        try:
            for alias in ["desktop-agent.cmd", "agent.cmd", "desktop-agent.bat", "agent.bat"]:
                target_file = os.path.join(BASE_DIR, alias)
                with open(target_file, "w", encoding="utf-8") as f:
                    f.write(cmd_content)
            
            # Add to PATH via PowerShell
            ps_cmd = f'[Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path", "User") + ";{BASE_DIR}", "User")'
            subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True)
            print(f"✅ Project directory added to User PATH! Commands 'desktop-agent' and 'agent' are now globally available.")
        except Exception as e:
            print(f"⚠️ Could not set global PATH: {e}")

def main():
    clear_screen()
    print_banner()
    
    # Load existing config if present
    existing_cfg = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                existing_cfg = yaml.safe_load(f) or {}
        except Exception:
            pass

    # Run setup steps
    ollama_cfg = setup_model_config()
    agent_cfg = setup_personality_config()
    tts_cfg = setup_voice_config()
    telegram_cfg = setup_telegram_config()
    setup_global_command()

    # Construct final configuration
    final_config = {
        "desktop_agent": {
            "action_delay_sec": 0.2,
            "control_mode": "AUTO_DETECT",
            "emergency_hotkey": "f12",
            "enable_desktop_inputs": True,
            "vision_interval_sec": 3.0,
            "window_title": ""
        },
        "ollama": ollama_cfg,
        "agent": agent_cfg,
        "tts": tts_cfg,
        "telegram": telegram_cfg,
        "web_dashboard": {
            "host": "127.0.0.1",
            "port": 8000
        }
    }

    # Save to config.yaml
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(final_config, f, default_flow_style=False, sort_keys=False)

    print("\n" + "=" * 70)
    print("🎉 SETUP COMPLETE!")
    print(f"📄 Configuration saved to: {CONFIG_PATH}")
    print("=" * 70)
    print("\nYou can now launch My Desktop Agent anytime by:")
    print("  1. Typing 'desktop-agent' or 'agent' in any terminal or Run dialog (Win + R)")
    print("  2. Double-clicking 'run_app.bat'")
    print("  3. Running 'python main.py'\n")

    launch_now = input("Would you like to launch My Desktop Agent now? (y/n) [default: y]: ").strip().lower()
    if launch_now != "n":
        print("\n🚀 Starting My Desktop Agent...")
        python_exe = sys.executable
        main_py = os.path.join(BASE_DIR, "main.py")
        subprocess.run([python_exe, main_py])

if __name__ == "__main__":
    main()
