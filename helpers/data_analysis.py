import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any


class DataAnalyzer:
    """Traditional rule-based data analysis methods"""
    
    def process_query(self, df: pd.DataFrame, query: str) -> Dict[str, Any]:
        """Process different types of queries"""
        query_lower = query.lower()
        
        # Statistical queries
        if any(word in query_lower for word in ['count', 'how many', 'total', 'number']):
            return self._handle_count_query(df, query)
        
        elif any(word in query_lower for word in ['average', 'mean', 'avg']):
            return self._handle_average_query(df, query)
        
        elif any(word in query_lower for word in ['sum', 'total value', 'total amount']):
            return self._handle_sum_query(df, query)
        
        # Filtering queries
        elif any(word in query_lower for word in ['status', 'pending', 'completed', 'cancelled', 'shipped']):
            return self._handle_status_query(df, query)
        
        elif any(word in query_lower for word in ['customer', 'client', 'top customer']):
            return self._handle_customer_query(df, query)
        
        elif any(word in query_lower for word in ['date', 'time', 'when', 'trend']):
            return self._handle_date_query(df, query)
        
        elif any(word in query_lower for word in ['show', 'display', 'list', 'view']):
            return self._handle_display_query(df, query)
        
        else:
            return self._handle_general_query(df, query)
    
    def _handle_count_query(self, df: pd.DataFrame, query: str) -> Dict[str, Any]:
        """Handle counting queries"""
        total_records = len(df)
        
        if 'order' in query.lower():
            response = f"📊 **Total Orders**: {total_records}"
            
            # Create a simple bar chart if we have categorical columns
            categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
            if categorical_cols:
                col = categorical_cols[0]
                counts = df[col].value_counts().head(10)
                fig = px.bar(x=counts.index, y=counts.values, 
                           title=f"Count by {col}", 
                           labels={'x': col, 'y': 'Count'})
                return {
                    'response': response,
                    'data': counts.to_dict(),
                    'chart': fig,
                    'agent': 'DataAnalyst'
                }
        
        return {
            'response': f"📊 **Total Records**: {total_records}",
            'data': {'total_records': total_records},
            'chart': None,
            'agent': 'DataAnalyst'
        }
    
    def _handle_average_query(self, df: pd.DataFrame, query: str) -> Dict[str, Any]:
        """Handle average/mean queries"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if not numeric_cols:
            return {
                'response': "❌ No numeric columns found for calculating averages.",
                'data': None,
                'chart': None,
                'agent': 'DataAnalyst'
            }
        
        averages = {}
        response_parts = ["📊 **Average Values:**"]
        
        for col in numeric_cols:
            avg_val = df[col].mean()
            averages[col] = avg_val
            response_parts.append(f"• {col}: {avg_val:.2f}")
        
        # Create visualization
        fig = px.bar(x=list(averages.keys()), y=list(averages.values()),
                    title="Average Values by Column",
                    labels={'x': 'Columns', 'y': 'Average Value'})
        
        return {
            'response': "\n".join(response_parts),
            'data': averages,
            'chart': fig,
            'agent': 'DataAnalyst'
        }
    
    def _handle_sum_query(self, df: pd.DataFrame, query: str) -> Dict[str, Any]:
        """Handle sum queries"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if not numeric_cols:
            return {
                'response': "❌ No numeric columns found for calculating sums.",
                'data': None,
                'chart': None,
                'agent': 'DataAnalyst'
            }
        
        sums = {}
        response_parts = ["📊 **Total Values:**"]
        
        for col in numeric_cols:
            sum_val = df[col].sum()
            sums[col] = sum_val
            response_parts.append(f"• {col}: {sum_val:,.2f}")
        
        return {
            'response': "\n".join(response_parts),
            'data': sums,
            'chart': None,
            'agent': 'DataAnalyst'
        }
    
    def _handle_status_query(self, df: pd.DataFrame, query: str) -> Dict[str, Any]:
        """Handle status-related queries"""
        # Find status-like columns
        status_cols = [col for col in df.columns if 'status' in col.lower() or 'state' in col.lower()]
        
        if not status_cols:
            # Try to find other categorical columns
            categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
            if categorical_cols:
                status_cols = [categorical_cols[0]]
            else:
                return {
                    'response': "❌ No status column found in the data.",
                    'data': None,
                    'chart': None,
                    'agent': 'DataAnalyst'
                }
        
        status_col = status_cols[0]
        status_counts = df[status_col].value_counts()
        
        response_parts = [f"📊 **{status_col} Breakdown:**"]
        for status, count in status_counts.items():
            percentage = (count / len(df)) * 100
            response_parts.append(f"• {status}: {count} ({percentage:.1f}%)")
        
        # Create pie chart
        fig = px.pie(values=status_counts.values, names=status_counts.index,
                    title=f"{status_col} Distribution")
        
        return {
            'response': "\n".join(response_parts),
            'data': status_counts.to_dict(),
            'chart': fig,
            'agent': 'DataAnalyst'
        }
    
    def _handle_customer_query(self, df: pd.DataFrame, query: str) -> Dict[str, Any]:
        """Handle customer-related queries"""
        # Find customer-like columns
        customer_cols = [col for col in df.columns 
                        if any(keyword in col.lower() for keyword in ['customer', 'client', 'name'])]
        
        if not customer_cols:
            return {
                'response': "❌ No customer column found in the data.",
                'data': None,
                'chart': None,
                'agent': 'DataAnalyst'
            }
        
        customer_col = customer_cols[0]
        customer_counts = df[customer_col].value_counts().head(10)
        
        response_parts = [f"👥 **Top Customers ({customer_col}):**"]
        for customer, count in customer_counts.items():
            response_parts.append(f"• {customer}: {count} orders")
        
        # Create bar chart
        fig = px.bar(x=customer_counts.values, y=customer_counts.index,
                    orientation='h', title=f"Top Customers by Order Count",
                    labels={'x': 'Number of Orders', 'y': customer_col})
        
        return {
            'response': "\n".join(response_parts),
            'data': customer_counts.to_dict(),
            'chart': fig,
            'agent': 'DataAnalyst'
        }
    
    def _handle_date_query(self, df: pd.DataFrame, query: str) -> Dict[str, Any]:
        """Handle date/time related queries"""
        # Find date-like columns
        date_cols = []
        for col in df.columns:
            if any(keyword in col.lower() for keyword in ['date', 'time', 'created', 'updated']):
                date_cols.append(col)
        
        if not date_cols:
            return {
                'response': "❌ No date columns found in the data.",
                'data': None,
                'chart': None,
                'agent': 'DataAnalyst'
            }
        
        date_col = date_cols[0]
        
        try:
            # Try to convert to datetime
            df_copy = df.copy()
            df_copy[date_col] = pd.to_datetime(df_copy[date_col], errors='coerce')
            df_copy = df_copy.dropna(subset=[date_col])
            
            # Group by date and count
            date_counts = df_copy.groupby(df_copy[date_col].dt.date).size()
            
            response = f"📅 **Orders by Date ({date_col}):**\nShowing trend over {len(date_counts)} days"
            
            # Create line chart
            fig = px.line(x=date_counts.index, y=date_counts.values,
                         title=f"Orders Trend by {date_col}",
                         labels={'x': 'Date', 'y': 'Number of Orders'})
            
            return {
                'response': response,
                'data': date_counts.to_dict(),
                'chart': fig,
                'agent': 'DataAnalyst'
            }
        except:
            return {
                'response': f"❌ Could not process date column '{date_col}'. Please check the date format.",
                'data': None,
                'chart': None,
                'agent': 'DataAnalyst'
            }
    
    def _handle_display_query(self, df: pd.DataFrame, query: str) -> Dict[str, Any]:
        """Handle display/show queries"""
        if 'sample' in query.lower() or 'example' in query.lower():
            sample_size = min(5, len(df))
            sample_data = df.head(sample_size)
            
            response = f"📋 **Sample Data (showing {sample_size} of {len(df)} records):**"
            
            return {
                'response': response,
                'data': sample_data.to_dict('records'),
                'chart': None,
                'agent': 'DataAnalyst',
                'show_table': True
            }
        
        return self._handle_general_query(df, query)
    
    def _handle_general_query(self, df: pd.DataFrame, query: str) -> Dict[str, Any]:
        """Handle general queries and provide overview"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
        
        response_parts = [
            f"📊 **Data Overview:**",
            f"• Total Records: {len(df)}",
            f"• Total Columns: {len(df.columns)}",
            f"• Numeric Columns: {len(numeric_cols)}",
            f"• Text Columns: {len(categorical_cols)}",
            "",
            f"🔍 **Column Names:** {', '.join(df.columns.tolist())}",
            "",
            "💡 **Try asking:**",
            "• 'How many orders are there?'",
            "• 'What's the average order value?'",
            "• 'Show me the status breakdown'",
            "• 'Who are the top customers?'",
            "• 'Show me sample data'"
        ]
        
        return {
            'response': "\n".join(response_parts),
            'data': {
                'total_records': len(df),
                'total_columns': len(df.columns),
                'numeric_columns': numeric_cols,
                'categorical_columns': categorical_cols
            },
            'chart': None,
            'agent': 'DataAnalyst'
        }