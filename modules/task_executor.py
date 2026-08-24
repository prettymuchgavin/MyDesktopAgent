import time
from typing import Dict, Any, List, Optional
from modules.logger import setup_logger

logger = setup_logger("TaskExecutor")

class DesktopTaskExecutor:
    """Manages autonomous desktop task planning, dynamic checklist updates, and execution."""
    def __init__(self):
        self.goal: str = ""
        self.state: str = "IDLE"  # IDLE, PLANNING, IN_PROGRESS, PAUSED, COMPLETED, FAILED
        self.plan_steps: List[str] = []
        self.current_step_idx: int = 0
        self.step_history: List[Dict[str, Any]] = []
        self.last_thought: str = ""
        self.created_at: float = 0.0
        self.updated_at: float = 0.0

    def start_task(self, goal: str, initial_plan: Optional[List[str]] = None) -> Dict[str, Any]:
        """Initializes and begins a new autonomous desktop task with custom plan."""
        self.goal = goal.strip()
        self.state = "IN_PROGRESS"
        self.current_step_idx = 0
        self.step_history = []
        self.created_at = time.time()
        self.updated_at = time.time()
        
        if initial_plan and isinstance(initial_plan, list) and len(initial_plan) > 0:
            self.plan_steps = [str(s).strip() for s in initial_plan if str(s).strip()]
        else:
            self.plan_steps = [
                f"Locate and open target application or browser for: {self.goal}",
                "Navigate to required workspace/canvas (e.g. document, search, editor)",
                "Draft, compose, and format primary content/data",
                "Review content, apply finishing touches, and finalize task"
            ]

        self.last_thought = f"Plan initialized with {len(self.plan_steps)} steps for: '{self.goal}'"
        logger.info(f"Autonomous Desktop Task started: '{self.goal}' with {len(self.plan_steps)} plan steps.")
        return self.get_status()

    def pause_task(self):
        if self.state == "IN_PROGRESS":
            self.state = "PAUSED"
            logger.info(f"Desktop Task paused: '{self.goal}'")

    def resume_task(self):
        if self.state == "PAUSED":
            self.state = "IN_PROGRESS"
            logger.info(f"Desktop Task resumed: '{self.goal}'")

    def stop_task(self):
        self.state = "IDLE"
        logger.info(f"Desktop Task stopped. Goal: '{self.goal}'")

    def update_plan_dynamically(self, updated_steps: List[str], current_step_hint: Optional[str] = None):
        """Updates or adapts the plan steps on-the-fly during task execution."""
        if not updated_steps or not isinstance(updated_steps, list):
            return

        cleaned_steps = [str(s).strip() for s in updated_steps if str(s).strip()]
        if cleaned_steps and cleaned_steps != self.plan_steps:
            logger.info(f"Adapting task plan on-the-fly! New plan ({len(cleaned_steps)} steps): {cleaned_steps}")
            self.plan_steps = cleaned_steps
            self.updated_at = time.time()
            
            # If current_step_idx is now out of bounds, clamp it
            if self.current_step_idx >= len(self.plan_steps):
                self.current_step_idx = max(0, len(self.plan_steps) - 1)

    def record_step_result(self, thought: str, actions: List[Dict[str, Any]], commentary: str, step_completed: bool = False, task_finished: bool = False, updated_plan: Optional[List[str]] = None):
        """Records executed actions, applies dynamic plan changes, and advances step progress."""
        self.last_thought = thought
        self.updated_at = time.time()
        
        # Check if model adapted the plan
        if updated_plan and isinstance(updated_plan, list) and len(updated_plan) > 0:
            self.update_plan_dynamically(updated_plan)

        self.step_history.append({
            "timestamp": time.strftime("%H:%M:%S"),
            "step_index": self.current_step_idx,
            "step_description": self.get_current_step_description(),
            "thought": thought,
            "actions_count": len(actions),
            "commentary": commentary
        })

        if step_completed:
            if self.current_step_idx < len(self.plan_steps) - 1:
                self.current_step_idx += 1
                logger.info(f"Step completed! Advancing to step {self.current_step_idx + 1}/{len(self.plan_steps)}: '{self.get_current_step_description()}'")
            else:
                task_finished = True

        if task_finished:
            self.state = "COMPLETED"
            self.last_thought = f"Task successfully completed: '{self.goal}'!"
            logger.info(f"Autonomous Desktop Task COMPLETED: '{self.goal}'")

    def get_current_step_description(self) -> str:
        if self.plan_steps and 0 <= self.current_step_idx < len(self.plan_steps):
            return self.plan_steps[self.current_step_idx]
        return "Executing task"

    def get_checklist(self) -> List[Dict[str, Any]]:
        """Returns structured list of checklist items with status (completed, in_progress, pending)."""
        checklist = []
        for idx, step_text in enumerate(self.plan_steps):
            if self.state == "COMPLETED" or idx < self.current_step_idx:
                status = "completed"
            elif idx == self.current_step_idx and self.state in ["IN_PROGRESS", "PAUSED"]:
                status = "in_progress"
            else:
                status = "pending"
                
            checklist.append({
                "index": idx + 1,
                "step": step_text,
                "status": status
            })
        return checklist

    def get_status(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "state": self.state,
            "current_step_idx": self.current_step_idx,
            "total_steps": len(self.plan_steps),
            "current_step": self.get_current_step_description(),
            "plan_steps": self.plan_steps,
            "checklist": self.get_checklist(),
            "last_thought": self.last_thought,
            "history_count": len(self.step_history),
            "recent_history": self.step_history[-5:]
        }
