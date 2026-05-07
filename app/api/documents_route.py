from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.dependencies import get_chunk_repository, get_document_repository
from app.core.config import settings
from app.models.document import Document
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.document_repository import DocumentRepository
from app.schemas.documents import (
    DocumentCreate,
    DocumentCreateResponse,
    DocumentResponse,
    DocumentUpdate,
)
from app.services.chunking_service import chunk_text
from app.services.embedding_service import EmbeddingClient, EmbeddingServiceError

router = APIRouter(prefix="/documents", tags=["documents"])


def serialize_document(document: Document) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        parent_id=document.parent_id,
        title=document.title,
        content=document.content,
        status=document.status,
        version=document.version,
        effective_from=document.effective_from,
        metadata=document.metadata_,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


@router.post("", response_model=DocumentCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    payload: DocumentCreate,
    index: bool = Query(default=True),
    document_repository: DocumentRepository = Depends(get_document_repository),
    chunk_repository: ChunkRepository = Depends(get_chunk_repository),
) -> DocumentCreateResponse:
    chunks: list[str] = []
    embeddings: list[list[float]] = []
    if index:
        chunks = chunk_text(payload.content)
        embeddings = await embed_chunks(chunks)

    if payload.parent_id is not None and await document_repository.get(payload.parent_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent document not found.")

    await document_repository.archive_active_by_title(payload.title)

    document = await document_repository.create(
        title=payload.title,
        content=payload.content,
        parent_id=payload.parent_id,
        version=payload.version,
        effective_from=payload.effective_from,
        metadata=payload.metadata,
    )

    chunks_created = 0
    if chunks:
        chunks_created = await chunk_repository.replace_for_document(
            document_id=document.id,
            chunks=chunks,
            embeddings=embeddings,
        )

    return DocumentCreateResponse(id=document.id, title=document.title, chunks_created=chunks_created)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    document_repository: DocumentRepository = Depends(get_document_repository),
) -> list[DocumentResponse]:
    documents = await document_repository.list(limit=limit, offset=offset)
    return [serialize_document(document) for document in documents]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    document_repository: DocumentRepository = Depends(get_document_repository),
) -> DocumentResponse:
    document = await document_repository.get(document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    return serialize_document(document)


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: UUID,
    payload: DocumentUpdate,
    document_repository: DocumentRepository = Depends(get_document_repository),
    chunk_repository: ChunkRepository = Depends(get_chunk_repository),
) -> DocumentResponse:
    document = await document_repository.get(document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    values = payload.model_dump(exclude_unset=True)
    if values.get("metadata") is None and "metadata" in values:
        values["metadata"] = {}
    if values.get("parent_id") == document_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document cannot be its own parent.",
        )
    if values.get("parent_id") is not None and "parent_id" in values:
        parent = await document_repository.get(values["parent_id"])
        if parent is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent document not found.",
            )

    content_changed = "content" in values
    updated_document = await document_repository.update(document, values)
    if content_changed:
        await chunk_repository.replace_for_document(
            document_id=document.id,
            chunks=[],
            embeddings=[],
        )

    return serialize_document(updated_document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    document_repository: DocumentRepository = Depends(get_document_repository),
) -> Response:
    deleted = await document_repository.delete(document_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{document_id}/reindex", response_model=DocumentCreateResponse)
async def reindex_document(
    document_id: UUID,
    document_repository: DocumentRepository = Depends(get_document_repository),
    chunk_repository: ChunkRepository = Depends(get_chunk_repository),
) -> DocumentCreateResponse:
    document = await document_repository.get(document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    chunks_created = await index_document_chunks(
        chunk_repository=chunk_repository,
        document=document,
    )
    return DocumentCreateResponse(
        id=document.id,
        title=document.title,
        chunks_created=chunks_created,
    )


async def index_document_chunks(
    *,
    chunk_repository: ChunkRepository,
    document: Document,
) -> int:
    chunks = chunk_text(document.content)
    if not chunks:
        return 0

    embeddings = await embed_chunks(chunks)
    return await chunk_repository.replace_for_document(
        document_id=document.id,
        chunks=chunks,
        embeddings=embeddings,
    )


async def embed_chunks(chunks: list[str]) -> list[list[float]]:
    try:
        embeddings = await EmbeddingClient().embed_many(chunks)
    except EmbeddingServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    if len(chunks) != len(embeddings):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Embedding service returned a different number of embeddings than chunks.",
        )

    invalid_dimensions = [
        len(embedding)
        for embedding in embeddings
        if len(embedding) != settings.embedding_dimension
    ]
    if invalid_dimensions:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Embedding service returned vectors with invalid dimensions. "
                f"Expected {settings.embedding_dimension}, got {invalid_dimensions[0]}."
            ),
        )

    return embeddings
