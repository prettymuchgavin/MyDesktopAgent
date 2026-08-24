import time
import queue
import threading
import numpy as np
from typing import Dict, Any, Optional
from modules.logger import setup_logger

logger = setup_logger("AudioListener")

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False

class DesktopAudioListener:
    def __init__(self, config: Dict[str, Any]):
        self.enabled = config.get("enabled", True)
        self.device_index = config.get("device_index", None)
        
        self.current_volume_rms = 0.0
        self.audio_event = "QUIET" # SILENT, QUIET, NORMAL, LOUD_ACTION
        self.last_loud_event_time = 0.0
        self.is_listening = False
        self.listen_thread = None

        if self.enabled and HAS_SOUNDDEVICE:
            self.start()

    def start(self):
        if self.is_listening:
            return
        self.is_listening = True
        self.listen_thread = threading.Thread(target=self._audio_stream_loop, daemon=True)
        self.listen_thread.start()
        logger.info("🎧 Desktop Audio Perception Engine started!")

    def stop(self):
        self.is_listening = False
        logger.info("Desktop Audio Perception Engine stopped.")

    def _audio_stream_loop(self):
        """Continuously captures system desktop audio and calculates real-time volume energy peak levels."""
        if not HAS_SOUNDDEVICE:
            return

        def audio_callback(indata, frames, time_info, status):
            if not self.is_listening:
                return
            try:
                # Calculate Root Mean Square (RMS) volume level
                rms = float(np.sqrt(np.mean(indata**2)))
                self.current_volume_rms = rms
                
                # Classify audio event state
                if rms > 0.08:
                    self.audio_event = "LOUD_ACTION"
                    self.last_loud_event_time = time.time()
                elif rms > 0.015:
                    self.audio_event = "NORMAL"
                elif rms > 0.003:
                    self.audio_event = "QUIET"
                else:
                    self.audio_event = "SILENT"
            except Exception:
                pass

        retry_delay = 5.0
        while self.is_listening:
            try:
                target_device = self.device_index
                if target_device is None:
                    # Find best input device (Stereo Mix, Cable Output, or default input)
                    devices = sd.query_devices()
                    for idx, d in enumerate(devices):
                        if d['max_input_channels'] > 0 and ('Stereo Mix' in d['name'] or 'CABLE' in d['name']):
                            target_device = idx
                            break
                    if target_device is None:
                        target_device = sd.default.device[0]

                logger.info(f"Audio Perception stream listening on device #{target_device}...")
                with sd.InputStream(device=target_device, channels=1, callback=audio_callback, samplerate=24000):
                    while self.is_listening:
                        time.sleep(0.5)
            except Exception as e:
                logger.error(f"Audio perception stream error: {e}. Retrying in {retry_delay}s...")
                time.sleep(retry_delay)

    def get_audio_context(self) -> Dict[str, Any]:
        """Returns human-readable audio state context for LLM & VLM prompts."""
        now = time.time()
        was_recently_loud = (now - self.last_loud_event_time) < 4.0

        return {
            "volume_rms": round(self.current_volume_rms, 4),
            "audio_event": self.audio_event,
            "was_recently_loud": was_recently_loud
        }
