"""
Image/Design Generation Tool
"""
from config.tool_registry import BaseTool, ToolCategory
import os
from loguru import logger
from config.settings import settings

class GenerateImageTool(BaseTool):
    name = "generate_design"
    description = "Membuat gambar/desain menggunakan AI berdasarkan prompt. Params: prompt"
    category = ToolCategory.WEB
    
    async def execute(self, prompt: str) -> dict:
        logger.info(f"Image generation requested: {prompt}")
        raise NotImplementedError(
            "Image generation belum dikonfigurasi. Sambungkan provider gambar terlebih dahulu; "
            "MyClaw tidak akan mengirim PNG placeholder sebagai hasil nyata."
        )
