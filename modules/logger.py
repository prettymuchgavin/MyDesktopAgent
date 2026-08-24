import logging
import collections
from datetime import datetime

# Global ring buffer log queue for Web Dashboard streaming (max 200 items)
dashboard_log_queue = collections.deque(maxlen=200)

class DashboardLogHandler(logging.Handler):
    def emit(self, record):
        try:
            log_entry = {
                "timestamp": datetime.fromtimestamp(record.created).strftime("%H:%M:%S"),
                "level": record.levelname,
                "message": record.getMessage(),
                "logger": record.name
            }
            dashboard_log_queue.append(log_entry)
        except Exception:
            self.handleError(record)

def setup_logger(name: str = "AI_Streamer", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if not logger.handlers:
        # Console Handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s", datefmt="%H:%M:%S")
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # Dashboard Handler
        dashboard_handler = DashboardLogHandler()
        logger.addHandler(dashboard_handler)
        
    return logger
