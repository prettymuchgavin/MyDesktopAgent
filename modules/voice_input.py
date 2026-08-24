import os
import io
import time
import threading
import numpy as np
from typing import Dict, Any, Optional, Callable
from modules.logger import setup_logger

logger = setup_logger("VoiceInput")

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False

try:
    import speech_recognition as sr
    HAS_SR = True
except ImportError:
    HAS_SR = False

try:
    from pynput import keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

class VoiceInputService:
    """Push-to-Talk and Microphone Speech-to-Text Voice Input for hands-free desktop control."""
    def __init__(self, config: Optional[Dict[str, Any]] = None, on_command_callback: Optional[Callable[[str], None]] = None):
        cfg = config or {}
        self.enabled = cfg.get("enable_voice_input", True)
        self.hotkey_combo = cfg.get("voice_input_hotkey", "alt+a").lower()
        self.on_command_callback = on_command_callback
        
        self.is_recording = False
        self.sample_rate = 16000
        self.recorded_frames = []
        self._current_keys = set()
        
        if self.enabled:
            self._init_hotkey_listener()

    def update_config(self, config: Dict[str, Any]):
        self.enabled = config.get("enable_voice_input", self.enabled)
        self.hotkey_combo = config.get("voice_input_hotkey", self.hotkey_combo).lower()

    def _init_hotkey_listener(self):
        if not HAS_PYNPUT:
            logger.warning("pynput not available for push-to-talk voice hotkey.")
            return

        def on_press(key):
            try:
                k_name = key.name if hasattr(key, 'name') else str(key).strip("'").lower()
                self._current_keys.add(k_name)
                
                # Check combo: e.g. alt+a or f8
                if "alt" in self._current_keys and "a" in self._current_keys:
                    if not self.is_recording:
                        threading.Thread(target=self.start_voice_capture, daemon=True).start()
                elif k_name == "f8":
                    if not self.is_recording:
                        threading.Thread(target=self.start_voice_capture, daemon=True).start()
            except Exception as e:
                logger.error(f"Voice hotkey press error: {e}")

        def on_release(key):
            try:
                k_name = key.name if hasattr(key, 'name') else str(key).strip("'").lower()
                self._current_keys.discard(k_name)
            except Exception:
                pass

        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.daemon = True
        listener.start()
        logger.info(f"🎙️ Push-to-Talk Voice Input activated! Press [Alt+A] or [F8] anytime to speak.")

    def start_voice_capture(self, max_duration_sec: float = 6.0):
        """Records microphone audio and transcribes into an actionable task command."""
        if self.is_recording:
            return
        self.is_recording = True
        logger.info("🎙️ [LISTENING] Speak your command now...")
        
        transcribed_text = ""
        try:
            if HAS_SR:
                r = sr.Recognizer()
                r.energy_threshold = 300
                r.dynamic_energy_threshold = True
                with sr.Microphone(sample_rate=16000) as source:
                    r.adjust_for_ambient_noise(source, duration=0.3)
                    audio = r.listen(source, timeout=5, phrase_time_limit=max_duration_sec)
                    try:
                        transcribed_text = r.recognize_google(audio)
                    except sr.UnknownValueError:
                        logger.info("Could not understand voice audio.")
                    except sr.RequestError as e:
                        logger.error(f"Speech recognition service error: {e}")
            else:
                logger.warning("speech_recognition library not installed.")
        except Exception as e:
            logger.error(f"Voice capture error: {e}")
        finally:
            self.is_recording = False

        if transcribed_text:
            logger.info(f"🎙️ Voice Command Transcribed: \"{transcribed_text}\"")
            if self.on_command_callback:
                self.on_command_callback(transcribed_text)
        else:
            logger.info("🎙️ Voice input ended with no speech detected.")
