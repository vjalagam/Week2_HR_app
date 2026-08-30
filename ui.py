import uuid
import streamlit as st
from enterprise_rag.app import run_question
from enterprise_rag.config import SETTINGS
from enterprise_rag.storage import ChatStore

st.set_page_config(page_title="Enterprise RAG Chatbot", page_icon="💼", layout="wide")
st.title("💼 Enterprise RAG Chatbot")
st.caption("Ask naturally—ABC automatically finds the right HR, technical, or compliance sources.")

username = "local-demo"
store = ChatStore()
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = store.history(st.session_state.session_id, username)

with st.sidebar:
    if st.button("New conversation"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()
    st.markdown("### Automatic search")
    st.markdown("No category selection needed. Ask a question or continue with a natural follow-up.")

    st.divider()
    st.markdown("### How it works")
    with st.expander("Ingestion phase", expanded=False):
        st.markdown(
            """
            1. Load HR, technical, and compliance documents.
            2. Split documents into overlapping chunks.
            3. Create normalized embeddings.
            4. Index chunks in matching Pinecone namespaces.

            Run ingestion when documents are added or changed:

            `python main.py --index`
            """
        )

    with st.expander("Query phase — 5 nodes", expanded=True):
        st.markdown(
            """
            1. **Router** — automatically selects HR, technical, compliance, or general.
            2. **Retriever** — finds the most relevant document chunks.
            3. **Grader** — removes chunks unrelated to the question.
            4. **Generator** — creates an answer using only retained context.
            5. **Checker** — verifies every answer claim against the sources.
            """
        )
        st.caption("Failed relevance checks widen retrieval. Failed grounding checks regenerate the answer, up to the retry limit.")

    with st.expander("Service usage", expanded=False):
        st.markdown(
            """
            - Router: 1 LLM call
            - Retriever: embeddings/vector search; no LLM call
            - Grader: 1 LLM call per retrieved chunk
            - Generator: 1 LLM call per attempt
            - Checker: 1 LLM call per attempt
            """
        )
        st.caption("Calls use local fallbacks when Nebius or Pinecone is unavailable.")

    with st.expander("Answer details", expanded=False):
        st.markdown(
            """
            Each answer can show:

            - Selected namespace
            - Grounding status
            - Retry count
            - Source documents and excerpts
            - Correlation ID for troubleshooting
            """
        )

    st.divider()
    st.markdown("### Connection status")
    st.write(f"Nebius LLM: {'Connected' if SETTINGS.has_nebius else 'Local fallback'}")
    st.write(f"Pinecone: {'Configured' if SETTINGS.has_pinecone else 'Local fallback'}")

def show_message(message):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        metadata = message.get("metadata", {})
        if message["role"] == "assistant" and metadata:
            with st.expander("Details"):
                st.write({key: metadata.get(key) for key in ("namespace", "grounded", "retry_count", "correlation_id")})
                for source in metadata.get("sources", []):
                    st.caption(f"{source['source']} [{source['namespace']}]")
                    st.write(source["excerpt"])
            message_id = message.get("id")
            if message_id:
                left, right = st.columns(2)
                if left.button("👍 Helpful", key=f"up-{message_id}"):
                    store.add_feedback(message_id, st.session_state.session_id, username, 1)
                if right.button("👎 Not helpful", key=f"down-{message_id}"):
                    store.add_feedback(message_id, st.session_state.session_id, username, -1)

for message in st.session_state.messages:
    show_message(message)

if prompt := st.chat_input("Ask a question in your own words..."):
    user_message = {"role": "user", "content": prompt, "metadata": {}}
    user_message["id"] = store.add_message(st.session_state.session_id, username, "user", prompt)
    st.session_state.messages.append(user_message)
    try:
        history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[:-1]]
        with st.spinner("Routing, retrieving, and verifying..."):
            result = run_question(prompt, history=history, identity=username)
        sources = [{"source": d.metadata.get("source", "unknown"), "namespace": d.metadata.get("namespace", "general"),
                    "excerpt": d.page_content[:200]} for d in result.get("documents", [])]
        metadata = {"namespace": result.get("doc_type", "general"),
                    "grounded": result.get("hallucination_result") == "grounded",
                    "retry_count": result.get("retry_count", 0),
                    "correlation_id": result.get("correlation_id"), "sources": sources}
        content = result.get("generation", "No grounded answer was found.")
        message_id = store.add_message(st.session_state.session_id, username, "assistant", content, metadata)
        st.session_state.messages.append({"id": message_id, "role": "assistant", "content": content, "metadata": metadata})
        st.rerun()
    except (ValueError, RuntimeError) as exc:
        st.error(str(exc))
    except Exception:
        st.error("The request failed. Check the structured logs for its correlation ID.")
