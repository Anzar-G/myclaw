import asyncio
import json
import time
import random
import os
import html
import re
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, CommandHandler, filters, ContextTypes
from loguru import logger

from config.settings import settings
from config.tool_registry import ToolRegistry, BaseTool, ToolResult
from src.command_parser import CommandParser, ActionRiskLevel
from llm.adaptive_runner import AdaptiveLLMRunner # Assuming this is the LLM runner
from memory.conversation_store import ConversationStore
from core.scheduler import Scheduler
from core.workflow import WorkflowRunner
from core.live_view import LiveView

class PendingApproval:
    def __init__(self, action_id: str, tool_name: str, params: Dict[str, Any],
                 chat_id: int, message_id: int, original_command: str,
                 created_at: datetime, expires_at: datetime):
        self.action_id = action_id
        self.tool_name = tool_name
        self.params = params
        self.chat_id = chat_id
        self.message_id = message_id
        self.original_command = original_command
        self.created_at = created_at
        self.expires_at = expires_at
        self.event = asyncio.Event() # Event to signal approval status
        self.approved: Optional[bool] = None # Store approval result

    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at

def _redact_sensitive(text: str) -> str:
    return re.sub(r"(?i)(password|passcode|otp|pin|api[_ -]?key|token)\s*[:=]?\s*[^\s]+", r"\1: [REDACTED]", text)

class TelegramAgentBot:
    def __init__(self, token: str, allowed_chat_id: int, tool_registry: ToolRegistry, llm_runner: AdaptiveLLMRunner):
        self.token = token
        self.allowed_chat_id = allowed_chat_id
        self.tool_registry = tool_registry
        self.llm_runner = llm_runner
        self.command_parser = CommandParser(llm_runner=self.llm_runner, tool_registry=self.tool_registry) # Pass LLM runner for fuzzy matching
        
        self.pending_approvals: Dict[str, PendingApproval] = {}
        self._files_sent_by_chat: Dict[int, set[str]] = {}
        self.conversations = ConversationStore()
        self.scheduler = Scheduler(self._send_scheduled_message)
        self.workflow_runner = WorkflowRunner(self.tool_registry)
        self.live_view = LiveView(settings.live_view_token)
        self._live_server_task = None
        self._watch_tasks: Dict[int, asyncio.Task] = {}
        self.application = Application.builder().token(token).post_init(self._post_init).post_shutdown(self._post_shutdown).build()
        self._setup_handlers()
        logger.info("TelegramAgentBot initialized.")

    def _setup_handlers(self):
        """Setup message and callback handlers"""
        self.application.add_handler(
            CommandHandler("help", self._help_command)
        )
        self.application.add_handler(
            CommandHandler("status", self._status_command)
        )
        self.application.add_handler(CommandHandler("workflow", self._workflow_command))
        self.application.add_handler(CommandHandler("watch", self._watch_command))
        self.application.add_handler(CommandHandler("stop_watch", self._stop_watch_command))
        self.application.add_handler(CommandHandler("live", self._live_command))
        self.application.add_handler(
            CommandHandler("schedule", self._schedule_command)
        )
        self.application.add_handler(
            CommandHandler("schedules", self._schedules_command)
        )
        self.application.add_handler(
            CommandHandler("cancel_schedule", self._cancel_schedule_command)
        )
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & filters.Chat(chat_id=self.allowed_chat_id),
                self._handle_command_message
            )
        )
        self.application.add_handler(
            CallbackQueryHandler(self._handle_approval_callback, pattern=r"^(approve|reject)_")
        )
        logger.info("Telegram handlers set up.")

    async def _post_init(self, application):
        await self.scheduler.start()
        import uvicorn
        config = uvicorn.Config(self.live_view.app, host=settings.live_view_bind, port=8765, log_level="warning")
        self._live_server_task = asyncio.create_task(uvicorn.Server(config).serve())

    async def _post_shutdown(self, application):
        await self.scheduler.stop()
        if self._live_server_task: self._live_server_task.cancel()

    async def _live_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.id != self.allowed_chat_id: return
        import socket
        reachable_host = "127.0.0.1"
        for interface in ("en0", "en1"):
            probe = subprocess.run(["/usr/sbin/ipconfig", "getifaddr", interface], capture_output=True, text=True)
            candidate = probe.stdout.strip()
            if candidate and not candidate.startswith("127."):
                reachable_host = candidate
                break
        if reachable_host == "127.0.0.1":
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); sock.connect(("192.0.2.1", 80))
                reachable_host = sock.getsockname()[0]; sock.close()
            except OSError: pass
        await update.message.reply_text(
            "Live view aktif di jaringan lokal:\n"
            f"http://{reachable_host}:8765/live?token={self.live_view.token}&fps=5\n\n"
            "HP harus berada di Wi-Fi yang sama. Untuk akses dari luar rumah, gunakan Tailscale/SSH; "
            "jangan port-forward langsung ke internet."
        )

    async def _schedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.id != self.allowed_chat_id: return
        text = " ".join(context.args)
        if len(context.args) < 2 or not context.args[0].isdigit():
            await update.message.reply_text("Format: /schedule <menit> <pesan>"); return
        item = self.scheduler.add(update.effective_chat.id, "⏰ " + text.split(" ", 1)[1], int(context.args[0]))
        await update.message.reply_text(f"Pengingat dibuat: {item['id']} (dalam {context.args[0]} menit)")

    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.id != self.allowed_chat_id: return
        await update.message.reply_text(
            "MyClaw siap menerima bahasa natural.\n\n"
            "Contoh: Status Mac, Cek baterai, Buka YouTube di Arc, "
            "Ambil screenshot dan kirim, Lihat isi folder ~/Desktop.\n\n"
            "Scheduler: /schedule <menit> <pesan>, /schedules, /cancel_schedule <id>"
        )

    async def _status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.id != self.allowed_chat_id: return
        await update.message.reply_text(
            f"MyClaw online. Tools: {len(self.tool_registry.tools)}. "
            f"Pengingat aktif: {len(self.scheduler.list(update.effective_chat.id))}."
        )

    async def _workflow_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.id != self.allowed_chat_id: return
        if not context.args:
            await update.message.reply_text("Workflow tersedia: system_report, capture_screen")
            return
        try:
            results = await self.workflow_runner.run(context.args[0])
            lines = [f"Workflow {context.args[0]} selesai:"]
            for item in results:
                icon = "✅" if item["success"] else "❌"
                lines.append(f"{icon} Langkah {item['step']} ({item['tool']}): {item['message']}")
                if item.get("data") and not isinstance(item["data"], dict): lines.append(str(item["data"])[:700])
            await update.message.reply_text("\n".join(lines))
            for item in results:
                data = item.get("data")
                if item.get("success") and isinstance(data, dict) and data.get("type") == "file" and os.path.exists(data.get("path", "")):
                    with open(data["path"], "rb") as handle:
                        await context.bot.send_document(chat_id=update.effective_chat.id, document=handle, caption=data.get("caption", "Workflow output"))
        except ValueError as exc:
            await update.message.reply_text(str(exc))

    async def _watch_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.id != self.allowed_chat_id: return
        chat_id = update.effective_chat.id
        if chat_id in self._watch_tasks and not self._watch_tasks[chat_id].done():
            await update.message.reply_text("Live monitor sudah berjalan. Gunakan /stop_watch untuk menghentikannya."); return
        interval = 5
        if context.args:
            try: interval = max(3, min(int(context.args[0]), 60))
            except ValueError: pass
        self._watch_tasks[chat_id] = asyncio.create_task(self._watch_loop(chat_id, interval))
        await update.message.reply_text(f"Live monitor aktif: screenshot setiap {interval} detik. Gunakan /stop_watch untuk berhenti.")

    async def _stop_watch_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        task = self._watch_tasks.pop(update.effective_chat.id, None)
        if task: task.cancel(); await update.message.reply_text("Live monitor dihentikan.")
        else: await update.message.reply_text("Tidak ada live monitor yang aktif.")

    async def _watch_loop(self, chat_id: int, interval: int):
        import tempfile
        while True:
            try:
                from tools.mac_automation import ScreenshotTool
                path = tempfile.mktemp(prefix="myclaw-watch-", suffix=".png")
                result = await ScreenshotTool().safe_execute(path=path)
                if result.success and os.path.exists(path):
                    with open(path, "rb") as handle:
                        await self.application.bot.send_photo(chat_id=chat_id, photo=handle, caption="🖥️ Live view")
                    os.unlink(path)
                else:
                    await self.application.bot.send_message(chat_id=chat_id, text=f"❌ Live view gagal: {result.message}")
                    return
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                return
            except Exception as exc:
                await self.application.bot.send_message(chat_id=chat_id, text=f"❌ Live view berhenti: {exc}")
                return

    async def _schedules_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        items = self.scheduler.list(update.effective_chat.id)
        await update.message.reply_text("\n".join(f"{x['id']} — {x['due']} — {x['message']}" for x in items) or "Tidak ada pengingat aktif.")

    async def _cancel_schedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        ok = bool(context.args) and self.scheduler.cancel(context.args[0])
        await update.message.reply_text("Pengingat dibatalkan." if ok else "ID pengingat tidak ditemukan.")

    async def _send_scheduled_message(self, chat_id, message, item_id):
        await self.application.bot.send_message(chat_id=chat_id, text=message)

    def start(self):
        """Start the bot"""
        logger.info("Starting Telegram bot polling...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

    async def _handle_command_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle command from user via Telegram"""
        user_message = update.message.text
        chat_id = update.message.chat_id

        logger.info(f"Received message from chat_id {chat_id}: {_redact_sensitive(user_message)}")

        if chat_id != self.allowed_chat_id:
            await context.bot.send_message(chat_id=chat_id, text="Maaf, Anda tidak diizinkan menggunakan bot ini.")
            logger.warning(f"Unauthorized access attempt from chat_id: {chat_id}")
            return

        try:
            self._files_sent_by_chat[chat_id] = set()
            history = self.conversations.recent(chat_id)
            self.conversations.append(chat_id, "user", _redact_sensitive(user_message))
            actions = await self.command_parser.parse_telegram_message(user_message, history)
            
            for tool_name, params, risk_level in actions:
                # Special handling for LLM fallback with send_telegram_message
                if tool_name == "send_telegram_message" and params.get("chat_id") == "current":
                    params["chat_id"] = chat_id

                if tool_name == "send_telegram_message":
                    message_to_send = params.get("message", "Pesan kosong.")
                    await context.bot.send_message(chat_id=params.get("chat_id", chat_id), text=message_to_send)
                    self.conversations.append(chat_id, "assistant", message_to_send)
                    continue

                if risk_level.value >= ActionRiskLevel.MEDIUM.value:
                    logger.warning(f"Approval required for tool '{tool_name}' with risk '{risk_level.name}'")
                    await self._request_approval(chat_id, tool_name, params, user_message, context)
                else:
                    logger.info(f"Executing tool '{tool_name}' directly (risk: {risk_level.name})")
                    await self._execute_tool(chat_id, tool_name, params, context)

        except Exception as e:
            logger.error(f"Error handling command message: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Error saat memproses perintah: {e}"
            )

    async def _request_approval(self, chat_id: int, tool_name: str, params: Dict[str, Any],
                                original_command: str, context: ContextTypes.DEFAULT_TYPE):
        """Request approval via inline buttons"""
        action_id = f"{tool_name}_{int(time.time())}_{random.randint(1000, 9999)}"
        
        keyboard = [
            [
                InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{action_id}"),
                InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{action_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message_text = f"""
🔒 APPROVAL REQUIRED

Command: {original_command}
Tool: {tool_name}
Risk: {self._get_risk_emoji(risk_level=self.command_parser._assess_risk(tool_name))}

Parameter:
```{json.dumps(params, indent=2, ensure_ascii=False)}```

Approve? (5 minute timeout)
"""
        
        try:
            sent_msg = await context.bot.send_message(
                chat_id=chat_id,
                text=message_text,
                reply_markup=reply_markup
            )
            
            approval = PendingApproval(
                action_id=action_id,
                tool_name=tool_name,
                params=params,
                chat_id=chat_id,
                message_id=sent_msg.message_id,
                original_command=original_command,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(minutes=5)
            )
            self.pending_approvals[action_id] = approval
            logger.info(f"Approval request sent for action_id: {action_id}")
        except Exception as e:
            logger.error(f"Failed to send approval request: {e}")
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Gagal mengirim permintaan persetujuan: {e}")

    async def _handle_approval_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button click (approve/reject)"""
        query = update.callback_query
        await query.answer() # Acknowledge the callback query
        callback_data = query.data
        chat_id = query.message.chat_id
        message_id = query.message.message_id

        logger.info(f"Received callback: {callback_data} from chat_id {chat_id}")
        
        if not callback_data:
            logger.warning("Empty callback_data received.")
            return

        action_type, action_id = callback_data.split("_", 1)
        
        if action_id not in self.pending_approvals:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"❌ Persetujuan kadaluarsa atau tidak ditemukan untuk `{action_id}`."
            )
            await query.answer("❌ Persetujuan kadaluarsa atau tidak ditemukan", show_alert=True)
            logger.warning(f"Approval for action_id {action_id} not found or expired.")
            return
        
        approval = self.pending_approvals[action_id]
        
        if approval.is_expired():
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"⏱️ Persetujuan kadaluarsa untuk `{action_id}`."
            )
            await query.answer("⏱️ Persetujuan kadaluarsa", show_alert=True)
            del self.pending_approvals[action_id]
            logger.warning(f"Approval for action_id {action_id} expired.")
            return

        approval.approved = (action_type == "approve")
        approval.event.set() # Signal that a decision has been made
        
        if approval.approved:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"✅ Disetujui: `{approval.original_command}`\n\n_Mengeksekusi..._"
            )
            logger.info(f"Action {action_id} approved. Executing tool '{approval.tool_name}'...")
            # Execute tool after approval
            await self._execute_tool(approval.chat_id, approval.tool_name, approval.params, context)
        else:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"❌ Ditolak: `{approval.original_command}`"
            )
            logger.warning(f"Action {action_id} rejected.")
        
        del self.pending_approvals[action_id] # Clean up

    async def _execute_tool(self, chat_id: int, tool_name: str, params: Dict[str, Any], context: ContextTypes.DEFAULT_TYPE):
        """Execute tool dan report hasil ke Telegram"""
        try:
            tool: BaseTool = self.tool_registry.get_tool(tool_name)
            logger.info(f"Executing tool '{tool_name}' with params: {params}")
            
            # Await the execution of the tool
            result: ToolResult = await tool.safe_execute(**params)

            # Check if result data contains a file path to send
            if result.success and isinstance(result.data, dict) and result.data.get("type") == "file":
                file_path = result.data.get("path")
                caption = result.data.get("caption", result.message)
                if file_path and os.path.exists(file_path):
                    normalized_path = os.path.abspath(file_path)
                    sent_files = self._files_sent_by_chat.setdefault(chat_id, set())
                    if normalized_path in sent_files:
                        logger.info(f"Skipping duplicate Telegram file send: {file_path}")
                        return
                    logger.info(f"Sending file to Telegram: {file_path}")
                    try:
                        if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                            with open(file_path, 'rb') as f:
                                await context.bot.send_photo(chat_id=chat_id, photo=f, caption=caption)
                        else:
                            with open(file_path, 'rb') as f:
                                await context.bot.send_document(chat_id=chat_id, document=f, caption=caption)
                        sent_files.add(normalized_path)
                        return
                    except Exception as fe:
                        logger.error(f"Failed to send file: {fe}")

            status_label = "berhasil dieksekusi" if result.success else "gagal dieksekusi"
            icon = "✅" if result.success else "❌"
            state = "Berhasil" if result.success else "Gagal"
            message_text = (
                f"{icon} <b>Hasil Eksekusi</b>\n"
                f"<b>Tool:</b> <code>{html.escape(tool_name)}</code>\n"
                f"<b>Status:</b> {state}\n"
                f"<b>Pesan:</b> {html.escape(str(result.message))}"
            )
            
            if result.data and str(result.data) != str(result.message):
                data_str = str(result.data)
                if len(data_str) > 500: # Truncate long data for Telegram
                    data_str = data_str[:497] + "..."
                message_text += f"\n<b>Data:</b>\n<pre>{html.escape(data_str)}</pre>"
            
            await context.bot.send_message(chat_id=chat_id, text=message_text, parse_mode="HTML")
            logger.info(f"Tool '{tool_name}' execution result sent to Telegram.")
            
        except ValueError as ve:
            logger.error(f"Tool '{tool_name}' not found: {ve}")
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ <b>Tool tidak ditemukan</b>\n<code>{html.escape(tool_name)}</code>\nMohon periksa kembali nama tool.",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ <b>Eksekusi gagal</b>\nTool: <code>{html.escape(tool_name)}</code>\n{html.escape(str(e))}",
                parse_mode="HTML"
            )

    def _get_risk_emoji(self, risk_level: ActionRiskLevel) -> str:
        if risk_level == ActionRiskLevel.CRITICAL:
            return "âš ï¸ KRITIS"
        elif risk_level == ActionRiskLevel.HIGH:
            return "âš ï¸ TINGGI"
        elif risk_level == ActionRiskLevel.MEDIUM:
            return "âš™ï¸ SEDANG"
        else:
            return "âœ… RENDAH"
