import chromadb
import os
from dotenv import load_dotenv
from llama_index.core import SimpleDirectoryReader, StorageContext, VectorStoreIndex, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.embeddings import MockEmbedding
from llama_index.llms.gemini import Gemini
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.chroma import ChromaVectorStore

load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

# Load Documents from Directory
documents = SimpleDirectoryReader('docs').load_data()


# embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-base-en-v1.5")
embed_model = HuggingFaceEmbedding()
Settings.embed_model = embed_model

# Define LLM Model
llm = Gemini()
Settings.llm = llm

def data_ingestion(folder_path, chroma_db_path):
    os.makedirs(folder_path, exist_ok=True)
    documents = SimpleDirectoryReader(folder_path).load_data()
    splitter = SentenceSplitter(chunk_size=512, chunk_overlap=64)

    db = chromadb.PersistentClient(path=chroma_db_path)
    chroma_collection = db.get_or_create_collection("DB_collection")

    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        embed_model=embed_model,
        transformations=[splitter]
        )


def handle_query(query, chroma_db_path):
    db = chromadb.PersistentClient(path=chroma_db_path)
    chroma_collection = db.get_or_create_collection("DB_collection")

    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    index = VectorStoreIndex.from_vector_store(
        vector_store,
        embed_model=embed_model,
        storage_context=storage_context
    )
    query_engine = index.as_query_engine(llm=llm, similarity_top_k=3, verbose=True, response="compact")
    response = query_engine.query(query)
    return response


