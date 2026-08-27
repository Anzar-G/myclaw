"""
Adaptive LLM runner yang auto-select API provider (Groq -> OpenRouter -> Gemini)
"""

import asyncio
from typing import Optional, Dict
from loguru import logger
import requests
import json
from config.settings import settings

class AdaptiveLLMRunner:
    """Intelligent LLM runner dengan API fallback logic"""
    
    def __init__(self):
        self.providers = []
        if settings.groq_api_key:
            self.providers.append({
                "name": "Groq",
                "url": "https://api.groq.com/openai/v1/chat/completions",
                "key": settings.groq_api_key,
                "model": "openai/gpt-oss-120b"
            })
        if settings.openrouter_api_key:
            self.providers.append({
                "name": "OpenRouter",
                "url": "https://openrouter.ai/api/v1/chat/completions",
                "key": settings.openrouter_api_key,
                "model": "openai/gpt-oss-120b"
            })
        if settings.gemini_api_key:
            self.providers.append({
                "name": "Gemini",
                "url": f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={settings.gemini_api_key}",
                "key": "",
                "model": "gemini-3.5-flash"
            })
            
        self.selected_model = self.providers[0]["name"] if self.providers else "mock"
    
    async def generate(self, prompt: str, temperature: float = 0.3, timeout: int = 30) -> str:
        if not self.providers:
            logger.warning("Tidak ada API key yang terkonfigurasi. Generating mock response.")
            await asyncio.sleep(1)
            return f"Mock response (No API Key) for prompt: {prompt[:50]}..."
            
        for provider in self.providers:
            try:
                logger.info(f"Mencoba provider: {provider['name']}...")
                if provider["name"] == "Gemini":
                    return await self._generate_gemini(prompt, provider, temperature, timeout)
                else:
                    return await self._generate_openai_compatible(prompt, provider, temperature, timeout)
            except Exception as e:
                logger.warning(f"Provider {provider['name']} gagal: {e}. Mencoba fallback...")
                continue
                
        return "Maaf, semua API provider gagal memproses permintaan Anda."
        
    async def _generate_openai_compatible(self, prompt: str, provider: dict, temperature: float, timeout: int) -> str:
        headers = {
            "Authorization": f"Bearer {provider['key']}",
            "Content-Type": "application/json"
        }
        if provider["name"] == "OpenRouter":
            headers["HTTP-Referer"] = "https://myclaw.agent"
            headers["X-Title"] = "MyClaw Agent"
            
        payload = {
            "model": provider["model"],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature
        }
        
        response = await asyncio.to_thread(
            requests.post, provider["url"], headers=headers, json=payload, timeout=timeout
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        raise RuntimeError(f"API error: {response.text}")

    async def _generate_gemini(self, prompt: str, provider: dict, temperature: float, timeout: int) -> str:
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature}
        }
        
        response = await asyncio.to_thread(
            requests.post, provider["url"], headers=headers, json=payload, timeout=timeout
        )
        if response.status_code == 200:
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]
        raise RuntimeError(f"API error: {response.text}")
