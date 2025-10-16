# src/pages/3_Document_Processor.py
import streamlit as st
import os
import asyncio
import tempfile
import lancedb
import litellm
from ragbits.core.llms import LiteLLM
from core.data_handler import extract_text_from_document
from ragbits.core.prompt import Prompt
from pydantic import BaseModel
from core.neo4j_handler import Neo4jHandler
import uuid
from datetime import datetime
import pandas as pd
import tiktoken
# NEW: Import prompt and input model from core.agents
from core.agents import DocumentQueryPrompt, DocumentQueryPromptInput
import traceback # NEW: For logging full tracebacks
from components.ui_styles import apply_custom_styles

# NEW: Page Configuration with icon
st.set_page_config(
    page_title="Document Processor",
    page_icon="📄", # Icon for Document Processor page
    layout="wide"
)

# Apply custom glassmorphic and animation styles (MUST be called on every page)
apply_custom_styles()

# Text splitting helper (mimics part of what Ragbits' DocumentSearch would do)
def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[str]:
    """Splits text into chunks using tiktoken for length awareness."""
    try:
        # Use a common encoding that is robust and doesn't require specific model lookups.
        # cl100k_base is a good general-purpose encoding.
        encoding = tiktoken.get_encoding("cl100k_base")
    except Exception as e:
        st.warning(f"Could not load tiktoken encoding for cl100k_base: {e}. Falling back to simple word count for chunking.")
        # Fallback to a simple word-based chunking if tiktoken fails
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - chunk_overlap): # Basic chunking without overlap precision
            chunks.append(" ".join(words[i:i + chunk_size]))
        return chunks
    words = text.split()
    chunks = []
    current_chunk = []
    current_chunk_tokens = 0
    for word in words:
        word_tokens = len(encoding.encode(word + " ")) # +1 for space after word
        if current_chunk_tokens + word_tokens <= chunk_size:
            current_chunk.append(word)
            current_chunk_tokens += word_tokens
        else:
            chunks.append(" ".join(current_chunk))
            # Start new chunk with overlap (approximate by word count)
            overlap_words_count = min(len(current_chunk), chunk_overlap // 4) # Heuristic
            current_chunk = current_chunk[-overlap_words_count:] + [word]
            current_chunk_tokens = len(encoding.encode(" ".join(current_chunk)))
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks
# Ensure authentication state is set
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.warning("Please log in to access this page.")
    st.stop()
st.header("Document Processor (Docling)")
st.markdown("---")
# Initialize LLM (from ragbits.core, but used directly)
if "llm_doc_processor" not in st.session_state:
    st.session_state.llm_doc_processor = LiteLLM(model_name=os.getenv("GEMINI_MODEL_NAME", "gemini/gemini-2.5-flash-preview-05-20"))
# Default embedding model for local Ollama setup
OLLAMA_EMBEDDING_MODEL = "nomic-embed-text-v2-moe-Q4_K_M:latest"
OLLAMA_API_BASE = "http://localhost:11434" # Default Ollama API base URL
# Initialize LanceDB client and table
LANCEDB_DIR = "./lancedb_data"
LANCEDB_TABLE_NAME = "ragbits_docs_lance" # Keeping a single table name for simplicity and clear-all
os.makedirs(LANCEDB_DIR, exist_ok=True)
# Use st.cache_resource for LanceDB client to ensure it's a singleton across reruns
@st.cache_resource
def get_lancedb_client():
    return lancedb.connect(LANCEDB_DIR)
st.session_state.lancedb_client = get_lancedb_client()
# This helper function now always tries to get the current table instance,
# or returns None if it doesn't exist (e.g., after clearing it).
def get_lancedb_table_instance():
    try:
        # Check if table exists before opening
        if LANCEDB_TABLE_NAME in st.session_state.lancedb_client.table_names():
            return st.session_state.lancedb_client.open_table(LANCEDB_TABLE_NAME)
        return None
    except Exception as e:
        # print(f"LanceDB table '{LANCEDB_TABLE_NAME}' not found or error opening: {e}. It will be created upon first document upload.")
        return None
# Initialize session state for the table object
if "lancedb_table" not in st.session_state:
    st.session_state.lancedb_table = get_lancedb_table_instance()
def clear_lancedb_table():
    """Clears the specific table in LanceDB by dropping it."""
    try:
        if LANCEDB_TABLE_NAME in st.session_state.lancedb_client.table_names():
            st.session_state.lancedb_client.drop_table(LANCEDB_TABLE_NAME)
            st.session_state.lancedb_table = None # Reset the session state table object
            # st.success(f"LanceDB table '{LANCEDB_TABLE_NAME}' cleared successfully.") # Commented to reduce excessive success messages
        # else:
            # st.info(f"LanceDB table '{LANCEDB_TABLE_NAME}' does not exist, no need to clear.") # Commented to reduce excessive info messages
    except Exception as e:
        st.error(f"Error clearing LanceDB table: {e}")
# Changed to synchronous function
def add_document_to_lancedb_sync(uploaded_file, document_name: str) -> bool:
    """Ingests a document's text into LanceDB directly. Synchronous operation."""
    text_content = extract_text_from_document(uploaded_file)
    if not text_content:
        st.error("No text extracted from document. Please ensure the file contains readable text.")
        return False
    chunks = chunk_text(text_content)
    if not chunks:
        st.warning("No chunks generated from document text.")
        return False
    data_to_add = []
    for i, chunk in enumerate(chunks):
        try:
            response = litellm.embedding(
                model=f"ollama/{OLLAMA_EMBEDDING_MODEL}",
                input=[chunk],
                api_base=OLLAMA_API_BASE
            )
            vector = response.data[0]['embedding']
            data_to_add.append({
                "id": str(uuid.uuid4()),
                "text": chunk,
                "vector": vector,
                "document_name": document_name,
                "chunk_index": i
            })
        except Exception as e:
            st.error(f"Error embedding chunk {i}: {e}. Ensure Ollama is running and '{OLLAMA_EMBEDDING_MODEL}' model is pulled (e.g., `ollama pull {OLLAMA_EMBEDDING_MODEL}`).")
            return False
    if not data_to_add:
        st.warning("No data to add to LanceDB after embedding attempts.")
        return False
    df = pd.DataFrame(data_to_add)
    # Check if the table exists. If not, create it.
    # If it exists, append to it.
    try:
        if LANCEDB_TABLE_NAME not in st.session_state.lancedb_client.table_names():
            st.session_state.lancedb_table = st.session_state.lancedb_client.create_table(LANCEDB_TABLE_NAME, data=df)
            # print(f"LanceDB: Created new table '{LANCEDB_TABLE_NAME}' with initial data.")
        else:
            current_table = get_lancedb_table_instance() # Get the current table object
            if current_table: # Ensure it's not None
                current_table.add(df)
                st.session_state.lancedb_table = current_table # Update session state with the latest table obj
                # print(f"LanceDB: Added {len(data_to_add)} entries to table '{LANCEDB_TABLE_NAME}'.")
            else: # This case should ideally not happen if table_names() check passes
                st.error("LanceDB table exists but could not be opened for adding data.")
                return False
    except Exception as e:
        st.error(f"LanceDB: Error adding data to table '{LANCEDB_TABLE_NAME}': {e}")
        return False
    return True
# Changed to synchronous function
def query_lancedb_document_sync(user_query: str) -> str:
    """Queries LanceDB and generates an answer using RAG directly. Synchronous operation."""
    table = get_lancedb_table_instance() # Get the latest table instance
    if table is None:
        return "No document data loaded into LanceDB yet. Please upload a document first."
    try:
        response = litellm.embedding(
            model=f"ollama/{OLLAMA_EMBEDDING_MODEL}",
            input=[user_query],
            api_base=OLLAMA_API_BASE
        )
        query_vector = response.data[0]['embedding']
        search_results = table.search(query_vector).limit(5).to_list()
        context_chunks = []
        if search_results:
            for item in search_results:
                context_chunks.append(item.get("text", ""))
        if not context_chunks:
            return "No relevant information found in the document for your query."
        context_str = "\n".join(context_chunks)
        # FIX: Correctly instantiate DocumentQueryPrompt with DocumentQueryPromptInput
        # The prompt is now created using the specific input model defined in agents.py
        rag_prompt_instance = DocumentQueryPrompt(DocumentQueryPromptInput(query=user_query, context_str=context_str))
        response = asyncio.run(st.session_state.llm_doc_processor.generate(prompt=rag_prompt_instance))
        return response
    except Exception as e:
        # Log the full traceback for debugging
        st.error(f"An unexpected error occurred during document querying: {e}")
        st.exception(e) # Display full traceback in Streamlit for user
        return f"Error: An unexpected error occurred during document querying: {e}"
# Initialize Neo4j Handler (once per session)
if "neo4j_handler_dp" not in st.session_state:
    st.session_state.neo4j_handler_dp = Neo4jHandler()
st.subheader("Upload Document")
uploaded_document = st.file_uploader("Upload a TXT or PDF document", type=["txt", "pdf"], key="doc_uploader")
if "document_text" not in st.session_state:
    st.session_state.document_text = ""
if "last_uploaded_doc_info" not in st.session_state:
    st.session_state.last_uploaded_doc_info = None
if "doc_answer" not in st.session_state:
    st.session_state.doc_answer = ""
# New session state for storing document query details for Neo4j
if "last_doc_query_details" not in st.session_state:
    st.session_state.last_doc_query_details = None
if uploaded_document:
    current_doc_info = (uploaded_document.name, uploaded_document.size)
    # Check if a new file is uploaded or if the existing one has changed
    if st.session_state.last_uploaded_doc_info != current_doc_info:
        st.session_state.document_text = "" # Clear old text immediately
        st.session_state.doc_answer = "" # Clear old answer
        st.session_state.last_doc_query_details = None # Clear old details
        # Clear LanceDB *before* processing the new document
        clear_lancedb_table()
        with st.spinner("Extracting text from document and setting up knowledge base..."):
            success = add_document_to_lancedb_sync(uploaded_document, uploaded_document.name)
            if success:
                st.session_state.document_text = extract_text_from_document(uploaded_document)
                st.session_state.last_uploaded_doc_info = current_doc_info
                st.success("Document text extracted and ingested into LanceDB knowledge base!")
            else:
                st.error("Failed to ingest document into LanceDB knowledge base.")
            st.rerun() # Rerun to update the UI with new document context
else:
    # If the file uploader is empty, ensure all document-related states are reset
    # and the LanceDB table is cleared.
    # Only clear if there was a document previously loaded or LanceDB table exists.
    if st.session_state.document_text or st.session_state.last_uploaded_doc_info or \
       (get_lancedb_table_instance() is not None): # Check if table object is not None
        st.session_state.document_text = ""
        st.session_state.last_uploaded_doc_info = None
        st.session_state.doc_answer = ""
        st.session_state.last_doc_query_details = None
        clear_lancedb_table() # Clear LanceDB when no document is uploaded
        st.rerun() # Rerun to update the UI
if st.session_state.document_text:
    st.subheader("Extracted Document Preview")
    with st.expander("Click to view full extracted text"):
        st.text_area("Document Content", st.session_state.document_text, height=300, disabled=True, key="doc_content_display")
else:
    st.info("Upload a document to see its extracted text.")
st.markdown("---")
st.subheader("Query Document Content")
user_query = st.text_input(
    "Ask a question about the document:",
    placeholder="e.g., 'What is the main topic of this document?'",
    key="doc_query_input",
    disabled=not st.session_state.document_text
)
# Define the button click handler as a synchronous function
def handle_document_query_sync():
    # Only proceed if there's a query and document text
    if user_query.strip() and st.session_state.document_text:
        st.session_state.last_doc_query_details = None
        with st.spinner("Getting answer from AI..."):
            answer = query_lancedb_document_sync(user_query) # Call synchronous function
            st.session_state.doc_answer = answer
            event_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()
            st.session_state.last_doc_query_details = {
                "event_id": event_id,
                "query": user_query,
                "answer": answer,
                "document_name": uploaded_document.name if uploaded_document else "N/A",
                "extracted_text_preview": (st.session_state.document_text[:500] + "...") if len(st.session_state.document_text) > 500 else st.session_state.document_text,
                "timestamp": timestamp
            }
            st.info("Answer generated. Click 'Save Document Query to Neo4j' to persist this event.")
    else:
        st.warning("Please upload a document and enter a query.")
    st.rerun() # Rerun to update UI after action
if st.button("Get Answer", key="get_doc_answer_button", on_click=handle_document_query_sync):
    pass # Handler is in on_click
if st.session_state.doc_answer:
    st.subheader("AI Answer")
    st.info(st.session_state.doc_answer)
    # New: Save Document Query Event to Neo4j button
    def save_doc_query_neo4j():
        if st.session_state.last_doc_query_details:
            with st.spinner("Saving document query event to Neo4j..."):
                details = st.session_state.last_doc_query_details
                if st.session_state.neo4j_handler_dp.store_document_query_event(
                    details["event_id"],
                    details["query"],
                    details["answer"],
                    details["document_name"],
                    details["extracted_text_preview"],
                    details["timestamp"]
                ):
                    st.success("Document query event saved to Neo4j!")
                else:
                    st.error("Failed to save document query event to Neo4j.")
                st.session_state.last_doc_query_details = None
            st.rerun()
    if st.session_state.last_doc_query_details:
        st.button("Save Document Query to Neo4j", key="save_doc_query_neo4j_button", on_click=save_doc_query_neo4j)