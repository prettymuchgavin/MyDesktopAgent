import time
import threading
from typing import Dict, Any, Optional
from modules.llm_engine import OllamaEngine
from modules.tts_engine import TTSEngine
from modules.game_agent import GameAgent
from modules.audio_listener import DesktopAudioListener
from modules.memory_manager import DesktopAgentMemoryManager
from modules.task_executor import DesktopTaskExecutor
from modules.telegram_bot import TelegramBotService
from modules.tool_manager import DesktopToolManager
from modules.skill_manager import SkillManager
from modules.knowledge_manager import LocalKnowledgeManager
from modules.scheduler_manager import SchedulerManager
from modules.voice_input import VoiceInputService
from modules.logger import setup_logger

logger = setup_logger("Orchestrator")

class DesktopAgentOrchestrator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.is_running = False
        self.loop_thread = None
        
        llm_cfg = config.get("llm", config.get("ollama", {}))
        self.llm = OllamaEngine(llm_cfg)
        self.tts = TTSEngine(config.get("tts", {}))
        
        desktop_cfg = config.get("desktop_agent", config.get("game_agent", {}))
        self.desktop_agent = GameAgent(desktop_cfg)
        
        # Knowledge Base & Skills
        self.knowledge_manager = LocalKnowledgeManager()
        self.skill_manager = SkillManager()
        
        # Tools & Safety
        self.tool_manager = DesktopToolManager(config.get("tools", {}), knowledge_manager=self.knowledge_manager)
        self.last_tool_output_summary: Optional[str] = None
        
        # Scheduler & Push-to-Talk Voice Input
        self.scheduler = SchedulerManager(task_trigger_callback=self._on_scheduled_task)
        self.voice_input = VoiceInputService(config.get("voice_input", {}), on_command_callback=self._on_voice_command)
        
        self.audio_listener = DesktopAudioListener(config.get("audio", {}))
        self.memory_manager = DesktopAgentMemoryManager()
        self.task_executor = DesktopTaskExecutor()
        
        # Telegram Bot integration (listens in background even when agent is OFF)
        self.telegram = TelegramBotService(config.get("telegram", {}), orchestrator_ref=self)
        self.telegram_requester_chat_id: Optional[Any] = None
        if self.telegram.enabled:
            self.telegram.start()
        
        self.persona = config.get("agent", {}).get("persona_prompt", "You are My Desktop Agent, an autonomous and proactive desktop assistant.")
        self.vision_interval = float(desktop_cfg.get("vision_interval_sec", 2.0))
        self.last_vision_time = 0.0
        self.last_spoken_commentary = ""

    def _on_voice_command(self, text: str):
        logger.info(f"🎙️ Executing Voice Command: '{text}'")
        self.tts.speak(f"Starting task: {text}")
        self.start_task(text)

    def _on_scheduled_task(self, goal: str, requester_chat_id: Optional[str] = None):
        logger.info(f"⏰ Executing Scheduled Task: '{goal}'")
        self.start_task(goal, requester_chat_id=requester_chat_id)

    def start(self):
        if self.is_running:
            return
        self.llm.reset_memory()
        self.last_tool_output_summary = None
        self.is_running = True
        self.loop_thread = threading.Thread(target=self._main_event_loop, daemon=True)
        self.loop_thread.start()
        logger.info("🟢 My Desktop Agent turned ON (Active)!")

    def stop(self):
        self.is_running = False
        self.task_executor.stop_task()
        logger.info("🔴 My Desktop Agent turned OFF (Standby).")

    def shutdown(self):
        self.stop()
        self.telegram.stop()
        logger.info("My Desktop Agent shutdown completely.")

    def start_task(self, goal: str, requester_chat_id: Optional[Any] = None) -> Dict[str, Any]:
        """Starts an autonomous desktop task with dynamic initial checklist planning."""
        self.telegram_requester_chat_id = requester_chat_id
        if not self.is_running:
            self.start()
        
        logger.info(f"Generating tailored initial plan for task: '{goal}'...")
        initial_plan = self.llm.generate_initial_task_plan(goal)
        return self.task_executor.start_task(goal, initial_plan=initial_plan)

    def pause_task(self):
        self.task_executor.pause_task()

    def resume_task(self):
        self.task_executor.resume_task()

    def stop_task(self):
        self.task_executor.stop_task()

    def update_config(self, new_config: Dict[str, Any]):
        """Updates runtime configuration live from Web Dashboard."""
        self.config = new_config
        self.persona = new_config.get("agent", {}).get("persona_prompt", self.persona)
        
        desktop_cfg = new_config.get("desktop_agent", new_config.get("game_agent", {}))
        self.vision_interval = float(desktop_cfg.get("vision_interval_sec", self.vision_interval))
        self.desktop_agent.enable_inputs = desktop_cfg.get("enable_desktop_inputs", desktop_cfg.get("enable_game_inputs", True))
        
        # Update Ollama models live
        ollama_cfg = new_config.get("ollama", {})
        self.llm.update_config(ollama_cfg)

        # Update Agent controls & TTS engine live
        self.desktop_agent.update_config(desktop_cfg)
        
        tts_cfg = new_config.get("tts", {})
        self.tts.update_config(tts_cfg)

        # Update Telegram bot
        telegram_cfg = new_config.get("telegram", {})
        self.telegram.update_config(telegram_cfg)

        logger.info(f"Runtime configuration updated. Text '{self.llm.text_model}' / Vision '{self.llm.vision_model}', TTS: '{self.tts.engine_type}', Telegram: {self.telegram.enabled}")

    def get_status(self) -> Dict[str, Any]:
        task_status = self.task_executor.get_status()
        active_mode = "DESKTOP_TASK" if task_status.get("state") == "IN_PROGRESS" else "STANDBY"
        return {
            "is_running": self.is_running,
            "active_mode": active_mode,
            "inputs_paused": self.desktop_agent.inputs_paused,
            "tts_playing": self.tts.is_playing,
            "audio_event": self.audio_listener.audio_event,
            "control_mode": self.desktop_agent.control_mode,
            "text_model": self.llm.text_model,
            "vision_model": self.llm.vision_model,
            "last_screenshot_available": self.desktop_agent.last_screenshot_b64 is not None,
            "task_state": task_status,
            "memory_stats": {
                "user_preferences": len(self.memory_manager.memory.get("user_preferences", {})),
                "saved_notes": len(self.memory_manager.memory.get("saved_notes", [])),
                "learned_workflows": len(self.memory_manager.memory.get("learned_workflows", []))
            }
        }

    def _main_event_loop(self):
        while self.is_running:
            try:
                # -------------------------------------------------------------
                # MODE A: Autonomous Desktop Task Mode (e.g. Write Docs, Search)
                # -------------------------------------------------------------
                if self.task_executor.state == "IN_PROGRESS":
                    now = time.time()
                    # Execute fast vision cycles without blocking on speech
                    if (now - self.last_vision_time) >= self.vision_interval:
                        self.last_vision_time = now
                        logger.info(f"Analyzing desktop to advance task: '{self.task_executor.goal}' (Step {self.task_executor.current_step_idx + 1})...")
                        
                        img_b64 = self.desktop_agent.capture_screen_b64()
                        if img_b64:
                            mouse_ctx = self.desktop_agent.get_mouse_context()
                            curr_step_desc = self.task_executor.get_current_step_description()
                            
                            # Inject relevant Markdown Skills and Knowledge Base context
                            skill_ctx = self.skill_manager.build_skill_context(self.task_executor.goal)
                            knowledge_ctx = self.knowledge_manager.get_knowledge_context(self.task_executor.goal)
                            
                            full_persona = self.persona
                            if skill_ctx:
                                full_persona += f"\n\n{skill_ctx}"
                            if knowledge_ctx:
                                full_persona += f"\n\n{knowledge_ctx}"
                            
                            task_res = self.llm.analyze_desktop_task(
                                image_b64=img_b64,
                                system_persona=full_persona,
                                goal=self.task_executor.goal,
                                current_step=curr_step_desc,
                                plan_steps=self.task_executor.plan_steps,
                                mouse_context=mouse_ctx,
                                tool_context=self.last_tool_output_summary
                            )
                            
                            thought = task_res.get("thought", "")
                            commentary = task_res.get("commentary", "")
                            actions = task_res.get("actions", [])
                            step_completed = task_res.get("step_completed", False)
                            task_finished = task_res.get("task_finished", False)
                            updated_plan = task_res.get("updated_plan", [])

                            # Fallback Completion Detection (e.g. If no more actions and goal is visible)
                            if not task_finished:
                                t_lower = (thought + " " + commentary).lower()
                                completion_phrases = [
                                    "task is complete", "task complete", "task is now complete",
                                    "goal is complete", "task finished", "successfully completed",
                                    "now open", "is now open", "loaded and visible", "goal has been achieved",
                                    "goal is achieved", "done!"
                                ]
                                if any(p in t_lower for p in completion_phrases) and not actions:
                                    logger.info(f"Completion detected from VLM reasoning: '{thought}'")
                                    task_finished = True
                                    step_completed = True

                            # 1. Record progress & apply dynamic checklist updates
                            self.task_executor.record_step_result(
                                thought=thought,
                                actions=actions,
                                commentary=commentary,
                                step_completed=step_completed,
                                task_finished=task_finished,
                                updated_plan=updated_plan
                            )

                            # 2. Speak live narration only if not duplicate/repetitive
                            if commentary and len(commentary) > 3:
                                if commentary.strip().lower() != getattr(self, "last_spoken_commentary", "").strip().lower():
                                    self.last_spoken_commentary = commentary.strip()
                                    self.tts.speak(commentary)
                            elif task_finished:
                                self.tts.speak(f"Task completed: {self.task_executor.goal}.")

                            # 3. Execute tools and desktop actions
                            if actions:
                                gui_actions = []
                                for act in actions:
                                    if not isinstance(act, dict):
                                        continue
                                    act_type = str(act.get("action") or act.get("type") or "").lower().strip()
                                    
                                    # Fast Direct Tools (Terminal, Web Search, Filesystem)
                                    if act_type in ["run_command", "terminal", "command", "powershell", "cmd", "shell", "exec", 
                                                    "web_search", "search", "search_web", "google", 
                                                    "fetch_url", "read_url", "get_webpage", "scrape", 
                                                    "read_file", "view_file", "cat", 
                                                    "write_file", "save_file", "create_file", 
                                                    "list_dir", "ls", "dir"]:
                                        tool_res = self.tool_manager.execute_tool(act)
                                        formatted = json.dumps(tool_res, indent=2)
                                        self.last_tool_output_summary = f"Tool '{act_type}' Output:\n{formatted}"
                                        logger.info(f"⚡ Tool '{act_type}' executed in real-time.")
                                    else:
                                        gui_actions.append(act)

                                if gui_actions:
                                    logger.info(f"Executing {len(gui_actions)} desktop GUI actions for goal '{self.task_executor.goal}'")
                                    self.desktop_agent.execute_actions(gui_actions)
                                    # Allow UI to settle and repaint before next screenshot
                                    time.sleep(0.5)

                            # 4. Notify via Telegram and turn agent back OFF if finished
                            if task_finished:
                                logger.info(f"🎉 Task '{self.task_executor.goal}' COMPLETED! Returning agent to OFF state.")
                                if self.telegram.enabled and self.telegram_requester_chat_id:
                                    screenshot_bytes = self.desktop_agent.capture_screen_jpeg(max_size=(1920, 1080), quality=85)
                                    caption = (
                                        f"✅ *Task Completed!*\n"
                                        f"Goal: \"_{self.task_executor.goal}_\"\n\n"
                                        f"📸 Final screen result attached."
                                    )
                                    if screenshot_bytes:
                                        self.telegram.send_photo(self.telegram_requester_chat_id, screenshot_bytes, caption=caption)
                                    else:
                                        self.telegram.send_message(self.telegram_requester_chat_id, caption)
                                    
                                    self.telegram_requester_chat_id = None
                                
                                self.stop()
                            elif step_completed:
                                # Allow UI brief moment to settle after step completion
                                time.sleep(0.4)
                                self.last_vision_time = 0.0

                    time.sleep(0.1)
                    continue

                # -------------------------------------------------------------
                # MODE B: Desktop Standby & Proactive Assistant Mode
                # -------------------------------------------------------------
                now = time.time()
                audio_ctx = self.audio_listener.get_audio_context()
                loud_audio_trigger = audio_ctx.get("was_recently_loud", False)
                min_cooldown = max(self.vision_interval, 2.0) if not loud_audio_trigger else 1.5

                if (now - self.last_vision_time) >= min_cooldown and not self.tts.is_playing:
                    if self.desktop_agent.is_loading_or_blank_screen():
                        time.sleep(0.5)
                        continue

                    self.last_vision_time = now
                    img_b64 = self.desktop_agent.capture_screen_b64()
                    if img_b64:
                        mouse_ctx = self.desktop_agent.get_mouse_context()
                        mem_context = self.memory_manager.get_memory_context_prompt()
                        
                        vision_res = self.llm.analyze_game_vision(
                            img_b64, self.persona, 
                            mouse_context=mouse_ctx, 
                            audio_context=audio_ctx,
                            memory_context=mem_context
                        )
                        commentary = vision_res.get("commentary", "").strip()
                        actions = vision_res.get("actions", [])
                        
                        if commentary and len(commentary) > 3 and commentary.lower() not in ["eyes on the screen!", "none"]:
                            self.tts.speak(commentary)

                        if actions:
                            logger.info(f"Executing {len(actions)} desktop actions: {actions}")
                            self.desktop_agent.execute_actions(actions)

                time.sleep(0.2)
            except Exception as e:
                logger.error(f"Error in orchestrator event loop: {e}")
                time.sleep(1.0)
