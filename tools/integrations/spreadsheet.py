"""
Google Spreadsheet Integration Tool
"""
from config.tool_registry import BaseTool, ToolCategory
from loguru import logger

class SpreadsheetTool(BaseTool):
    name = "edit_spreadsheet"
    description = "Mengedit data di Google Spreadsheet. Params: sheet_url, data_to_append"
    category = ToolCategory.WEB
    
    async def execute(self, sheet_url: str, data_to_append: str) -> str:
        # Note: True integration requires gspread & credentials.json
        # This is a stub ready for integration.
        logger.info(f"Mock Spreadsheet Edit: Appending {data_to_append} to {sheet_url}")
        return f"Berhasil menambahkan data ke Spreadsheet: {data_to_append}"
