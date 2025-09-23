import streamlit as st
import requests
import json
import pandas as pd
from typing import Dict, Any
import time
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# Configure Streamlit page
st.set_page_config(
    page_title="ADOR - Financial Document Reader",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration
API_BASE_URL = "http://localhost:8000"

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #1f4e79, #2e7d32);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    .entity-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #007bff;
        margin: 0.5rem 0;
    }
    
    .success-entity {
        border-left-color: #28a745;
        background: #d4edda;
    }
    
    .null-entity {
        border-left-color: #ffc107;
        background: #fff3cd;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

class APIClient:
    """FastAPI client wrapper"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    def health_check(self) -> bool:
        """Check if API is healthy"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def extract_entities(self, file, endpoint: str) -> Dict[str, Any]:
        """Extract entities from uploaded file"""
        try:
            files = {"file": (file.name, file.getvalue(), file.type)}
            response = requests.post(f"{self.base_url}/extract/{endpoint}", files=files)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"API Error: {response.status_code} - {response.text}"}
        except requests.exceptions.RequestException as e:
            return {"error": f"Connection error: {str(e)}"}
    
    def extract_auto(self, file) -> Dict[str, Any]:
        """Auto-detect document type and extract"""
        return self.extract_entities(file, "auto")

def display_header():
    """Display main application header"""
    st.markdown("""
    <div class="main-header">
        <h1>🏦 ADOR - Augmented Document Reader</h1>
        <p>Financial Entity Extraction powered by AI</p>
    </div>
    """, unsafe_allow_html=True)

def display_sidebar_info():
    """Display sidebar with information and metrics"""
    with st.sidebar:
        st.image("https://via.placeholder.com/200x100/1f4e79/white?text=ADOR", caption="Financial Document AI")
        
        st.markdown("### 📊 Supported Document Types")
        st.markdown("""
        - **DOCX**: Rule-based parsing
        - **PDF**: Gemini LLM processing  
        - **TXT/Chat**: NER model extraction
        """)
        
        st.markdown("### 🎯 Extractable Entities")
        entities = [
            "Counterparty", "Notional Amount", "ISIN", "Underlying Assets",
            "Maturity Date", "Valuation Date", "Coupon Rate", "Barrier Level"
        ]
        for entity in entities:
            st.markdown(f"• {entity}")
        
        # API Status
        st.markdown("### 🔧 System Status")
        api_client = APIClient(API_BASE_URL)
        if api_client.health_check():
            st.success("✅ API Connected")
        else:
            st.error("❌ API Disconnected")

def display_entity_results(result: Dict[str, Any]):
    """Display extracted entities in an organized way"""
    if "error" in result:
        st.error(f"❌ Processing Error: {result['error']}")
        return
    
    # Header info
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Document Type", result.get("document_type", "Unknown").upper())
    
    with col2:
        st.metric("Processing Method", result.get("processing_method", "Unknown").replace("_", " ").title())
    
    with col3:
        confidence = result.get("confidence_score", 0)
        st.metric("Confidence Score", f"{confidence:.1%}")
    
    with col4:
        entities = result.get("entities", {})
        found_count = len([v for v in entities.values() if v is not None and v != "null"])
        st.metric("Entities Found", f"{found_count}/{len(entities)}")
    
    st.divider()
    
    # Entity display
    st.subheader("📋 Extracted Entities")
    
    entities = result.get("entities", {})
    if not entities:
        st.warning("No entities found in the document.")
        return
    
    # Split into two columns for better display
    col1, col2 = st.columns(2)
    
    entity_items = list(entities.items())
    mid_point = len(entity_items) // 2
    
    with col1:
        for key, value in entity_items[:mid_point]:
            display_entity_card(key, value)
    
    with col2:
        for key, value in entity_items[mid_point:]:
            display_entity_card(key, value)
    
    # Raw JSON view (collapsible)
    with st.expander("🔍 View Raw JSON Response"):
        st.json(result)

def display_entity_card(entity_name: str, entity_value: Any):
    """Display individual entity card"""
    # Determine card style based on value
    if entity_value is None or entity_value == "null" or entity_value == "":
        card_class = "entity-card null-entity"
        icon = "⚠️"
        display_value = "Not Found"
    else:
        card_class = "entity-card success-entity"
        icon = "✅"
        display_value = str(entity_value)
    
    # Format entity name for display
    formatted_name = entity_name.replace("_", " ").title()
    
    st.markdown(f"""
    <div class="{card_class}">
        <strong>{icon} {formatted_name}</strong><br>
        <span style="color: #666; font-family: monospace;">{display_value}</span>
    </div>
    """, unsafe_allow_html=True)

def display_analytics_dashboard(results_history: list):
    """Display analytics dashboard for processed documents"""
    if not results_history:
        return
    
    st.subheader("📈 Processing Analytics")
    
    # Prepare data for visualization
    df_data = []
    for i, result in enumerate(results_history):
        if "entities" in result:
            entities = result["entities"]
            found_count = len([v for v in entities.values() if v is not None and v != "null"])
            total_count = len(entities)
            
            df_data.append({
                "Document": f"Doc {i+1}",
                "Type": result.get("document_type", "Unknown"),
                "Method": result.get("processing_method", "Unknown"),
                "Entities_Found": found_count,
                "Total_Entities": total_count,
                "Success_Rate": found_count / total_count if total_count > 0 else 0,
                "Confidence": result.get("confidence_score", 0)
            })
    
    if not df_data:
        return
    
    df = pd.DataFrame(df_data)
    
    # Create visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        # Entity extraction success rate by document type
        fig1 = px.bar(
            df, 
            x="Document", 
            y="Success_Rate",
            color="Type",
            title="Entity Extraction Success Rate",
            labels={"Success_Rate": "Success Rate (%)", "Document": "Processed Documents"}
        )
        fig1.update_layout(yaxis_tickformat=".0%")
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # Processing method distribution
        method_counts = df["Method"].value_counts()
        fig2 = px.pie(
            values=method_counts.values,
            names=method_counts.index,
            title="Processing Methods Used"
        )
        st.plotly_chart(fig2, use_container_width=True)

def main():
    """Main Streamlit application"""
    
    # Initialize session state
    if "results_history" not in st.session_state:
        st.session_state.results_history = []
    
    # Display header
    display_header()
    
    # Display sidebar
    display_sidebar_info()
    
    # Main content area
    st.markdown("### 📤 Upload Financial Document")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a document file",
        type=["docx", "pdf", "txt"],
        help="Supported formats: DOCX (structured documents), PDF (complex documents), TXT (chat/simple text)"
    )
    
    if uploaded_file is not None:
        # Display file info
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info(f"**Filename:** {uploaded_file.name}")
        
        with col2:
            st.info(f"**Size:** {len(uploaded_file.getvalue())} bytes")
        
        with col3:
            file_type = uploaded_file.name.split('.')[-1].upper()
            st.info(f"**Type:** {file_type}")
        
        # Processing options
        st.markdown("### ⚙️ Processing Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            processing_mode = st.selectbox(
                "Select Processing Mode",
                ["auto", "docx", "pdf", "chat"],
                help="Auto-detect will choose the best method based on file type"
            )
        
        with col2:
            if st.button("🚀 Extract Entities", type="primary"):
                # Show processing indicator
                with st.spinner(f"Processing {uploaded_file.name} using {processing_mode} method..."):
                    start_time = time.time()
                    
                    # Initialize API client
                    api_client = APIClient(API_BASE_URL)
                    
                    # Extract entities
                    if processing_mode == "auto":
                        result = api_client.extract_auto(uploaded_file)
                    else:
                        result = api_client.extract_entities(uploaded_file, processing_mode)
                    
                    processing_time = time.time() - start_time
                    
                    # Add metadata to result
                    result["processing_time"] = processing_time
                    result["timestamp"] = datetime.now().isoformat()
                    result["filename"] = uploaded_file.name
                    
                    # Store in session state
                    st.session_state.results_history.append(result)
                
                # Display results
                st.markdown("### 🎯 Extraction Results")
                st.success(f"✅ Processing completed in {processing_time:.2f} seconds")
                
                display_entity_results(result)
        
        # Display analytics if we have historical data
        if len(st.session_state.results_history) > 1:
            st.divider()
            display_analytics_dashboard(st.session_state.results_history)
        
        # Clear history option
        if st.session_state.results_history:
            if st.button("🗑️ Clear History"):
                st.session_state.results_history = []
                st.rerun()
    
    # Footer
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 2rem;">
        <p>ADOR - Augmented Document Reader | Powered by FastAPI + Gemini AI + Streamlit</p>
        <p>CMI Architecture & Innovation Team</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()