import os
import sys
import time
import yaml
import asyncio
from typing import Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from modules.orchestrator import DesktopAgentOrchestrator
from modules.logger import setup_logger, dashboard_log_queue

logger = setup_logger("WebApp")

def resolve_config_path() -> str:
    if getattr(sys, 'frozen', False):
        exe_dir_cfg = os.path.join(os.path.dirname(sys.executable), "config.yaml")
        if os.path.exists(exe_dir_cfg):
            return exe_dir_cfg
    project_cfg = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config.yaml"))
    if os.path.exists(project_cfg):
        return project_cfg
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        bundle_cfg = os.path.join(sys._MEIPASS, "config.yaml")
        if os.path.exists(bundle_cfg):
            return bundle_cfg
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "config.yaml"))

def resolve_static_dir() -> str:
    if hasattr(sys, '_MEIPASS'):
        meipass_static = os.path.join(sys._MEIPASS, "web", "static")
        if os.path.exists(meipass_static):
            return meipass_static
        meipass_static2 = os.path.join(sys._MEIPASS, "static")
        if os.path.exists(meipass_static2):
            return meipass_static2
    if getattr(sys, 'frozen', False):
        exe_static = os.path.join(os.path.dirname(sys.executable), "web", "static")
        if os.path.exists(exe_static):
            return exe_static
        exe_static2 = os.path.join(os.path.dirname(sys.executable), "static")
        if os.path.exists(exe_static2):
            return exe_static2
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))

CONFIG_PATH = resolve_config_path()

def load_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Error loading config from {CONFIG_PATH}: {e}")
    return {}

def save_config(cfg: Dict[str, Any]):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, default_flow_style=False)

app = FastAPI(title="AI Streamer Web Control Panel")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global orchestrator instance
config_data = load_config()
orchestrator = DesktopAgentOrchestrator(config_data)

static_dir = resolve_static_dir()
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_root():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h2>My Desktop Agent (Ready)</h2>")

@app.get("/api/status")
def get_status():
    status = orchestrator.get_status()
    status["config"] = orchestrator.config
    return status

@app.get("/api/models")
def get_models():
    models = orchestrator.llm.get_installed_models()
    return {"models": models}

@app.post("/api/start")
def start_agent():
    orchestrator.start()
    return {"status": "started"}

@app.post("/api/stop")
def stop_agent():
    orchestrator.stop()
    return {"status": "stopped"}

def generate_live_stream_frames():
    while True:
        frame_bytes = orchestrator.desktop_agent.capture_screen_jpeg(max_size=(480, 480), quality=50)
        if frame_bytes:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.1) # Gentle 10 FPS rate prevents GDI DC lock cursor flicker

@app.get("/api/live_feed")
def get_live_feed():
    """Streams live desktop video feed on-demand."""
    return StreamingResponse(
        generate_live_stream_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/api/vision_snapshot")
def get_vision_snapshot():
    b64 = orchestrator.desktop_agent.last_screenshot_b64
    if b64:
        return {"image_b64": b64}
    return {"image_b64": None}

class ConfigUpdateRequest(BaseModel):
    config: Dict[str, Any]

@app.post("/api/update_config")
def update_config(req: ConfigUpdateRequest):
    try:
        new_cfg = req.config
        save_config(new_cfg)
        orchestrator.update_config(new_cfg)
        return {"status": "success", "message": "Configuration updated and saved."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class EnhancePromptRequest(BaseModel):
    prompt: Optional[str] = ""
    agent_name: Optional[str] = "Carl"

@app.post("/api/enhance_prompt")
def enhance_prompt(req: EnhancePromptRequest):
    try:
        enhanced = orchestrator.llm.enhance_system_prompt(req.prompt or "", req.agent_name or "Carl")
        return {"status": "success", "enhanced_prompt": enhanced}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class AddMemoryRequest(BaseModel):
    category: str
    item_text: str
    user: Optional[str] = "Host"

@app.get("/api/memory")
def get_memory():
    return orchestrator.memory_manager.get_all_memory()

@app.post("/api/memory/clear")
def clear_memory():
    orchestrator.memory_manager.clear_all_memory()
    return {"status": "success", "message": "Memory cleared."}

class StartTaskRequest(BaseModel):
    goal: str

@app.post("/api/task/start")
def start_task(req: StartTaskRequest):
    if not req.goal.strip():
        raise HTTPException(status_code=400, detail="Goal cannot be empty.")
    result = orchestrator.start_task(req.goal.strip())
    return {"status": "started", "task": result}

@app.post("/api/task/stop")
def stop_task():
    orchestrator.stop_task()
    return {"status": "stopped"}

@app.post("/api/task/pause")
def pause_task():
    orchestrator.pause_task()
    return {"status": "paused"}

@app.post("/api/task/resume")
def resume_task():
    orchestrator.resume_task()
    return {"status": "resumed"}

@app.get("/api/task/status")
def get_task_status():
    return orchestrator.task_executor.get_status()

# --- Skills API ---
@app.get("/api/skills")
def get_skills():
    return {"skills": orchestrator.skill_manager.get_all_skills()}

# --- Schedules API ---
@app.get("/api/schedules")
def get_schedules():
    return {"schedules": orchestrator.scheduler.list_schedules()}

class AddScheduleRequest(BaseModel):
    goal: str
    time: str
    recurring: Optional[bool] = True

@app.post("/api/schedules/add")
def add_schedule(req: AddScheduleRequest):
    item = orchestrator.scheduler.add_schedule(req.goal, req.time, recurring=req.recurring)
    return {"status": "success", "schedule": item}

@app.post("/api/schedules/delete/{schedule_id}")
def delete_schedule(schedule_id: str):
    res = orchestrator.scheduler.delete_schedule(schedule_id)
    return {"status": "success" if res else "not_found"}

# --- Monitors API ---
@app.get("/api/monitors")
def get_monitors():
    return {
        "monitors": orchestrator.desktop_agent.list_monitors(),
        "active_monitor": orchestrator.desktop_agent.active_monitor_idx
    }

class SwitchMonitorRequest(BaseModel):
    index: int

@app.post("/api/monitors/switch")
def switch_monitor(req: SwitchMonitorRequest):
    orchestrator.desktop_agent.switch_monitor(req.index)
    return {"status": "success", "active_monitor": req.index}

# --- Knowledge Base API ---
class SearchKnowledgeRequest(BaseModel):
    query: str

@app.post("/api/knowledge/search")
def search_knowledge(req: SearchKnowledgeRequest):
    results = orchestrator.knowledge_manager.search(req.query)
    return {"results": results}

# --- MCP (Model Context Protocol) API ---
@app.get("/api/mcp/servers")
def get_mcp_servers():
    return {
        "servers": orchestrator.mcp_manager.get_servers_status(),
        "tools": orchestrator.mcp_manager.get_all_tools()
    }

class MCPCallRequest(BaseModel):
    tool: str
    arguments: Optional[Dict[str, Any]] = None
    server: Optional[str] = None

@app.post("/api/mcp/call")
def call_mcp_tool(req: MCPCallRequest):
    res = orchestrator.mcp_manager.call_tool(req.tool, req.arguments or {}, server_name=req.server)
    return res

class AddMCPServerRequest(BaseModel):
    name: str
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    url: Optional[str] = None

@app.post("/api/mcp/add")
def api_add_mcp_server(req: AddMCPServerRequest):
    cfg = {}
    if req.url:
        cfg["url"] = req.url
    elif req.command:
        cfg["command"] = req.command
        cfg["args"] = req.args or []
        if req.env:
            cfg["env"] = req.env
    return orchestrator.mcp_manager.add_server(req.name, cfg)

class RemoveMCPServerRequest(BaseModel):
    name: str

@app.post("/api/mcp/remove")
def api_remove_mcp_server(req: RemoveMCPServerRequest):
    return orchestrator.mcp_manager.remove_server(req.name)

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    last_idx = 0
    try:
        while True:
            current_logs = list(dashboard_log_queue)
            if len(current_logs) > last_idx:
                new_items = current_logs[last_idx:]
                last_idx = len(current_logs)
                await websocket.send_json({"type": "logs", "data": new_items})
            
            # Send current status update periodically
            status = orchestrator.get_status()
            await websocket.send_json({"type": "status", "data": status})
            
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
