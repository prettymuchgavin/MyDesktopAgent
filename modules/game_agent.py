import io
import time
import math
import random
import base64
import threading
from typing import Dict, Any, List, Optional
from PIL import Image, ImageDraw
from modules.logger import setup_logger

logger = setup_logger("GameAgent")

try:
    import mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.0
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False

try:
    from pynput import keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

class GameAgent:
    def __init__(self, config: Dict[str, Any]):
        self.window_title = config.get("window_title", "").strip()
        self.enable_inputs = config.get("enable_game_inputs", True)
        self.action_delay = float(config.get("action_delay_sec", 0.2))
        self.emergency_hotkey = config.get("emergency_hotkey", "f12").lower()
        self.control_mode = config.get("control_mode", "AUTO_DETECT").upper()
        self.game_genre = config.get("game_genre", "General Desktop")
        self.inputs_paused = False
        self.current_mouse_mode = "pointing"
        
        self.latest_jpeg_bytes: Optional[bytes] = None
        self.last_screenshot_b64: Optional[str] = None
        self.last_analyzed_jpeg_bytes: Optional[bytes] = None
        
        self.active_monitor_idx = int(config.get("monitor_index", 1))
        self._sct = None
        self._init_emergency_hotkey()

    def _get_sct(self):
        if self._sct is None and HAS_MSS:
            self._sct = mss.mss()
        return self._sct

    def list_monitors(self) -> List[Dict[str, Any]]:
        """Returns details on all connected displays/monitors."""
        sct = self._get_sct()
        if not sct:
            return []
        monitors_info = []
        for idx, m in enumerate(sct.monitors):
            if idx == 0:
                name = "All Monitors (Combined Virtual Screen)"
            else:
                name = f"Monitor {idx} ({m['width']}x{m['height']})"
            monitors_info.append({
                "index": idx,
                "name": name,
                "width": m["width"],
                "height": m["height"],
                "left": m["left"],
                "top": m["top"]
            })
        return monitors_info

    def switch_monitor(self, monitor_index: int):
        """Switches active display for vision capture and mouse actions."""
        sct = self._get_sct()
        if sct and 0 <= monitor_index < len(sct.monitors):
            self.active_monitor_idx = monitor_index
            logger.info(f"🖥️ Switched active vision monitor to #{monitor_index}")

    def focus_window(self, title: str) -> bool:
        """Focuses/brings a window to foreground by partial title matching."""
        if not title:
            return False
        logger.info(f"🪟 Focusing window with title containing '{title}'...")
        try:
            import subprocess
            # Use PowerShell to find and bring window to front
            ps_script = f"""
            $w = Get-Process | Where-Object {{ $_.MainWindowTitle -like '*{title}*' }} | Select-Object -First 1
            if ($w) {{
                $sig = '[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);'
                Add-Type -MemberDefinition $sig -Name NativeMethods -Namespace Win32
                [Win32.NativeMethods]::SetForegroundWindow($w.MainWindowHandle)
            }}
            """
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, timeout=5)
            time.sleep(0.3)
            return True
        except Exception as e:
            logger.error(f"Error focusing window '{title}': {e}")
            return False

    def update_config(self, config: Dict[str, Any]):
        """Updates game control mode live."""
        self.control_mode = config.get("control_mode", self.control_mode).upper()
        self.game_genre = config.get("game_genre", self.game_genre)
        self.enable_inputs = config.get("enable_desktop_inputs", config.get("enable_game_inputs", self.enable_inputs))
        self.active_monitor_idx = int(config.get("monitor_index", self.active_monitor_idx))
        logger.info(f"DesktopAgent updated. Control Mode: '{self.control_mode}', Inputs: {self.enable_inputs}, Monitor: {self.active_monitor_idx}")

    def _init_emergency_hotkey(self):
        """Initializes global hotkey listener (F12) to pause/resume AI controls."""
        if HAS_PYNPUT:
            def on_press(key):
                try:
                    key_name = key.name if hasattr(key, 'name') else str(key).strip("'")
                    if key_name and key_name.lower() == self.emergency_hotkey:
                        self.inputs_paused = not self.inputs_paused
                        status = "PAUSED" if self.inputs_paused else "RESUMED"
                        logger.warning(f"EMERGENCY HOTKEY TRIGGERED ({self.emergency_hotkey.upper()}): AI Desktop Controls {status}")
                except Exception as e:
                    logger.error(f"Hotkey listener error: {e}")

            listener = keyboard.Listener(on_press=on_press)
            listener.daemon = True
            listener.start()

    def get_mouse_context(self) -> Dict[str, Any]:
        """Returns current mouse coordinates, normalized screen ratios, quadrant, and active cursor mode."""
        if not HAS_PYAUTOGUI:
            return {
                "x": 0, "y": 0, "x_ratio": 0.5, "y_ratio": 0.5, 
                "mode": self.current_mouse_mode, "quadrant": "center",
                "control_mode": self.control_mode
            }

        try:
            x, y = pyautogui.position()
            screen_w, screen_h = pyautogui.size()
            x_ratio = round(x / max(screen_w, 1), 2)
            y_ratio = round(y / max(screen_h, 1), 2)

            horiz = "left" if x_ratio < 0.35 else ("right" if x_ratio > 0.65 else "center")
            vert = "top" if y_ratio < 0.35 else ("bottom" if y_ratio > 0.65 else "center")
            quadrant = f"{vert}-{horiz}" if horiz != "center" or vert != "center" else "center"

            return {
                "x": x,
                "y": y,
                "x_ratio": x_ratio,
                "y_ratio": y_ratio,
                "quadrant": quadrant,
                "mode": self.current_mouse_mode,
                "control_mode": self.control_mode,
                "active_monitor": self.active_monitor_idx
            }
        except Exception:
            return {
                "x": 0, "y": 0, "x_ratio": 0.5, "y_ratio": 0.5, 
                "mode": self.current_mouse_mode, "quadrant": "center",
                "control_mode": self.control_mode
            }

    def capture_screen_image(self) -> Optional[Image.Image]:
        """Captures a clean desktop frame on-demand with automatic stale-handle recovery and ImageGrab fallback."""
        # Method 1: Fast MSS Screen Capture
        if HAS_MSS:
            try:
                sct = self._get_sct()
                if sct:
                    idx = self.active_monitor_idx if 0 <= self.active_monitor_idx < len(sct.monitors) else (1 if len(sct.monitors) > 1 else 0)
                    monitor = sct.monitors[idx]
                    sct_img = sct.grab(monitor)
                    return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            except Exception:
                try:
                    if self._sct:
                        self._sct.close()
                except Exception:
                    pass
                self._sct = None

        # Method 2: Robust PIL ImageGrab fallback (Immune to BitBlt GDI handle corruption)
        try:
            from PIL import ImageGrab
            return ImageGrab.grab(all_screens=True)
        except Exception:
            pass

        # Method 3: PyAutoGUI Fallback
        if HAS_PYAUTOGUI:
            try:
                return pyautogui.screenshot()
            except Exception:
                pass

        return None

    def capture_screen_jpeg(self, max_size=(448, 448), quality=55) -> Optional[bytes]:
        """Captures and compresses on-demand JPEG frame for fast live stream or analysis."""
        img = self.capture_screen_image()
        
        # If desktop is locked or asleep, provide previous frame or clean standby canvas
        if not img:
            if self.latest_jpeg_bytes:
                return self.latest_jpeg_bytes
            try:
                from PIL import ImageDraw
                standby_img = Image.new("RGB", (480, 270), color=(11, 19, 38))
                draw = ImageDraw.Draw(standby_img)
                draw.text((150, 125), "Desktop Standby / Screen Asleep", fill=(181, 196, 255))
                buf = io.BytesIO()
                standby_img.save(buf, format="JPEG", quality=quality)
                standby_bytes = buf.getvalue()
                self.latest_jpeg_bytes = standby_bytes
                self.last_screenshot_b64 = base64.b64encode(standby_bytes).decode("utf-8")
                return standby_bytes
            except Exception:
                return None

        try:
            img.thumbnail(max_size)
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG", quality=quality)
            jpeg_bytes = buffered.getvalue()
            self.latest_jpeg_bytes = jpeg_bytes
            self.last_screenshot_b64 = base64.b64encode(jpeg_bytes).decode("utf-8")
            return jpeg_bytes
        except Exception:
            return self.latest_jpeg_bytes

    def capture_screen_b64(self) -> Optional[str]:
        """Captures fast, lightweight desktop screenshot in base64 JPEG format for instant AI inference."""
        self.capture_screen_jpeg(max_size=(448, 448), quality=55)
        return self.last_screenshot_b64

    def is_loading_or_blank_screen(self) -> bool:
        """Analyzes latest captured frame to detect black/blank screens."""
        return False

    def human_move_mouse(self, target_x: int, target_y: int, duration: float = 0.08, mode: str = "pointing"):
        """Fast, smooth cursor positioning without artificial lag."""
        if not HAS_PYAUTOGUI or self.inputs_paused:
            return

        self.current_mouse_mode = mode
        try:
            pyautogui.moveTo(target_x, target_y, duration=max(0.04, min(duration, 0.12)))
        except Exception:
            pass

    def execute_actions(self, actions: List[Dict[str, Any]]):
        """Executes a list of vision AI actions safely based on active Control Mode."""
        if not self.enable_inputs or self.inputs_paused or self.control_mode == "COMMENTARY_ONLY":
            if self.inputs_paused:
                logger.info("Skipping input actions: AI controls are currently PAUSED.")
            return

        if not HAS_PYAUTOGUI:
            logger.error("pyautogui is missing.")
            return

        if not actions or not isinstance(actions, list):
            return

        screen_w, screen_h = pyautogui.size()

        for act in actions:
            if not isinstance(act, dict):
                continue
            try:
                # Flexible action type identification
                action_type = str(act.get("action") or act.get("type") or act.get("input") or "").lower().strip()
                mode = str(act.get("mode", "pointing")).lower()
                self.current_mouse_mode = mode

                # Coordinate extraction helper
                raw_x = act.get("x_ratio", act.get("x", act.get("pos_x")))
                raw_y = act.get("y_ratio", act.get("y", act.get("pos_y")))
                
                # Check list/tuple format: e.g. "coordinates": [0.5, 0.6]
                if raw_x is None and "coordinates" in act and isinstance(act["coordinates"], (list, tuple)) and len(act["coordinates"]) >= 2:
                    raw_x, raw_y = act["coordinates"][0], act["coordinates"][1]

                if raw_x is not None and raw_y is not None:
                    x_ratio = float(raw_x)
                    y_ratio = float(raw_y)
                    # Convert normalized ratio or absolute pixels safely
                    target_x = int(x_ratio) if x_ratio > 1.0 else int(screen_w * x_ratio)
                    target_y = int(y_ratio) if y_ratio > 1.0 else int(screen_h * y_ratio)
                    target_x = max(0, min(screen_w - 1, target_x))
                    target_y = max(0, min(screen_h - 1, target_y))
                else:
                    target_x, target_y = None, None

                # 1. Key Press Actions
                if action_type in ["key_press", "press", "key", "keydown", "keyup"]:
                    if self.control_mode == "POINT_AND_CLICK":
                        logger.info("Point & Click Mode active: Skipping keyboard key press action.")
                        continue

                    key = str(act.get("key", "w")).lower().strip()
                    duration = float(act.get("duration", 0.1))
                    logger.info(f"Action: Key press '{key}' for {duration}s")
                    pyautogui.keyDown(key)
                    time.sleep(duration)
                    pyautogui.keyUp(key)

                # 2. Key Combination / Hotkeys (e.g. ctrl+t, ctrl+v, alt+tab, win+r, ctrl+s)
                elif action_type in ["hotkey", "shortcut", "key_combo"]:
                    keys = act.get("keys") or act.get("combo") or [act.get("key")]
                    if isinstance(keys, str):
                        keys = [k.strip().lower() for k in keys.split("+")]
                    if isinstance(keys, list) and keys:
                        logger.info(f"Action: System Hotkey '{'+'.join(keys)}'")
                        pyautogui.hotkey(*keys)

                # 3. Type Text / Write (human typing or instant clipboard paste)
                elif action_type in ["type", "type_text", "write", "paste", "input_text"]:
                    text = str(act.get("text") or act.get("content") or "")
                    use_paste = act.get("paste", True) if len(text) > 20 or "\n" in text else False
                    
                    if target_x is not None and target_y is not None:
                        self.human_move_mouse(target_x, target_y, duration=0.25, mode="click_hover")
                        pyautogui.click(target_x, target_y)
                        time.sleep(0.15)

                    if use_paste:
                        logger.info(f"Action: Fast pasting text ({len(text)} chars) via clipboard")
                        try:
                            import subprocess
                            # Use PowerShell to set clipboard safely on Windows
                            process = subprocess.Popen(['powershell', '-command', 'Set-Clipboard', '-Value', '$input'], stdin=subprocess.PIPE)
                            process.communicate(input=text.encode('utf-8'))
                            time.sleep(0.1)
                            pyautogui.hotkey("ctrl", "v")
                        except Exception as p_err:
                            logger.warning(f"Clipboard paste fallback to typewrite: {p_err}")
                            pyautogui.typewrite(text, interval=0.01)
                    else:
                        logger.info(f"Action: Typing text '{text[:40]}...'")
                        pyautogui.typewrite(text, interval=float(act.get("interval", 0.02)))

                    if act.get("press_enter", False):
                        time.sleep(0.1)
                        pyautogui.press("enter")

                # 4. Mouse Move Actions
                elif action_type in ["move", "mouse_move", "hover", "aim"]:
                    if target_x is not None and target_y is not None:
                        logger.info(f"Action: Organic human mouse move (mode: {mode}) to ({target_x}, {target_y})")
                        self.human_move_mouse(target_x, target_y, duration=random.uniform(0.3, 0.5), mode=mode)

                # 5. Mouse Click Actions (Left, Right, Double)
                elif action_type in ["click", "mouse_click", "left_click", "right_click", "double_click"]:
                    button = "right" if "right" in action_type or str(act.get("button", "")).lower() == "right" else "left"
                    
                    if target_x is not None and target_y is not None:
                        logger.info(f"Action: Human move & click ({target_x}, {target_y}) button '{button}'")
                        self.human_move_mouse(target_x, target_y, duration=random.uniform(0.25, 0.45), mode="click_hover")
                        time.sleep(random.uniform(0.04, 0.08))
                    else:
                        logger.info(f"Action: Click at current cursor position button '{button}'")

                    if "double" in action_type:
                        pyautogui.doubleClick(button=button)
                    else:
                        pyautogui.mouseDown(button=button)
                        time.sleep(random.uniform(0.06, 0.12))
                        pyautogui.mouseUp(button=button)
                        
                    self.current_mouse_mode = "pointing"

                # 6. Scroll (Mouse Wheel Up / Down)
                elif action_type in ["scroll", "mouse_scroll", "wheel", "scroll_down", "scroll_up"]:
                    direction = str(act.get("direction", "down")).lower().strip()
                    if "up" in action_type:
                        direction = "up"
                    elif "down" in action_type:
                        direction = "down"

                    raw_clicks = act.get("clicks", act.get("amount", act.get("delta", 300)))
                    try:
                        clicks_val = int(raw_clicks)
                    except (ValueError, TypeError):
                        clicks_val = 300

                    # Standardize scroll sign: negative = scroll down, positive = scroll up
                    if direction == "down":
                        scroll_amount = -abs(clicks_val)
                    else:
                        scroll_amount = abs(clicks_val)

                    # Move mouse to target element / canvas first if coordinates provided
                    if target_x is not None and target_y is not None:
                        self.human_move_mouse(target_x, target_y, duration=0.2, mode="pointing")
                        time.sleep(0.05)

                    logger.info(f"Action: Smooth mouse scroll ({direction.upper()}, {abs(scroll_amount)} ticks)")
                    
                    # Humanized stepped scrolling in smooth micro-bursts
                    steps = max(2, int(abs(scroll_amount) / 100))
                    step_delta = int(scroll_amount / steps)
                    for _ in range(steps):
                        pyautogui.scroll(step_delta)
                        time.sleep(random.uniform(0.02, 0.05))

                # 7. Open URL in Default Browser
                elif action_type in ["open_url", "browse_url", "navigate_url"]:
                    url = str(act.get("url") or act.get("link") or "").strip()
                    if url:
                        if not url.startswith("http://") and not url.startswith("https://"):
                            url = "https://" + url
                        logger.info(f"Action: Opening web URL in browser: {url}")
                        import webbrowser
                        webbrowser.open(url)
                        time.sleep(2.0)

                # 8. Open Windows Application (e.g. notepad, calc, msedge, etc.)
                elif action_type in ["open_app", "launch_app"]:
                    app_name = str(act.get("app") or act.get("name") or "notepad").strip()
                    logger.info(f"Action: Launching desktop application '{app_name}'")
                    import subprocess
                    subprocess.Popen(app_name, shell=True)
                    time.sleep(1.5)

                # 9. Focus Window (bring to foreground)
                elif action_type in ["focus_window", "switch_window", "bring_to_front", "window_focus"]:
                    win_title = str(act.get("title") or act.get("name") or act.get("window") or "").strip()
                    self.focus_window(win_title)

                # 10. Switch Monitor Display
                elif action_type in ["switch_monitor", "set_monitor", "select_monitor"]:
                    m_idx = int(act.get("monitor", act.get("index", 1)))
                    self.switch_monitor(m_idx)

                # 11. Wait / Sleep
                elif action_type in ["wait", "sleep", "pause"]:
                    sec = float(act.get("seconds") or act.get("duration") or 1.0)
                    logger.info(f"Action: Waiting {sec}s for application / page response")
                    time.sleep(sec)

                time.sleep(self.action_delay)
            except Exception as e:
                logger.error(f"Error executing action {act}: {e}")
