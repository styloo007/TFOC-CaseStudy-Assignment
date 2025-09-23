import os
from app.services.rag_pipeline import data_ingestion, handle_query
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from app.services.docx_parser import extract_entities_from_docx
from app.services.text_ner import extract_financial_entities_from_text
from typing import Dict, Any
from io import BytesIO


app = FastAPI()

# RAG pipeline config
RAG_UPLOAD_DIR = "uploaded_rag_docs"
RAG_SESSION_ID = "default_session"
CHROMA_DB_PATH = os.path.join("chroma_db", RAG_SESSION_ID)

class QueryRequest(BaseModel):
    query: str

# Endpoint to upload PDF and ingest
@app.post("/rag/ingest")
async def rag_ingest(file: UploadFile = File(...)):
    os.makedirs(RAG_UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(RAG_UPLOAD_DIR, file.filename)
    try:
        with open(file_path, "wb") as f:
            f.write(await file.read())
        # Ingest the uploaded file's folder
        data_ingestion(RAG_UPLOAD_DIR, CHROMA_DB_PATH)
        return {"status": "ingested"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# Allow CORS for local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/extract/docx")
async def extract_docx(file: UploadFile = File(...)) -> Dict[str, Any]:
    file_bytes = await file.read()
    entities = extract_entities_from_docx(BytesIO(file_bytes))
    return {
        "document_type": "docx",
        "processing_method": "rule_based",
        "confidence_score": 1.0,
        "entities": entities
    }

@app.post("/extract/text")
async def extract_text(file: UploadFile = File(...)):
    text = (await file.read()).decode('utf-8')
    entities = extract_financial_entities_from_text(text)
    return {
        "document_type":"txt",
        "preprocessing_method":"ner_based",
        "entities":entities
    }


@app.post("/extract/auto")
async def extract_auto(file: UploadFile = File(...)) -> Dict[str, Any]:
    if file.filename.lower().endswith(".docx"):
        return await extract_docx(file)
    return {"error": "Auto mode only supports DOCX for now."}


@app.post("/rag/query")
async def rag_query(request: QueryRequest):
    try:
        response = handle_query(request.query, CHROMA_DB_PATH)
        return {"response": str(response)}
    except Exception as e:
        return {"response": f"Error: {str(e)}"}