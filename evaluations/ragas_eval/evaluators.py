"""RAGAS scorers for one agent run, with an item-scoped async API client."""

from openai import AsyncOpenAI
from ragas.embeddings.base import embedding_factory
from ragas.llms import llm_factory
from ragas.metrics.collections import (
    ContextPrecision, ContextRecall, Faithfulness, AnswerRelevancy, AnswerCorrectness,
)
from agent import settings  # Loads the project-root .env before creating clients.


class RagasEvaluators:
    """Use `async with RagasEvaluators()` for each dataset item's five scores."""

    async def __aenter__(self):
        self.client = AsyncOpenAI(timeout=60.0, max_retries=2)
        try:
            llm = llm_factory(
                model="gpt-4.1-mini", client=self.client, max_tokens=4096, temperature=0,
            )
            embeddings = embedding_factory(
                "openai", model="text-embedding-3-small", client=self.client, interface="modern",
            )
            self.precision = ContextPrecision(llm=llm)
            self.recall = ContextRecall(llm=llm)
            self.faithfulness = Faithfulness(llm=llm)
            self.relevancy = AnswerRelevancy(llm=llm, embeddings=embeddings)
            self.correctness = AnswerCorrectness(llm=llm, embeddings=embeddings, weights=[0.75, 0.25])
        except Exception:
            await self.client.close()
            raise
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.client.close()

    @staticmethod
    def _validate_contexts(chunks):
        if not isinstance(chunks, list) or not chunks:
            raise ValueError("Expected a nonempty list of actual retrieved document strings")
        if any(not isinstance(chunk, str) or not chunk.strip() for chunk in chunks):
            raise ValueError("Each retrieved chunk must be a nonblank string")

    async def context_precision(self, question: str, reference_answer: str, retrieved_chunks: list[str]) -> float:
        self._validate_contexts(retrieved_chunks)
        result = await self.precision.ascore(
            user_input=question, reference=reference_answer, retrieved_contexts=retrieved_chunks,
        )
        return result.value

    async def context_recall(self, question: str, reference_answer: str, retrieved_chunks: list[str]) -> float:
        self._validate_contexts(retrieved_chunks)
        result = await self.recall.ascore(
            user_input=question, reference=reference_answer, retrieved_contexts=retrieved_chunks,
        )
        return result.value

    async def faithfulness_metric(self, question: str, answer: str, retrieved_chunks: list[str]) -> float:
        self._validate_contexts(retrieved_chunks)
        result = await self.faithfulness.ascore(
            user_input=question, response=answer, retrieved_contexts=retrieved_chunks,
        )
        return result.value

    async def answer_relevancy(self, question: str, answer: str) -> float:
        result = await self.relevancy.ascore(user_input=question, response=answer)
        return result.value

    async def answer_correctness(self, question: str, answer: str, reference_answer: str) -> float:
        result = await self.correctness.ascore(user_input=question, response=answer, reference=reference_answer)
        return result.value
