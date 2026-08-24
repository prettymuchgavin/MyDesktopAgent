import os
import time
import json
import uuid
import threading
from typing import Dict, Any, List, Optional, Callable
from modules.logger import setup_logger

logger = setup_logger("Scheduler")

SCHEDULES_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "schedules.json")

class SchedulerManager:
    """Manages scheduled routines, periodic reminders, and recurring daily briefings."""
    def __init__(self, task_trigger_callback: Optional[Callable] = None):
        self.task_trigger_callback = task_trigger_callback
        self.schedules: List[Dict[str, Any]] = []
        self.is_running = True
        self._load_schedules()
        
        self.worker_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.worker_thread.start()
        logger.info(f"⏰ Scheduler Manager started with {len(self.schedules)} scheduled routines.")

    def _load_schedules(self):
        os.makedirs(os.path.dirname(SCHEDULES_FILE), exist_ok=True)
        if os.path.exists(SCHEDULES_FILE):
            try:
                with open(SCHEDULES_FILE, "r", encoding="utf-8") as f:
                    self.schedules = json.load(f)
            except Exception as e:
                logger.error(f"Error loading schedules: {e}")
                self.schedules = []
        else:
            # Default default morning routine example
            self.schedules = [
                {
                    "id": "morning-briefing",
                    "goal": "Search top world and tech news headlines today, summarize in 4 bullet points, and check weather",
                    "time": "08:30",
                    "recurring": True,
                    "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                    "enabled": False,
                    "last_run": 0.0,
                    "target": "telegram"
                }
            ]
            self._save_schedules()

    def _save_schedules(self):
        try:
            with open(SCHEDULES_FILE, "w", encoding="utf-8") as f:
                json.dump(self.schedules, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving schedules: {e}")

    def add_schedule(self, goal: str, time_str: str, recurring: bool = True, target_chat_id: Optional[str] = None) -> Dict[str, Any]:
        """Adds a new scheduled automation routine (e.g. time_str='08:30' or '17:00')."""
        item = {
            "id": str(uuid.uuid4())[:8],
            "goal": goal.strip(),
            "time": time_str.strip(),
            "recurring": recurring,
            "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "enabled": True,
            "last_run": 0.0,
            "target_chat_id": target_chat_id
        }
        self.schedules.append(item)
        self._save_schedules()
        logger.info(f"⏰ Added new schedule: '{goal}' at {time_str}")
        return item

    def delete_schedule(self, schedule_id: str) -> bool:
        initial_len = len(self.schedules)
        self.schedules = [s for s in self.schedules if s.get("id") != schedule_id]
        if len(self.schedules) < initial_len:
            self._save_schedules()
            logger.info(f"Deleted schedule {schedule_id}")
            return True
        return False

    def list_schedules(self) -> List[Dict[str, Any]]:
        return self.schedules

    def _scheduler_loop(self):
        """Checks every 20 seconds if any scheduled routine should fire."""
        while self.is_running:
            try:
                now = time.time()
                current_hm = time.strftime("%H:%M")
                
                for item in self.schedules:
                    if not item.get("enabled", True):
                        continue
                        
                    target_time = item.get("time", "")
                    last_run = item.get("last_run", 0.0)
                    
                    # Fire if time matches and haven't run in the last 70 seconds
                    if current_hm == target_time and (now - last_run) > 70:
                        logger.info(f"⏰ Scheduled routine triggered: '{item.get('goal')}' (Time: {target_time})")
                        item["last_run"] = now
                        self._save_schedules()
                        
                        if self.task_trigger_callback:
                            self.task_trigger_callback(
                                goal=item.get("goal"),
                                requester_chat_id=item.get("target_chat_id")
                            )

                        if not item.get("recurring", True):
                            item["enabled"] = False
                            self._save_schedules()
                            
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                
            time.sleep(20)
