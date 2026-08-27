import asyncio
from dotenv import load_dotenv
import os
from loguru import logger

from config.settings import settings
from config.tool_registry import ToolRegistry
from llm.adaptive_runner import AdaptiveLLMRunner
from src.telegram_bot import TelegramAgentBot
from src.approval_manager import ApprovalManager

load_dotenv()

def main():
    logger.add("telegram_bot.log", rotation="10 MB", level="INFO")
    logger.info("Starting MyClaw Telegram Bot...")

    # Validate essential settings
    if not settings.telegram_token:
        logger.error("TELEGRAM_TOKEN is not set in .env. Please provide it to run the Telegram bot.")
        return
    if not settings.telegram_chat_id:
        logger.error("TELEGRAM_CHAT_ID is not set in .env. Please provide it to run the Telegram bot.")
        return
    if not any([settings.groq_api_key, settings.openrouter_api_key, settings.gemini_api_key]):
        logger.error("No LLM API keys configured (GROQ_API_KEY_1, OPENROUTER_API_KEY_1, GEMINI_API_KEY_1). LLM features will be limited.")

    tool_registry = ToolRegistry()
    llm_runner = AdaptiveLLMRunner()
    
    # Initialize ApprovalManager. For Telegram, the bot itself handles the approval flow,
    # so we're not passing a direct callback here that the agent would use for blocking.
    # The TelegramAgentBot will interact with ApprovalManager's set_approval_result for its own blocking.
    approval_manager = ApprovalManager(approval_timeout=settings.approval_timeout) # Assuming approval_timeout is in settings or default

    telegram_bot = TelegramAgentBot(
        token=settings.telegram_token,
        allowed_chat_id=settings.telegram_chat_id,
        tool_registry=tool_registry,
        llm_runner=llm_runner
    )

    # If the approval_manager needs to be "fed" approval results from the Telegram bot for
    # non-Telegram-initiated tasks (e.g., if ZeroBudgetAgent in Streamlit uses it),
    # the Telegram bot would need to be able to call approval_manager.set_approval_result.
    # For now, TelegramAgentBot handles its own blocking approval.

    telegram_bot.start()

if __name__ == '__main__':
    main()