"""
Human-in-the-loop approval system for destructive actions
"""

from enum import Enum
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass
from loguru import logger
import asyncio
from datetime import datetime, timedelta
import json
from pathlib import Path

# Assuming settings is still needed for configuration, e.g., approval_timeout
from config.settings import settings

class ActionRiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# Moved PendingApproval class to telegram_bot.py as it contains telegram-specific fields
# The ApprovalManager will now just manage the events and results for approvals

class ApprovalManager:
    RISK_LEVELS = {
        "write_file": ActionRiskLevel.MEDIUM,
        "delete_file": ActionRiskLevel.CRITICAL, # Changed to Critical as per user feedback
        "update_notion": ActionRiskLevel.MEDIUM,
        "send_email": ActionRiskLevel.HIGH,
        "system_automation": ActionRiskLevel.CRITICAL,
        "open_browser_tab": ActionRiskLevel.LOW,
        "close_browser_tab": ActionRiskLevel.MEDIUM,
        "search_in_browser": ActionRiskLevel.LOW,
        "switch_browser_tab": ActionRiskLevel.LOW,
        "search_in_finder": ActionRiskLevel.LOW,
        "open_folder": ActionRiskLevel.LOW,
        "list_files": ActionRiskLevel.LOW,
        "sleep_mac": ActionRiskLevel.MEDIUM,
        "shutdown_mac": ActionRiskLevel.CRITICAL,
        "restart_mac": ActionRiskLevel.CRITICAL, # Changed to Critical
        "lock_screen": ActionRiskLevel.MEDIUM,
        "set_volume": ActionRiskLevel.LOW,
        "play_notification_sound": ActionRiskLevel.LOW,
        "type_text": ActionRiskLevel.MEDIUM,
        "press_key": ActionRiskLevel.MEDIUM,
        "mouse_click": ActionRiskLevel.HIGH, # Clicking can be highly disruptive
        "mouse_move": ActionRiskLevel.LOW,
        "take_screenshot": ActionRiskLevel.LOW,
        "open_app": ActionRiskLevel.LOW,
        "close_app": ActionRiskLevel.MEDIUM,
        "switch_app": ActionRiskLevel.LOW,
        "get_active_app": ActionRiskLevel.LOW,
        "execute_shortcut": ActionRiskLevel.HIGH, # Shortcuts can be powerful
        "whatsapp_send": ActionRiskLevel.MEDIUM,
        "whatsapp_read": ActionRiskLevel.LOW,
        "read_email": ActionRiskLevel.LOW,
        "notion_create_page": ActionRiskLevel.MEDIUM,
        "notion_read_database": ActionRiskLevel.LOW,
        "notion_add_comment": ActionRiskLevel.MEDIUM,
    }
    
    def __init__(self, approval_timeout: int = 300, on_approval_requested_callback: Optional[Callable] = None):
        self.approval_timeout = approval_timeout
        self.on_approval_requested_callback = on_approval_requested_callback
        
        # Internal state to manage approval events and results for blocking calls
        self.pending_approval_events: Dict[str, asyncio.Event] = {}
        self.pending_approval_results: Dict[str, bool] = {}
        logger.info("ApprovalManager initialized.")
    
    def get_risk_level(self, tool_name: str) -> ActionRiskLevel:
        return self.RISK_LEVELS.get(tool_name, ActionRiskLevel.MEDIUM) # Default to Medium if not specified
    
    async def should_require_approval(self, tool_name: str, parameters: Dict) -> bool:
        risk_level = self.get_risk_level(tool_name)
        
        # Specific overrides for more nuanced approval logic
        if tool_name == "delete_file":
            return True # Always require approval for file deletion
        if tool_name == "send_email":
            recipients = parameters.get("to", "")
            if isinstance(recipients, str):
                recipients = [r.strip() for r in recipients.split(',') if r.strip()]
            return len(recipients) > 1 # Require approval if sending to multiple recipients
        if risk_level in {ActionRiskLevel.MEDIUM, ActionRiskLevel.HIGH, ActionRiskLevel.CRITICAL}:
            return True
        return False
    
    async def request_approval(self, action_id: str, tool_name: str, parameters: Dict, action_description: str) -> bool:
        """
        Requests approval for an action and waits for the response.
        This method is blocking until an approval decision is received or timeout.
        """
        if not self.on_approval_requested_callback:
            logger.warning(f"No approval callback set. Rejecting action: {tool_name} - {action_description}")
            return False
            
        logger.info(f"Requesting approval for action_id: {action_id}, tool: {tool_name}")
        
        # Create an Event to wait for the approval decision
        event = asyncio.Event()
        self.pending_approval_events[action_id] = event
        
        try:
            # Call the external callback to send the approval request
            # The callback must eventually call self.set_approval_result(action_id, approved)
            await self.on_approval_requested_callback(
                action_id=action_id,
                tool_name=tool_name,
                parameters=parameters,
                action_description=action_description,
                risk_level=self.get_risk_level(tool_name),
                timeout=self.approval_timeout
            )
            
            # Wait for the approval decision or timeout
            try:
                await asyncio.wait_for(event.wait(), timeout=self.approval_timeout)
            except asyncio.TimeoutError:
                logger.warning(f"Approval for action_id {action_id} timed out.")
                self.pending_approval_results[action_id] = False # Mark as rejected on timeout
            
            approved = self.pending_approval_results.get(action_id, False)
            return approved
            
        finally:
            # Clean up the event and result after decision or timeout
            if action_id in self.pending_approval_events:
                del self.pending_approval_events[action_id]
            if action_id in self.pending_approval_results:
                del self.pending_approval_results[action_id]

    def set_approval_result(self, action_id: str, approved: bool):
        """
        Called by the external approval mechanism (e.g., Telegram bot, Streamlit UI)
        to set the result of a pending approval and unblock the waiting task.
        """
        if action_id in self.pending_approval_events:
            self.pending_approval_results[action_id] = approved
            self.pending_approval_events[action_id].set()
            logger.info(f"Approval result set for action_id {action_id}: {'Approved' if approved else 'Rejected'}")
        else:
            logger.warning(f"Received approval result for unknown or expired action_id: {action_id}")
