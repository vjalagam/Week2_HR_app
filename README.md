# Enterprise RAG with LangGraph + Pinecone + DeepSeek

This project builds a production-hardened retrieval-augmented generation workflow for HR, technical, and compliance knowledge over enterprise documents.

## Architecture

The pipeline follows the requested 5-step flow:

1. Router: classify the query into `hr`, `technical`, `compliance`, or `general`
2. Retriever: search the Pinecone namespace for relevant chunks
3. Grader: filter the retrieved chunks by relevance
4. Generator: produce a grounded answer from the filtered context
5. Checker: verify the answer is supported by the source documents and retry up to 2 times if needed
<img width="1024" height="1536" alt="image" src="https://github.com/user-attachments/assets/ea284d2e-867a-4ea6-b2f3-181d08034067" />

## Project layout

- `enterprise_rag/config.py` — environment configuration
- `enterprise_rag/data_ingestion.py` — document loading and chunking
- `enterprise_rag/vector_store.py` — Pinecone indexing and fallback retrieval
- `enterprise_rag/graph.py` — LangGraph orchestration
- `enterprise_rag/app.py` — CLI entrypoint
- `Docs/` — enterprise documentation source files

## Setup

1. Create a virtual environment and install dependencies:

   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

2. Copy `.env.example` to `.env` and populate the credentials:

   cp .env.example .env

3. Add your API keys:
   - `DEEPSEEK_API_KEY` for the LLM
   - `PINECONE_API_KEY` for vector search

4. Build the Pinecone index and load documents:

   python main.py --index

5. Ask a question:

   python main.py --question "How much paid annual leave do full-time employees get?"

## Notes

- When external API keys are not configured, the app falls back to a local lexical retrieval path so the system still runs in a demo/offline mode.
- When DeepSeek credentials are present, the router, grader, generator, and checker use the DeepSeek OpenAI-compatible endpoint.

## Production controls

- The UI currently runs directly in local-demo mode without authentication.
- Production secrets can be mounted through `DEEPSEEK_API_KEY_FILE` and `PINECONE_API_KEY_FILE`.
- Chat history and user feedback persist locally in SQLite at `RAG_DATABASE_PATH`.
- Every request emits JSON logs containing a correlation ID and latency. The UI exposes that ID for support investigations.
- Questions are length-validated and rate-limited for the local application identity.
- Pinecone ingestion writes each document category to its own namespace.

Run the labeled evaluation suite with:

    python -m enterprise_rag.evaluation evaluation/dataset.json

Run the application locally with `streamlit run ui.py` after activating the project virtual environment.
