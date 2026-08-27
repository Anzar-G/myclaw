import asyncio
from loguru import logger
import sys

# Add current directory to sys.path
sys.path.append(".")

from tools.integrations.whatsapp import WhatsAppSendTool, WhatsAppReadTool

async def main():
    logger.info("Testing WhatsApp Web...")
    tool = WhatsAppReadTool()
    # This will just open the browser and try to read from a non-existent contact, or just wait for login
    # Wait, the tool waits for the search box. So it will open and wait for scan.
    # We will test read on a dummy contact.
    try:
        res = await tool.execute("Test Contact")
        logger.info(f"Result: {res}")
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
