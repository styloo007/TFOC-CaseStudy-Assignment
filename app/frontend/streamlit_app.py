import streamlit as st
import requests
import json
import pandas as pd
from typing import Dict, Any
import time
from datetime import datetime


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
    st.metric("Document Type", result.get("document_type", "Unknown").upper())
    st.metric("Processing Method", result.get("processing_method", "Unknown").replace("_", " ").title())
    confidence = result.get("confidence_score", 0)
    st.metric("Confidence Score", f"{confidence:.1%}")

    entities = result.get("entities", {})
    # Handle dict (DOCX) and list (TXT/NER)
    if isinstance(entities, dict):
        found_count = len([v for v in entities.values() if v is not None and v != "null"])
        total_count = len(entities)
    elif isinstance(entities, list):
        found_count = len(entities)
        total_count = found_count
    else:
        found_count = 0
        total_count = 0
    st.metric("Entities Found", f"{found_count}/{total_count}")

    st.divider()

    # Entity display
    st.subheader("📋 Extracted Entities")
    if not entities:
        st.warning("No entities found in the document.")
        return

    # Display entities
    if isinstance(entities, dict):
        entity_items = list(entities.items())
        mid_point = len(entity_items) // 2
        col1, col2 = st.columns(2)
        with col1:
            for key, value in entity_items[:mid_point]:
                display_entity_card(key, value)
        with col2:
            for key, value in entity_items[mid_point:]:
                display_entity_card(key, value)
    elif isinstance(entities, list):
        # For spaCy NER, show text and label
        for ent in entities:
            display_entity_card(ent.get("text", "Entity"), ent.get("label", "Label"))

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
    

def main():
    # File uploader at the very top so uploaded_file is always defined
    uploaded_file = st.file_uploader(
        "Choose a document file",
        type=["docx", "pdf", "txt"],
        help="Supported formats: DOCX, PDF, TXT"
    )

    if uploaded_file is not None and uploaded_file.name.lower().endswith(".pdf"):
        # --- File Info at the Top ---
        st.markdown("""
            <div style='background: #f0f4f8; border-radius: 10px; padding: 1.2rem 1rem 0.5rem 1rem; margin-bottom: 1.5rem;'>
                <h3 style='color: #1f4e79; margin-bottom: 0.5rem;'>📄 File Information</h3>
            </div>
        """, unsafe_allow_html=True)
        file_type = uploaded_file.name.split('.')[-1].upper()
        file_info = {
            "Filename": uploaded_file.name,
            "Size (bytes)": len(uploaded_file.getvalue()),
            "Type": file_type
        }
        st.table(pd.DataFrame([file_info]))

        st.divider()
        st.markdown("## <span style='color:#2e7d32;'>RAG Pipeline</span>", unsafe_allow_html=True)
        if "rag_ingested" not in st.session_state:
            st.session_state.rag_ingested = False

        if not st.session_state.rag_ingested:
            st.info("To chat with your PDF, please ingest it first.")
            if st.button("Ingest PDF for RAG", key="rag_ingest", help="Send PDF to backend for ingestion"):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                with st.spinner("Ingesting PDF..."):
                    ingest_response = requests.post(f"{API_BASE_URL}/rag/ingest", files=files)
                if ingest_response.ok and ingest_response.json().get("status") == "ingested":
                    st.session_state.rag_ingested = True
                    st.success("PDF ingested. You can now chat with your documents.")
                else:
                    st.error(f"Ingestion failed: {ingest_response.text}")
        if st.session_state.rag_ingested:
            st.markdown("""
                <div style='background: #e8f5e9; border-radius: 10px; padding: 1.2rem 1rem 0.5rem 1rem; margin-bottom: 1.5rem;'>
                    <h3 style='color: #1f4e79; margin-bottom: 0.5rem;'>💬 RAG Chatbot</h3>
                    <p style='color: #555;'>Ask questions about your PDF. Both <b>Enter</b> and <b>Send</b> will submit your query.</p>
                </div>
            """, unsafe_allow_html=True)
            if "chat_history" not in st.session_state:
                st.session_state.chat_history = []

            # --- Chat Input with Enter/Send (above chat history) ---
            with st.form(key="rag_chat_form", clear_on_submit=True):
                user_input = st.text_input(
                    "Ask a question about your PDF:",
                    key="rag_user_input",
                    placeholder="Type your question and press Enter or click Send...",
                    label_visibility="collapsed"
                )
                submitted = st.form_submit_button("Send", use_container_width=True)
                if submitted and user_input:
                    st.session_state.chat_history.append({"role": "user", "content": user_input})
                    with st.spinner("Fetching response..."):
                        response = requests.post(
                            f"{API_BASE_URL}/rag/query",
                            json={"query": user_input}
                        )
                    if response.ok:
                        answer = response.json().get("response", "")
                        st.session_state.chat_history.append({"role": "assistant", "content": answer})

            # --- Chat History Display (below form) ---
            st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
            for msg in st.session_state.chat_history:
                if msg["role"] == "user":
                    st.markdown(f"""
                        <div style='background:#e3f2fd; border-radius:8px; padding:0.7rem 1rem; margin-bottom:0.5rem;'>
                            <span style='color:#1565c0; font-weight:600;'>You:</span> <span style='color:#222'>{msg['content']}</span>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                        <div style='background:#f1f8e9; border-radius:8px; padding:0.7rem 1rem; margin-bottom:0.5rem;'>
                            <span style='color:#2e7d32; font-weight:600;'>RAG Bot:</span> <span style='color:#222'>{msg['content']}</span>
                        </div>
                    """, unsafe_allow_html=True)

    elif uploaded_file is not None:
        st.markdown("#### File Information")
        file_type = uploaded_file.name.split('.')[-1].upper()
        file_info = {
            "Filename": uploaded_file.name,
            "Size (bytes)": len(uploaded_file.getvalue()),
            "Type": file_type
        }
        st.table(pd.DataFrame([file_info]))

        st.markdown("#### Processing Options")
        processing_mode = st.selectbox(
            "Select Processing Mode",
            ["docx", "text"],
            help="Auto-detect will choose the best method based on file type"
        )

        if "latest_result" not in st.session_state:
            st.session_state.latest_result = None
        if "results_history" not in st.session_state:
            st.session_state.results_history = []

        extract_clicked = st.button("🚀 Extract Entities", type="primary")
        if extract_clicked:
            with st.spinner(f"Processing {uploaded_file.name} using {processing_mode} method..."):
                start_time = time.time()
                api_client = APIClient(API_BASE_URL)
                if processing_mode == "auto":
                    result = api_client.extract_auto(uploaded_file)
                elif processing_mode == "text" and file_type == "TXT":
                    result = api_client.extract_entities(uploaded_file, "text")
                else:
                    result = api_client.extract_entities(uploaded_file, processing_mode)
                processing_time = time.time() - start_time
                result["processing_time"] = processing_time
                result["timestamp"] = datetime.now().isoformat()
                result["filename"] = uploaded_file.name
                st.session_state.results_history.append(result)
                st.session_state.latest_result = result

        result = st.session_state.latest_result
        if result:
            st.markdown("#### Extraction Results")
            st.success(f"✅ Processing completed in {result.get('processing_time', 0):.2f} seconds")
            entities = result.get("entities", {})
            # For spaCy NER, display as table with text and label columns
            if file_type == "TXT" and processing_mode == "text" and isinstance(entities, list):
                entity_df = pd.DataFrame(entities)
                st.dataframe(entity_df, use_container_width=True)
                csv_data = entity_df.to_csv(index=False).encode('utf-8')
                json_data = json.dumps(entities, indent=2)
                col_csv, col_json = st.columns(2)
                with col_csv:
                    st.download_button(
                        label="⬇️ Export Entities as CSV",
                        data=csv_data,
                        file_name=f"{result['filename']}_entities.csv",
                        mime="text/csv",
                        key="csv_export"
                    )
                with col_json:
                    st.download_button(
                        label="⬇️ Export Entities as JSON",
                        data=json_data,
                        file_name=f"{result['filename']}_entities.json",
                        mime="application/json",
                        key="json_export"
                    )
            elif isinstance(entities, dict):
                entity_df = pd.DataFrame(list(entities.items()), columns=["Entity", "Value"])
                st.dataframe(entity_df, use_container_width=True)
                csv_data = entity_df.to_csv(index=False).encode('utf-8')
                json_data = json.dumps(entities, indent=2)
                col_csv, col_json = st.columns(2)
                with col_csv:
                    st.download_button(
                        label="⬇️ Export Entities as CSV",
                        data=csv_data,
                        file_name=f"{result['filename']}_entities.csv",
                        mime="text/csv",
                        key="csv_export"
                    )
                with col_json:
                    st.download_button(
                        label="⬇️ Export Entities as JSON",
                        data=json_data,
                        file_name=f"{result['filename']}_entities.json",
                        mime="application/json",
                        key="json_export"
                    )
            else:
                st.warning("Entities format not recognized for tabular display.")
            display_entity_results(result)

        if st.session_state.results_history:
            if st.button("🗑️ Clear History"):
                st.session_state.results_history = []
                st.session_state.latest_result = None
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