import os
import sys
import yaml
import requests
from typing import Dict, Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def load_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            pass
    return {}

def save_config(cfg: Dict[str, Any]):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, default_flow_style=False, sort_keys=False)
    print("✅ Configuration updated and saved successfully!")

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

def edit_models(cfg: Dict[str, Any]):
    from setup import setup_model_config
    print("\n--- Current Model Settings ---")
    ollama_data = cfg.get("ollama", {})
    provider = ollama_data.get("provider", "ollama")
    print(f"Provider: {provider}")
    print(f"Text Model: {ollama_data.get('text_model', 'None')}")
    print(f"Vision Model: {ollama_data.get('vision_model', 'None')}")
    if provider != "ollama":
        print(f"Base URL: {ollama_data.get('base_url', '')}")
        print(f"API Key: {'*' * 8 if ollama_data.get('api_key') else 'None'}")
    
    confirm = input("\nDo you want to reconfigure models & provider? (y/n) [default: y]: ").strip().lower()
    if confirm != "n":
        new_model_cfg = setup_model_config()
        cfg["ollama"] = new_model_cfg
        save_config(cfg)

def edit_personality(cfg: Dict[str, Any]):
    from setup import setup_personality_config
    agent_data = cfg.get("agent", {})
    print("\n--- Current Personality Settings ---")
    print(f"Name: {agent_data.get('name', 'My Desktop Agent')}")
    print(f"Prompt: {agent_data.get('persona_prompt', '')[:120]}...")
    
    confirm = input("\nDo you want to reconfigure personality & name? (y/n) [default: y]: ").strip().lower()
    if confirm != "n":
        new_agent_cfg = setup_personality_config()
        cfg["agent"] = new_agent_cfg
        save_config(cfg)

def edit_voice(cfg: Dict[str, Any]):
    from setup import setup_voice_config
    tts_data = cfg.get("tts", {})
    print("\n--- Current Voice Settings ---")
    print(f"Engine: {tts_data.get('engine', 'none')}")
    if tts_data.get("engine") == "elevenlabs":
        el = tts_data.get("elevenlabs", {})
        print(f"ElevenLabs Voice ID: {el.get('voice_id')}")
        print(f"ElevenLabs API Key: {'*' * 8 if el.get('api_key') else 'None'}")
    
    confirm = input("\nDo you want to reconfigure voice & TTS? (y/n) [default: y]: ").strip().lower()
    if confirm != "n":
        new_tts_cfg = setup_voice_config()
        cfg["tts"] = new_tts_cfg
        save_config(cfg)

def edit_telegram(cfg: Dict[str, Any]):
    from setup import setup_telegram_config
    tg_data = cfg.get("telegram", {})
    print("\n--- Current Telegram Settings ---")
    print(f"Enabled: {tg_data.get('enabled', False)}")
    print(f"Bot Token: {'*' * 8 if tg_data.get('bot_token') else 'None'}")
    print(f"Allowed User IDs: {tg_data.get('allowed_user_ids', [])}")
    
    confirm = input("\nDo you want to reconfigure Telegram remote control & keys? (y/n) [default: y]: ").strip().lower()
    if confirm != "n":
        new_tg_cfg = setup_telegram_config()
        cfg["telegram"] = new_tg_cfg
        save_config(cfg)

def edit_automation(cfg: Dict[str, Any]):
    desktop_data = cfg.get("desktop_agent", {})
    print("\n--- Current Automation & Safety Settings ---")
    interval = desktop_data.get("vision_interval_sec", 3.0)
    hotkey = desktop_data.get("emergency_hotkey", "f12")
    inputs = desktop_data.get("enable_desktop_inputs", True)
    print(f"Vision Interval: {interval} seconds")
    print(f"Emergency Pause Hotkey: {hotkey}")
    print(f"Desktop Automation Controls (PyAutoGUI): {'Enabled' if inputs else 'Disabled'}")

    new_interval = input(f"\nEnter Vision Interval in seconds [current: {interval}]: ").strip()
    if new_interval:
        try:
            desktop_data["vision_interval_sec"] = float(new_interval)
        except ValueError:
            print("Invalid number, keeping existing interval.")

    new_hotkey = input(f"Enter Emergency Pause Hotkey [current: {hotkey}]: ").strip()
    if new_hotkey:
        desktop_data["emergency_hotkey"] = new_hotkey.lower()

    toggle_inputs = input(f"Enable Desktop Mouse & Keyboard Controls? (y/n) [current: {'y' if inputs else 'n'}]: ").strip().lower()
    if toggle_inputs in ["y", "n"]:
        desktop_data["enable_desktop_inputs"] = (toggle_inputs == "y")

    cfg["desktop_agent"] = desktop_data
    save_config(cfg)

def run_config_menu():
    while True:
        clear_screen()
        cfg = load_config()
        
        ollama_data = cfg.get("ollama", {})
        agent_data = cfg.get("agent", {})
        tts_data = cfg.get("tts", {})
        tg_data = cfg.get("telegram", {})
        desktop_data = cfg.get("desktop_agent", {})

        provider = ollama_data.get("provider", "ollama")
        model_str = f"{provider} ({ollama_data.get('text_model', 'default')})"
        agent_name = agent_data.get("name", "My Desktop Agent")
        tts_engine = tts_data.get("engine", "none")
        tg_status = "Enabled" if tg_data.get("enabled") else "Disabled"

        print("=" * 70)
        print("⚙️   MY DESKTOP AGENT - CONFIGURATION MANAGER")
        print("=" * 70)
        print("Select a setting to view and adjust parameters:\n")
        print(f"  [1] AI Models & Provider        (Current: {model_str})")
        print(f"  [2] Personality & Agent Name    (Current: \"{agent_name}\")")
        print(f"  [3] Voice & TTS Engine          (Current: {tts_engine})")
        print(f"  [4] Telegram Keys & Security    (Current: {tg_status})")
        print(f"  [5] Automation & Safety         (Interval: {desktop_data.get('vision_interval_sec', 3.0)}s, Hotkey: {desktop_data.get('emergency_hotkey', 'f12')})")
        print(f"  [6] Full Setup Wizard (Run all setup steps)")
        print(f"  [7] Exit Configuration Manager")
        print("=" * 70)

        choice = input("\nSelect option [1-7]: ").strip()
        if choice == "1":
            edit_models(cfg)
            input("\nPress Enter to return to menu...")
        elif choice == "2":
            edit_personality(cfg)
            input("\nPress Enter to return to menu...")
        elif choice == "3":
            edit_voice(cfg)
            input("\nPress Enter to return to menu...")
        elif choice == "4":
            edit_telegram(cfg)
            input("\nPress Enter to return to menu...")
        elif choice == "5":
            edit_automation(cfg)
            input("\nPress Enter to return to menu...")
        elif choice == "6":
            import setup
            setup.main()
            break
        elif choice in ["7", "exit", "q", "quit"]:
            print("\nExiting Configuration Manager. Goodbye!")
            break

if __name__ == "__main__":
    run_config_menu()
