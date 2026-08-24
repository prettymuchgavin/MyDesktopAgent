import os
import sys
import time
import json
import urllib.request
import urllib.parse
import subprocess
import re
from typing import Dict, Any, List, Optional
from modules.logger import setup_logger

logger = setup_logger("ToolManager")

DANGEROUS_PATTERNS = [
    r"rmdir\s+/[sq]",
    r"del\s+/[fs]",
    r"rm\s+-rf?",
    r"format\s+[a-z]:",
    r"drop\s+database",
    r"drop\s+table",
    r"remove-item\s+.*-recurse",
    r"shutdown\s+/[sr]",
    r"taskkill\s+/[fF]\s+/[iI][mM]\s+explorer\.exe",
    r"diskpart",
    r"bcdedit"
]

class DesktopToolManager:
    """High-speed desktop execution tools (Terminal Commands, Fast Web Search, Web Scraping, Filesystem)."""
    def __init__(self, config: Optional[Dict[str, Any]] = None, knowledge_manager=None):
        cfg = config or {}
        self.enable_commands = cfg.get("enable_terminal_commands", True)
        self.command_timeout = float(cfg.get("terminal_timeout_sec", 20.0))
        self.knowledge_manager = knowledge_manager
        self.last_tool_output: Optional[Dict[str, Any]] = None

    def update_config(self, config: Dict[str, Any]):
        self.enable_commands = config.get("enable_terminal_commands", self.enable_commands)
        self.command_timeout = float(config.get("terminal_timeout_sec", self.command_timeout))

    def is_dangerous_command(self, command: str) -> bool:
        """Detects potentially destructive commands that require safety confirmation."""
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return True
        return False

    def run_command(self, command: str, cwd: Optional[str] = None, timeout: Optional[float] = None, bypass_safety: bool = False) -> Dict[str, Any]:
        """Runs a PowerShell/CMD shell command with destructive command safety gating."""
        if not self.enable_commands:
            return {"status": "error", "error": "Terminal command execution is disabled in settings."}

        cmd_str = command.strip()
        if not cmd_str:
            return {"status": "error", "error": "Command string cannot be empty."}

        # Safety Gate Check
        if not bypass_safety and self.is_dangerous_command(cmd_str):
            logger.warning(f"🛡️ SAFETY GATE TRIGGERED: Blocked destructive command: '{cmd_str}'")
            return {
                "status": "safety_warning",
                "blocked": True,
                "error": f"🛡️ Safety Gate: Command '{cmd_str}' was blocked because it contains potentially destructive actions."
            }

        timeout_sec = timeout or self.command_timeout
        logger.info(f"💻 Running Terminal Command: '{cmd_str}' (timeout: {timeout_sec}s)")
        
        start_time = time.time()
        try:
            # Use PowerShell for rich Windows command set
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd_str],
                capture_output=True,
                text=True,
                cwd=cwd or os.getcwd(),
                timeout=timeout_sec
            )
            elapsed = round(time.time() - start_time, 2)
            stdout = proc.stdout.strip()
            stderr = proc.stderr.strip()
            
            # Truncate very long outputs to fit prompt budget
            if len(stdout) > 2500:
                stdout = stdout[:2500] + f"\n... [Output truncated ({len(stdout)} chars total)]"
            if len(stderr) > 1000:
                stderr = stderr[:1000] + "\n... [Stderr truncated]"

            result = {
                "status": "success" if proc.returncode == 0 else "failed",
                "exit_code": proc.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "elapsed_sec": elapsed
            }
            self.last_tool_output = result
            logger.info(f"Command finished in {elapsed}s (Exit code: {proc.returncode}). Output: {stdout[:80]}...")
            return result
        except subprocess.TimeoutExpired:
            logger.error(f"Command '{cmd_str}' timed out after {timeout_sec}s.")
            return {"status": "error", "error": f"Command timed out after {timeout_sec} seconds."}
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return {"status": "error", "error": str(e)}

    def web_search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Performs instant web search using DuckDuckGo HTML and returns top snippets in < 1 second."""
        logger.info(f"🌐 Fast Web Search: '{query}'")
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode("utf-8", errors="ignore")

            # Extract search snippets
            results = []
            snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', html, re.DOTALL)
            titles = re.findall(r'<a class="result__url[^>]*href="([^"]*)"[^>]*>(.*?)</a>', html, re.DOTALL)
            
            for i, snip in enumerate(snippets[:max_results]):
                clean_snip = re.sub(r'<[^>]+>', '', snip).strip()
                link = titles[i][0] if i < len(titles) else ""
                results.append({
                    "snippet": clean_snip,
                    "url": link
                })

            if not results:
                # Fallback simple text search
                clean_text = re.sub(r'<[^>]+>', ' ', html)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                results.append({"snippet": clean_text[:600], "url": url})

            result = {"status": "success", "query": query, "results": results}
            self.last_tool_output = result
            return result
        except Exception as e:
            logger.error(f"Web search error: {e}")
            return {"status": "error", "error": str(e)}

    def read_url(self, url: str, max_chars: int = 2500) -> Dict[str, Any]:
        """Fetches and extracts clean text content from a web URL directly."""
        logger.info(f"🌐 Fetching URL content: '{url}'")
        try:
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "https://" + url
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as response:
                html = response.read().decode("utf-8", errors="ignore")

            # Clean out scripts, styles, and HTML tags
            text = re.sub(r'<script.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<style.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            
            if len(text) > max_chars:
                text = text[:max_chars] + f"\n... [Truncated, {len(text)} chars total]"

            result = {"status": "success", "url": url, "content": text}
            self.last_tool_output = result
            return result
        except Exception as e:
            logger.error(f"Read URL error: {e}")
            return {"status": "error", "error": str(e)}

    def read_file(self, file_path: str, max_chars: int = 3500) -> Dict[str, Any]:
        """Reads local file content directly without opening GUI editors."""
        logger.info(f"📂 Reading File: '{file_path}'")
        try:
            if not os.path.exists(file_path):
                return {"status": "error", "error": f"File not found: {file_path}"}

            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(max_chars + 100)

            if len(content) > max_chars:
                content = content[:max_chars] + f"\n... [File truncated at {max_chars} chars]"

            result = {"status": "success", "path": file_path, "content": content}
            self.last_tool_output = result
            return result
        except Exception as e:
            logger.error(f"Read file error: {e}")
            return {"status": "error", "error": str(e)}

    def write_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """Writes or creates a local file directly with content."""
        logger.info(f"📝 Writing File: '{file_path}' ({len(content)} chars)")
        try:
            dir_name = os.path.dirname(file_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            result = {"status": "success", "path": file_path, "bytes_written": len(content)}
            self.last_tool_output = result
            return result
        except Exception as e:
            logger.error(f"Write file error: {e}")
            return {"status": "error", "error": str(e)}

    def list_directory(self, dir_path: str = ".") -> Dict[str, Any]:
        """Lists files and folders in a local directory."""
        logger.info(f"📂 Listing Directory: '{dir_path}'")
        try:
            target = os.path.abspath(dir_path)
            if not os.path.exists(target):
                return {"status": "error", "error": f"Directory not found: {target}"}
            items = []
            for item in os.listdir(target)[:40]:
                full_item = os.path.join(target, item)
                is_dir = os.path.isdir(full_item)
                size = os.path.getsize(full_item) if not is_dir else 0
                items.append({"name": item, "is_directory": is_dir, "size_bytes": size})
            result = {"status": "success", "path": target, "items": items}
            self.last_tool_output = result
            return result
        except Exception as e:
            logger.error(f"List directory error: {e}")
            return {"status": "error", "error": str(e)}

    def execute_tool(self, action_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Routes action dict to appropriate tool."""
        act_type = str(action_dict.get("action") or action_dict.get("type") or "").lower().strip()
        
        if act_type in ["run_command", "terminal", "command", "powershell", "cmd", "shell", "exec"]:
            cmd = action_dict.get("command") or action_dict.get("cmd") or action_dict.get("text") or ""
            return self.run_command(cmd, cwd=action_dict.get("cwd"))

        elif act_type in ["web_search", "search", "search_web", "google"]:
            query = action_dict.get("query") or action_dict.get("q") or action_dict.get("search") or ""
            return self.web_search(query)

        elif act_type in ["fetch_url", "read_url", "get_webpage", "scrape"]:
            url = action_dict.get("url") or action_dict.get("link") or ""
            return self.read_url(url)

        elif act_type in ["read_file", "view_file", "cat"]:
            path = action_dict.get("path") or action_dict.get("file") or action_dict.get("filename") or ""
            return self.read_file(path)

        elif act_type in ["write_file", "save_file", "create_file"]:
            path = action_dict.get("path") or action_dict.get("file") or ""
            content = action_dict.get("content") or action_dict.get("text") or ""
            return self.write_file(path, content)

        elif act_type in ["list_dir", "ls", "dir", "list_directory"]:
            path = action_dict.get("path") or action_dict.get("dir") or "."
            return self.list_directory(path)

        elif act_type in ["search_knowledge", "knowledge", "rag", "find_notes"]:
            query = action_dict.get("query") or action_dict.get("text") or ""
            if self.knowledge_manager:
                results = self.knowledge_manager.search(query)
                return {"status": "success", "query": query, "results": results}
            return {"status": "error", "error": "Knowledge manager not attached."}

        return {"status": "unknown_tool", "action": act_type}
