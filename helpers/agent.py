import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from typing import Dict, List, Any, Optional
from openai import OpenAI
import streamlit as st
#from config import DEFAULT_MODEL, ADVANCED_MODEL
from dotenv import load_dotenv
import os

# Load variables from .env into the environment
load_dotenv()

# Access them
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL","gpt-4o-mini")
ADVANCED_MODEL = os.getenv("ADVANCED_MODEL","gpt-4o")

class OpenAILLMAgent:
    """Base agent class with OpenAI LLM integration"""
    
    def __init__(self, name: str, role: str, system_prompt: str):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.conversation_history = []
        self.client = None
        
    def initialize_client(self, api_key: str):
        """Initialize OpenAI client with API key"""
        try:
            self.client = OpenAI(api_key=api_key)
            return True
        except Exception as e:
            st.error(f"Failed to initialize OpenAI client: {str(e)}")
            return False
    
    def generate_response(self, user_query: str, data_context: str, use_advanced_model: bool = False) -> str:
        """Generate response using OpenAI LLM"""
        if not self.client:
            return "❌ OpenAI client not initialized. Please check your API key."
        
        model = ADVANCED_MODEL if use_advanced_model else DEFAULT_MODEL
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "system", "content": f"Data Context: {data_context}"},
            {"role": "user", "content": user_query}
        ]
        
        # Add recent conversation history for context
        if self.conversation_history:
            recent_history = self.conversation_history[-4:]  # Last 4 exchanges
            for entry in recent_history:
                if entry.startswith("User:"):
                    messages.insert(-1, {"role": "user", "content": entry[5:]})
                elif entry.startswith("Agent:"):
                    messages.insert(-1, {"role": "assistant", "content": entry[6:]})
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.1,
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Error generating response: {str(e)}"


class DataAnalysisAgent(OpenAILLMAgent):
    """AutoGen-style agent for data analysis with LLM integration"""
    
    def analyze_data(self, df: pd.DataFrame, query: str, use_llm: bool = True) -> Dict[str, Any]:
        """Analyze data based on user query with optional LLM enhancement"""
        self.conversation_history.append(f"User: {query}")
        
        try:
            # Import analysis functions from separate module
            from helpers.data_analysis import DataAnalyzer
            analyzer = DataAnalyzer()
            basic_result = analyzer.process_query(df, query)
            
            if use_llm and self.client:
                # Enhance with LLM analysis
                data_context = self._generate_data_context(df)
                llm_response = self.generate_response(query, data_context)
                
                # Combine traditional analysis with LLM insights
                enhanced_response = self._combine_responses(basic_result['response'], llm_response)
                basic_result['response'] = enhanced_response
                basic_result['llm_enhanced'] = True
            
            self.conversation_history.append(f"Agent: {basic_result['response']}")
            return basic_result
            
        except Exception as e:
            error_result = {
                'response': f"❌ Error analyzing data: {str(e)}",
                'data': None,
                'chart': None,
                'agent': self.name,
                'llm_enhanced': False
            }
            self.conversation_history.append(f"Agent: {error_result['response']}")
            return error_result
    
    def _generate_data_context(self, df: pd.DataFrame) -> str:
        """Generate context about the data for LLM"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
        
        context_parts = [
            f"Dataset has {len(df)} rows and {len(df.columns)} columns.",
            f"Columns: {', '.join(df.columns.tolist())}",
            f"Numeric columns: {', '.join(numeric_cols) if numeric_cols else 'None'}",
            f"Categorical columns: {', '.join(categorical_cols) if categorical_cols else 'None'}"
        ]
        
        # Add sample statistics
        if numeric_cols:
            for col in numeric_cols[:3]:  # First 3 numeric columns
                stats = df[col].describe()
                context_parts.append(f"{col}: mean={stats['mean']:.2f}, min={stats['min']:.2f}, max={stats['max']:.2f}")
        
        # Add categorical summaries
        if categorical_cols:
            for col in categorical_cols[:3]:  # First 3 categorical columns
                value_counts = df[col].value_counts()
                top_values = value_counts.head(3)
                context_parts.append(f"{col} top values: {dict(top_values)}")
        
        return " | ".join(context_parts)
    
    def _combine_responses(self, traditional_response: str, llm_response: str) -> str:
        """Combine traditional analysis with LLM insights"""
        # If LLM response is substantial, use it; otherwise combine both
        if len(llm_response) > 100 and not llm_response.startswith("❌"):
            return f"{llm_response}\n\n---\n**Technical Analysis:**\n{traditional_response}"
        else:
            return traditional_response


class InsightAgent(OpenAILLMAgent):
    """Agent specialized in generating business insights"""
    
    def generate_insights(self, df: pd.DataFrame, analysis_result: Dict[str, Any], user_query: str) -> str:
        """Generate business insights based on analysis results"""
        if not self.client:
            return "💡 **Business Insight:** LLM not available for advanced insights."
        
        data_context = f"""
        Analysis Result: {analysis_result.get('response', 'No analysis available')}
        Data Summary: {len(df)} records, {len(df.columns)} columns
        User Query: {user_query}
        """
        
        insight_query = f"Based on this data analysis, provide 2-3 actionable business insights and recommendations: {user_query}"
        
        return self.generate_response(insight_query, data_context, use_advanced_model=True)


class AutoGenChatSystem:
    """Enhanced AutoGen-style multi-agent chat system with OpenAI LLM"""
    
    def __init__(self):
        from helpers.config import AGENTS_CONFIG
        
        self.agents = {
            'data_analyst': DataAnalysisAgent(
                AGENTS_CONFIG['data_analyst']['name'],
                AGENTS_CONFIG['data_analyst']['role'],
                AGENTS_CONFIG['data_analyst']['system_prompt']
            ),
            'insight_analyst': InsightAgent(
                AGENTS_CONFIG['insight_analyst']['name'],
                AGENTS_CONFIG['insight_analyst']['role'],
                AGENTS_CONFIG['insight_analyst']['system_prompt']
            )
        }
        self.conversation_history = []
        self.openai_enabled = False
        self.use_llm_enhancement = True
    
    def initialize_openai(self, api_key: str) -> bool:
        """Initialize OpenAI for all agents"""
        success = True
        for agent in self.agents.values():
            if not agent.initialize_client(api_key):
                success = False
        
        self.openai_enabled = success
        return success
    
    def process_message(self, df: pd.DataFrame, message: str, generate_insights: bool = False) -> Dict[str, Any]:
        """Process user message through the enhanced agent system"""
        # Primary analysis with data analyst
        agent = self.agents['data_analyst']
        result = agent.analyze_data(df, message, use_llm=self.openai_enabled and self.use_llm_enhancement)
        
        # Generate additional insights if requested and LLM is available
        if generate_insights and self.openai_enabled:
            insight_agent = self.agents['insight_analyst']
            insights = insight_agent.generate_insights(df, result, message)
            if insights and not insights.startswith("❌"):
                result['insights'] = insights
        
        # Add to conversation history
        self.conversation_history.append({
            'timestamp': datetime.now(),
            'user_message': message,
            'agent_response': result['response'],
            'agent_name': result['agent'],
            'llm_enhanced': result.get('llm_enhanced', False)
        })
        
        return result