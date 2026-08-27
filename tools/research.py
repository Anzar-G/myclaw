"""Lightweight web research: search, collect snippets, and summarize."""
from config.tool_registry import BaseTool, ToolCategory
from llm.adaptive_runner import AdaptiveLLMRunner
import requests
from html.parser import HTMLParser
from urllib.parse import quote_plus, urlparse, parse_qs

class _SearchParser(HTMLParser):
    def __init__(self): super().__init__(); self.items=[]; self.href=None; self.buf=[]
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag == 'a' and 'result__a' in attrs.get('class',''): self.href=attrs.get('href'); self.buf=[]
    def handle_data(self, data):
        if self.href is not None: self.buf.append(data)
    def handle_endtag(self, tag):
        if tag == 'a' and self.href:
            title=' '.join(''.join(self.buf).split())
            if title: self.items.append((title,self.href))
            self.href=None

class _GoogleParser(HTMLParser):
    def __init__(self): super().__init__(); self.items=[]; self.href=None; self.in_h3=False; self.buf=[]
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag == 'a' and attrs.get('href','').startswith('http'): self.href=attrs['href']; self.buf=[]
        if tag == 'h3': self.in_h3=True; self.buf=[]
    def handle_data(self, data):
        if self.in_h3: self.buf.append(data)
    def handle_endtag(self, tag):
        if tag == 'h3':
            title=' '.join(''.join(self.buf).split())
            if title and self.href: self.items.append((title,self.href))
            self.in_h3=False; self.href=None

class _BingParser(HTMLParser):
    def __init__(self): super().__init__(); self.items=[]; self.href=None; self.in_h2=False; self.buf=[]
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag == 'a' and attrs.get('href','').startswith('http'): self.href=attrs['href']
        if tag == 'h2': self.in_h2=True; self.buf=[]
    def handle_data(self, data):
        if self.in_h2: self.buf.append(data)
    def handle_endtag(self, tag):
        if tag == 'h2':
            title=' '.join(''.join(self.buf).split())
            if title and self.href: self.items.append((title,self.href))
            self.in_h2=False; self.href=None

class WebResearchTool(BaseTool):
    name = "web_research"
    description = "Mencari berita/informasi terbaru dari web dan merangkumnya. Params: query, max_sources (opsional)"
    category = ToolCategory.WEB
    async def execute(self, query: str, max_sources: int = 5) -> str:
        try:
            response=requests.get("https://html.duckduckgo.com/html/?q="+quote_plus(query),headers={"User-Agent":"MyClaw research/1.0"},timeout=20)
            response.raise_for_status(); parser=_SearchParser(); parser.feed(response.text)
        except requests.exceptions.SSLError:
            # Some networks intercept DuckDuckGo TLS; use Bing as a verified fallback.
            response=requests.get("https://www.bing.com/search?q="+quote_plus(query),headers={"User-Agent":"Mozilla/5.0"},timeout=20)
            response.raise_for_status(); parser=_BingParser(); parser.feed(response.text)
        results=parser.items[:max(1,min(int(max_sources),8))]
        if not results: return "Tidak menemukan sumber untuk query tersebut."
        sources='\n'.join(f"[{i+1}] {title}\nURL: {url}" for i,(title,url) in enumerate(results))
        prompt=(f"Rangkum hasil riset berikut dalam bahasa Indonesia. Query: {query}\n"
                "Gunakan hanya informasi dari judul/URL, jangan mengarang fakta. Sertakan sumber.\n\n"+sources)
        summary=await AdaptiveLLMRunner().generate(prompt,temperature=0.2)
        return f"Hasil riset untuk: {query}\n\n{summary}\n\nSumber:\n{sources}"
