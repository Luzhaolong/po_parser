import streamlit as st
import pandas as pd
import numpy as np
from helpers.config import EXAMPLE_QUESTIONS


def apply_custom_css():
    """Apply custom CSS styling to the Streamlit app"""
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(135deg, #C0C0C0 0%, #FFD700 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .main-header h1 {
        color: white;
        margin: 0;
        text-align: center;
    }
    .main-header p {
        color: rgba(255, 255, 255, 0.8);
        text-align: center;
        margin: 0.5rem 0 0 0;
    }
    .agent-message {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
    .llm-enhanced {
        border-left: 4px solid #28a745;
        background: linear-gradient(90deg, #f8f9fa 0%, #e8f5e8 100%);
    }
    .user-message {
        background-color: #e8f4f8;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
    .insight-box {
        background: linear-gradient(135deg, #667eea22 0%, #764ba222 100%);
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #667eea44;
        margin: 1rem 0;
    }
    .stats-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .openai-status {
        padding: 0.5rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .openai-connected {
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    .openai-disconnected {
        background-color: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
    }
    </style>
    """, unsafe_allow_html=True)
    
def render_header():
    """Render the main header of the application"""
    col1, col2 = st.columns([1, 6])  # Define the column layout
    with col1:
        # Display the logo in the first column
        st.image("logo.png", caption="", use_container_width=True)

    with col2:
        # Render the header content in the second column
        st.markdown("""
        <div class="main-header">
            <h1>ILM Order Tracker Assistant</h1>
            <p>AI-powered chatbot with AutoGen agents and OpenAI LLM integration</p>
        </div>
        """, unsafe_allow_html=True)


def render_openai_config(chat_system):
    """Render OpenAI configuration section"""
    st.subheader("🔑 OpenAI API Setup")
    
    # API Key input
    api_key_input = st.text_input(
        "OpenAI API Key",
        type="password",
        help="Enter your OpenAI API key for enhanced LLM responses"
    )
    
    if api_key_input and not st.session_state.openai_configured:
        if st.button("🔗 Connect to OpenAI"):
            with st.spinner("Connecting to OpenAI..."):
                success = chat_system.initialize_openai(api_key_input)
                if success:
                    st.session_state.openai_configured = True
                    st.success("✅ OpenAI connected successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to connect to OpenAI. Check your API key.")
    
    # Show connection status
    if st.session_state.openai_configured:
        st.markdown("""
        <div class="openai-status openai-connected">
            ✅ OpenAI LLM: Connected
        </div>
        """, unsafe_allow_html=True)
        return True
    else:
        st.markdown("""
        <div class="openai-status openai-disconnected">
            ❌ OpenAI LLM: Not Connected
        </div>
        """, unsafe_allow_html=True)
        return False


def render_llm_settings(chat_system, openai_connected):
    """Render LLM settings section"""
    if openai_connected:
        st.subheader("LLM Settings")
        chat_system.use_llm_enhancement = st.checkbox(
            "Enable LLM Enhancement", 
            value=True,
            help="Use OpenAI LLM for enhanced natural language understanding"
        )
        
        auto_insights = st.checkbox(
            "Auto-generate Business Insights",
            value=False,
            help="Automatically generate business insights for each query"
        )
        return auto_insights
    return False


def render_file_upload():
    """Render file upload section and return uploaded dataframe"""
    st.header("📁 Data Source")
    
    uploaded_file = st.file_uploader(
        "Upload ILM_Order_Tracker.csv",
        type=['csv'],
        help="Upload your CSV file to start analyzing"
    )
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.session_state.df = df
            
            st.success(f"✅ Successfully loaded {len(df)} records!")
            
            # Data overview
            st.subheader("📊 Data Overview")
            st.markdown(f"""
            <div class="stats-container">
                <strong>Records:</strong> {len(df)}<br>
                <strong>Columns:</strong> {len(df.columns)}<br>
                <strong>Numeric Fields:</strong> {len(df.select_dtypes(include=[np.number]).columns)}<br>
                <strong>Text Fields:</strong> {len(df.select_dtypes(include=['object']).columns)}
            </div>
            """, unsafe_allow_html=True)
            
            # Column information
            with st.expander("🔍 Column Details"):
                for i, col in enumerate(df.columns, 1):
                    col_type = str(df[col].dtype)
                    unique_vals = df[col].nunique()
                    st.write(f"{i}. **{col}** ({col_type}) - {unique_vals} unique values")
            
            return df
            
        except Exception as e:
            st.error(f"❌ Error loading file: {str(e)}")
            return None
    
    return None


def render_example_questions():
    """Render example questions section"""
    st.write('---')
    st.subheader("💡 Example Questions")
    
    for question in EXAMPLE_QUESTIONS:
        if st.button(question, key=f"example_{hash(question)}"):
            if st.session_state.df is not None:
                st.session_state.messages.append({"role": "user", "content": question})
                st.rerun()


def render_agent_status(chat_system):
    """Render agent system status"""
    st.subheader("🔧 Agents' Status")
    
    # Agent status
    agents = chat_system.agents
    for agent_key, agent in agents.items():
        with st.expander(f"🤖 {agent.name}", expanded=True):
            st.write(f"**Role:** {agent.role}")
            st.write(f"**Status:** {'🟢 Ready' if st.session_state.df is not None else '🔴 Waiting for data'}")
            st.write(f"**Conversations:** {len(agent.conversation_history)}")


def render_system_metrics():
    """Render system metrics"""
    if st.session_state.df is not None:
        st.subheader("📈 System Metrics")
        st.metric("Data Loaded", "✅ Yes")
        st.metric("Total Messages", len(st.session_state.messages))
        st.metric("Agent Responses", len([m for m in st.session_state.messages if m['role'] == 'assistant']))


def render_chat_message(message):
    """Render individual chat message"""
    if message["role"] == "user":
        st.markdown(f"""
        <div class="user-message">
            <strong>👤 You:</strong><br>
            {message["content"]}
        </div>
        """, unsafe_allow_html=True)
    else:
        # Determine message class based on LLM enhancement
        message_class = "agent-message llm-enhanced" if message.get('llm_enhanced', False) else "agent-message"
        enhancement_indicator = "🧠 LLM Enhanced" if message.get('llm_enhanced', False) else "📊 Traditional"
        
        st.markdown(f"""
        <div class="{message_class}">
            <strong>🤖 {message.get('agent', 'Assistant')} ({enhancement_indicator}):</strong><br>
            {message["content"]}
        </div>
        """, unsafe_allow_html=True)
        
        # Show chart if available
        if 'chart' in message and message['chart'] is not None:
            st.plotly_chart(message['chart'], use_container_width=True)
        
        # Show table if available
        if 'show_table' in message and message['show_table']:
            if 'data' in message and message['data']:
                st.dataframe(pd.DataFrame(message['data']), use_container_width=True)
        
        # Show insights if available
        if 'insights' in message and message['insights']:
            st.markdown(f"""
            <div class="insight-box">
                <strong>💡 Business Insights:</strong><br>
                {message['insights']}
            </div>
            """, unsafe_allow_html=True)


def render_footer():
    """Render application footer"""
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666;">
        <p>🤖 Powered by AutoGen Multi-Agent System + OpenAI | Built with Streamlit</p>
    </div>
    """, unsafe_allow_html=True)