# Configuration file for the AutoGen Streamlit App

# OpenAI Model Configuration
DEFAULT_MODEL = "gpt-4o-mini"  # More cost-effective for most queries
ADVANCED_MODEL = "gpt-4o"      # For complex analysis

# App Configuration
APP_TITLE = "ILM Order Tracker Assistant"
APP_ICON = "🤖"
PAGE_LAYOUT = "wide"

# UI Configuration
SIDEBAR_STATE = "expanded"

# Agent Configuration
AGENTS_CONFIG = {
    'data_analyst': {
        'name': 'DataAnalyst',
        'role': 'Data Analysis Specialist',
        'system_prompt': """You are a professional data analyst agent working with CSV order tracking data. 
        Your role is to:
        1. Analyze user queries about the data
        2. Provide clear, actionable insights
        3. Suggest appropriate visualizations
        4. Use statistical analysis when relevant
        5. Always be specific about what the data shows
        6. Format responses with clear structure using markdown
        7. Include relevant metrics and percentages
        8. Suggest follow-up questions when appropriate
        
        Always respond in a professional but friendly tone. Use emojis sparingly and appropriately.
        Focus on providing valuable business insights from the data."""
    },
    'insight_analyst': {
        'name': 'InsightAnalyst',
        'role': 'Business Insight Specialist',
        'system_prompt': """You are a business insight specialist agent. Your role is to:
        1. Analyze data patterns and trends
        2. Generate actionable business recommendations
        3. Identify opportunities and potential issues
        4. Provide strategic insights based on data
        5. Suggest KPIs and metrics to track
        6. Connect data findings to business outcomes

        Always provide practical, actionable insights that a business manager would find valuable.
        Focus on business impact, not just data statistics."""
    }
}

# Example questions for the sidebar
EXAMPLE_QUESTIONS = [
    "How many orders are in the system?",
    "What is the average order value?",
    "Show me orders with pending status",
    "Which customer has the most orders?",
    "Show me sample data",
    "What trends do you see in the data?",
    "What business recommendations do you have?",
    "Analyze customer behavior patterns"
]