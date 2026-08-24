import os
import time
import json
import threading
import requests
import io
from typing import Dict, Any, List, Optional, Callable
from PIL import Image
from modules.logger import setup_logger

logger = setup_logger("TelegramBot")

class TelegramBotService:
    """Telegram Bot integration for remote desktop control and background task activation."""
    def __init__(self, config: Dict[str, Any], orchestrator_ref=None):
        self.config = config
        self.enabled = bool(config.get("enabled", False))
        self.bot_token = config.get("bot_token", "").strip()
        
        # Allowed user IDs (integer or string)
        raw_ids = config.get("allowed_user_ids", [])
        if isinstance(raw_ids, (int, str)):
            raw_ids = [raw_ids]
        self.allowed_user_ids = [str(uid).strip() for uid in raw_ids if str(uid).strip()]
        
        self.orchestrator = orchestrator_ref
        self.running = False
        self.polling_thread = None
        self.last_update_id = 0
        self.api_base = f"https://api.telegram.org/bot{self.bot_token}"

    def update_config(self, config: Dict[str, Any]):
        self.config = config
        was_enabled = self.enabled
        self.enabled = bool(config.get("enabled", False))
        self.bot_token = config.get("bot_token", "").strip()
        self.api_base = f"https://api.telegram.org/bot{self.bot_token}"
        
        raw_ids = config.get("allowed_user_ids", [])
        if isinstance(raw_ids, (int, str)):
            raw_ids = [raw_ids]
        self.allowed_user_ids = [str(uid).strip() for uid in raw_ids if str(uid).strip()]

        if self.enabled and not was_enabled:
            self.start()
        elif not self.enabled and was_enabled:
            self.stop()

    def is_authorized(self, user_id: Any) -> bool:
        """Verifies if the incoming message sender ID is in the trusted allowed list."""
        if not self.allowed_user_ids:
            return False
        return str(user_id).strip() in self.allowed_user_ids

    def start(self):
        if self.running or not self.enabled or not self.bot_token:
            return
        
        # Test bot token
        try:
            res = requests.get(f"{self.api_base}/getMe", timeout=8)
            if res.status_code == 200:
                bot_info = res.json().get("result", {})
                bot_username = bot_info.get("username", "UnknownBot")
                logger.info(f"📱 Telegram Bot connected as @{bot_username}. Allowed User IDs: {self.allowed_user_ids}")
            else:
                logger.error(f"Telegram Bot token validation failed (HTTP {res.status_code}): {res.text}")
                return
        except Exception as e:
            logger.error(f"Could not connect to Telegram API: {e}")
            return

        self.running = True
        self.polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self.polling_thread.start()

    def stop(self):
        self.running = False
        logger.info("Telegram Bot service stopped.")

    def get_quick_keyboard(self) -> Dict[str, Any]:
        """Generates interactive inline keyboard buttons for 1-tap remote control."""
        return {
            "inline_keyboard": [
                [
                    {"text": "📸 Screenshot", "callback_data": "cmd_screen"},
                    {"text": "📊 Status", "callback_data": "cmd_status"}
                ],
                [
                    {"text": "⏸️ Pause", "callback_data": "cmd_pause"},
                    {"text": "▶️ Resume", "callback_data": "cmd_resume"},
                    {"text": "⏹️ Stop", "callback_data": "cmd_stop"}
                ],
                [
                    {"text": "🧩 View Skills", "callback_data": "cmd_skills"}
                ]
            ]
        }

    def send_message(self, chat_id: Any, text: str, parse_mode: Optional[str] = "Markdown", with_keyboard: bool = False, custom_keyboard: Optional[Dict] = None):
        """Sends a text message back to the user via Telegram with optional inline buttons."""
        if not self.bot_token:
            return
        url = f"{self.api_base}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if custom_keyboard:
            payload["reply_markup"] = custom_keyboard
        elif with_keyboard:
            payload["reply_markup"] = self.get_quick_keyboard()

        try:
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            # Fallback without markdown if parse error
            try:
                payload.pop("parse_mode", None)
                requests.post(url, json=payload, timeout=10)
            except Exception:
                logger.error(f"Failed to send Telegram message: {e}")

    def send_photo(self, chat_id: Any, image_bytes: bytes, caption: str = "", with_keyboard: bool = True):
        """Sends a screenshot photo back to the user with interactive action buttons."""
        if not self.bot_token:
            return
        url = f"{self.api_base}/sendPhoto"
        files = {"photo": ("screenshot.jpg", image_bytes, "image/jpeg")}
        data = {"chat_id": chat_id, "caption": caption}
        if with_keyboard:
            data["reply_markup"] = json.dumps(self.get_quick_keyboard())

        try:
            requests.post(url, files=files, data=data, timeout=15)
        except Exception as e:
            logger.error(f"Failed to send Telegram photo: {e}")

    def answer_callback_query(self, callback_query_id: str, text: Optional[str] = None):
        """Answers incoming Telegram button tap."""
        if not self.bot_token:
            return
        try:
            requests.post(f"{self.api_base}/answerCallbackQuery", json={"callback_query_id": callback_query_id, "text": text or "Command received!"}, timeout=5)
        except Exception:
            pass

    def notify_user(self, message: str):
        """Broadcasts a notification to all authorized users."""
        for uid in self.allowed_user_ids:
            self.send_message(uid, message, with_keyboard=True)

    def _polling_loop(self):
        """Long polling loop fetching incoming messages and button callbacks from Telegram."""
        while self.running:
            try:
                url = f"{self.api_base}/getUpdates?offset={self.last_update_id + 1}&timeout=20"
                res = requests.get(url, timeout=30)
                if res.status_code == 200:
                    data = res.json()
                    updates = data.get("result", [])
                    for update in updates:
                        self.last_update_id = max(self.last_update_id, update.get("update_id", 0))
                        
                        # Case 1: Standard Text Message
                        msg = update.get("message", {})
                        if msg:
                            self._handle_incoming_message(msg)
                            
                        # Case 2: Interactive Inline Button Click
                        cb = update.get("callback_query", {})
                        if cb:
                            self._handle_callback_query(cb)

                time.sleep(0.5)
            except Exception as e:
                time.sleep(2.0)

    def _handle_callback_query(self, cb: Dict[str, Any]):
        cb_id = cb.get("id")
        user = cb.get("from", {})
        user_id = str(user.get("id", ""))
        chat_id = cb.get("message", {}).get("chat", {}).get("id") or user_id
        data = cb.get("data", "")

        if not self.is_authorized(user_id):
            self.answer_callback_query(cb_id, "⛔ Access Denied")
            return

        self.answer_callback_query(cb_id, f"Executing {data}...")
        logger.info(f"📱 Telegram Button Click from user {user_id}: '{data}'")

        if data == "cmd_screen":
            if self.orchestrator:
                jpeg_bytes = self.orchestrator.desktop_agent.capture_screen_jpeg(max_size=(1920, 1080), quality=80)
                if jpeg_bytes:
                    self.send_photo(chat_id, jpeg_bytes, caption="🖥️ Current Desktop Screen", with_keyboard=True)
                else:
                    self.send_message(chat_id, "⚠️ No screen capture available right now.")
        elif data == "cmd_status":
            self._send_status_message(chat_id)
        elif data == "cmd_pause":
            if self.orchestrator:
                self.orchestrator.pause_task()
                self.send_message(chat_id, "⏸️ Task paused.", with_keyboard=True)
        elif data == "cmd_resume":
            if self.orchestrator:
                self.orchestrator.resume_task()
                self.send_message(chat_id, "▶️ Task resumed.", with_keyboard=True)
        elif data == "cmd_stop":
            if self.orchestrator:
                self.orchestrator.stop_task()
                self.send_message(chat_id, "⏹️ Task stopped.", with_keyboard=True)
        elif data == "cmd_skills":
            self._send_skills_message(chat_id)

    def _send_status_message(self, chat_id: Any):
        if not self.orchestrator:
            self.send_message(chat_id, "⚠️ Orchestrator not attached.")
            return
        status = self.orchestrator.get_status()
        t_state = status.get("task_state", {})
        curr_goal = t_state.get("goal") or "None"
        curr_step = t_state.get("current_step") or "Idle"
        state = t_state.get("state") or "IDLE"
        
        msg_out = (
            f"📊 *Desktop Agent Status:*\n"
            f"• **Agent State:** `{state}`\n"
            f"• **Active Goal:** {curr_goal}\n"
            f"• **Current Step:** {curr_step}\n"
            f"• **Model:** `{status.get('text_model')}`"
        )
        self.send_message(chat_id, msg_out, with_keyboard=True)

    def _send_skills_message(self, chat_id: Any):
        if self.orchestrator and hasattr(self.orchestrator, "skill_manager"):
            skills = self.orchestrator.skill_manager.get_all_skills()
            if skills:
                skill_lines = [f"• *{s['name']}* (`{s['filename']}`)\n  _{s['description']}_" for s in skills]
                self.send_message(chat_id, "🧩 *Active Markdown Skills:*\n\n" + "\n\n".join(skill_lines), with_keyboard=True)
                return
        self.send_message(chat_id, "🧩 No custom skills loaded.", with_keyboard=True)

    def _handle_incoming_message(self, msg: Dict[str, Any]):
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        user = msg.get("from", {})
        user_id = str(user.get("id", ""))
        user_name = user.get("first_name", "User")
        text = msg.get("text", "").strip()

        if not text:
            return

        # 1. Strict Authorization Gate
        if not self.is_authorized(user_id):
            logger.warning(f"⛔ Unauthorized Telegram access attempt from user_id {user_id} (@{user.get('username')})")
            self.send_message(
                chat_id,
                f"⛔ *Access Denied*\nYour Telegram User ID (`{user_id}`) is not authorized to control this desktop agent.\n"
                f"To authorize this account, add `{user_id}` to `allowed_user_ids` in `config.yaml` or run `python setup.py`."
            )
            return

        logger.info(f"📱 Authorized Telegram command from @{user.get('username', user_id)}: '{text}'")

        # 2. Command Routing
        cmd = text.lower()
        
        if cmd in ["/start", "/help"]:
            help_text = (
                f"🤖 *My Desktop Agent - Remote Control*\n\n"
                f"Hello {user_name}! You are authenticated to control your desktop remotely.\n\n"
                f"📋 *Available Commands:*\n"
                f"• `/status` - Check agent state, current task, & step\n"
                f"• `/screen` - Get a live desktop screenshot\n"
                f"• `/task <goal>` - Execute an autonomous desktop task\n"
                f"• `/pause` - Pause active task\n"
                f"• `/resume` - Resume paused task\n"
                f"• `/stop` - Stop current task\n"
                f"• Or *send any prompt directly* to start executing it on your desktop!"
            )
            self.send_message(chat_id, help_text)
            return

        if cmd == "/status":
            if not self.orchestrator:
                self.send_message(chat_id, "⚠️ Orchestrator not attached.")
                return
            status = self.orchestrator.get_status()
            t_state = status.get("task_state", {})
            curr_goal = t_state.get("goal") or "None"
            curr_step = t_state.get("current_step") or "Idle"
            state = t_state.get("state") or "IDLE"
            
            msg_out = (
                f"📊 *Desktop Agent Status:*\n"
                f"• **Agent State:** `{state}`\n"
                f"• **Active Goal:** {curr_goal}\n"
                f"• **Current Step:** {curr_step}\n"
                f"• **Model:** `{status.get('text_model')}`"
            )
            self.send_message(chat_id, msg_out)
            return

        if cmd in ["/screen", "/screenshot"]:
            if self.orchestrator:
                jpeg_bytes = self.orchestrator.desktop_agent.capture_screen_jpeg(max_size=(1920, 1080), quality=80)
                if jpeg_bytes:
                    self.send_photo(chat_id, jpeg_bytes, caption="🖥️ Current Desktop Screen")
                else:
                    self.send_message(chat_id, "⚠️ No screen capture available right now.")
            return

        if cmd == "/pause":
            if self.orchestrator:
                self.orchestrator.pause_task()
                self.send_message(chat_id, "⏸️ Task paused.")
            return

        if cmd == "/resume":
            if self.orchestrator:
                self.orchestrator.resume_task()
                self.send_message(chat_id, "▶️ Task resumed.")
            return

        if cmd == "/stop":
            if self.orchestrator:
                self.orchestrator.stop_task()
                self.send_message(chat_id, "⏹️ Task stopped.")
            return

        # 3. Autonomous Task Execution (Direct text prompt or /task <goal>)
        task_goal = text
        if cmd.startswith("/task "):
            task_goal = text[6:].strip()

        if task_goal and self.orchestrator:
            self.send_message(chat_id, f"🚀 *Starting Task:* \"_{task_goal}_\"\nGenerating checklist and starting execution...")
            result = self.orchestrator.start_task(task_goal, requester_chat_id=chat_id)
            
            # Send initial plan back to user
            plan_steps = result.get("plan_steps", [])
            if plan_steps:
                checklist_text = "\n".join([f"{idx+1}. {step}" for idx, step in enumerate(plan_steps)])
                self.send_message(chat_id, f"📋 *Plan Generated:*\n{checklist_text}")
