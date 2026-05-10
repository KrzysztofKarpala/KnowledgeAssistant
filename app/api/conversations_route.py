from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.chat_route import calculate_confidence
from app.api.dependencies import (
    get_answer_service,
    get_conversation_message_repository,
    get_conversation_repository,
    get_retrieval_service,
)
from app.models.conversation import Conversation, ConversationMessage, ConversationMessageRole
from app.repositories.conversation_repository import (
    ConversationMessageRepository,
    ConversationRepository,
)
from app.schemas.chat import SourceReference
from app.schemas.conversations import (
    ConversationChatResponse,
    ConversationCreate,
    ConversationMessageCreate,
    ConversationMessageResponse,
    ConversationResponse,
)
from app.services.answer_service import AnswerService, ConversationTurn
from app.services.embedding_service import EmbeddingServiceError
from app.services.llm_service import LLMServiceError
from app.services.retrieval_service import RetrievalService

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
        cited_chunk_ids=message.cited_chunk_ids,
        metadata=message.metadata_,
        created_at=message.created_at,
    )


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
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    answer_service: AnswerService = Depends(get_answer_service),
) -> ConversationChatResponse:
    conversation = await conversation_repository.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

    recent_messages = await message_repository.list_recent_for_conversation(
        conversation_id=conversation_id,
        limit=10,
    )
    history = [
        ConversationTurn(role=message.role.value, content=message.content)
        for message in recent_messages
        if message.role in {ConversationMessageRole.USER, ConversationMessageRole.ASSISTANT}
    ]

    user_message = await message_repository.create(
        conversation_id=conversation_id,
        role=ConversationMessageRole.USER,
        content=payload.content,
    )

    try:
        retrieved_chunks = await retrieval_service.retrieve(question=payload.content)
        answer = await answer_service.answer(
            question=payload.content,
            sources=retrieved_chunks,
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

    sources = [
        SourceReference(
            document_id=result.document_id,
            parent_id=result.parent_id,
            document_title=result.document_title,
            document_version=result.document_version,
            effective_from=result.effective_from,
            chunk_id=result.chunk_id,
            chunk_index=result.chunk_index,
            similarity=result.similarity,
            source_role=result.source_role,
        )
        for result in retrieved_chunks
    ]
    assistant_message = await message_repository.create(
        conversation_id=conversation_id,
        role=ConversationMessageRole.ASSISTANT,
        content=answer.answer,
        cited_chunk_ids=[str(chunk_id) for chunk_id in answer.cited_chunk_ids],
        metadata={
            "sources": [source.model_dump(mode="json") for source in sources],
            "confidence": calculate_confidence([source.similarity for source in sources]),
        },
    )

    return ConversationChatResponse(
        conversation_id=conversation_id,
        user_message_id=user_message.id,
        assistant_message_id=assistant_message.id,
        answer=answer.answer,
        sources=sources,
        cited_chunk_ids=answer.cited_chunk_ids,
        confidence=calculate_confidence([source.similarity for source in sources]),
    )
