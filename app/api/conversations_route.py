from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.chat_route import build_source_references, calculate_confidence
from app.api.dependencies import (
    get_answer_service,
    get_chunk_repository,
    get_conversation_message_repository,
    get_conversation_repository,
    get_conversation_title_service,
    get_follow_up_classifier,
    get_query_rewrite_service,
    get_retrieval_service,
)
from app.models.conversation import (
    DEFAULT_CONVERSATION_TITLES,
    Conversation,
    ConversationMessage,
    ConversationMessageRole,
)
from app.repositories.conversation_repository import (
    ConversationMessageRepository,
    ConversationRepository,
)
from app.repositories.chunk_repository import ChunkRepository
from app.schemas.conversations import (
    ConversationChatResponse,
    ConversationCreate,
    ConversationMessageCreate,
    ConversationMessageResponse,
    ConversationResponse,
    ConversationUpdate,
)
from app.services.answer_service import AnswerService, ConversationTurn
from app.services.conversation_title_service import ConversationTitleService
from app.services.embedding_service import EmbeddingServiceError
from app.services.follow_up_service import FollowUpClassifier
from app.services.llm_service import LLMServiceError
from app.services.query_rewrite_service import QueryRewriteService
from app.services.retrieval_service import RetrievedChunk, RetrievalService

router = APIRouter(prefix="/conversations", tags=["conversations"])


def serialize_conversation(conversation: Conversation) -> ConversationResponse:
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        status=conversation.status,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


def serialize_message(message: ConversationMessage) -> ConversationMessageResponse:
    return ConversationMessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        role=message.role,
        content=message.content,
        cited_chunk_ids=[UUID(chunk_id) for chunk_id in message.cited_chunk_ids],
        metadata=message.metadata_,
        created_at=message.created_at,
    )


def build_conversation_history(messages: list[ConversationMessage]) -> list[ConversationTurn]:
    return [
        ConversationTurn(role=message.role.value, content=message.content)
        for message in messages
        if message.role in {ConversationMessageRole.USER, ConversationMessageRole.ASSISTANT}
    ]


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate,
    conversation_repository: ConversationRepository = Depends(get_conversation_repository),
) -> ConversationResponse:
    conversation = await conversation_repository.create(title=payload.title)
    return serialize_conversation(conversation)


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    conversation_repository: ConversationRepository = Depends(get_conversation_repository),
) -> list[ConversationResponse]:
    conversations = await conversation_repository.list(limit=limit, offset=offset)
    return [serialize_conversation(conversation) for conversation in conversations]


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    conversation_repository: ConversationRepository = Depends(get_conversation_repository),
) -> ConversationResponse:
    conversation = await conversation_repository.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

    return serialize_conversation(conversation)


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: UUID,
    payload: ConversationUpdate,
    conversation_repository: ConversationRepository = Depends(get_conversation_repository),
) -> ConversationResponse:
    conversation = await conversation_repository.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

    updated = await conversation_repository.update_title(
        conversation=conversation,
        title=payload.title,
    )
    return serialize_conversation(updated)


@router.get("/{conversation_id}/messages", response_model=list[ConversationMessageResponse])
async def list_conversation_messages(
    conversation_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    conversation_repository: ConversationRepository = Depends(get_conversation_repository),
    message_repository: ConversationMessageRepository = Depends(get_conversation_message_repository),
) -> list[ConversationMessageResponse]:
    conversation = await conversation_repository.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

    messages = await message_repository.list_for_conversation(
        conversation_id=conversation_id,
        limit=limit,
        offset=offset,
    )
    return [serialize_message(message) for message in messages]


@router.post("/{conversation_id}/messages", response_model=ConversationChatResponse)
async def create_conversation_message(
    conversation_id: UUID,
    payload: ConversationMessageCreate,
    conversation_repository: ConversationRepository = Depends(get_conversation_repository),
    message_repository: ConversationMessageRepository = Depends(get_conversation_message_repository),
    chunk_repository: ChunkRepository = Depends(get_chunk_repository),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    answer_service: AnswerService = Depends(get_answer_service),
    follow_up_classifier: FollowUpClassifier = Depends(get_follow_up_classifier),
    title_service: ConversationTitleService = Depends(get_conversation_title_service),
    query_rewrite_service: QueryRewriteService = Depends(get_query_rewrite_service),
) -> ConversationChatResponse:
    conversation = await conversation_repository.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

    recent_messages = await message_repository.list_recent_for_conversation(
        conversation_id=conversation_id,
        limit=10,
    )
    history = build_conversation_history(list(recent_messages))

    user_message = await message_repository.create(
        conversation_id=conversation_id,
        role=ConversationMessageRole.USER,
        content=payload.content,
    )

    try:
        if should_autoname_conversation(conversation=conversation, history=history):
            conversation = await conversation_repository.update_title(
                conversation=conversation,
                title=await title_service.generate_title(first_user_message=payload.content),
            )

        include_previous_evidence = await follow_up_classifier.is_follow_up(
            question=payload.content,
            conversation_history=history,
        )
        retrieval_question = await query_rewrite_service.rewrite(
            question=payload.content,
            conversation_history=history if include_previous_evidence else [],
        )
        retrieved_chunks = await retrieval_service.retrieve(question=retrieval_question)
        previous_chunks = await previous_retrieved_chunks(
            messages=list(recent_messages),
            chunk_repository=chunk_repository,
        )
        evidence_chunks = merge_evidence_chunks(
            current_chunks=retrieved_chunks,
            previous_chunks=previous_chunks if include_previous_evidence else [],
        )
        answer = await answer_service.answer(
            question=retrieval_question,
            sources=evidence_chunks,
            conversation_history=history,
        )
    except EmbeddingServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except LLMServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    sources = build_source_references(evidence_chunks)
    confidence = calculate_confidence([source.similarity for source in sources])
    assistant_message = await message_repository.create(
        conversation_id=conversation_id,
        role=ConversationMessageRole.ASSISTANT,
        content=answer.answer,
        cited_chunk_ids=[str(chunk_id) for chunk_id in answer.cited_chunk_ids],
        metadata={
            "sources": [source.model_dump(mode="json") for source in sources],
            "retrieved_chunks": serialize_retrieved_chunks(evidence_chunks),
            "retrieval_question": retrieval_question,
            "original_question": payload.content,
            "used_previous_evidence": include_previous_evidence,
            "confidence": confidence,
        },
    )

    return ConversationChatResponse(
        conversation_id=conversation_id,
        user_message_id=user_message.id,
        assistant_message_id=assistant_message.id,
        answer=answer.answer,
        sources=sources,
        cited_chunk_ids=answer.cited_chunk_ids,
        confidence=confidence,
    )


def should_autoname_conversation(
    *,
    conversation: Conversation,
    history: list[ConversationTurn],
) -> bool:
    title = (conversation.title or "").strip().lower()
    return not history and (not title or title in DEFAULT_CONVERSATION_TITLES)


async def previous_retrieved_chunks(
    *,
    messages: list[ConversationMessage],
    chunk_repository: ChunkRepository,
) -> list[RetrievedChunk]:
    for message in reversed(messages):
        if message.role != ConversationMessageRole.ASSISTANT:
            continue

        serialized_chunks = message.metadata_.get("retrieved_chunks")
        if isinstance(serialized_chunks, list) and serialized_chunks:
            return [
                chunk
                for item in serialized_chunks
                if (chunk := deserialize_retrieved_chunk(item)) is not None
            ]

        sources = message.metadata_.get("sources")
        chunk_ids = extract_source_chunk_ids(sources)
        if not chunk_ids:
            continue

        rows = await chunk_repository.get_by_ids(chunk_ids=chunk_ids)
        scores_by_chunk_id = {
            UUID(source["chunk_id"]): float(source.get("similarity", 0.0))
            for source in sources
            if isinstance(source, dict) and isinstance(source.get("chunk_id"), str)
        }
        roles_by_chunk_id = {
            UUID(source["chunk_id"]): str(source.get("source_role", "previous_context"))
            for source in sources
            if isinstance(source, dict) and isinstance(source.get("chunk_id"), str)
        }
        return [
            RetrievedChunk(
                document_id=document.id,
                parent_id=document.parent_id,
                document_title=document.title,
                document_version=document.version,
                effective_from=document.effective_from,
                chunk_id=chunk.id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                similarity=scores_by_chunk_id.get(chunk.id, 0.0),
                source_role=roles_by_chunk_id.get(chunk.id, "previous_context"),
            )
            for chunk, document in rows
        ]

    return []


def merge_evidence_chunks(
    *,
    current_chunks: list[RetrievedChunk],
    previous_chunks: list[RetrievedChunk],
) -> list[RetrievedChunk]:
    chunks_by_id: dict[UUID, RetrievedChunk] = {}
    for chunk in previous_chunks + current_chunks:
        chunks_by_id[chunk.chunk_id] = chunk
    return sorted(chunks_by_id.values(), key=lambda chunk: chunk.similarity, reverse=True)


def serialize_retrieved_chunks(chunks: list[RetrievedChunk]) -> list[dict]:
    return [
        {
            "document_id": str(chunk.document_id),
            "parent_id": str(chunk.parent_id) if chunk.parent_id else None,
            "document_title": chunk.document_title,
            "document_version": chunk.document_version,
            "effective_from": chunk.effective_from.isoformat() if chunk.effective_from else None,
            "chunk_id": str(chunk.chunk_id),
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "similarity": chunk.similarity,
            "source_role": chunk.source_role,
        }
        for chunk in chunks
    ]


def deserialize_retrieved_chunk(item: object) -> RetrievedChunk | None:
    if not isinstance(item, dict):
        return None

    try:
        return RetrievedChunk(
            document_id=UUID(str(item["document_id"])),
            parent_id=UUID(str(item["parent_id"])) if item.get("parent_id") else None,
            document_title=str(item["document_title"]),
            document_version=str(item["document_version"]) if item.get("document_version") else None,
            effective_from=None,
            chunk_id=UUID(str(item["chunk_id"])),
            chunk_index=int(item["chunk_index"]),
            content=str(item["content"]),
            similarity=float(item["similarity"]),
            source_role=str(item.get("source_role", "previous_context")),
        )
    except (KeyError, TypeError, ValueError):
        return None


def extract_source_chunk_ids(sources: object) -> list[UUID]:
    if not isinstance(sources, list):
        return []

    chunk_ids: list[UUID] = []
    for source in sources:
        if not isinstance(source, dict) or not isinstance(source.get("chunk_id"), str):
            continue
        try:
            chunk_ids.append(UUID(source["chunk_id"]))
        except ValueError:
            continue
    return chunk_ids
