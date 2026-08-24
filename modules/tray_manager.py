import os
import sys
import threading
import time
import webbrowser
from typing import Optional, Callable
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item
from modules.logger import setup_logger

logger = setup_logger("TrayManager")

def create_tray_icon_image() -> Image.Image:
    """Generates a high-visibility, modern 64x64 robot assistant icon for the Windows system tray."""
    img = Image.new("RGBA", (64, 64), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Outer rounded background
    draw.rounded_rectangle([2, 2, 62, 62], radius=16, fill=(30, 27, 75, 255), outline=(99, 102, 241, 255), width=3)
    
    # Inner robot face / screen
    draw.rounded_rectangle([12, 16, 52, 48], radius=8, fill=(15, 23, 42, 255), outline=(56, 189, 248, 255), width=2)
    
    # Glowing bright eyes (cyan)
    draw.ellipse([18, 24, 28, 34], fill=(56, 189, 248, 255))
    draw.ellipse([36, 24, 46, 34], fill=(56, 189, 248, 255))
    
    # Antenna
    draw.line([32, 2, 32, 16], fill=(99, 102, 241, 255), width=4)
    draw.ellipse([27, 0, 37, 10], fill=(236, 72, 153, 255))
    
    return img

class SystemTrayManager:
    """Manages the Windows taskbar system tray icon, notifications, and menu."""
    def __init__(self, orchestrator_ref=None, open_window_callback: Optional[Callable] = None, quit_callback: Optional[Callable] = None, host: str = "127.0.0.1", port: int = 8000):
        self.orchestrator = orchestrator_ref
        self.open_window_callback = open_window_callback
        self.quit_callback = quit_callback
        self.host = host
        self.port = port
        self.icon: Optional[pystray.Icon] = None
        self._build_icon()

    def _build_icon(self):
        icon_img = create_tray_icon_image()
        
        menu = pystray.Menu(
            item("🖥️ Open Dashboard", self._on_open_dashboard, default=True),
            pystray.Menu.SEPARATOR,
            item(lambda text: self._get_status_text(), self._on_toggle_agent),
            item(lambda text: self._get_telegram_text(), lambda icon, item: None, enabled=False),
            pystray.Menu.SEPARATOR,
            item("⚙️ Configure Agent (agent config)", self._on_open_config),
            item("🌐 Open in Browser", lambda icon, item: webbrowser.open(f"http://{self.host}:{self.port}")),
            pystray.Menu.SEPARATOR,
            item("🚪 Exit My Desktop Agent", self._on_quit)
        )
        
        self.icon = pystray.Icon(
            "MyDesktopAgent",
            icon_img,
            "My Desktop Agent (Ready)",
            menu=menu
        )

    def run(self):
        """Runs the system tray icon on the main thread (blocking, runs Win32 message loop)."""
        if not self.icon:
            self._build_icon()
        logger.info("System Tray Win32 message loop starting on main thread...")
        self.icon.run(setup=self._on_setup)

    def start_in_thread(self):
        """Starts the tray icon in a dedicated background thread."""
        if not self.icon:
            self._build_icon()
        t = threading.Thread(target=self.icon.run, kwargs={"setup": self._on_setup}, daemon=True)
        t.start()
        logger.info("System Tray background thread started.")

    def _on_setup(self, icon):
        icon.visible = True
        try:
            icon.notify("My Desktop Agent is running in your taskbar system tray.\nTelegram remote activation is active.", "My Desktop Agent")
        except Exception:
            pass

    def stop(self):
        if self.icon:
            self.icon.stop()

    def notify(self, title: str, message: str):
        """Shows a Windows system notification toast."""
        if self.icon:
            try:
                self.icon.notify(message, title)
            except Exception as e:
                logger.warning(f"Could not send tray notification: {e}")

    def _get_status_text(self) -> str:
        if self.orchestrator:
            status = self.orchestrator.get_status()
            if status.get("is_running"):
                return "Agent: 🟢 Active"
            return "Agent: 🔴 Standby (OFF)"
        return "Agent: Ready"

    def _get_telegram_text(self) -> str:
        if self.orchestrator and hasattr(self.orchestrator, "telegram"):
            if self.orchestrator.telegram.enabled:
                return "Telegram: 📱 Listening for Messages"
            return "Telegram: ⚪ Disabled"
        return "Telegram: Ready"

    def _on_open_dashboard(self, icon, item):
        if self.open_window_callback:
            self.open_window_callback()
        else:
            webbrowser.open(f"http://{self.host}:{self.port}")

    def _on_open_config(self, icon, item):
        python_exe = sys.executable
        main_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))
        os.system(f'start cmd /k ""{python_exe}" "{main_py}" config"')

    def _on_toggle_agent(self, icon, item):
        if self.orchestrator:
            if self.orchestrator.is_running:
                self.orchestrator.stop()
                self.notify("My Desktop Agent", "Agent is now in Standby (OFF).")
            else:
                self.orchestrator.start()
                self.notify("My Desktop Agent", "Agent turned ON (Active).")

    def _on_quit(self, icon, item):
        logger.info("Quitting My Desktop Agent from System Tray menu...")
        if self.icon:
            self.icon.stop()
        if self.quit_callback:
            self.quit_callback()
        else:
            if self.orchestrator:
                self.orchestrator.shutdown()
            os._exit(0)
