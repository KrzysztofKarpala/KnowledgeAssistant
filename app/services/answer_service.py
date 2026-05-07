from app.services.llm_service import LLMClient, load_answer_system_prompt
from app.services.retrieval_service import RetrievedChunk


class AnswerService:
    def __init__(self, *, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    async def answer(self, *, question: str, sources: list[RetrievedChunk]) -> str:
        if not sources:
            return "The available documentation does not contain enough information to answer this question."

        context = self._build_context(sources)
        user_prompt = (
            "Question:\n"
            f"{question}\n\n"
            "Context sources:\n"
            f"{context}\n\n"
            "Answer using only the context sources above."
        )

        return await self.llm_client.generate(
            system_prompt=load_answer_system_prompt(),
            user_prompt=user_prompt,
        )

    def _build_context(self, sources: list[RetrievedChunk]) -> str:
        blocks: list[str] = []
        for source in sources:
            blocks.append(
                "\n".join(
                    [
                        f"Source: {source.document_title}",
                        f"Document ID: {source.document_id}",
                        f"Version: {source.document_version or 'unknown'}",
                        f"Effective from: {source.effective_from or 'unknown'}",
                        f"Chunk: {source.chunk_index}",
                        f"Similarity: {source.similarity:.4f}",
                        f"Content: {source.content}",
                    ]
                )
            )

        return "\n\n---\n\n".join(blocks)
