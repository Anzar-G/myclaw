"""
Error recovery system dengan auto-retry dan graceful degradation
"""

import asyncio
from typing import Callable, Optional, Any, Tuple
from loguru import logger
from functools import wraps
from enum import Enum

class RecoveryStrategy(Enum):
    RETRY = "retry"
    FALLBACK = "fallback"
    SKIP = "skip"
    HALT = "halt"

class ErrorRecoveryManager:
    def __init__(self):
        self.max_retries = 3
        self.base_delay = 1
        self.max_delay = 60
    
    async def execute_with_recovery(self, func: Callable, args: Tuple = (), kwargs: dict = None, 
                                   strategy: RecoveryStrategy = RecoveryStrategy.RETRY, 
                                   fallback_func: Optional[Callable] = None) -> Any:
        if kwargs is None: kwargs = {}
        attempt = 0
        last_error = None
        
        while attempt < self.max_retries:
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                attempt += 1
                logger.warning(f"Execution failed (attempt {attempt}/{self.max_retries}): {e}")
                
                if strategy == RecoveryStrategy.RETRY:
                    if attempt < self.max_retries:
                        delay = min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)
                        await asyncio.sleep(delay)
                    else:
                        if fallback_func:
                            if asyncio.iscoroutinefunction(fallback_func):
                                return await fallback_func(*args, **kwargs)
                            return fallback_func(*args, **kwargs)
                        raise
                elif strategy == RecoveryStrategy.SKIP:
                    return None
                elif strategy == RecoveryStrategy.HALT:
                    raise
        raise last_error

def with_error_recovery(max_retries: int = 3, fallback: Optional[Callable] = None):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            recovery = ErrorRecoveryManager()
            recovery.max_retries = max_retries
            return await recovery.execute_with_recovery(func, args=args, kwargs=kwargs, fallback_func=fallback)
        return wrapper
    return decorator
