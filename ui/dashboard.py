"""
Streamlit-based UI untuk Zero-Budget Agent
"""

import streamlit as st
import asyncio
import json
from datetime import datetime
from pathlib import Path
from loguru import logger
import pandas as pd
import plotly.express as px

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent import ZeroBudgetAgent
from config.settings import settings

st.set_page_config(
    page_title="🤖 Zero-Budget AI Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.title("🎛️ Control Panel")
page = st.sidebar.radio(
    "Navigate to:",
    ["📊 Dashboard", "🚀 New Task", "📝 Task History", "⚙️ Settings", "📋 Memory"]
)

with st.sidebar.expander("🔍 System Status", expanded=True):
    status_cols = st.columns(2)
    with status_cols[0]:
        groq_ok = bool(settings.groq_api_key)
        st.metric(
            "LLM API",
            "✅ Ready" if groq_ok else "❌ No Key",
            delta="Groq/Gemini"
        )
    with status_cols[1]:
        mem_path = Path(settings.data_dir) / "memory.json"
        st.metric(
            "Memory DB",
            "✅ Ready" if mem_path.exists() else "⚠️ Init needed",
            delta="JSON Fallback"
        )
    
    st.subheader("API Services")
    services = settings.validate_required_services()
    for service, available in services.items():
        icon = "✅" if available else "❌"
        st.write(f"{icon} {service}")

if page == "📊 Dashboard":
    st.title("🤖 Zero-Budget AI Agent Dashboard")
    col1, col2, col3 = st.columns(3)
    col1.metric("Tasks Completed", "12", delta="+3 today")
    col2.metric("Memory Items", "456", delta="+42 today")
    col3.metric("Uptime", "23h 45m", delta="99.2%")
    
    st.subheader("📈 Recent Executions")
    df_executions = pd.DataFrame({
        "Time": pd.date_range("2024-01-01", periods=10, freq="1h"),
        "Task": ["Research", "Email", "Notion", "File", "Research"] * 2,
        "Status": ["✅"] * 8 + ["⚠️", "✅"],
        "Duration (s)": [12, 5, 8, 3, 15, 9, 7, 6, 20, 4]
    })
    fig = px.bar(df_executions, x="Time", y="Duration (s)", color="Task", title="Task Execution Timeline")
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("📋 Recent Logs")
    log_file = Path(settings.log_file)
    if log_file.exists():
        with open(log_file, 'r') as f:
            logs = f.readlines()[-20:]
        with st.container():
            for line in logs:
                try:
                    log_data = json.loads(line)
                    if log_data["level"] == "ERROR":
                        st.error(log_data["message"])
                    elif log_data["level"] == "WARNING":
                        st.warning(log_data["message"])
                    else:
                        st.text(f"[{log_data['level']}] {log_data['message']}")
                except:
                    st.text(line.strip())

elif page == "🚀 New Task":
    st.title("🚀 Submit New Task")
    with st.form("task_form"):
        task_description = st.text_area("📝 Describe what you want the agent to do:", height=150)
        with st.expander("⚙️ Advanced Options"):
            require_approval = st.checkbox("🔒 Require Approval Before Execution", value=True)
            timeout = st.number_input("⏱️ Task Timeout (seconds)", min_value=30, max_value=3600, value=300)
        submitted = st.form_submit_button("🚀 Submit Task", use_container_width=True, type="primary")
    
    if submitted and task_description:
        st.info("⏳ Task submitted! Processing...")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            agent = ZeroBudgetAgent(enable_approval_gates=require_approval)
            status_text.text("🔍 Searching memory and reasoning...")
            progress_bar.progress(30)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(agent.run(task_description))
            loop.close()
            
            status_text.text("✅ Task completed!")
            progress_bar.progress(100)
            
            st.success("Task Completed Successfully!")
            st.subheader("📋 Agent Response")
            st.write(result['final_response'])
            
            st.subheader("🔧 Execution Details")
            exec_df = pd.DataFrame(result['execution_results'])
            if not exec_df.empty:
                display_cols = [c for c in ['tool', 'success', 'message', 'data'] if c in exec_df.columns]
                st.dataframe(exec_df[display_cols], use_container_width=True, hide_index=True)
            
            with st.expander("🧠 Detailed Reasoning"):
                st.json(result.get('reasoning', {}))
        except Exception as e:
            st.error(f"❌ Task failed: {str(e)}")

elif page == "📝 Task History":
    st.title("📝 Task History & Analytics")
    log_file = Path(settings.log_file)
    if log_file.exists():
        with open(log_file, 'r') as f:
            content = f.read()
        total_tasks = content.count("Agent started")
        st.metric("Total Tasks Handled", total_tasks)
        st.info("Log analytics display would appear here in full production.")

elif page == "⚙️ Settings":
    st.title("⚙️ Configuration Settings")
    st.info(f"LLM Providers: Groq → OpenRouter → Gemini (fallback chain)")
    
    from config.tool_registry import ToolRegistry
    registry = ToolRegistry()
    st.dataframe(pd.DataFrame([{"Tool": name, "Description": tool.description} for name, tool in registry.tools.items()]))

elif page == "📋 Memory":
    st.title("💾 Memory Management")
    from memory.memory_manager import MemoryManager
    memory_mgr = MemoryManager()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    all_memories = loop.run_until_complete(memory_mgr.get_all())
    loop.close()
    
    st.metric("Total Memories", len(all_memories))
    st.subheader("🔍 Search Memory")
    search_query = st.text_input("Enter search query:")
    if search_query:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(memory_mgr.search(search_query))
        loop.close()
        for i, memory in enumerate(results, 1):
            with st.expander(f"Result {i} - {memory.get('similarity', 0):.2%}"):
                st.write(memory['content'])
