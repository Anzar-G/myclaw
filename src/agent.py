"""
Core Zero-Budget Agent Orchestrator with Tool Parsing
"""

import asyncio
import json
import re
from loguru import logger
from typing import Dict, Any, List
from config.settings import settings
from config.tool_registry import ToolRegistry
from llm.adaptive_runner import AdaptiveLLMRunner
from src.approval_manager import ApprovalManager
import time
import random

class ZeroBudgetAgent:
    def __init__(self, enable_approval_gates: bool = True, on_approval_requested_callback=None):
        self.tool_registry = ToolRegistry()
        self.approval_manager = ApprovalManager(on_approval_requested_callback=on_approval_requested_callback) if enable_approval_gates else None
        self.llm_runner = AdaptiveLLMRunner()
        
    def _build_system_prompt(self) -> str:
        tools_desc = []
        for name, tool in self.tool_registry.tools.items():
            tools_desc.append(f"- {name}: {tool.description}")
        tools_str = "\n".join(tools_desc)
        
        import os
        home_dir = os.path.expanduser("~")
        
        prompt = f"""You are MyClaw (also known as OpenClaw), an advanced, friendly, and highly capable personal AI assistant running locally on the user's Macbook. 
Your goal is to assist the user by having casual conversations OR executing actions on their machine.

System Context:
- OS: macOS
- User Home Directory: {home_dir}

Available Tools:
{tools_str}

CRITICAL INSTRUCTIONS:
1. If the user just wants to chat casually, respond with friendly, natural plain text.
2. If the user asks you to perform an action (e.g. open an app, read a file, send an email), you MUST use a tool.
3. To use a tool, you MUST output a JSON block wrapped in <tool> tags. DO NOT output any other text when using a tool.
   Format:
   <tool>{{"name": "tool_name", "params": {{"key": "value"}}}}</tool>
4. You can only use ONE tool at a time. After you use a tool, the system will execute it and give you the result, then you can talk to the user.
5. If the user asks you to open finder, open an app, etc, always use the tool! Do not just tell them how to do it.
6. CRITICAL: You MUST close the tag with </tool>.

Example of casual chat:
User: Halo apa kabar?
You: Halo! Kabar baik, saya MyClaw siap membantu Anda hari ini. Ada yang bisa saya bantu?

Example of using a tool:
User: Tolong buka Finder
You: <tool>{{"name": "open_finder_path", "params": {{"path": "/"}}}}</tool>
"""
        return prompt

    async def run(self, task_description: str, message_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        logger.info(f"Agent started with input: {task_description[:50]}...")
        
        system_prompt = self._build_system_prompt()
        
        # Build prompt context
        prompt = f"{system_prompt}\n\nUser: {task_description}\nYou:"
        
        # 1. Generate initial response via LLM
        final_response = await self.llm_runner.generate(prompt, temperature=0.3)
        
        # 2. Check if LLM emitted a tool call
        tool_call_match = re.search(r'<tool>(.*?)(?:</tool>|$)', final_response, re.DOTALL)
        
        execution_results = []
        
        if tool_call_match:
            try:
                tool_json_str = tool_call_match.group(1).strip()
                tool_data = json.loads(tool_json_str)
                
                tool_calls = [tool_data]
                state = {"tool_calls": tool_calls, "execution_results": []}
                
                # Execute the tool
                state = await self._execution_node(state)
                execution_results = state["execution_results"]
                
                tool_result_str = json.dumps(execution_results[0])
                followup_prompt = f"Pengguna sebelumnya meminta: '{task_description}'.\nSebagai asisten AI MyClaw, Anda baru saja menjalankan tool dan mendapatkan hasil berikut:\n{tool_result_str}\n\nJelaskan hasil ini kepada pengguna dengan bahasa Indonesia yang natural, singkat, dan ramah. Jawab HANYA dengan apa yang ingin Anda sampaikan ke pengguna."
                
                final_response = await self.llm_runner.generate(followup_prompt, temperature=0.5)
                
            except Exception as e:
                logger.error(f"Failed to parse or execute tool call: {e}")
                final_response = f"Maaf, saya mencoba mengeksekusi perintah tersebut namun terjadi kesalahan pemahaman sistem ({str(e)})."

        logger.info("Agent completed task.")
        return {
            "final_response": final_response,
            "execution_results": execution_results,
            "reasoning": {"task": task_description}
        }

    async def _execution_node(self, state: Dict) -> Dict:
        results = []
        for i, tool_call in enumerate(state['tool_calls']):
            tool_name = tool_call.get('name')
            params = tool_call.get('params', {})
            
            if self.approval_manager:
                needs_approval = await self.approval_manager.should_require_approval(tool_name, params)
                if needs_approval:
                    action_id = f"{tool_name}_{int(time.time())}_{random.randint(1000, 9999)}"
                    action_desc = f"Execute {tool_name} with {json.dumps(params)}"
                    approved = await self.approval_manager.request_approval(action_id, tool_name, params, action_desc)
                    if not approved:
                        logger.warning(f"⛔ Action rejected by user: {tool_name}")
                        results.append({"tool": tool_name, "step": i + 1, "success": False, "message": "Rejected by user approval"})
                        continue
            
            try:
                tool = self.tool_registry.get_tool(tool_name)
                result = await tool.safe_execute(**params)
                results.append({
                    "tool": tool_name,
                    "success": result.success,
                    "message": result.message,
                    "data": str(result.data)[:1000]
                })
            except Exception as e:
                results.append({"tool": tool_name, "success": False, "error": str(e)})
        
        state['execution_results'] = results
        return state
