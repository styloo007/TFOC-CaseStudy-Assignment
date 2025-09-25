# Global Architecture Document (GAD)

**Project:** Financial Document Reader — NER Proof of Concept (PoC)

**Author:** Shashank Agasimani

**Date:** 2025-09-23

---

## 1. Purpose & Scope

This GAD describes a high-level architecture for a financial document reader that extracts structured entities from financial documents (DOCX, chat/plain text, PDF). The system is built as a PoC focused on **Named Entity Recognition (NER)** and demonstrates three processing flows:

* Rule-based parsing for DOCX
* HuggingFace Transformers-based NER for chat/text
* LLM + RAG pipeline (Google Gemini + ChromaDB + HuggingFace embeddings + LlamaIndex) for PDFs

The document includes component interactions, data flow, example APIs, storage choices, security considerations, and an example output schema.

---

## 2. High-level architecture

```mermaid
flowchart TB
  subgraph UI[Frontend]
    A[Streamlit UI]
  end

  subgraph API[API Layer - FastAPI]
    B[API Gateway]
    C{Dispatcher}
  end

  subgraph DocxFlow[Docx Parser Service]
    D1a[Docx Reader]
    D1b[Regex Heuristics]
    D1a --> D1b
  end

  subgraph TextFlow[Text NER Service]
    D2a[Open Source NER Model]
    D2b[Entity Postprocessor]
    D2a --> D2b
  end

  subgraph PDFFlow[PDF RAG Service]
    P1[PDF Parser OCR]
    P2[Chunking]
    P3[Embedding Model]
    P4[ChromaDB Store]
    P5[Retriever]
    P6[LlamaIndex Orchestrator]
    P7[Gemini Extractor]
    P1 --> P2 --> P3 --> P4
    P5 --> P6 --> P7
    P4 --> P5
  end

  subgraph Storage[Storage Layer]
    V[ChromaDB]
  end

  subgraph Output[Results]
    O[JSON Output]
  end

  A --> B --> C
  C --> DocxFlow
  C --> TextFlow
  C --> PDFFlow

  PDFFlow --> V
  V --> P5

  P7 --> O
  O --> A
```

> Diagram (Mermaid) visualizes how the Streamlit UI calls FastAPI. The API dispatches to specialized services and returns a JSON result to the UI.

---

## 3. Components & Responsibilities

### 3.1 Streamlit (Frontend)

* Purpose: simple web UI for uploading documents, pasting text, selecting processing mode (NER, Summary, Q\&A), and displaying results.
* Actions: POST file/text to FastAPI endpoints, poll for async job status (for large PDFs).

### 3.2 FastAPI (API Layer)

### 1. **Document Extraction Endpoints**

* **`POST /extract/docx`** → Upload a `.docx` file, extracts financial entities using a **rule-based parser**, returns JSON with entities.
* **`POST /extract/text`** → Upload a `.txt` file, extracts entities using an **NER model**, returns JSON with entities.
* **`POST /extract/auto`** → Auto-detect extraction (currently supports `.docx` only).

---

### 2. **RAG (PDF) Pipeline Endpoints**

* **`POST /rag/ingest`** → Upload a PDF, ingest it into the **RAG pipeline** (embeddings + ChromaDB).
* **`POST /rag/query`** → Send a query against previously ingested docs, returns **LLM-based answer**.

---

### 3. **Utility Endpoint**

* **`GET /health`** → Health check endpoint, returns `{ "status": "ok" }`.


### 3.3 Docx Parser Service (Rule-based)

* Libraries: `python-docx`, regex, dateparser.
* Responsibility: reliably parse semi-structured term sheets and extract target entities using deterministic rules and heuristics.
* Output: JSON with entities + metadata (confidence = deterministic / high).

### 3.4 Text NER Service (HuggingFace Transformers)

* Libraries: HuggingFace Transformers (dslim/bert-base-NER), custom entity labels possible with fine-tuning.
* Responsibility: run NER on chat-like or free text and return token-level and span-level extractions.
* Fine-tuning: methodology doc (GMD) describes how to fine-tune on labeled financial data.

### 3.5 PDF RAG Service (LLM + Vector DB)

* Libraries: LlamaIndex (framework), ChromaDB (vector store), embedding model `baai/bge-base-en-v1.5`, Google Gemini for generative extraction and reasoning.
* Responsibility: preprocess PDF (OCR if required), chunk text, create embeddings, store/retrieve vectors, and use RAG to ask the LLM targeted prompts for structured extraction.
* Output: JSON with extracted entities, provenance (source chunk ids), confidence/LLM reasoning trace.

### 3.6 Storage

* **ChromaDB**: persistent vector store for embeddings (PDF chunks + metadata).
* **Object store / filesystem**: encrypted temporary storage for uploaded files.

---

## 4. Data Flow & Processing

### 4.1 Docx flow (sync)

1. Streamlit upload → `POST /ner` (type=docx)
2. FastAPI validates → calls Docx Parser Service
3. Parser reads docx, runs heuristics (header matching, key-value patterns, table parsing)
4. Parser returns JSON (entities + confidence)
5. FastAPI stores result in DB and returns JSON to UI

### 4.2 Chat/text flow (sync)

1. Streamlit paste/text → `POST /ner` (type=text)
2. FastAPI forwards to Open Source NER service
3. NER Model returns spans & labels → post-process to canonicalize dates/currencies
4. Store results and return JSON

### 4.3 PDF flow (async / RAG)

1. Streamlit upload → `POST /ner` (type=pdf)
2. FastAPI stores file, enqueues job (BackgroundWorker/Celery/Rq)
3. Worker: (a) OCR (if needed), (b) split into chunks, (c) compute embeddings (baai/bge), (d) upsert into ChromaDB
4. Run retrieval for candidate chunks and prompt Gemini via LlamaIndex to extract entities.
5. Return structured JSON and provenance for each entity; store in DB.

---

## 5. Entity Schema / Example Output

Canonical entity names and types (PoC):

* `Counterparty` (string)
* `Notional` (currency + numeric)
* `ISIN` (string)
* `Underlying` (string)
* `InitialValuationDate` (YYYY-MM-DD)
* `ValuationDate` (YYYY-MM-DD)
* `EffectiveDate` (YYYY-MM-DD)
* `TerminationDate` (YYYY-MM-DD)
* `Coupon` (percentage)
* `Barrier` (percentage)
* `Exchange` (string)
* `CalculationAgent` (string)
* `InterestPayments` (text/enum)

Example JSON (from Allianz trade):

```json
{
  "Counterparty": "BANK ABC",
  "PartyB": "CACIB",
  "TradeDate": "2025-01-31",
  "TradeTime": "09:12:15",
  "InitialValuationDate": "2025-01-31",
  "EffectiveDate": "2025-02-07",
  "Notional": "EUR 1,000,000",
  "UpfrontPayment": "TBD",
  "ValuationDate": "2026-07-31",
  "TerminationDate": "2026-08-07",
  "Underlying": "Allianz SE (ISIN DE0008404005)",
  "Exchange": "XETRA",
  "Coupon": "0%",
  "Barrier": "75%",
  "InterestPayments": "None",
  "CalculationAgent": "Party B and Party A",
  "ISDADocumentation": "Option"
}
```

---

## 6. Tech Stack & Libraries (PoC)

* Frontend: **Streamlit**
* API: **FastAPI** (uvicorn)
* Docx parsing: `python-docx`, `regex`, `dateparser`
* NER: **HuggingFace Transformers** (dslim/bert-base-NER, optionally fine-tuned)
* LLM & RAG: **Google Gemini** (LLM), **LlamaIndex** (framework), **ChromaDB** (vector DB), embeddings: `baai/bge-base-en-v1.5`
* Storage: SQLite/Postgres (PoC), filesystem for temp files
* Background jobs: Celery / RQ / FastAPI BackgroundTasks

---


### 7 NER Fine-Tuning Methodology (GMD)
If further accuracy or domain adaptation is required, the following methodology can be used to fine-tune a NER model for financial entities:

1. **Data Collection:**
   - Gather a corpus of financial documents (term sheets, contracts, chat logs, etc.).
   - Annotate entities of interest (e.g., Counterparty, Notional, ISIN, Dates, Coupon, Barrier, etc.) using annotation tools like Prodigy, doccano, or Label Studio.

2. **Data Preparation:**
   - Convert annotated data to a format compatible with the chosen NER framework (e.g., spaCy, HuggingFace). For HuggingFace, use the CoNLL or JSON format.

3. **Model Selection:**
   - Start with a pretrained model (e.g., `bert-base-cased`, `dslim/bert-base-NER`, or a spaCy transformer model).

4. **Fine-Tuning:**
   - Train the model on the annotated dataset, monitoring entity-level F1 score.
   - Use early stopping and validation splits to avoid overfitting.

5. **Evaluation:**
   - Evaluate on a held-out test set. Report precision, recall, and F1 for each entity type.

6. **Deployment:**
   - Integrate the fine-tuned model into the backend pipeline (replace the general NER model).
   - Optionally, expose a `/ner` endpoint for custom entity extraction.

7. **Continuous Improvement:**
   - Periodically retrain with new annotated data to improve coverage and accuracy.


### 8 LLM/RAG Pipeline Methodology (for PDF NER)
- **Chunking:** PDF is split into manageable text chunks.
- **Embedding:** Each chunk is embedded using a transformer model (HuggingFace).
- **Vector Storage:** Embeddings are stored in ChromaDB.
- **Retrieval:** At query time, relevant chunks are retrieved based on similarity to the user query.
- **LLM Extraction:** Gemini LLM is prompted with the retrieved context to extract entities.
- **Extensibility:** This pipeline can be adapted for Q&A, summarization, or topic modeling by changing the prompt and post-processing logic.

---

## 9. How to Run and Test
- Install requirements: `pip install -r requirements.txt`
- Start the FastAPI backend: `uvicorn app.api.main:app --reload`
- Start the Streamlit frontend: `streamlit run app/frontend/streamlit_app.py`
- Upload DOCX, PDF, or TXT files and extract entities via the UI.

---



