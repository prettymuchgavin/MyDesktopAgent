import socket
import threading
import queue
import time
import re
from typing import Dict, Any, Optional
from modules.logger import setup_logger

logger = setup_logger("TwitchChat")

class TwitchChatListener:
    def __init__(self, config: Dict[str, Any]):
        self.channel_name = config.get("channel_name", "").strip().lower()
        self.enabled = config.get("enabled", True)
        self.chat_queue = queue.Queue(maxsize=100)
        self.running = False
        self.socket = None
        self.listen_thread = None

        if self.enabled and self.channel_name:
            self.start()

    def start(self):
        if self.running:
            return
        self.running = True
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()
        logger.info(f"Twitch chat listener started for channel: #{self.channel_name}")

    def stop(self):
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
        logger.info("Twitch chat listener stopped.")

    def _connect(self):
        server = "irc.chat.twitch.tv"
        port = 6667
        nickname = "justinfan88421"  # Anonymous Twitch IRC connection
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10.0)
        sock.connect((server, port))
        sock.send(f"NICK {nickname}\r\n".encode("utf-8"))
        sock.send(f"JOIN #{self.channel_name}\r\n".encode("utf-8"))
        return sock

    def _listen_loop(self):
        retry_delay = 5.0
        while self.running:
            try:
                self.socket = self._connect()
                logger.info(f"Connected to Twitch IRC channel #{self.channel_name}")
                buffer = ""
                
                while self.running:
                    try:
                        data = self.socket.recv(2048).decode("utf-8", errors="ignore")
                        if not data:
                            break
                        
                        buffer += data
                        lines = buffer.split("\r\n")
                        buffer = lines.pop()

                        for line in lines:
                            if line.startswith("PING"):
                                self.socket.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
                            elif "PRIVMSG" in line:
                                self._parse_privmsg(line)
                    except socket.timeout:
                        continue
                    except Exception as e:
                        logger.error(f"Error reading from Twitch socket: {e}")
                        break

            except Exception as e:
                logger.error(f"Twitch IRC connection failed: {e}. Retrying in {retry_delay}s...")
                time.sleep(retry_delay)

    def _parse_privmsg(self, raw_line: str):
        try:
            # Twitch PRIVMSG format: :username!username@username.tmi.twitch.tv PRIVMSG #channel :message text
            match = re.match(r"^:(\w+)!\w+@\w+\.tmi\.twitch\.tv PRIVMSG #\w+ :(.*)$", raw_line)
            if match:
                user = match.group(1)
                msg = match.group(2).strip()
                
                # Basic spam / bot filtering
                if len(msg) > 0 and not msg.startswith("!") and not user.endswith("bot"):
                    chat_item = {"user": user, "message": msg, "timestamp": time.time()}
                    if not self.chat_queue.full():
                        self.chat_queue.put(chat_item)
                        logger.info(f"Twitch Chat [@{user}]: {msg}")
        except Exception as e:
            logger.error(f"Error parsing Twitch message: {e}")

    def get_next_message(self) -> Optional[Dict[str, str]]:
        try:
            return self.chat_queue.get_nowait()
        except queue.Empty:
            return None
