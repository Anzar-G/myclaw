"""
Browser Automation using Playwright
"""
from config.tool_registry import BaseTool, ToolCategory
from loguru import logger

class OpenBrowserTool(BaseTool):
    name = "open_website"
    description = "Membuka website dan mengambil teks kontennya. Params: url"
    category = ToolCategory.WEB
    
    async def execute(self, url: str) -> str:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise Exception("Playwright belum ter-install. Silakan jalankan 'pip install playwright' dan 'playwright install'.")
            
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=30000)
            
            title = await page.title()
            body_text = await page.evaluate("document.body.innerText")
            
            await browser.close()
            return f"Judul: {title}\n\nKonten: {body_text[:1500]}...\n[Teks dipotong demi menghemat token]"

class BrowserScreenshotTool(BaseTool):
    name = "browser_screenshot"
    description = "Mengambil tangkapan layar (screenshot) dari sebuah website secara langsung di background. Params: url, path (opsional)"
    category = ToolCategory.WEB
    async def execute(self, url: str, path: str = "web_screenshot.png") -> dict:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url)
            await page.screenshot(path=path)
            await browser.close()
            return {
                "type": "file",
                "path": path,
                "caption": f"Screenshot of {url}"
            }

class BrowserActionTool(BaseTool):
    name = "browser_action"
    description = "Melakukan aksi kompleks di browser (click, type, submit). Params: url, actions (list of dicts like {'action': 'click', 'selector': '...'})"
    category = ToolCategory.WEB
    async def execute(self, url: str, actions: list) -> str:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False) # Headless False to see it? Maybe not for background agent.
            page = await browser.new_page()
            await page.goto(url)
            
            for action in actions:
                type_ = action.get('type')
                selector = action.get('selector')
                value = action.get('value')
                
                if type_ == 'click':
                    await page.click(selector)
                elif type_ == 'type':
                    await page.fill(selector, value)
                elif type_ == 'wait':
                    await page.wait_for_timeout(value if value else 1000)
            
            final_url = page.url
            content = await page.evaluate("document.body.innerText")
            await browser.close()
            return f"Aksi selesai di {final_url}. Konten akhir: {content[:500]}"
