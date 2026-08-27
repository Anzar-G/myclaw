"""
Notion Integration Tool using official notion-client SDK
"""
from config.tool_registry import BaseTool, ToolCategory
from config.settings import settings
from loguru import logger


def _get_notion_client():
    from notion_client import Client
    token = settings.notion_api_token
    if not token:
        raise Exception("NOTION_API_TOKEN belum diisi di file .env!")
    return Client(auth=token)


class NotionCreatePageTool(BaseTool):
    name = "notion_create_page"
    description = "Membuat halaman baru di Notion database. Params: database_id, title, content"
    category = ToolCategory.DATABASE
    
    async def execute(self, database_id: str, title: str, content: str) -> str:
        client = _get_notion_client()
        
        new_page = client.pages.create(
            parent={"database_id": database_id},
            properties={
                "Name": {"title": [{"text": {"content": title}}]}
            },
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": content}}]
                    }
                }
            ]
        )
        
        page_url = new_page.get("url", "")
        return f"Halaman Notion '{title}' berhasil dibuat!\nURL: {page_url}"


class NotionReadDatabaseTool(BaseTool):
    name = "notion_read_database"
    description = "Membaca isi database Notion. Params: database_id"
    category = ToolCategory.DATABASE
    
    async def execute(self, database_id: str) -> str:
        client = _get_notion_client()
        
        results = client.databases.query(database_id=database_id, page_size=10)
        pages = results.get("results", [])
        
        if not pages:
            return "Database Notion ini kosong."
        
        entries = []
        for page in pages:
            props = page.get("properties", {})
            # Coba ambil property 'Name' atau property pertama yang bertipe title
            title_value = "(Untitled)"
            for key, val in props.items():
                if val.get("type") == "title":
                    title_items = val.get("title", [])
                    if title_items:
                        title_value = title_items[0].get("text", {}).get("content", "(Untitled)")
                    break
            entries.append(f"• {title_value}")
        
        return f"📋 {len(entries)} entri di database Notion:\n" + "\n".join(entries)


class NotionAddCommentTool(BaseTool):
    name = "notion_add_comment"
    description = "Menambahkan komentar/blok teks ke halaman Notion yang sudah ada. Params: page_id, comment_text"
    category = ToolCategory.DATABASE
    
    async def execute(self, page_id: str, comment_text: str) -> str:
        client = _get_notion_client()
        
        client.blocks.children.append(
            block_id=page_id,
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": comment_text}}]
                    }
                }
            ]
        )
        
        return f"Berhasil menambahkan konten ke halaman Notion {page_id}."
