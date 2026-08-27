"""
Real-time resource monitoring untuk prevent OOM crashes
"""

import psutil
import asyncio
from loguru import logger

class ResourceMonitor:
    def __init__(self, alert_threshold: float = 85.0, check_interval: int = 30):
        self.alert_threshold = alert_threshold
        self.check_interval = check_interval
        self.is_running = False
    
    async def start_monitoring(self):
        self.is_running = True
        logger.info("🔍 Resource monitoring started")
        
        while self.is_running:
            await self._check_resources()
            await asyncio.sleep(self.check_interval)
    
    async def _check_resources(self):
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=1)
        
        if memory.percent > self.alert_threshold:
            logger.warning(f"⚠️ High memory usage: {memory.percent:.1f}%")
        
        if cpu > 90:
            logger.warning(f"⚠️ High CPU usage: {cpu:.1f}%")
        
        logger.debug(f"📊 RAM: {memory.percent:.1f}% | CPU: {cpu:.1f}%")
    
    def stop_monitoring(self):
        self.is_running = False
        logger.info("⏹️ Monitoring stopped")
