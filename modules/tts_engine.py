import os
import io
import time
import queue
import random
import requests
import threading
import numpy as np
from typing import Dict, Any, Optional
from modules.logger import setup_logger

logger = setup_logger("TTSEngine")

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False

try:
    import soundfile as sf
    HAS_SOUNDFILE = True
except ImportError:
    HAS_SOUNDFILE = False

try:
    from kokoro_onnx import Kokoro
    HAS_KOKORO = True
except ImportError:
    HAS_KOKORO = False

# Natural subtle conversational transitions
NATURAL_FILLERS = [
    "Alright, ", "Let's see, ", "Hmm, ", "So, ", "Okay, ", "Well, "
]

class TTSEngine:
    def __init__(self, config: Dict[str, Any]):
        self.engine_type = config.get("engine", "kokoro-onnx").lower()
        self.voice = config.get("voice", "af_sarah")
        self.base_speed = float(config.get("speed", 1.1))
        self.sample_rate = int(config.get("sample_rate", 24000))
        
        # ElevenLabs Configuration
        el_cfg = config.get("elevenlabs", {})
        self.elevenlabs_api_key = el_cfg.get("api_key", "").strip()
        self.elevenlabs_voice_id = el_cfg.get("voice_id", "21m00Tcm4TlvDq8ikWAM").strip()
        self.elevenlabs_model_id = el_cfg.get("model_id", "eleven_turbo_v2_5").strip()

        self.audio_queue = queue.Queue()
        self.is_playing = False
        self.kokoro_instance = None
        
        self._init_engine()
        
        # Start worker thread for asynchronous audio playback
        self.worker_thread = threading.Thread(target=self._audio_playback_loop, daemon=True)
        self.worker_thread.start()

    def update_config(self, config: Dict[str, Any]):
        """Updates TTS settings live from Web Dashboard."""
        self.engine_type = config.get("engine", self.engine_type).lower()
        self.voice = config.get("voice", self.voice)
        self.base_speed = float(config.get("speed", self.base_speed))
        
        el_cfg = config.get("elevenlabs", {})
        self.elevenlabs_api_key = el_cfg.get("api_key", self.elevenlabs_api_key).strip()
        self.elevenlabs_voice_id = el_cfg.get("voice_id", self.elevenlabs_voice_id).strip()
        self.elevenlabs_model_id = el_cfg.get("model_id", self.elevenlabs_model_id).strip()
        logger.info(f"TTS Engine updated. Active Engine: '{self.engine_type}'")

    def _init_engine(self):
        """Initializes Kokoro-TTS ONNX model."""
        model_path = os.path.join(os.path.dirname(__file__), "..", "models", "kokoro-v0_19.onnx")
        voices_bin_path = os.path.join(os.path.dirname(__file__), "..", "models", "voices.bin")
        voices_json_path = os.path.join(os.path.dirname(__file__), "..", "models", "voices.json")
        voices_path = voices_bin_path if os.path.exists(voices_bin_path) else voices_json_path

        if HAS_KOKORO and os.path.exists(model_path) and os.path.exists(voices_path):
            try:
                self.kokoro_instance = Kokoro(model_path, voices_path)
                logger.info("🔊 Kokoro-TTS ONNX Voice Engine initialized successfully!")
            except Exception as e:
                logger.error(f"Failed to initialize Kokoro-TTS ONNX: {e}")
        else:
            logger.warning("Kokoro-TTS model files not found locally. ElevenLabs will be used if configured.")

        if self.engine_type == "elevenlabs" and self.elevenlabs_api_key:
            logger.info("🎙️ ElevenLabs Cloud TTS Engine activated!")

    def humanize_speech_text(self, text: str) -> str:
        """Infuses natural subtle cadence into raw LLM text."""
        cleaned = text.strip()
        if not cleaned:
            return ""

        # 25% chance to inject a natural conversational filler prefix if text doesn't already have one
        if random.random() < 0.25 and not any(cleaned.lower().startswith(f.strip().lower()) for f in NATURAL_FILLERS):
            prefix = random.choice(NATURAL_FILLERS)
            cleaned = prefix + cleaned[0].lower() + cleaned[1:] if cleaned else prefix

        # Inject natural cadence pause commas if sentence is very long
        if len(cleaned) > 70 and "," not in cleaned:
            words = cleaned.split(" ")
            if len(words) > 8:
                mid = len(words) // 2
                words[mid] += ","
                cleaned = " ".join(words)

        return cleaned

    def clear_queue(self):
        """Clears any pending audio backlog to prevent speech lag."""
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except Exception:
                break

    def speak(self, text: str):
        """Queues text to be spoken asynchronously by active TTS engine."""
        if not text or not text.strip() or self.engine_type == "none":
            return

        # If audio is already playing or queue has items, drop stale backlog so it never lags behind
        if self.is_playing or not self.audio_queue.empty():
            self.clear_queue()

        humanized_text = self.humanize_speech_text(text)
        logger.info(f"Speech queued ({self.engine_type.upper()}): '{humanized_text}'")
        try:
            self.audio_queue.put_nowait({"text": humanized_text})
        except queue.Full:
            pass

    def _generate_elevenlabs_audio(self, text: str) -> Optional[tuple[np.ndarray, int]]:
        """Synthesizes voice using ElevenLabs REST API and decodes MP3 stream directly to PCM array."""
        if not self.elevenlabs_api_key:
            logger.error("ElevenLabs API Key is missing. Enter your API Key in config.yaml or Web Dashboard.")
            return None

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.elevenlabs_voice_id}/stream"
        headers = {
            "xi-api-key": self.elevenlabs_api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "model_id": self.elevenlabs_model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

        try:
            res = requests.post(url, json=payload, headers=headers, timeout=20)
            if res.status_code == 200:
                if HAS_SOUNDFILE:
                    audio_data, sr = sf.read(io.BytesIO(res.content))
                    return audio_data, sr
                else:
                    logger.error("soundfile module missing for ElevenLabs MP3 decoding.")
            else:
                logger.error(f"ElevenLabs API returned HTTP error {res.status_code}: {res.text}")
        except Exception as e:
            logger.error(f"ElevenLabs speech synthesis failed: {e}")

        return None

    def _audio_playback_loop(self):
        """Background thread loop consuming text from queue and playing audio."""
        while True:
            try:
                item = self.audio_queue.get()
                if item is None:
                    break
                
                text = item.get("text", "")
                self.is_playing = True
                
                # Option 1: ElevenLabs Cloud TTS
                if self.engine_type == "elevenlabs":
                    el_res = self._generate_elevenlabs_audio(text)
                    if el_res:
                        samples, sr = el_res
                        if HAS_SOUNDDEVICE and len(samples) > 0:
                            sd.play(samples, sr)
                            sd.wait()
                    else:
                        logger.warning("ElevenLabs synthesis failed or unconfigured. Falling back to Kokoro-TTS.")
                        if self.kokoro_instance:
                            samples, sr = self.kokoro_instance.create(text, voice=self.voice, speed=self.base_speed, lang="en-us")
                            if HAS_SOUNDDEVICE and len(samples) > 0:
                                sd.play(samples, sr)
                                sd.wait()

                # Option 2: Local Kokoro-TTS ONNX
                else:
                    if self.kokoro_instance:
                        try:
                            samples, sr = self.kokoro_instance.create(
                                text, voice=self.voice, speed=self.base_speed, lang="en-us"
                            )
                            if HAS_SOUNDDEVICE and len(samples) > 0:
                                sd.play(samples, sr)
                                sd.wait()
                        except Exception as e:
                            logger.error(f"Kokoro audio playback error: {e}")
                    else:
                        logger.warning("Kokoro instance not ready. Skipping audio output.")
                        time.sleep(len(text) * 0.08)

                self.is_playing = False
                self.audio_queue.task_done()
            except Exception as e:
                logger.error(f"Audio playback loop exception: {e}")
                self.is_playing = False
