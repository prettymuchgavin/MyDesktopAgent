import requests
import json
import base64
import re
import collections
from typing import Dict, Any, Optional, List
from modules.logger import setup_logger

logger = setup_logger("LLMEngine")

def sanitize_commentary(text: str) -> str:
    """Removes leaked system prompts, mouse coordinates, mode labels, JSON keys, and AI jargon."""
    if not text:
        return ""

    cleaned = text.strip()

    # Reject if it looks like raw JSON, list, or python dict
    if cleaned.startswith("{") or cleaned.startswith("[") or "}" in cleaned or '"actions":' in cleaned or '"commentary":' in cleaned:
        return ""

    # Patterns of prompt metadata leakage
    leakage_patterns = [
        r"\[current mouse cursor state\].*?(\n|$)",
        r"\[desktop game audio hearing\].*?(\n|$)",
        r"\[relevant user notes.*?\]",
        r"\[user desktop preferences.*?\]",
        r"position\s*\(\d+,\s*\d+\)",
        r"x:\s*\d+%,?\s*y:\s*\d+%",
        r"quadrant:\s*[a-z-]+",
        r"mode:\s*(pointing|click_hover|selecting|crosshair|busy)",
        r"actions:\s*\[.*?\]",
        r"key_press",
        r"mouse_move",
        r"x_ratio",
        r"y_ratio",
        r"commentary\s*:",
        r"^actions\s*:"
    ]

    for pat in leakage_patterns:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE).strip()

    # Clean up double quotes, extra colons or dangling punctuation
    cleaned = cleaned.strip('"').strip("'").strip("`").strip()
    
    # If the text is purely technical keywords or empty, discard
    lower = cleaned.lower()
    if any(keyword == lower for keyword in ["pointing", "center", "none", "eyes on the screen!"]):
        return ""
    
    if len(cleaned) < 4:
        return ""

    return cleaned

def parse_json_safely(raw_text: str) -> Dict[str, Any]:
    """Extracts and safely parses JSON even if VLM outputs trailing commas, unescaped quotes, or markdown wrappers."""
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(json)?", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()

    json_start = cleaned.find("{")
    json_end = cleaned.rfind("}")
    if json_start != -1 and json_end != -1:
        json_str = cleaned[json_start:json_end+1]
        
        try:
            parsed = json.loads(json_str)
            raw_comm = parsed.get("commentary", "")
            parsed["commentary"] = sanitize_commentary(raw_comm)
            return parsed
        except Exception:
            pass

        fixed = re.sub(r",\s*([\}\]])", r"\1", json_str)
        try:
            parsed = json.loads(fixed)
            raw_comm = parsed.get("commentary", "")
            parsed["commentary"] = sanitize_commentary(raw_comm)
            return parsed
        except Exception:
            pass

        commentary = ""
        comm_match = re.search(r'"commentary"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', json_str)
        if comm_match:
            commentary = comm_match.group(1)
        else:
            comm_match2 = re.search(r'"commentary"\s*:\s*"(.*?)"', json_str, re.DOTALL)
            if comm_match2:
                commentary = comm_match2.group(1)

        actions = []
        actions_match = re.search(r'"actions"\s*:\s*(\[.*?\])', json_str, re.DOTALL)
        if actions_match:
            try:
                cleaned_acts = re.sub(r",\s*([\}\]])", r"\1", actions_match.group(1))
                actions = json.loads(cleaned_acts)
            except Exception:
                pass

        return {"commentary": sanitize_commentary(commentary), "actions": actions if isinstance(actions, list) else []}

    # If no JSON braces found, DO NOT output prompt metadata as commentary!
    return {"commentary": "", "actions": []}

class OllamaEngine:
    """Unified LLM & Vision Engine supporting local Ollama and Cloud Providers (OpenRouter, OpenAI, Groq, Anthropic, Gemini)."""
    def __init__(self, config: Dict[str, Any]):
        self.provider = config.get("provider", "ollama").lower()
        self.host = config.get("host", "http://localhost:11434").rstrip("/")
        self.api_key = config.get("api_key", "").strip()
        self.base_url = config.get("base_url", "https://openrouter.ai/api/v1").rstrip("/")
        self.text_model = config.get("text_model", "gemma4:31b-cloud")
        self.vision_model = config.get("vision_model", "gemma4:31b-cloud")
        self.temperature = float(config.get("temperature", 0.7))
        self.conversation_history: List[Dict[str, str]] = []
        self.recent_spoken_phrases = collections.deque(maxlen=30)
        
        if self.provider == "ollama":
            self._ensure_models_available()
        else:
            logger.info(f"Cloud LLM Engine initialized (Provider: '{self.provider}', Model: '{self.text_model}')")

    def update_config(self, config: Dict[str, Any]):
        """Updates model and provider settings live."""
        self.provider = config.get("provider", self.provider).lower()
        if config.get("host"):
            self.host = config.get("host").rstrip("/")
        if config.get("api_key"):
            self.api_key = config.get("api_key").strip()
        if config.get("base_url"):
            self.base_url = config.get("base_url").rstrip("/")
        if config.get("text_model"):
            self.text_model = config.get("text_model").strip()
        if config.get("vision_model"):
            self.vision_model = config.get("vision_model").strip()
        logger.info(f"LLMEngine updated. Provider: '{self.provider}', Text: '{self.text_model}', Vision: '{self.vision_model}'")

    def reset_memory(self):
        """Clears conversation memory and anti-repetition cache."""
        self.conversation_history.clear()
        self.recent_spoken_phrases.clear()
        logger.info("Agent conversation memory and anti-repetition cache reset.")

    def is_duplicate_phrase(self, text: str) -> bool:
        """Returns True if the text is substantially similar to anything spoken recently."""
        cleaned = re.sub(r'[^\w\s]', '', text.lower()).strip()
        if not cleaned or len(cleaned) < 5:
            return True

        new_words = set(cleaned.split())
        for past_phrase in self.recent_spoken_phrases:
            past_words = set(past_phrase.split())
            if not past_words:
                continue
            
            intersection = new_words.intersection(past_words)
            union = new_words.union(past_words)
            similarity = len(intersection) / float(len(union))
            
            if similarity > 0.55 or cleaned in past_phrase or past_phrase in cleaned:
                logger.info(f"Anti-Repetition Filter blocked duplicate phrase: '{text}'")
                return True

        return False

    def remember_phrase(self, text: str):
        cleaned = re.sub(r'[^\w\s]', '', text.lower()).strip()
        if cleaned:
            self.recent_spoken_phrases.append(cleaned)

    def get_installed_models(self) -> List[str]:
        """Fetch list of models available in local Ollama instance or common cloud presets."""
        if self.provider == "ollama":
            try:
                res = requests.get(f"{self.host}/api/tags", timeout=5)
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("name") for m in data.get("models", [])]
                    if models:
                        return models
            except Exception as e:
                logger.error(f"Failed to connect to Ollama at {self.host}: {e}")
        return [
            "gemma4:31b-cloud", "gemma4:latest", "llama3.2-vision:latest", 
            "qwen2.5:3b", "llama3.1:8b", "llama2-uncensored:latest",
            "openai/gpt-4o-mini", "anthropic/claude-3.5-sonnet", "google/gemini-2.0-flash-001"
        ]

    def _ensure_models_available(self):
        installed = self.get_installed_models()
        logger.info(f"Ollama connected. Installed models: {installed}")
        
        # Check text model fallback if not directly matching
        if installed and not any(self.text_model == m or self.text_model in m for m in installed):
            for candidate in ["gemma4:31b-cloud", "gemma4:latest", "llama3.1:8b", "llama2-uncensored:latest", installed[0]]:
                if candidate in installed or any(candidate in m for m in installed):
                    logger.warning(f"Configured text model '{self.text_model}' not found. Falling back to '{candidate}'.")
                    self.text_model = candidate
                    break

        # Check vision model fallback if not directly matching
        if installed and not any(self.vision_model == m or self.vision_model in m for m in installed):
            vision_candidates = [m for m in installed if "vision" in m or "vl" in m or "cloud" in m or "gemma4" in m or "kimi" in m]
            if vision_candidates:
                fallback_vision = vision_candidates[0]
                logger.warning(f"Configured vision model '{self.vision_model}' not found. Falling back to '{fallback_vision}'.")
                self.vision_model = fallback_vision
            elif installed:
                self.vision_model = installed[0]

    def _call_cloud_chat(self, model: str, messages: List[Dict[str, Any]], temperature: float = 0.5, max_tokens: int = 300) -> str:
        """Standard OpenAI-compatible Chat Completions API call for Cloud Providers."""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        res = requests.post(url, json=payload, headers=headers, timeout=45)
        if res.status_code == 200:
            data = res.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        else:
            logger.error(f"Cloud API error {res.status_code}: {res.text}")
            raise RuntimeError(f"Cloud API returned error {res.status_code}")

    def generate_chat_commentary(self, system_persona: str, chat_user: Optional[str], chat_message: Optional[str], game_context: str = "", memory_context: str = "") -> str:
        """Generates natural assistant response to user request or ongoing activity."""
        full_system = system_persona
        if memory_context:
            full_system += f"\n{memory_context}"

        content = ""
        if game_context:
            content += f"[Current Screen State]: {game_context}\n"
        if chat_user and chat_message:
            content += f"[@{chat_user}]: {chat_message}\nRespond directly to @{chat_user} in a natural, friendly, and helpful way."
        else:
            content += "Give a short, natural thought or remark about what you are doing right now."

        prompt_messages = [
            {"role": "system", "content": full_system},
            *self.conversation_history[-8:],
            {"role": "user", "content": content}
        ]

        try:
            if self.provider == "ollama":
                payload = {
                    "model": self.text_model,
                    "messages": prompt_messages,
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": 60,
                        "num_ctx": 1024,
                        "repeat_penalty": 1.2
                    },
                    "stream": False
                }
                res = requests.post(f"{self.host}/api/chat", json=payload, timeout=20)
                if res.status_code == 200:
                    raw_reply = res.json().get("message", {}).get("content", "").strip()
                else:
                    return ""
            else:
                raw_reply = self._call_cloud_chat(self.text_model, prompt_messages, temperature=self.temperature, max_tokens=60)

            reply = sanitize_commentary(raw_reply)
            logger.info(f"LLM Response generated ({self.text_model}): {reply}")
            
            if not reply or self.is_duplicate_phrase(reply):
                return ""

            self.remember_phrase(reply)
            self.conversation_history.append({"role": "user", "content": content})
            self.conversation_history.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            logger.error(f"Error generating chat commentary: {e}")
            
        return ""

    def generate_initial_task_plan(self, goal: str) -> List[str]:
        """Uses Text LLM to generate an intelligent, concise step-by-step checklist for the user's task."""
        prompt = (
            f"User Goal: '{goal}'\n\n"
            "Create a concise, actionable step-by-step plan (4 to 6 numbered steps) to accomplish this goal on a Windows desktop.\n"
            "Respond strictly in valid JSON format with a single key 'plan': [\"Step 1 description\", \"Step 2 description\", ...]\n"
            "Example format:\n"
            "{\n"
            "  \"plan\": [\n"
            "    \"Open the browser and navigate to Google Docs\",\n"
            "    \"Create a new blank document\",\n"
            "    \"Write the document header and executive summary\",\n"
            "    \"Add case studies and contact details\",\n"
            "    \"Review and finalize document\"\n"
            "  ]\n"
            "}"
        )
        try:
            if self.provider == "ollama":
                payload = {
                    "model": self.text_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "options": {"temperature": 0.2, "num_predict": 200, "num_ctx": 1024},
                    "stream": False
                }
                res = requests.post(f"{self.host}/api/chat", json=payload, timeout=15)
                if res.status_code == 200:
                    resp_text = res.json().get("message", {}).get("content", "").strip()
                else:
                    resp_text = ""
            else:
                resp_text = self._call_cloud_chat(self.text_model, [{"role": "user", "content": prompt}], temperature=0.2, max_tokens=200)

            if resp_text:
                cleaned = re.sub(r"^```(json)?|```$", "", resp_text, flags=re.IGNORECASE).strip()
                data = json.loads(cleaned)
                plan = data.get("plan", [])
                if isinstance(plan, list) and len(plan) >= 2:
                    return [str(s).strip() for s in plan if str(s).strip()]
        except Exception as e:
            logger.warning(f"Failed to generate dynamic LLM plan: {e}")

        # Sensible fallback checklist
        return [
            f"Locate and open the required application/browser for: {goal}",
            "Navigate to the workspace, document canvas, or search bar",
            "Compose, draft, and format the main content and data",
            "Review progress, apply finishing touches, and finalize task"
        ]

    def enhance_system_prompt(self, current_prompt: str, agent_name: str = "Carl") -> str:
        """Takes a user's brief personality/system prompt and expands it into a detailed, high-performance Desktop Agent persona."""
        cleaned = current_prompt.strip() if current_prompt else ""
        if not cleaned:
            cleaned = f"A helpful, proactive, and intelligent desktop assistant named {agent_name} who assists with productivity, coding, applications, and web research."

        meta_prompt = (
            f"You are an expert AI Prompt Engineer and Persona Architect.\n"
            f"The user has written an initial system prompt/personality description for their Desktop Agent named '{agent_name}':\n"
            f"\"\"\"\n{cleaned}\n\"\"\"\n\n"
            f"Your job is to expand and enhance this prompt into a comprehensive, highly detailed, and professional System Persona Prompt for an Autonomous Desktop AI Agent.\n\n"
            f"The enhanced system prompt MUST include the following structured elements:\n"
            f"1. Core Identity & Mission: Clear definition of {agent_name}'s role as an autonomous desktop companion.\n"
            f"2. Personality & Communication Style: Precise tone (e.g. grounded, concise, professional yet personable), pacing, and vocal delivery guidelines.\n"
            f"3. Desktop Action & Tool Competence: Guidance on navigating Windows apps, web browsers, documents, code editors, and keyboard shortcuts effectively.\n"
            f"4. Proactive Problem-Solving & Step Adaptation: How to handle errors, unexpected UI states, and break down multi-step desktop tasks efficiently.\n"
            f"5. Key Rules & Constraints: Speak in present-tense intent, never repeat coordinates or internal JSON parameters aloud, announce task completions clearly.\n\n"
            f"Output ONLY the final enhanced system prompt text. Do NOT include markdown code fences, meta-commentary, or introductory remarks."
        )

        try:
            if self.provider == "ollama":
                payload = {
                    "model": self.text_model,
                    "messages": [
                        {"role": "system", "content": "You are a master AI Prompt Engineer. Output only the refined system prompt text."},
                        {"role": "user", "content": meta_prompt}
                    ],
                    "options": {"temperature": 0.5, "num_predict": 450, "num_ctx": 2048},
                    "stream": False
                }
                res = requests.post(f"{self.host}/api/chat", json=payload, timeout=15)
                if res.status_code == 200:
                    enhanced = res.json().get("message", {}).get("content", "").strip()
                else:
                    enhanced = ""
            else:
                messages = [
                    {"role": "system", "content": "You are a master AI Prompt Engineer. Output only the refined system prompt text."},
                    {"role": "user", "content": meta_prompt}
                ]
                enhanced = self._call_cloud_chat(self.text_model, messages, temperature=0.5, max_tokens=500)

            # Strip any markdown code fences if generated
            enhanced = re.sub(r"^```(markdown|text)?\n?", "", enhanced, flags=re.IGNORECASE).strip()
            enhanced = re.sub(r"\n?```$", "", enhanced).strip()
            
            if enhanced and len(enhanced) > 50:
                logger.info(f"System prompt enhanced successfully ({len(enhanced)} chars).")
                return enhanced
        except Exception as e:
            logger.error(f"Error enhancing system prompt: {e}")

        # High-quality fallback expansion if LLM call is offline
        return (
            f"You are {agent_name}, an autonomous, highly capable, and proactive desktop AI assistant.\n"
            f"• Core Role: You assist the user by autonomously executing desktop tasks, writing content, organizing files, navigating web applications, and providing concise technical insights.\n"
            f"• Communication Style: Direct, intelligent, professional, and natural. Speak with clarity and grounded brevity. Always speak in present-tense intent.\n"
            f"• Desktop Execution: You interact smoothly with Windows apps, web browsers, and tools. You analyze on-screen context, dynamically adapt task steps when needed, and report progress transparently.\n"
            f"• Key Principles: Maintain high accuracy, verify completion on screen before finishing, and never output raw internal parameters aloud."
        )

    def analyze_game_vision(self, image_b64: str, system_persona: str, mouse_context: Optional[Dict[str, Any]] = None, audio_context: Optional[Dict[str, Any]] = None, memory_context: str = "") -> Dict[str, Any]:
        """Analyzes desktop screenshot and outputs natural assistant commentary + optional control actions."""
        mouse_info = ""
        if mouse_context:
            mouse_info = (
                f"[Current Mouse Cursor State]: Position ({mouse_context.get('x')}, {mouse_context.get('y')}) "
                f"[X: {int(mouse_context.get('x_ratio', 0.5)*100)}%, Y: {int(mouse_context.get('y_ratio', 0.5)*100)}%], "
                f"Quadrant: {mouse_context.get('quadrant')}, Mode: {mouse_context.get('mode')}.\n"
            )

        full_system = system_persona
        if memory_context:
            full_system += f"\n{memory_context}"

        prompt = (
            "You are My Desktop Agent, a helpful, grounded, and observant assistant watching what is on screen.\n"
            + mouse_info +
            "Analyze what is on screen and respond strictly in valid JSON format with two keys:\n"
            "1. 'commentary': A short, natural 1-sentence thought or remark spoken out loud about what you see or are about to do right now (speak naturally like a normal person, in present tense, never past tense).\n"
            "   CRITICAL RULES FOR 'commentary':\n"
            "   - Speak naturally and conversationally.\n"
            "   - NEVER read aloud or repeat mouse coordinates, cursor mode, screen quadrants, audio states, or JSON keys.\n"
            "   - If nothing noteworthy is happening, or if the screen is loading/blank, leave 'commentary' as \"\".\n"
            "2. 'actions': A list of automated mouse & keyboard input actions to control the app on screen.\n"
            "   - To click on buttons, items, or UI elements on screen: [{\"action\": \"click\", \"x_ratio\": 0.5, \"y_ratio\": 0.6}]\n"
            "   - To aim or move the cursor: [{\"action\": \"move\", \"x_ratio\": 0.4, \"y_ratio\": 0.3}]\n"
            "   - To scroll mouse wheel up/down: [{\"action\": \"scroll\", \"direction\": \"down\", \"clicks\": 300, \"x_ratio\": 0.5, \"y_ratio\": 0.5}]\n"
            "   If the screen is in a loading state or no input is needed right now, leave 'actions' as [].\n\n"
            "JSON output format example:\n"
            "{\n"
            "  \"commentary\": \"\",\n"
            "  \"actions\": [{\"action\": \"click\", \"x_ratio\": 0.5, \"y_ratio\": 0.5}]\n"
            "}"
        )

        try:
            if self.provider == "ollama":
                payload = {
                    "model": self.vision_model,
                    "messages": [
                        {"role": "system", "content": full_system},
                        {"role": "user", "content": prompt, "images": [image_b64]}
                    ],
                    "options": {"temperature": 0.5, "num_predict": 80, "num_ctx": 1024, "repeat_penalty": 1.2},
                    "stream": False
                }
                res = requests.post(f"{self.host}/api/chat", json=payload, timeout=45)
                if res.status_code == 200:
                    resp_text = res.json().get("message", {}).get("content", "").strip()
                else:
                    return {"commentary": "", "actions": []}
            else:
                messages = [
                    {"role": "system", "content": full_system},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                        ]
                    }
                ]
                resp_text = self._call_cloud_chat(self.vision_model, messages, temperature=0.5, max_tokens=100)

            parsed = parse_json_safely(resp_text)
            commentary = parsed.get("commentary", "").strip()
            
            if commentary:
                if self.is_duplicate_phrase(commentary):
                    parsed["commentary"] = ""
                else:
                    self.remember_phrase(commentary)
            return parsed
        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            
        return {"commentary": "", "actions": []}

    def analyze_desktop_task(self, image_b64: str, system_persona: str, goal: str, current_step: str, plan_steps: List[str], mouse_context: Optional[Dict[str, Any]] = None, tool_context: Optional[str] = None) -> Dict[str, Any]:
        """Analyzes desktop screen and executes autonomous tasks using fast tools (terminal commands, web search, files) and GUI actions."""
        mouse_info = ""
        if mouse_context:
            mouse_info = f"[Mouse Cursor Position]: ({mouse_context.get('x')}, {mouse_context.get('y')}) [X: {int(mouse_context.get('x_ratio', 0.5)*100)}%, Y: {int(mouse_context.get('y_ratio', 0.5)*100)}%].\n"

        tool_info = ""
        if tool_context:
            tool_info = f"\n[Recent Tool Execution Output]:\n{tool_context}\n"

        prompt = (
            f"You are My Desktop Agent, an autonomous assistant executing a user desktop task.\n"
            f"OVERALL USER GOAL: \"{goal}\"\n"
            f"CURRENT ACTIVE STEP: \"{current_step}\"\n"
            f"FULL TASK PLAN CHECKLIST: {json.dumps(plan_steps)}\n"
            + mouse_info
            + tool_info +
            "\nAnalyze the screen and tool outputs to determine if the goal has been achieved or what tool/action is needed next.\n\n"
            "CRITICAL GOAL COMPLETION RULES:\n"
            f"- If the overall goal ('{goal}') is ALREADY ACCOMPLISHED on screen or via tool output:\n"
            "  * Set 'task_finished': true\n"
            "  * Set 'step_completed': true\n"
            "  * Set 'actions': []\n"
            "  * In 'commentary', explicitly state that the goal has been accomplished.\n"
            "- If not finished, choose the fastest tool or GUI action to advance the task.\n\n"
            "AVAILABLE TOOLS & ACTIONS:\n"
            "⚡ FAST DIRECT TOOLS (Recommended for speed):\n"
            "   - Run Terminal Command (PowerShell): {\"action\": \"run_command\", \"command\": \"ipconfig\"}\n"
            "   - Instant Web Search: {\"action\": \"web_search\", \"query\": \"latest news on...\"}\n"
            "   - Fetch Webpage Text: {\"action\": \"fetch_url\", \"url\": \"https://github.com\"}\n"
            "   - Read Local File: {\"action\": \"read_file\", \"path\": \"C:\\\\path\\\\file.txt\"}\n"
            "   - Write Local File: {\"action\": \"write_file\", \"path\": \"summary.txt\", \"content\": \"...\"}\n"
            "   - List Directory: {\"action\": \"list_dir\", \"path\": \".\"}\n\n"
            "🖱️ DESKTOP GUI ACTIONS:\n"
            "   - Open URL in Browser: {\"action\": \"open_url\", \"url\": \"https://github.com\"}\n"
            "   - Open Application: {\"action\": \"open_app\", \"app\": \"notepad\"}\n"
            "   - Click Target: {\"action\": \"click\", \"x_ratio\": 0.5, \"y_ratio\": 0.4}\n"
            "   - Type Text: {\"action\": \"type_text\", \"text\": \"...\", \"paste\": true, \"press_enter\": false}\n"
            "   - Hotkey Shortcut: {\"action\": \"hotkey\", \"keys\": [\"ctrl\", \"t\"]}\n"
            "   - Scroll: {\"action\": \"scroll\", \"direction\": \"down\", \"clicks\": 300}\n"
            "   - Wait: {\"action\": \"wait\", \"seconds\": 1.0}\n\n"
            "Respond strictly in valid JSON format with keys:\n"
            "1. 'thought': Short explanation of current screen state, tool outputs, and next step.\n"
            "2. 'commentary': A 1-sentence natural remark spoken out loud about what you are doing right now.\n"
            "3. 'actions': List of input actions or fast tools to execute.\n"
            "4. 'step_completed': true if current step is completed, else false.\n"
            "5. 'task_finished': true if goal is completely achieved, else false.\n"
            "6. 'updated_plan': Optional list of adjusted plan steps.\n\n"
            "JSON output format example:\n"
            "{\n"
            "  \"thought\": \"Running terminal command to check system network IP configuration.\",\n"
            "  \"commentary\": \"Checking your network status via the terminal now.\",\n"
            "  \"actions\": [{\"action\": \"run_command\", \"command\": \"ipconfig\"}],\n"
            "  \"step_completed\": false,\n"
            "  \"task_finished\": false,\n"
            "  \"updated_plan\": []\n"
            "}"
        )

        try:
            if self.provider == "ollama":
                payload = {
                    "model": self.vision_model,
                    "messages": [
                        {"role": "system", "content": system_persona},
                        {"role": "user", "content": prompt, "images": [image_b64]}
                    ],
                    "options": {"temperature": 0.3, "num_predict": 250, "num_ctx": 2048},
                    "stream": False
                }
                res = requests.post(f"{self.host}/api/chat", json=payload, timeout=50)
                if res.status_code == 200:
                    resp_text = res.json().get("message", {}).get("content", "").strip()
                else:
                    return {"thought": "Processing...", "commentary": "", "actions": [], "step_completed": False, "task_finished": False, "updated_plan": []}
            else:
                messages = [
                    {"role": "system", "content": system_persona},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                        ]
                    }
                ]
                resp_text = self._call_cloud_chat(self.vision_model, messages, temperature=0.3, max_tokens=250)

            logger.info(f"Desktop Task response: {resp_text[:100]}...")
            parsed = parse_json_safely(resp_text)
            
            try:
                raw_parsed = json.loads(re.sub(r"^```(json)?|```$", "", resp_text, flags=re.IGNORECASE).strip())
                parsed["step_completed"] = bool(raw_parsed.get("step_completed", False))
                parsed["task_finished"] = bool(raw_parsed.get("task_finished", False))
                parsed["thought"] = str(raw_parsed.get("thought", ""))
                if "actions" in raw_parsed and isinstance(raw_parsed["actions"], list):
                    parsed["actions"] = raw_parsed["actions"]
                if "updated_plan" in raw_parsed and isinstance(raw_parsed["updated_plan"], list) and len(raw_parsed["updated_plan"]) > 0:
                    parsed["updated_plan"] = raw_parsed["updated_plan"]
            except Exception:
                pass

            return parsed
        except Exception as e:
            logger.error(f"Desktop Task vision analysis failed: {e}")

        return {
            "thought": "Observing screen to plan next action.",
            "commentary": "Analyzing the desktop to continue our task.",
            "actions": [],
            "step_completed": False,
            "task_finished": False,
            "updated_plan": []
        }
