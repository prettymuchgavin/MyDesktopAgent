import os
import sys
import time
import json
import threading
import subprocess
import requests
from typing import Dict, Any, List, Optional
from modules.logger import setup_logger

logger = setup_logger("MCPClient")

class MCPServerConnection:
    """Represents a connection to an individual Model Context Protocol (MCP) server via Stdio or SSE/HTTP."""
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.transport_type = "stdio" if "command" in config else ("sse" if "url" in config else "stdio")
        
        self.process: Optional[subprocess.Popen] = None
        self.is_connected = False
        self.tools: List[Dict[str, Any]] = []
        self.resources: List[Dict[str, Any]] = []
        
        self._request_id = 0
        self._pending_requests: Dict[int, Any] = {}
        self._lock = threading.Lock()
        self._reader_thread: Optional[threading.Thread] = None

    def connect(self) -> bool:
        """Establishes connection and completes MCP protocol handshake."""
        if self.transport_type == "stdio":
            return self._connect_stdio()
        elif self.transport_type == "sse":
            return self._connect_sse()
        return False

    def _connect_stdio(self) -> bool:
        cmd = self.config.get("command")
        args = self.config.get("args", [])
        env = os.environ.copy()
        if "env" in self.config and isinstance(self.config["env"], dict):
            env.update({k: str(v) for k, v in self.config["env"].items()})

        full_cmd = [cmd] + args
        try:
            logger.info(f"🔌 Connecting to MCP Server '{self.name}' via Stdio: {' '.join(full_cmd)}")
            
            # Windows creation flags to prevent popup windows
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0x08000000

            self.process = subprocess.Popen(
                full_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=env,
                creationflags=creation_flags
            )

            # Start stdout reader thread
            self._reader_thread = threading.Thread(target=self._stdio_reader_loop, daemon=True)
            self._reader_thread.start()

            # 1. MCP Initialize Handshake
            init_res = self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": True},
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "MyDesktopAgent",
                    "version": "2.4.0"
                }
            }, timeout=15)

            if init_res:
                # 2. Send initialized notification
                self._send_notification("notifications/initialized", {})
                self.is_connected = True
                logger.info(f"✅ MCP Server '{self.name}' initialized successfully.")
                
                # 3. Discover Tools & Resources
                self.refresh_tools()
                return True
            else:
                logger.error(f"MCP Server '{self.name}' initialization response timed out.")
                return False

        except Exception as e:
            logger.error(f"Failed to start MCP server process '{self.name}': {e}")
            self.is_connected = False
            return False

    def _connect_sse(self) -> bool:
        """Connects to an HTTP/SSE MCP server endpoint."""
        url = self.config.get("url")
        logger.info(f"🔌 Connecting to MCP Server '{self.name}' via SSE/HTTP: {url}")
        try:
            # Simple HTTP JSON-RPC endpoint check
            res = requests.post(url, json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {"name": "MyDesktopAgent", "version": "2.4.0"}
                }
            }, timeout=10)
            if res.status_code == 200:
                self.is_connected = True
                self.refresh_tools()
                return True
        except Exception as e:
            logger.error(f"SSE MCP connection error '{self.name}': {e}")
        return False

    def _stdio_reader_loop(self):
        """Continuously reads JSON-RPC responses from stdout."""
        while self.process and self.process.poll() is None:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if not line or not line.startswith("{"):
                    continue
                data = json.loads(line)
                req_id = data.get("id")
                if req_id is not None and req_id in self._pending_requests:
                    event, result_box = self._pending_requests[req_id]
                    result_box["response"] = data
                    event.set()
            except Exception:
                pass
        self.is_connected = False

    def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None, timeout: float = 15.0) -> Optional[Dict[str, Any]]:
        """Sends JSON-RPC 2.0 request and waits for response."""
        with self._lock:
            self._request_id += 1
            req_id = self._request_id

        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {}
        }

        if self.transport_type == "stdio":
            if not self.process or self.process.poll() is not None:
                return None
            event = threading.Event()
            result_box = {}
            self._pending_requests[req_id] = (event, result_box)
            try:
                self.process.stdin.write(json.dumps(payload) + "\n")
                self.process.stdin.flush()
                if event.wait(timeout=timeout):
                    resp = result_box.get("response", {})
                    return resp.get("result")
            except Exception as e:
                logger.error(f"Error sending request to MCP '{self.name}': {e}")
            finally:
                self._pending_requests.pop(req_id, None)

        elif self.transport_type == "sse":
            try:
                url = self.config.get("url")
                res = requests.post(url, json=payload, timeout=timeout)
                if res.status_code == 200:
                    return res.json().get("result")
            except Exception as e:
                logger.error(f"Error calling SSE MCP server '{self.name}': {e}")

        return None

    def _send_notification(self, method: str, params: Optional[Dict[str, Any]] = None):
        """Sends one-way JSON-RPC notification (no response expected)."""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        if self.transport_type == "stdio" and self.process:
            try:
                self.process.stdin.write(json.dumps(payload) + "\n")
                self.process.stdin.flush()
            except Exception:
                pass

    def refresh_tools(self) -> List[Dict[str, Any]]:
        """Queries the server for available tools (tools/list)."""
        res = self._send_request("tools/list", {})
        if res and "tools" in res:
            self.tools = res["tools"]
            logger.info(f"🛠️ MCP Server '{self.name}' provides {len(self.tools)} tools: {[t.get('name') for t in self.tools]}")
        return self.tools

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Executes an MCP tool on this server."""
        logger.info(f"⚡ Executing MCP Tool '{self.name}/{tool_name}' with args: {arguments}")
        start_time = time.time()
        res = self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments
        }, timeout=30.0)
        elapsed = round(time.time() - start_time, 2)
        
        if res is not None:
            content_list = res.get("content", [])
            text_outputs = []
            for item in content_list:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_outputs.append(item.get("text", ""))
                elif isinstance(item, str):
                    text_outputs.append(item)
            
            output_text = "\n".join(text_outputs) if text_outputs else json.dumps(res, indent=2)
            return {
                "status": "success",
                "server": self.name,
                "tool": tool_name,
                "output": output_text,
                "raw_result": res,
                "elapsed_sec": elapsed
            }
        else:
            return {
                "status": "error",
                "server": self.name,
                "tool": tool_name,
                "error": f"Tool call timed out or failed on MCP server '{self.name}'."
            }

    def disconnect(self):
        self.is_connected = False
        if self.process:
            try:
                self.process.terminate()
            except Exception:
                pass
            self.process = None

class MCPClientManager:
    """Manages all registered MCP servers, tool discovery, and routing for My Desktop Agent."""
    def __init__(self, mcp_servers_config: Optional[Dict[str, Any]] = None):
        self.servers: Dict[str, MCPServerConnection] = {}
        self.config = mcp_servers_config or {}
        self.init_servers()

    def update_config(self, mcp_servers_config: Dict[str, Any]):
        self.config = mcp_servers_config
        self.init_servers()

    def init_servers(self):
        """Initializes and connects to all configured MCP servers."""
        # Stop existing connections
        for s in self.servers.values():
            s.disconnect()
        self.servers = {}

        if not self.config:
            logger.info("No MCP servers configured.")
            return

        for name, cfg in self.config.items():
            if not isinstance(cfg, dict):
                continue
            conn = MCPServerConnection(name, cfg)
            self.servers[name] = conn
            # Connect in background thread to avoid blocking startup
            threading.Thread(target=conn.connect, daemon=True).start()

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Returns all tools from all connected MCP servers."""
        all_tools = []
        for s_name, server in self.servers.items():
            if server.is_connected:
                for t in server.tools:
                    tool_copy = dict(t)
                    tool_copy["server"] = s_name
                    all_tools.append(tool_copy)
        return all_tools

    def get_servers_status(self) -> List[Dict[str, Any]]:
        status_list = []
        for name, server in self.servers.items():
            status_list.append({
                "name": name,
                "transport": server.transport_type,
                "connected": server.is_connected,
                "tools_count": len(server.tools),
                "tools": [t.get("name") for t in server.tools]
            })
        return status_list

    def call_tool(self, tool_name: str, arguments: Dict[str, Any], server_name: Optional[str] = None) -> Dict[str, Any]:
        """Calls a tool on a specific server or searches across servers."""
        # If server specified
        if server_name and server_name in self.servers:
            return self.servers[server_name].call_tool(tool_name, arguments)

        # Otherwise look for the server providing this tool
        for s_name, server in self.servers.items():
            if server.is_connected:
                for t in server.tools:
                    if t.get("name") == tool_name:
                        return server.call_tool(tool_name, arguments)

        return {"status": "error", "error": f"MCP tool '{tool_name}' not found on any connected server."}

    def add_server(self, name: str, server_config: Dict[str, Any], config_path: str = "config.yaml") -> Dict[str, Any]:
        """Dynamically adds or updates an MCP server, connects immediately, and persists to config.yaml."""
        if not name or not isinstance(server_config, dict):
            return {"status": "error", "error": "Invalid server name or configuration."}

        # Disconnect existing if replacing
        if name in self.servers:
            self.servers[name].disconnect()

        # Connect new server
        conn = MCPServerConnection(name, server_config)
        self.servers[name] = conn
        success = conn.connect()

        self.config[name] = server_config
        self._persist_to_yaml(config_path)

        return {
            "status": "success" if success else "connected_with_warnings",
            "server": name,
            "connected": conn.is_connected,
            "tools_count": len(conn.tools),
            "tools": [t.get("name") for t in conn.tools],
            "message": f"MCP Server '{name}' added successfully with {len(conn.tools)} tools." if success else f"MCP Server '{name}' added but handshake did not complete."
        }

    def remove_server(self, name: str, config_path: str = "config.yaml") -> Dict[str, Any]:
        """Disconnects and removes an MCP server, and updates config.yaml."""
        if name not in self.servers and name not in self.config:
            return {"status": "not_found", "error": f"MCP server '{name}' does not exist."}

        if name in self.servers:
            self.servers[name].disconnect()
            del self.servers[name]

        if name in self.config:
            del self.config[name]

        self._persist_to_yaml(config_path)
        return {"status": "success", "message": f"MCP Server '{name}' removed successfully."}

    def _persist_to_yaml(self, config_path: str = "config.yaml"):
        """Saves current mcp_servers to config.yaml safely preserving other config keys."""
        try:
            import yaml
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    existing_cfg = yaml.safe_load(f) or {}
            else:
                existing_cfg = {}

            existing_cfg["mcp_servers"] = self.config
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(existing_cfg, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"💾 Persisted {len(self.config)} MCP servers to {config_path}")
        except Exception as e:
            logger.error(f"Failed to persist MCP servers to {config_path}: {e}")

    def get_mcp_prompt_context(self) -> str:
        """Builds prompt documentation of all currently active MCP tools for the LLM."""
        tools = self.get_all_tools()
        if not tools:
            return ""

        lines = ["--- CONNECTED MCP (MODEL CONTEXT PROTOCOL) TOOLS ---"]
        lines.append("You can call any of the following external MCP tools using action: 'mcp_tool':")
        lines.append("Format: {\"action\": \"mcp_tool\", \"server\": \"<server_name>\", \"tool\": \"<tool_name>\", \"arguments\": {...}}\n")

        for t in tools:
            name = t.get("name")
            server = t.get("server")
            desc = t.get("description", "No description")
            schema = t.get("inputSchema", {})
            properties = schema.get("properties", {})
            param_names = list(properties.keys())
            lines.append(f"• Tool: `{server}/{name}`")
            lines.append(f"  Description: {desc}")
            if param_names:
                lines.append(f"  Parameters: {param_names}")
            lines.append("")

        lines.append("---------------------------------------------------")
        return "\n".join(lines)
