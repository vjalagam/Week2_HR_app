from __future__ import annotations

import json
import logging
import re
from typing import TypedDict

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from .config import SETTINGS
from .data_ingestion import chunk_documents, load_enterprise_documents
from .vector_store import search_documents

# Constants
MAX_RETRIES = 2
TOP_K_PER_NAMESPACE = 4
TOP_K_GENERAL = 2
GRADER_CHUNK_LIMIT = 1500
CHECKER_CONTEXT_LIMIT = 6000


class RAGState(TypedDict):
    question: str
    doc_type: str  # 'hr', 'technical', 'compliance', 'general'
    documents: list[Document]  # all retrieved documents
    grading_result: str  # 'relevant', 'not_relevant'
    generation: str  # the generated answer
    hallucination_result: str  # 'grounded', 'not_grounded'
    retry_count: int
    conversation_history: list[dict[str, str]]
    correlation_id: str
    retrieval_query: str


def contextualize_question(question: str, history: list[dict[str, str]]) -> str:
    """Add the latest user turn to short/ambiguous follow-ups for routing and search."""
    prior_user_messages = [
        item.get("content", "").strip()
        for item in history
        if item.get("role") == "user" and item.get("content", "").strip()
    ]
    if not prior_user_messages:
        return question
    ambiguous = len(question.split()) < 8 or any(
        token in question.lower().split()
        for token in {"it", "that", "this", "they", "those", "there", "also"}
    )
    return f"Previous question: {prior_user_messages[-1]}\nFollow-up question: {question}" if ambiguous else question


def normalize_retrieval_query(question: str) -> str:
    """Add policy terminology for common natural-language synonyms."""
    normalized = question.strip()
    if re.search(r"\b(vacation|vacations|holiday|holidays|pto)\b", normalized, re.IGNORECASE):
        normalized += " annual leave paid leave days"
    return normalized


def get_llm():
    if SETTINGS.has_deepseek:
        return ChatOpenAI(
            model=SETTINGS.deepseek_model,
            api_key=SETTINGS.deepseek_api_key,
            base_url=SETTINGS.deepseek_base_url,
            temperature=0.1,
            timeout=30,
            max_retries=1,
        )
    return None


def route_question_llm(question: str) -> str:
    """LLM-driven router: one call to classify into 4 namespaces."""
    # Known domain vocabulary is more reliable and cheaper to route deterministically.
    deterministic_route = route_question_fallback(question)
    if deterministic_route != "general":
        return deterministic_route

    llm = get_llm()
    if llm is None:
        # Fallback to keyword-based routing if no LLM available
        return route_question_fallback(question)
    
    try:
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a document routing expert. Classify the user question into exactly one category. Return only the category name: 'hr', 'technical', 'compliance', or 'general'."),
            ("user", "Question: {question}\n\nCategory:")
        ])
        chain = prompt | llm
        response = chain.invoke({"question": question})
        category = response.content.strip().lower()
        
        # Sanitization fallback
        if category not in ['hr', 'technical', 'compliance', 'general']:
            return 'general'
        return category
    except Exception:
        # If LLM call fails, fall back to keyword-based routing
        return route_question_fallback(question)


def route_question_fallback(question: str) -> str:
    """Keyword-based fallback routing."""
    lower = question.lower()
    if any(term in lower for term in ["gdpr", "privacy", "security", "breach", "incident", "compliance", "audit", "vendor", "data retention"]):
        return "compliance"
    if any(term in lower for term in ["leave", "vacation", "holiday", "pto", "sick", "maternity", "paternity", "remote work", "manager", "payroll", "benefit", "hr", "employee"]):
        return "hr"
    if any(term in lower for term in ["api", "rate limit", "oauth", "aws", "kubernetes", "deployment", "database", "webhook", "sdk", "sla", "server"]):
        return "technical"
    if "policy" in lower:
        return "compliance"
    return "general"


# Backward compatibility alias
classify_namespace = route_question_fallback


def router_node(state: RAGState) -> RAGState:
    """Entry point: classify the question into a namespace."""
    question = state["question"]
    retrieval_query = normalize_retrieval_query(
        contextualize_question(question, state.get("conversation_history", []))
    )
    state["retrieval_query"] = retrieval_query
    state["doc_type"] = route_question_llm(retrieval_query)
    state["retry_count"] = 0
    logging.getLogger(__name__).info("routed namespace=%s", state["doc_type"])
    return state


def retrieve_documents(question: str, doc_type: str, all_chunks: list[Document]) -> list[Document]:
    """Retrieve documents in targeted or general mode based on doc_type."""
    if doc_type != "general":
        # Targeted mode: search single namespace, return TOP_K_PER_NAMESPACE
        docs = search_documents(question, doc_type, all_chunks, k=TOP_K_PER_NAMESPACE)
    else:
        # General mode: search all 3 namespaces, return TOP_K_GENERAL per namespace
        docs_hr = search_documents(question, "hr", all_chunks, k=TOP_K_GENERAL)
        docs_tech = search_documents(question, "technical", all_chunks, k=TOP_K_GENERAL)
        docs_comp = search_documents(question, "compliance", all_chunks, k=TOP_K_GENERAL)
        docs = docs_hr + docs_tech + docs_comp
    
    return docs


def retriever_node(state: RAGState) -> RAGState:
    """Retrieve documents from enterprise knowledge base."""
    all_docs = load_enterprise_documents()
    all_chunks = chunk_documents(all_docs)
    question = state.get("retrieval_query") or state["question"]
    doc_type = state["doc_type"]
    retry_count = state.get("retry_count", 0)
    
    # After failed grading, widen to all namespaces.
    if state.get("grading_result") == "not_relevant" and retry_count > 0:
        documents = retrieve_documents(question, "general", all_chunks)
    else:
        documents = retrieve_documents(question, doc_type, all_chunks)

    state["documents"] = documents
    return state


def grade_chunk(question: str, chunk: Document) -> bool:
    """Grade a single chunk for relevance using LLM."""
    llm = get_llm()
    if llm is None:
        # Fallback: check for keyword overlap
        low_q = question.lower().split()
        low_text = chunk.page_content.lower()
        overlap = sum(1 for term in low_q if term in low_text and len(term) > 3)
        return overlap >= 2
    
    try:
        # Truncate chunk to GRADER_CHUNK_LIMIT
        truncated_content = chunk.page_content[:GRADER_CHUNK_LIMIT]
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a relevance grader. Determine if the chunk is relevant to the question. Return ONLY valid JSON: {\"score\": \"yes\"} or {\"score\": \"no\"}"),
            ("user", "Question: {question}\n\nChunk:\n{chunk}")
        ])
        chain = prompt | llm
        response = chain.invoke({"question": question, "chunk": truncated_content})
        result = json.loads(response.content)
        return result.get("score", "no").lower() == "yes"
    except Exception:
        # Fail-open: keep the chunk if parsing fails
        return True


def grader_node(state: RAGState) -> RAGState:
    """Grade each retrieved document for relevance."""
    documents = state["documents"]
    question = state.get("retrieval_query") or state["question"]
    
    # Grade each chunk
    filtered = [doc for doc in documents if grade_chunk(question, doc)]
    
    # Update state with filtered documents
    state["documents"] = filtered
    
    # Set grading result and increment retry count on failure
    if not filtered:
        state["grading_result"] = "not_relevant"
        state["retry_count"] = state.get("retry_count", 0) + 1
    else:
        state["grading_result"] = "relevant"
    
    return state


def generator_node(state: RAGState) -> RAGState:
    """Generate answer from filtered context."""
    documents = state["documents"]
    question = state["question"]
    llm = get_llm()
    
    # Format context: chunk text only, no filenames
    if documents:
        context = "\n\n---\n\n".join(doc.page_content for doc in documents)
    else:
        context = "No relevant documents were found."
    
    if llm is None:
        # Fallback local answer
        if context and context != "No relevant documents were found.":
            state["generation"] = context[:500]
        else:
            state["generation"] = "I couldn't find a definitive answer in the knowledge base. The question may be out of scope or not covered in the available documents."
        return state
    
    try:
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a careful enterprise policy assistant for ABC documents (HR, Technical, Compliance).
STRICT RULES:
1. ONLY answer questions directly related to enterprise HR policies, technical documentation, or compliance guidelines.
2. If the question is NOT about these topics, respond ONLY with: "I can only answer questions about enterprise HR policies, technical documentation, and compliance guidelines. Your question appears to be outside this scope."
3. Answer ONLY using the provided context - never add information not in the documents.
4. If the context is empty or clearly irrelevant to the question, refuse to answer.
5. Do not mention document filenames or formatting.
6. Treat common wording such as vacation, holiday, or PTO as annual leave when the context contains an annual-leave policy.
7. Prefer an explicit, direct answer with the relevant unit (for example, days per calendar year), followed by any necessary qualification.
8. Be direct and concise."""),
            ("user", "Question: {question}\n\nContext:\n{context}")
        ])
        chain = prompt | llm
        history = "\n".join(
            f"{item.get('role', 'user')}: {item.get('content', '')[:500]}"
            for item in state.get("conversation_history", [])[-6:]
        )
        contextual_question = f"Conversation history:\n{history}\n\nCurrent question: {question}" if history else question
        response = chain.invoke({"question": contextual_question, "context": context})
        state["generation"] = response.content
    except Exception:
        # Fallback: use context directly if LLM fails
        if context and context != "No relevant documents were found.":
            state["generation"] = context[:500]
        else:
            state["generation"] = "I couldn't find a definitive answer in the knowledge base. The question may be out of scope or not covered in the available documents."
    
    return state


def check_hallucination_chunk(chunk: Document, generation: str) -> bool:
    """Check whether the combined source context fully supports the generation."""
    llm = get_llm()
    
    # Simple fallback: check keyword overlap
    def keyword_overlap_check(gen: str, text: str) -> bool:
        gen_words = set(w.lower() for w in gen.split() if len(w) > 4)
        text_words = set(w.lower() for w in text.split() if len(w) > 4)
        overlap = len(gen_words & text_words)
        return overlap >= 2
    
    if llm is None:
        return keyword_overlap_check(generation, chunk.page_content)
    
    try:
        truncated_content = chunk.page_content[:CHECKER_CONTEXT_LIMIT]
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a hallucination detector. Determine whether an AI-generated answer is fully supported by the provided source document.

Score "yes" -> The answer contains ONLY information that appears in the document.
Score "no" -> The answer contains facts, numbers, or claims NOT found in the document.

Respond with JSON only.
Format: {"score": "yes"} or {"score": "no"}
No explanation, no extra text."""),
            ("user", "AI-GENERATED ANSWER:\n{generation}\n\nSOURCE DOCUMENT:\n{chunk}")
        ])
        chain = prompt | llm
        response = chain.invoke({"generation": generation, "chunk": truncated_content})
        
        # Extract JSON from response
        content = response.content.strip()
        result = json.loads(content)
        return result.get("score", "no").lower() == "yes"
    except Exception:
        # Fallback to simple keyword overlap check if LLM fails
        return keyword_overlap_check(generation, chunk.page_content)


def checker_node(state: RAGState) -> RAGState:
    """Verify that the generated answer is grounded in documents."""
    documents = state["documents"]
    generation = state["generation"]
    retry_count = state.get("retry_count", 0)
    
    # If no documents, pass through (mark as grounded)
    if not documents:
        state["hallucination_result"] = "grounded"
        return state
    
    # Evaluate all retrieved sources together so claims may be supported across chunks.
    combined_sources = Document(
        page_content="\n\n---\n\n".join(doc.page_content for doc in documents),
        metadata={"source": "combined_retrieval_context"},
    )
    if check_hallucination_chunk(combined_sources, generation):
        state["hallucination_result"] = "grounded"
    else:
        state["hallucination_result"] = "not_grounded"
    
    # Increment retry count
    state["retry_count"] = retry_count + 1
    
    return state


def route_after_grader(state: RAGState):
    """Route based on grading result."""
    grading_result = state.get("grading_result")
    retry_count = state.get("retry_count", 0)
    
    if grading_result == "not_relevant":
        # If max retries reached, proceed to generator anyway
        if retry_count >= MAX_RETRIES:
            return "generator"
        # Otherwise retry retrieval
        return "retriever"
    
    return "generator"


def route_after_checker(state: RAGState):
    """Route based on hallucination check result."""
    if state.get("hallucination_result") == "grounded":
        return END
    
    # If not grounded but within retry limit, regenerate
    if state.get("retry_count", 0) < MAX_RETRIES:
        return "generator"
    
    # After MAX_RETRIES, if still not grounded, return refusal message
    if state.get("hallucination_result") == "not_grounded":
        state["generation"] = "I cannot provide a reliable answer to this question based on available enterprise documents. Please ask about HR policies, technical documentation, or compliance guidelines."
    
    return END


def build_graph():
    workflow = StateGraph(RAGState)
    
    # Add all nodes
    workflow.add_node("router", router_node)
    workflow.add_node("retriever", retriever_node)
    workflow.add_node("grader", grader_node)
    workflow.add_node("generator", generator_node)
    workflow.add_node("checker", checker_node)
    
    # Set entry point
    workflow.set_entry_point("router")
    
    # Add edges
    workflow.add_edge("router", "retriever")
    workflow.add_edge("retriever", "grader")
    workflow.add_conditional_edges("grader", route_after_grader, {"retriever": "retriever", "generator": "generator"})
    workflow.add_edge("generator", "checker")
    workflow.add_conditional_edges("checker", route_after_checker, {"generator": "generator", END: END})
    
    return workflow.compile()
