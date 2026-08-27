"""
Telegram Remote Interface for MyClaw
Listens to Telegram messages and executes tasks via ZeroBudgetAgent
"""

import asyncio
import os
import sys
from pathlib import Path
from loguru import logger
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Ensure correct path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from src.agent import ZeroBudgetAgent

# Globals for callback routing
CURRENT_CHAT_ID = None
BOT_INSTANCE = None

async def telegram_approval_callback(approval):
    if not BOT_INSTANCE or not CURRENT_CHAT_ID:
        logger.warning("Bot instance or chat ID not set for approval callback.")
        return
        
    keyboard = [
        [
            InlineKeyboardButton("✅ Izinkan", callback_data=f"approve_{approval.action_id}"),
            InlineKeyboardButton("❌ Tolak", callback_data=f"reject_{approval.action_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    import html
    safe_desc = html.escape(approval.description)
    safe_params = html.escape(str(approval.parameters))
    
    text = (
        f"⚠️ <b>Persetujuan Diperlukan</b>\n\n"
        f"Agen MyClaw mencoba menjalankan aksi kritis:\n"
        f"Maksud: {safe_desc}\n"
        f"<code>{approval.tool_name}</code>\n"
        f"<code>{safe_params}</code>\n\n"
        f"Apakah Anda mengizinkan eksekusi ini?"
    )
    try:
        await BOT_INSTANCE.send_message(
            chat_id=CURRENT_CHAT_ID, 
            text=text, 
            parse_mode='HTML', 
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Gagal mengirim pesan approval Telegram: {e}")

# Initialize Agent
agent = ZeroBudgetAgent(enable_approval_gates=True, on_approval_requested_callback=telegram_approval_callback)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start command"""
    welcome_msg = (
        "🤖 *MyClaw Online!*\n\n"
        "Saya adalah asisten virtual Anda yang berjalan langsung di Macbook Anda.\n"
        "Silakan berikan instruksi apapun (contoh: 'Buka Safari', 'Buat file txt', dll)."
    )
    await update.message.reply_text(welcome_msg, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for all text messages"""
    user_id = str(update.message.from_user.id)
    chat_id = str(update.message.chat.id)
    
    global CURRENT_CHAT_ID
    CURRENT_CHAT_ID = chat_id
    
    # Security Check: Only allow authorized chat_id (if configured)
    if settings.telegram_chat_id and chat_id != settings.telegram_chat_id:
        logger.warning(f"Unauthorized access attempt from chat_id: {chat_id}")
        await update.message.reply_text("Maaf, Anda tidak terverifikasi untuk mengakses agent ini.")
        return

    user_text = update.message.text
    logger.info(f"Received Telegram command: {user_text}")
    
    # Send processing status
    status_msg = await update.message.reply_text("⏳ *Memproses perintah...*", parse_mode='Markdown')
    
    try:
        # Run the agent synchronously in the context
        result = await agent.run(user_text)
        
        # Format the result
        response_text = result.get('final_response', '')
        
        # Send back to user
        await status_msg.edit_text(response_text[:4000], parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error executing remote command: {e}")
        await status_msg.edit_text(f"❌ *Terjadi Kesalahan di Macbook:*\n{str(e)}", parse_mode='Markdown')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    try:
        action_type, action_id = data.split("_", 1)
    except ValueError:
        return
        
    if action_type == "approve":
        approved_file = Path(settings.data_dir) / f"approved_{action_id}.txt"
        approved_file.touch()
        await query.edit_message_text(text=f"✅ Aksi diizinkan oleh Anda.")
    elif action_type == "reject":
        rejected_file = Path(settings.data_dir) / f"rejected_{action_id}.txt"
        rejected_file.touch()
        await query.edit_message_text(text=f"❌ Aksi ditolak. Agen akan membatalkan perintah.")

def main():
    token = settings.telegram_token
    if not token or token == "":
        logger.error("TELEGRAM_TOKEN tidak ditemukan di file .env! Listener gagal berjalan.")
        return

    logger.info("Memulai MyClaw Telegram Listener...")
    
    from telegram.request import HTTPXRequest
    req = HTTPXRequest(connection_pool_size=8, read_timeout=60.0, write_timeout=60.0, connect_timeout=60.0, pool_timeout=60.0)
    
    application = (
        ApplicationBuilder()
        .token(token)
        .request(req)
        .build()
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))

    global BOT_INSTANCE
    BOT_INSTANCE = application.bot

    logger.info("Bot is polling... Buka Telegram Anda dan coba kirim pesan! Tekan Ctrl+C untuk berhenti.")
    application.run_polling()

if __name__ == "__main__":
    main()
