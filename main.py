import os
import sys
import time
import threading
import argparse
import subprocess
import requests
import yaml
import uvicorn
import multiprocessing
import webbrowser
from modules.logger import setup_logger
from modules.tray_manager import SystemTrayManager

logger = setup_logger("Main")

PID_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "agent.pid")

try:
    import webview
    HAS_WEBVIEW = True
except ImportError:
    HAS_WEBVIEW = False

class ServerThread(threading.Thread):
    def __init__(self, host: str, port: int):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.server = None

    def run(self):
        try:
            from web.app import app
            config = uvicorn.Config(app=app, host=self.host, port=self.port, reload=False, log_level="warning")
            self.server = uvicorn.Server(config)
            self.server.run()
        except Exception as e:
            logger.error(f"Uvicorn ServerThread error: {e}")

    def stop(self):
        if self.server:
            self.server.should_exit = True

def wait_for_server_ready(host: str, port: int, timeout: float = 20.0) -> bool:
    """Polls local backend to ensure the server is ready before launching the native UI."""
    start_time = time.time()
    url = f"http://{host}:{port}/api/status"
    while time.time() - start_time < timeout:
        try:
            res = requests.get(url, timeout=1.0)
            if res.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.25)
    return False

def spawn_detached_background_process() -> int:
    """Spawns a detached pythonw background process completely independent of this terminal."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    python_dir = os.path.dirname(sys.executable)
    pythonw_exe = os.path.join(python_dir, "pythonw.exe")
    if not os.path.exists(pythonw_exe):
        pythonw_exe = sys.executable

    main_py = os.path.join(base_dir, "main.py")
    cmd = [pythonw_exe, main_py, "--background-worker"]

    DETACHED_PROCESS = 0x00000008
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    CREATE_NO_WINDOW = 0x08000000
    flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW

    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)

    proc = subprocess.Popen(
        cmd,
        cwd=base_dir,
        creationflags=flags,
        close_fds=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL
    )
    
    with open(PID_FILE, "w", encoding="utf-8") as f:
        f.write(str(proc.pid))

    return proc.pid

def stop_background_process():
    """Stops any currently running detached background process."""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r", encoding="utf-8") as f:
                pid_str = f.read().strip()
                if pid_str.isdigit():
                    pid = int(pid_str)
                    subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
                    print(f"🛑 Stopped background agent process (PID: {pid}).")
            os.remove(PID_FILE)
            return
        except Exception as e:
            print(f"Could not kill PID: {e}")
    
    # Also stop via local API if online
    try:
        requests.post("http://127.0.0.1:8000/api/stop", timeout=2)
    except Exception:
        pass
    print("Background agent stopped.")

def main():
    multiprocessing.freeze_support()
    
    parser = argparse.ArgumentParser(description="My Desktop Agent")
    parser.add_argument("command", nargs="?", default=None, choices=["config", "setup", "start", "stop", "status", None], help="Subcommand to execute")
    parser.add_argument("--config", "-c", action="store_true", help="Launch interactive configuration manager")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address")
    parser.add_argument("--port", type=int, default=8000, help="Port")
    parser.add_argument("--web-only", action="store_true", help="Run only as web server without native PC window")
    parser.add_argument("--background", "-b", "--tray", action="store_true", help="Launch in background taskbar system tray and detach from terminal")
    parser.add_argument("--background-worker", action="store_true", help="Internal worker flag for detached background execution")
    parser.add_argument("--setup", action="store_true", help="Run interactive terminal setup wizard")
    args = parser.parse_args()

    if args.command == "stop":
        stop_background_process()
        return

    if args.command == "config" or args.config:
        import config_editor
        config_editor.run_config_menu()
        return

    if args.command == "setup" or args.setup:
        import setup
        setup.main()
        return

    # If user ran --background from terminal, spawn detached process and exit terminal immediately!
    if args.background and not args.background_worker:
        pid = spawn_detached_background_process()
        print("=" * 70)
        print(f"🚀 MY DESKTOP AGENT STARTED IN BACKGROUND (PID: {pid})")
        print("=" * 70)
        print("• The agent icon is now active in your Windows System Tray (Taskbar area).")
        print("  (Look near your clock or inside the '^' taskbar overflow arrow)")
        print("• You can safely CLOSE this terminal window at any time!")
        print("• Telegram remote activation is listening for messages from your phone.")
        print("• To open dashboard: click the tray icon or run 'agent'.")
        print("• To stop background agent: run 'agent stop'.")
        print("=" * 70)
        sys.exit(0)

    # Determine config file path
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        config_path = os.path.join(exe_dir, "config.yaml")
    else:
        config_path = os.path.join(base_dir, "config.yaml")

    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
                web_cfg = cfg.get("web_dashboard", {})
                host = args.host or web_cfg.get("host", "127.0.0.1")
                port = args.port or web_cfg.get("port", 8000)
        except Exception:
            host = args.host
            port = args.port
    else:
        host = args.host
        port = args.port

    logger.info("=" * 65)
    logger.info("🖥️  MY DESKTOP AGENT - AUTONOMOUS ASSISTANT")
    logger.info(f"🌐 Local Backend Service: http://{host}:{port}")
    logger.info("=" * 65)

    # 1. Start Web & API backend server in background
    logger.info("Starting local backend server...")
    server_thread = ServerThread(host=host, port=port)
    server_thread.start()

    # 2. Wait for backend to be fully online
    is_ready = wait_for_server_ready(host=host, port=port, timeout=20.0)
    if is_ready:
        logger.info(f"✅ Backend server online at http://{host}:{port}")
    else:
        logger.warning("Backend server startup timed out, proceeding with window launch...")

    from web.app import orchestrator

    def open_dashboard_url():
        webbrowser.open(f"http://{host}:{port}")

    def quit_application():
        logger.info("Stopping My Desktop Agent completely...")
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except Exception:
                pass
        orchestrator.shutdown()
        server_thread.stop()
        sys.exit(0)

    # 3. Create System Tray Manager
    tray = SystemTrayManager(
        orchestrator_ref=orchestrator,
        open_window_callback=open_dashboard_url,
        quit_callback=quit_application,
        host=host,
        port=port
    )

    # 4. Handle Detached Background Worker Mode
    if args.background_worker:
        logger.info("🕶️ Running in Detached System Tray Mode (Win32 tray message loop active).")
        # Run tray loop on main thread to guarantee Windows Shell tray registration
        tray.run()
        return

    # If running with GUI window, start tray in background thread
    tray.start_in_thread()

    # 5. Launch Native PC Desktop App Window (WebView2)
    if HAS_WEBVIEW and not args.web_only:
        try:
            logger.info("🚀 Launching My Desktop Agent Window...")
            window = webview.create_window(
                title="My Desktop Agent",
                url=f"http://{host}:{port}",
                width=1420,
                height=920,
                min_size=(1050, 680),
                background_color="#0b0d12",
                resizable=True,
                confirm_close=False
            )
            webview.start()
            logger.info("Desktop window closed. Agent is now running in the System Tray.")
            tray.notify("My Desktop Agent", "Minimized to System Tray. Telegram remote activation is active.")
            
            # Keep running in background tray after window close
            while True:
                time.sleep(1)
        except Exception as e:
            logger.error(f"Could not open native window: {e}. Falling back to browser view.")

    # 6. Fallback: Keep running in background
    logger.info(f"Running in background. Open http://{host}:{port} in your browser.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        quit_application()

if __name__ == "__main__":
    main()
