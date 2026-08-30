import unittest
import tempfile
from pathlib import Path

from enterprise_rag.app import answer_question
from enterprise_rag.graph import classify_namespace, contextualize_question
from enterprise_rag.security import allowed_namespaces, hash_password, verify_password, validate_question
from enterprise_rag.storage import ChatStore
from enterprise_rag.evaluation import token_f1


class TestRAGPipeline(unittest.TestCase):
    def test_namespace_routing(self):
        self.assertEqual(classify_namespace("How much annual leave do full-time employees receive?"), "hr")
        self.assertEqual(classify_namespace("What is the API rate limit for enterprise tier?"), "technical")
        self.assertEqual(classify_namespace("What is the GDPR retention period for employee data?"), "compliance")

    def test_answer_question_without_llm(self):
        answer = answer_question("How many days of paid annual leave do full-time employees get?")
        self.assertIn("15", answer)
        self.assertIn("annual leave", answer.lower())

    def test_security_controls(self):
        encoded = hash_password("correct horse")
        self.assertTrue(verify_password("correct horse", encoded))
        self.assertFalse(verify_password("wrong", encoded))
        self.assertEqual(allowed_namespaces("engineer"), {"technical"})
        self.assertEqual(validate_question("  hello  "), "hello")

    def test_durable_history_and_feedback(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ChatStore(Path(directory) / "test.db")
            message_id = store.add_message("session", "alice", "assistant", "answer", {"grounded": True})
            store.add_feedback(message_id, "session", "alice", 1)
            history = store.history("session", "alice")
            self.assertEqual(history[0]["content"], "answer")
            self.assertTrue(history[0]["metadata"]["grounded"])

    def test_evaluation_metric(self):
        self.assertEqual(token_f1("same words", "same words"), 1.0)

    def test_natural_follow_up_uses_context(self):
        query = contextualize_question(
            "What about part-time employees?",
            [{"role": "user", "content": "How much annual leave do employees receive?"}],
        )
        self.assertIn("annual leave", query)
        self.assertEqual(classify_namespace(query), "hr")


if __name__ == "__main__":
    unittest.main()
