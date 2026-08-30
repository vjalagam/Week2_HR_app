# Enterprise RAG Chatbot UI (Streamlit)

A modern, interactive web interface for the Enterprise RAG system with source citations, namespace display, and retry count tracking.

## Features

✨ **Real-time Chat UI** — Native Streamlit chat interface  
📊 **Source Citations** — Expandable source documents with excerpts  
🏷️ **Namespace Display** — Color-coded by category (HR, Technical, Compliance, General)  
🔄 **Retry Tracking** — View retrieval attempts per question  
✅ **Groundedness Indicator** — Know if answers are verified against sources  
💾 **Chat History** — Conversation persists in session  
⚡ **Live Reload** — Auto-refresh on code changes (dev mode)

## Installation

1. **Install Streamlit** (if not already installed):
   ```bash
   pip install streamlit==1.28.1
   ```

2. **Or install from requirements.txt**:
   ```bash
   pip install -r requirements.txt
   ```

## Running the UI

### Quick Start (Recommended)
```bash
cd '/Users/user/MavenLearning/Week2 work'
chmod +x start-ui.sh
./start-ui.sh
```

### Manual Start
```bash
cd '/Users/user/MavenLearning/Week2 work'
. .venv/bin/activate
streamlit run ui.py
```

The app will open automatically at **http://localhost:8501**

## Usage

1. **Type your question** in the chat input at the bottom
2. **Press Enter** or click the submit button
3. **View the response** with:
   - **Answer** — Full generated response
   - **Details Expander** — Namespace, Grounded status, Retry count
   - **Sources** — Expandable document excerpts (by filename and category)

4. **Continue the conversation** — All messages persist in the sidebar

## Example Questions

### HR Questions (🟢)
```
"How many days of paid annual leave do full-time employees get?"
"What is the remote work policy?"
"What is the maternity leave entitlement?"
"Can I request annual leave during December 17-31?"
```

### Technical Questions (🔵)
```
"What is the API rate limit for enterprise tier?"
"What authentication methods are supported?"
"How do I deploy using Kubernetes?"
```

### Compliance Questions (🟠)
```
"What is the GDPR retention period for employee data?"
"What should employees do if they suspect a security breach?"
"What are the vendor management requirements?"
```

## Interface Components

### Main Chat Area
- **Messages** — User (right, purple) and Assistant (left, gray)
- **Details Expander** — Expandable metadata for each response
- **Source Citations** — Expandable document excerpts for verification

### Sidebar
- **📚 Document Categories** — Quick reference for document types
- **⚙️ How It Works** — RAG pipeline explanation
- **Example Questions** — Expandable by category

## Metadata Display

Each assistant response shows:

| Metric | Values | Meaning |
|--------|--------|---------|
| **Namespace** | HR / Technical / Compliance / General | Question classification |
| **Grounded** | ✓ Yes / ✗ No | Answer verified against sources |
| **Retries** | 0-2 | Retrieval attempts needed |

## Configuration

Optional `.env` file settings:
```bash
# LLM Configuration
NEBIUS_API_KEY=your-key
NEBIUS_BASE_URL=https://api.studio.nebius.ai/v1
NEBIUS_MODEL=Qwen/Qwen2.5-72B-Instruct

# Vector Database (Pinecone)
PINECONE_API_KEY=your-key
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=acme-enterprise-rag

# Embeddings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

If not configured, the system uses:
- **Local keyword-based routing** (no LLM needed)
- **Local document search** (CPU-based embeddings)
- **Keyword fallback answer extraction**

## Troubleshooting

### Streamlit not found
```bash
cd '/Users/user/MavenLearning/Week2 work'
. .venv/bin/activate
pip install streamlit==1.28.1
```

### Port 8501 already in use
```bash
streamlit run ui.py --server.port=8502
```

### No documents found
- Ensure `Docs/` directory contains `*.txt` files
- Run `python main.py --index` to optionally index to Pinecone

### Slow initial load
- First load downloads embeddings model (~90MB)
- Subsequent runs are instant

## Advanced Options

### Dev Mode (Auto-reload on changes)
```bash
streamlit run ui.py --logger.level=debug
```

### Custom Config
```bash
streamlit run ui.py --client.showErrorDetails=true
```

### Deploy to Streamlit Cloud
1. Push repo to GitHub
2. Go to https://streamlit.io/cloud
3. Create new app → Select repo/branch/ui.py
4. Configure secrets (API keys)
5. Deploy

## Architecture

- **Frontend**: Pure Streamlit (Python-based UI)
- **Backend**: LangGraph RAG pipeline
- **Retrieval**: Local fallback + optional Pinecone
- **LLM**: Optional Nebius/OpenAI compatible
- **Embeddings**: HuggingFace sentence-transformers

## Performance

- **First load**: ~5-10s (downloads embeddings)
- **Subsequent loads**: <1s
- **Response time**: 2-5s (depends on LLM availability)
- **Memory**: ~500MB (Python + models in memory)
