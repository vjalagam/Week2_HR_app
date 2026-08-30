import streamlit as st
from enterprise_rag.graph import build_graph, RAGState

# Page configuration
st.set_page_config(
    page_title="Enterprise RAG Chatbot",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding-top: 2rem;
    }
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)

# Header
st.markdown("""
    # 💼 Enterprise RAG Chatbot
    ### Intelligent Q&A over ABC Enterprise Documents
    """)

# Sidebar information
with st.sidebar:
    st.markdown("## 📚 Document Categories")
    st.markdown("""
    - **HR** 🟢 — Leave policies, benefits, remote work
    - **Technical** 🔵 — APIs, SDKs, deployment, rate limits
    - **Compliance** 🟠 — GDPR, privacy, incident response
    - **General** 🟣 — Multi-category questions
    """)
    
    st.markdown("---")
    st.markdown("## ⚙️ How It Works")
    st.markdown("""
    1. **Route** — Question classified into category
    2. **Retrieve** — Relevant documents fetched
    3. **Grade** — Chunks evaluated for relevance
    4. **Generate** — Answer composed from sources
    5. **Check** — Answer verified against documents
    """)
    
    st.markdown("---")
    st.markdown("### Example Questions")
    examples = {
        "HR": [
            "How many days of annual leave do employees get?",
            "What is the remote work policy?",
        ],
        "Technical": [
            "What is the API rate limit?",
            "How to authenticate with OAuth?"
        ],
        "Compliance": [
            "What is the GDPR retention period?",
            "How to report a security breach?"
        ]
    }
    
    for category, questions in examples.items():
        with st.expander(f"{category} Questions", expanded=False):
            for q in questions:
                st.caption(f"• {q}")

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        if message["role"] == "assistant" and "metadata" in message:
            with st.expander("📊 Details", expanded=False):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    namespace = message["metadata"]["namespace"]
                    namespace_colors = {
                        "hr": "🟢",
                        "technical": "🔵",
                        "compliance": "🟠",
                        "general": "🟣"
                    }
                    st.metric("Namespace", f"{namespace_colors.get(namespace, '•')} {namespace.upper()}")
                
                with col2:
                    grounded = message["metadata"]["grounded"]
                    st.metric("Grounded", "✓ Yes" if grounded else "✗ No", 
                             delta="Verified" if grounded else "Unverified")
                
                with col3:
                    retry_count = message["metadata"]["retry_count"]
                    st.metric("Retries", retry_count)
            
            # Display sources
            sources = message["metadata"].get("sources", [])
            if sources:
                st.markdown("#### 📄 Sources")
                for source in sources:
                    with st.expander(f"📋 {source['source']} [{source['namespace'].upper()}]"):
                        st.caption(f"**Namespace:** {source['namespace']}")
                        st.write(source['excerpt'])

# Chat input
if prompt := st.chat_input("Ask about HR, Technical, or Compliance policies..."):
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate response with loading indicator
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Build and run the graph
                graph = build_graph()
                state: RAGState = {
                    "question": prompt,
                    "doc_type": "general",
                    "documents": [],
                    "grading_result": "",
                    "generation": "",
                    "hallucination_result": "",
                    "retry_count": 0
                }
                result = graph.invoke(state)
                
                # Extract metadata
                generation = result.get("generation", "")
                doc_type = result.get("doc_type", "general")
                retry_count = result.get("retry_count", 0)
                documents = result.get("documents", [])
                hallucination_result = result.get("hallucination_result", "")
                
                # Build sources list
                sources = []
                for doc in documents:
                    sources.append({
                        "source": doc.metadata.get("source", "unknown"),
                        "namespace": doc.metadata.get("namespace", "general"),
                        "excerpt": doc.page_content[:200]
                    })
                
                # Display answer
                st.markdown(generation)
                
                # Add to history with metadata
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": generation,
                    "metadata": {
                        "namespace": doc_type,
                        "retry_count": retry_count,
                        "grounded": hallucination_result == "grounded",
                        "sources": sources
                    }
                })
                
                # Display metadata
                with st.expander("📊 Details", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        namespace_colors = {
                            "hr": "🟢",
                            "technical": "🔵",
                            "compliance": "🟠",
                            "general": "🟣"
                        }
                        st.metric("Namespace", f"{namespace_colors.get(doc_type, '•')} {doc_type.upper()}")
                    
                    with col2:
                        grounded = hallucination_result == "grounded"
                        st.metric("Grounded", "✓ Yes" if grounded else "✗ No",
                                 delta="Verified" if grounded else "Unverified")
                    
                    with col3:
                        st.metric("Retries", retry_count)
                
                # Display sources
                if sources:
                    st.markdown("#### 📄 Sources")
                    for source in sources:
                        with st.expander(f"📋 {source['source']} [{source['namespace'].upper()}]"):
                            st.caption(f"**Namespace:** {source['namespace']}")
                            st.write(source['excerpt'])
                
            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.session_state.messages.pop()  # Remove failed message from history
