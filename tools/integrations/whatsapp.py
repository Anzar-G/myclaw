"""
WhatsApp Web Automation Tool using Playwright Persistent Context
"""
from config.tool_registry import BaseTool, ToolCategory
from loguru import logger
import asyncio
import os

WHATSAPP_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "whatsapp_session")

class WhatsAppSendTool(BaseTool):
    name = "whatsapp_send"
    description = "Mengirim pesan WhatsApp ke kontak/nomor tertentu. Params: contact_name, message"
    category = ToolCategory.COMMUNICATION
    
    async def execute(self, contact_name: str, message: str) -> str:
        from playwright.async_api import async_playwright
        
        os.makedirs(WHATSAPP_DATA_DIR, exist_ok=True)
        
        async with async_playwright() as p:
            # Persistent context menyimpan cookies/session agar tidak perlu scan QR ulang
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=WHATSAPP_DATA_DIR,
                headless=False,  # Harus visible untuk scan QR pertama kali
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = browser.pages[0] if browser.pages else await browser.new_page()
            
            await page.goto("https://web.whatsapp.com", timeout=60000)
            
            # Tunggu WhatsApp Web selesai loading (cari search box)
            try:
                await page.wait_for_selector('div[contenteditable="true"][data-tab="3"]', timeout=60000)
            except Exception:
                await browser.close()
                return "WhatsApp Web belum login. Silakan scan QR Code terlebih dahulu dengan menjalankan ulang perintah ini."
            
            # Cari kontak
            search_box = page.locator('div[contenteditable="true"][data-tab="3"]')
            await search_box.click()
            await search_box.fill(contact_name)
            await asyncio.sleep(2)
            
            # Klik kontak pertama yang muncul
            try:
                contact = page.locator(f'span[title*="{contact_name}"]').first
                await contact.click()
                await asyncio.sleep(1)
            except Exception:
                await browser.close()
                return f"Kontak '{contact_name}' tidak ditemukan di WhatsApp."
            
            # Ketik dan kirim pesan
            msg_box = page.locator('div[contenteditable="true"][data-tab="10"]')
            await msg_box.click()
            await msg_box.fill(message)
            await page.keyboard.press("Enter")
            await asyncio.sleep(2)
            
            await browser.close()
            return f"Pesan berhasil dikirim ke {contact_name}: '{message}'"


class WhatsAppReadTool(BaseTool):
    name = "whatsapp_read"
    description = "Membaca pesan terakhir dari kontak WhatsApp tertentu. Params: contact_name"
    category = ToolCategory.COMMUNICATION
    
    async def execute(self, contact_name: str) -> str:
        from playwright.async_api import async_playwright
        
        os.makedirs(WHATSAPP_DATA_DIR, exist_ok=True)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=WHATSAPP_DATA_DIR,
                headless=False,
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = browser.pages[0] if browser.pages else await browser.new_page()
            
            await page.goto("https://web.whatsapp.com", timeout=60000)
            
            try:
                await page.wait_for_selector('div[contenteditable="true"][data-tab="3"]', timeout=60000)
            except Exception:
                await browser.close()
                return "WhatsApp Web belum login. Silakan scan QR Code terlebih dahulu."
            
            # Cari kontak
            search_box = page.locator('div[contenteditable="true"][data-tab="3"]')
            await search_box.click()
            await search_box.fill(contact_name)
            await asyncio.sleep(2)
            
            try:
                contact = page.locator(f'span[title*="{contact_name}"]').first
                await contact.click()
                await asyncio.sleep(2)
            except Exception:
                await browser.close()
                return f"Kontak '{contact_name}' tidak ditemukan di WhatsApp."
            
            # Baca pesan-pesan terakhir
            messages = await page.locator('div.message-in span.selectable-text').all_text_contents()
            last_messages = messages[-5:] if len(messages) > 5 else messages
            
            await browser.close()
            
            if not last_messages:
                return f"Tidak ada pesan terbaru dari {contact_name}."
            
            formatted = "\n".join([f"- {msg}" for msg in last_messages])
            return f"Pesan terakhir dari {contact_name}:\n{formatted}"
