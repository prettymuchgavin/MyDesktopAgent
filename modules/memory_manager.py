import os
import json
import time
from typing import Dict, Any, List, Optional
from modules.logger import setup_logger

logger = setup_logger("MemoryManager")

MEMORY_FILE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "agent_memory.json")

class DesktopAgentMemoryManager:
    def __init__(self, file_path: str = MEMORY_FILE_PATH):
        self.file_path = file_path
        self.memory: Dict[str, Any] = {
            "user_preferences": {
                "default_browser": "Chrome / Default Web Browser",
                "default_editor": "Google Docs / Notepad",
                "communication_style": "Clear, concise, conversational"
            },
            "saved_notes": [],
            "learned_workflows": []
        }
        self._ensure_dir()
        self.load_memory()

    def _ensure_dir(self):
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

    def load_memory(self):
        """Loads persistent assistant memory from disk."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.memory.update(loaded)
                    logger.info(f"Loaded {len(self.memory.get('saved_notes', []))} saved notes and {len(self.memory.get('learned_workflows', []))} workflows from memory.")
            except Exception as e:
                logger.error(f"Failed to load agent memory file: {e}")
        else:
            self.save_memory()

    def save_memory(self):
        """Persists agent memory to disk."""
        try:
            self._ensure_dir()
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.memory, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save agent memory file: {e}")

    def add_preference(self, key: str, value: str):
        self.memory["user_preferences"][key] = value
        self.save_memory()
        logger.info(f"Saved preference '{key}': '{value}'")

    def add_note(self, title: str, content: str):
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        self.memory["saved_notes"].append({
            "title": title.strip(),
            "content": content.strip(),
            "timestamp": now
        })
        self.save_memory()
        logger.info(f"Saved note: '{title}'")

    def add_workflow(self, name: str, steps: List[str]):
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        self.memory["learned_workflows"].append({
            "name": name.strip(),
            "steps": steps,
            "timestamp": now
        })
        self.save_memory()
        logger.info(f"Saved learned workflow: '{name}'")

    def add_custom_memory(self, category: str, item_text: str, user: str = "Host"):
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        if category == "preferences":
            self.memory["user_preferences"][f"pref_{int(time.time())}"] = item_text
        elif category == "workflows":
            self.memory["learned_workflows"].append({
                "name": item_text,
                "steps": [],
                "timestamp": now
            })
        else:
            self.memory["saved_notes"].append({
                "title": "Quick Note",
                "content": item_text,
                "timestamp": now
            })
        self.save_memory()

    def get_memory_context_prompt(self) -> str:
        """Constructs a concise context snippet for LLM prompts."""
        context_parts = []
        
        # 1. Preferences
        prefs = self.memory.get("user_preferences", {})
        if prefs:
            pref_items = [f"- {k}: {v}" for k, v in prefs.items()]
            context_parts.append("[User Desktop Preferences]:\n" + "\n".join(pref_items))

        # 2. Saved Notes (recent 3)
        notes = self.memory.get("saved_notes", [])
        if notes:
            recent_notes = [f"- {n.get('title')}: {n.get('content')}" for n in notes[-3:]]
            context_parts.append("[Relevant User Notes]:\n" + "\n".join(recent_notes))

        # 3. Workflows (recent 2)
        wf = self.memory.get("learned_workflows", [])
        if wf:
            wf_items = [f"- {w.get('name')}: {' -> '.join(w.get('steps', []))}" for w in wf[-2:]]
            context_parts.append("[Saved Workflows]:\n" + "\n".join(wf_items))

        return "\n\n".join(context_parts)

    def get_all_memory(self) -> Dict[str, Any]:
        return self.memory

    def clear_all_memory(self):
        self.memory = {
            "user_preferences": {},
            "saved_notes": [],
            "learned_workflows": []
        }
        self.save_memory()
        logger.info("Cleared all desktop agent memory.")
