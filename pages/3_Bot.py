import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv

# Import custom modules
from helpers.config import APP_TITLE, APP_ICON, PAGE_LAYOUT, SIDEBAR_STATE
from helpers.agent import AutoGenChatSystem
from helpers.ui_components import (
    apply_custom_css, render_header, render_openai_config, 
    render_llm_settings, render_file_upload, render_example_questions,
    render_agent_status, render_system_metrics, render_chat_message,
    render_footer
)

# Load environment variables
load_dotenv()

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.error("You must be logged in to access this page.")
    st.stop()  # Stop further execution of the page
    
def initialize_session_state():
    """Initialize Streamlit session state variables"""
    if 'chat_system' not in st.session_state:
        st.session_state.chat_system = AutoGenChatSystem()
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'df' not in st.session_state:
        st.session_state.df = None
    if 'openai_configured' not in st.session_state:
        st.session_state.openai_configured = False


def render_sidebar():
    """Render the complete sidebar"""
    with st.sidebar:
        st.header("🔧 Configuration")
        
        # OpenAI Configuration
        openai_connected = render_openai_config(st.session_state.chat_system)
        
        # LLM Settings
        auto_insights = render_llm_settings(st.session_state.chat_system, openai_connected)
        
        st.markdown("---")
        
        # File upload
        df = render_file_upload()
        
        # Example questions
        render_example_questions()
        
        return auto_insights


def render_main_chat():
    """Render the main chat interface"""
    st.subheader("💬 Chat with AutoGen + OpenAI Assistant")
    
    # Display chat messages
    chat_container = st.container()
    
    with chat_container:
        for message in st.session_state.messages:
            render_chat_message(message)
    
    # Chat input
    if st.session_state.df is not None:
        user_input = st.chat_input("Ask me about your order data...")
        
        return user_input
    else:
        st.info("👆 Please upload your CSV file to start chatting!")
        return None


def process_user_input(user_input, auto_insights):
    """Process user input and generate response"""
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Process with AutoGen system
    with st.spinner("🤖 AutoGen agents are analyzing your data..."):
        result = st.session_state.chat_system.process_message(
            st.session_state.df, 
            user_input, 
            generate_insights=auto_insights
        )
    
    # Add assistant response
    assistant_message = {
        "role": "assistant", 
        "content": result['response'],
        "agent": result['agent'],
        "llm_enhanced": result.get('llm_enhanced', False)
    }
    
    # Add additional data if available
    if result.get('chart') is not None:
        assistant_message['chart'] = result['chart']
    
    if result.get('show_table', False):
        assistant_message['show_table'] = True
        assistant_message['data'] = result['data']
    
    if result.get('insights'):
        assistant_message['insights'] = result['insights']
    
    st.session_state.messages.append(assistant_message)


def render_status_panel():
    """Render the status panel on the right"""
    # Agent status
    render_agent_status(st.session_state.chat_system)
    
    # System metrics
    render_system_metrics()
    
    # Clear chat button
    if st.button("🗑️ Clear Chat History", type="secondary"):
        st.session_state.messages = []
        st.session_state.chat_system = AutoGenChatSystem()
        st.rerun()


def main():
    """Main application function"""
    # Page configuration
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        layout=PAGE_LAYOUT,
        initial_sidebar_state=SIDEBAR_STATE
    )
    
    # Apply custom CSS
    apply_custom_css()
    
    # Render header
    render_header()
    
    # Initialize session state
    initialize_session_state()
    
    # Render sidebar and get settings
    auto_insights = render_sidebar()
    
    # Main content area
    col1, col2 = st.columns([4, 1])
    
    with col1:
        # Render main chat interface
        user_input = render_main_chat()
        
        # Process user input if provided
        if user_input:
            process_user_input(user_input, auto_insights)
            st.rerun()
    
    with col2:
        # Render status panel
        render_status_panel()
    
    # Render footer
    render_footer()


if __name__ == "__main__":
    main()