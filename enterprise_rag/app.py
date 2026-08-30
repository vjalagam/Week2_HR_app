from __future__ import annotations

import argparse

from .graph import RAGState, build_graph
from .observability import configure_logging, new_correlation_id, timed_operation
from .security import check_rate_limit, validate_question


def run_question(question: str, history: list[dict[str, str]] | None = None,
                 identity: str = "cli", correlation_id: str | None = None) -> RAGState:
    configure_logging()
    question = validate_question(question)
    check_rate_limit(identity)
    request_id = new_correlation_id(correlation_id)
    graph = build_graph()
    state: RAGState = {
        "question": question,
        "doc_type": "general",
        "documents": [],
        "grading_result": "",
        "generation": "",
        "hallucination_result": "",
        "retry_count": 0,
        "conversation_history": history or [],
        "correlation_id": request_id,
        "retrieval_query": question,
    }
    with timed_operation("answer_question"):
        result = graph.invoke(state)
    return result


def answer_question(question: str, history: list[dict[str, str]] | None = None) -> str:
    result = run_question(question, history=history)
    return result.get("generation") or "I could not determine a grounded answer from the available enterprise documents."


def main():
    parser = argparse.ArgumentParser(description="Enterprise RAG over ABC docs")
    parser.add_argument("--question", type=str, help="Question to answer from enterprise documents")
    parser.add_argument("--index", action="store_true", help="Index the enterprise documents into the configured vector store")
    args = parser.parse_args()

    if args.index:
        from .data_ingestion import chunk_documents, load_enterprise_documents
        from .vector_store import init_vector_index

        docs = load_enterprise_documents()
        chunks = chunk_documents(docs)
        init_vector_index(chunks)
        print("Documents indexed successfully.")
        return

    if not args.question:
        parser.error("Provide a --question value or use --index to build the vector index.")

    response = answer_question(args.question)
    print(response)


if __name__ == "__main__":
    main()
