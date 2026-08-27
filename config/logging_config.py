"""
Production-grade structured logging dengan multiple handlers
"""

import json
from pathlib import Path
from loguru import logger
from datetime import datetime
from typing import Dict, Any, Optional
import sys

from config.settings import settings

class StructuredLogger:
    """Structured logging untuk better debugging & monitoring"""
    
    def __init__(self, log_dir: str = settings.log_dir):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self._setup_loggers()
    
    def _setup_loggers(self):
        """Setup multiple loggers untuk different purposes"""
        
        # Remove default handler
        logger.remove()
        
        # 1. Main log file (semua levels)
        logger.add(
            self.log_dir / "agent.log",
            level="DEBUG",
            rotation="100 MB",
            retention="30 days",
            compression="zip",
            format=self._json_format,
            serialize=True
        )
        
        # 2. Error log file (hanya ERROR & CRITICAL)
        logger.add(
            self.log_dir / "errors.log",
            level="ERROR",
            rotation="50 MB",
            retention="90 days",
            format=self._json_format,
            serialize=True
        )
        
        # 3. Performance log (slow operations)
        logger.add(
            self.log_dir / "performance.log",
            level="WARNING",
            rotation="50 MB",
            retention="30 days",
            filter=lambda record: "slow" in record["extra"],
            format="{time} | {level} | {message}"
        )
        
        # 4. Console output (colorized)
        logger.add(
            sys.stderr,
            level="INFO",
            colorize=True,
            format="<level>{level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> | <level>{message}</level>"
        )
        
        # 5. Audit log (user actions)
        logger.add(
            self.log_dir / "audit.log",
            level="INFO",
            rotation="100 MB",
            retention="365 days",
            filter=lambda record: "audit" in record["extra"],
            format="{time:YYYY-MM-DD HH:mm:ss} | {message}"
        )
    
    def _json_format(self, record) -> str:
        """Format log record sebagai JSON"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": record["level"].name,
            "logger": record["name"],
            "function": record["function"],
            "line": record["line"],
            "message": record["message"],
            "extra": record["extra"]
        }
        
        # Add exception info if exists
        if record["exception"]:
            log_data["exception"] = {
                "type": record["exception"][0].__name__,
                "message": str(record["exception"][1]),
                "traceback": record["exc_info"]
            }
        
        return json.dumps(log_data)
    
    @staticmethod
    def log_execution(tool_name: str, params: Dict, result: Dict):
        """Log tool execution untuk audit"""
        logger.bind(audit=True).info(
            f"Tool executed: {tool_name} | Success: {result.get('success', False)} | "
            f"Duration: {result.get('duration', 'N/A')}s"
        )
    
    @staticmethod
    def log_slow_operation(operation: str, duration: float, threshold: float = 10.0):
        """Log operasi yang melebihi threshold"""
        if duration > threshold:
            logger.bind(slow=True).warning(
                f"Slow operation detected: {operation} took {duration:.2f}s (threshold: {threshold}s)"
            )
    
    @staticmethod
    def log_error_with_context(error: Exception, context: Dict):
        """Log error dengan context information"""
        logger.error(
            f"Error: {str(error)} | Context: {json.dumps(context, default=str)}"
        )

# Global logger instance
structured_logger = StructuredLogger()
