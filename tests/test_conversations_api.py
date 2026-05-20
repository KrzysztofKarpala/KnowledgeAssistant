from datetime import date
from uuid import uuid4

from app.api.dependencies import (
    get_answer_service,
    get_conversation_title_service,
    get_follow_up_classifier,
    get_query_rewrite_service,
    get_retrieval_service,
)
from app.api.conversations_route import merge_evidence_chunks
from app.main import app
from app.services.answer_service import AnswerResult
from app.services.retrieval_service import RetrievedChunk


async def test_update_conversation_title(api_client):
    created_response = await api_client.post("/conversations", json={"title": "Old title"})
    assert created_response.status_code == 201

    update_response = await api_client.patch(
        f"/conversations/{created_response.json()['id']}",
        json={"title": "Renamed conversation"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Renamed conversation"


async def test_first_user_message_sets_default_conversation_title(api_client):
    app.dependency_overrides[get_retrieval_service] = lambda: RetrievalServiceMock()
    app.dependency_overrides[get_answer_service] = lambda: AnswerServiceMock()
    title_service = ConversationTitleServiceMock(title="Reset Admin Password")
    app.dependency_overrides[get_conversation_title_service] = lambda: title_service

    created_response = await api_client.post("/conversations", json={"title": "New conversation"})
    assert created_response.status_code == 201
    conversation_id = created_response.json()["id"]

    message_response = await api_client.post(
        f"/conversations/{conversation_id}/messages",
        json={
            "content": (
                "How do I reset a user password from the admin console? "
                "Please answer with the safest procedure."
            )
        },
    )
    assert message_response.status_code == 200

    conversation_response = await api_client.get(f"/conversations/{conversation_id}")

    assert conversation_response.status_code == 200
    assert conversation_response.json()["title"] == "Reset Admin Password"
    assert title_service.messages == [
        "How do I reset a user password from the admin console? "
        "Please answer with the safest procedure."
    ]


async def test_conversation_uses_llm_follow_up_classifier_for_previous_evidence(api_client):
    previous_chunk = make_retrieved_chunk(content="Line SMT-04 approves AX-100.", similarity=0.9)
    current_chunk = make_retrieved_chunk(content="Unrelated current retrieval.", similarity=0.2)
    retrieval_service = RetrievalServiceMock(results=[[previous_chunk], [current_chunk]])
    answer_service = AnswerServiceMock()
    follow_up_classifier = FollowUpClassifierMock(results=[False, True])
    query_rewrite_service = QueryRewriteServiceMock(
        rewritten_queries=["Why is line SMT-04 approved for AX-100?"]
    )
    app.dependency_overrides[get_retrieval_service] = lambda: retrieval_service
    app.dependency_overrides[get_answer_service] = lambda: answer_service
    app.dependency_overrides[get_follow_up_classifier] = lambda: follow_up_classifier
    app.dependency_overrides[get_conversation_title_service] = lambda: ConversationTitleServiceMock()
    app.dependency_overrides[get_query_rewrite_service] = lambda: query_rewrite_service

    created_response = await api_client.post("/conversations", json={"title": "New conversation"})
    conversation_id = created_response.json()["id"]

    first_response = await api_client.post(
        f"/conversations/{conversation_id}/messages",
        json={"content": "Which production line approves AX-100?"},
    )
    assert first_response.status_code == 200

    second_response = await api_client.post(
        f"/conversations/{conversation_id}/messages",
        json={"content": "Why?"},
    )

    assert second_response.status_code == 200
    assert follow_up_classifier.questions == [
        "Which production line approves AX-100?",
        "Why?",
    ]
    assert retrieval_service.questions == [
        "Which production line approves AX-100?",
        "Why is line SMT-04 approved for AX-100?",
    ]
    assert [chunk.content for chunk in answer_service.source_calls[-1]] == [
        "Line SMT-04 approves AX-100.",
        "Unrelated current retrieval.",
    ]


async def test_follow_up_rewritten_query_is_used_for_retrieval_and_metadata(api_client):
    retrieval_service = RetrievalServiceMock()
    follow_up_classifier = FollowUpClassifierMock(results=[False, True])
    query_rewrite_service = QueryRewriteServiceMock(
        rewritten_queries=["Is product CX-300 approved or suitable for use on line SMT-04?"]
    )
    app.dependency_overrides[get_retrieval_service] = lambda: retrieval_service
    app.dependency_overrides[get_answer_service] = lambda: AnswerServiceMock()
    app.dependency_overrides[get_follow_up_classifier] = lambda: follow_up_classifier
    app.dependency_overrides[get_conversation_title_service] = lambda: ConversationTitleServiceMock()
    app.dependency_overrides[get_query_rewrite_service] = lambda: query_rewrite_service

    created_response = await api_client.post("/conversations", json={"title": "New conversation"})
    conversation_id = created_response.json()["id"]

    await api_client.post(
        f"/conversations/{conversation_id}/messages",
        json={"content": "What product should be used in line SMT-04?"},
    )
    second_response = await api_client.post(
        f"/conversations/{conversation_id}/messages",
        json={"content": "What about product CX-300?"},
    )

    assert second_response.status_code == 200
    assert retrieval_service.questions[-1] == (
        "Is product CX-300 approved or suitable for use on line SMT-04?"
    )

    messages_response = await api_client.get(f"/conversations/{conversation_id}/messages")
    latest_assistant = messages_response.json()[-1]
    assert latest_assistant["metadata"]["original_question"] == "What about product CX-300?"
    assert latest_assistant["metadata"]["retrieval_question"] == (
        "Is product CX-300 approved or suitable for use on line SMT-04?"
    )
    assert latest_assistant["metadata"]["used_previous_evidence"] is True


def test_follow_up_evidence_merges_previous_retrieved_chunks():
    previous_chunk = make_retrieved_chunk(content="Line SMT-04 approves AX-100.", similarity=0.52)
    current_chunk = make_retrieved_chunk(content="Unrelated current retrieval.", similarity=0.2)

    evidence = merge_evidence_chunks(
        current_chunks=[current_chunk],
        previous_chunks=[previous_chunk],
    )

    assert [chunk.content for chunk in evidence] == [
        "Line SMT-04 approves AX-100.",
        "Unrelated current retrieval.",
    ]


class RetrievalServiceMock:
    def __init__(self, results: list[list[RetrievedChunk]] | None = None) -> None:
        self.results = list(results or [])
        self.questions = []

    async def retrieve(self, *, question: str):
        self.questions.append(question)
        if self.results:
            return self.results.pop(0)
        return []


class AnswerServiceMock:
    def __init__(self) -> None:
        self.source_calls = []

    async def answer(self, *, question: str, sources: list, conversation_history: list | None = None):
        self.source_calls.append(sources)
        return AnswerResult(answer="No indexed source contains that answer.", cited_chunk_ids=[])


class FollowUpClassifierMock:
    def __init__(self, results: list[bool] | None = None) -> None:
        self.results = list(results or [False])
        self.questions = []

    async def is_follow_up(self, *, question: str, conversation_history: list) -> bool:
        self.questions.append(question)
        if self.results:
            return self.results.pop(0)
        return False


class ConversationTitleServiceMock:
    def __init__(self, title: str = "Mock conversation title") -> None:
        self.title = title
        self.messages = []

    async def generate_title(self, *, first_user_message: str) -> str:
        self.messages.append(first_user_message)
        return self.title


class QueryRewriteServiceMock:
    def __init__(self, rewritten_queries: list[str] | None = None) -> None:
        self.rewritten_queries = list(rewritten_queries or [])
        self.questions = []
        self.histories = []

    async def rewrite(self, *, question: str, conversation_history: list) -> str:
        self.questions.append(question)
        self.histories.append(conversation_history)
        if not conversation_history:
            return question
        if self.rewritten_queries:
            return self.rewritten_queries.pop(0)
        return question


def make_retrieved_chunk(*, content: str, similarity: float) -> RetrievedChunk:
    return RetrievedChunk(
        document_id=uuid4(),
        parent_id=None,
        document_title="Document",
        document_version="1.0",
        effective_from=date(2026, 1, 1),
        chunk_id=uuid4(),
        chunk_index=0,
        content=content,
        similarity=similarity,
    )
