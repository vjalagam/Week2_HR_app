import unittest

from enterprise_rag.app import answer_question
from enterprise_rag.graph import classify_namespace


class TestRAGPipeline(unittest.TestCase):
    def test_namespace_routing(self):
        self.assertEqual(classify_namespace("How much annual leave do full-time employees receive?"), "hr")
        self.assertEqual(classify_namespace("What is the API rate limit for enterprise tier?"), "technical")
        self.assertEqual(classify_namespace("What is the GDPR retention period for employee data?"), "compliance")

    def test_answer_question_without_llm(self):
        answer = answer_question("How many days of paid annual leave do full-time employees get?")
        self.assertIn("15", answer)
        self.assertIn("annual leave", answer.lower())


if __name__ == "__main__":
    unittest.main()
