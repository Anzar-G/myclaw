"""Minimal sequential workflow engine with explicit tool steps."""
from dataclasses import dataclass
from typing import Any

@dataclass
class Workflow:
    name: str
    description: str
    steps: list[dict[str, Any]]

class WorkflowRunner:
    def __init__(self, registry):
        self.registry = registry
        self.workflows = {
            "system_report": Workflow("system_report", "Laporan status Mac lengkap", [
                {"tool": "system_info", "params": {}},
                {"tool": "battery_status", "params": {}},
                {"tool": "active_app", "params": {}},
            ]),
            "capture_screen": Workflow("capture_screen", "Screenshot dan kirim ke Telegram", [
                {"tool": "take_screenshot", "params": {"path": "workflow_screenshot.png"}},
            ]),
        }

    async def run(self, name: str) -> list[dict[str, Any]]:
        workflow = self.workflows.get(name.casefold())
        if not workflow:
            raise ValueError(f"Workflow tidak ditemukan: {name}")
        results = []
        for index, step in enumerate(workflow.steps, 1):
            tool_name = step["tool"]
            try:
                result = await self.registry.get_tool(tool_name).safe_execute(**step.get("params", {}))
                results.append({"step": index, "tool": tool_name, "success": result.success, "message": result.message, "data": result.data})
                if not result.success:
                    break
            except Exception as exc:
                results.append({"step": index, "tool": tool_name, "success": False, "message": str(exc)})
                break
        return results
