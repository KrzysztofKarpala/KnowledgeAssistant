import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import delete

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.database import async_session_factory, engine
from app.models.document import Document, DocumentStatus
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.document_repository import DocumentRepository
from app.services.chunking_service import chunk_text
from app.services.embedding_service import EmbeddingClient


DEFAULT_FIXTURE_PATH = PROJECT_ROOT / "seed" / "mes_products_v1.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed MES product/place/equipment demo documents.")
    parser.add_argument(
        "--fixture",
        type=Path,
        default=DEFAULT_FIXTURE_PATH,
        help="Path to the seed fixture JSON file.",
    )
    parser.add_argument(
        "--index",
        action="store_true",
        help="Chunk and embed seeded documents. Requires the configured embedding service.",
    )
    parser.add_argument(
        "--no-index",
        action="store_true",
        help="Create documents without chunks or embeddings. This is the default.",
    )
    return parser.parse_args()


def load_fixture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


async def delete_existing_seed_documents(dataset: str) -> None:
    async with async_session_factory() as session:
        await session.execute(
            delete(Document).where(Document.metadata_["seed_dataset"].astext == dataset)
        )
        await session.commit()


async def create_documents(fixture: dict[str, Any], *, index: bool) -> dict[str, str]:
    dataset = fixture["dataset"]
    documents = fixture["documents"]
    created_ids_by_seed_key: dict[str, str] = {}

    async with async_session_factory() as session:
        document_repository = DocumentRepository(session)
        chunk_repository = ChunkRepository(session)
        embedding_client = EmbeddingClient()

        pending_documents = list(documents)
        while pending_documents:
            created_in_pass = 0
            for document_data in pending_documents[:]:
                parent_seed_key = document_data.get("parent_seed_key")
                if parent_seed_key and parent_seed_key not in created_ids_by_seed_key:
                    continue

                parent_id = parse_uuid(created_ids_by_seed_key.get(parent_seed_key))
                document = await document_repository.create(
                    title=document_data["title"],
                    content=document_data["content"],
                    parent_id=parent_id,
                    version=document_data.get("version"),
                    effective_from=parse_date(document_data.get("effective_from")),
                    metadata={
                        "seed_dataset": dataset,
                        "seed_key": document_data["seed_key"],
                        "category": document_data["category"],
                    },
                )
                apply_seed_status(document, document_data.get("status", DocumentStatus.ACTIVE))
                await session.commit()
                await session.refresh(document)
                created_ids_by_seed_key[document_data["seed_key"]] = str(document.id)

                if index:
                    chunks = chunk_text(document.content)
                    embeddings = await embedding_client.embed_many(chunks)
                    await chunk_repository.replace_for_document(
                        document_id=document.id,
                        chunks=chunks,
                        embeddings=embeddings,
                    )

                pending_documents.remove(document_data)
                created_in_pass += 1

            if created_in_pass == 0:
                unresolved = ", ".join(document["seed_key"] for document in pending_documents)
                raise RuntimeError(f"Could not resolve parent_seed_key values for: {unresolved}")

    return created_ids_by_seed_key


def parse_date(value: str | None) -> date | None:
    if value is None:
        return None
    return date.fromisoformat(value)


def parse_uuid(value: str | None) -> UUID | None:
    if value is None:
        return None
    return UUID(value)


def apply_seed_status(document: Document, status: str) -> None:
    parsed_status = DocumentStatus(status)
    if parsed_status == DocumentStatus.ARCHIVED:
        document.move_to_archived()


def print_summary(fixture: dict[str, Any], created_ids_by_seed_key: dict[str, str], *, index: bool) -> None:
    print(f"Seeded dataset: {fixture['dataset']}")
    print(f"Documents created: {len(created_ids_by_seed_key)}")
    print(f"Indexing: {'enabled' if index else 'disabled'}")
    print()
    for seed_key, document_id in created_ids_by_seed_key.items():
        print(f"{seed_key}: {document_id}")

    print()
    print("Suggested questions:")
    for question in fixture.get("questions", []):
        print(f"- {question}")


async def main() -> None:
    args = parse_args()
    index = bool(args.index and not args.no_index)
    fixture = load_fixture(args.fixture)

    await delete_existing_seed_documents(fixture["dataset"])
    created_ids_by_seed_key = await create_documents(fixture, index=index)
    await engine.dispose()

    print_summary(fixture, created_ids_by_seed_key, index=index)


if __name__ == "__main__":
    asyncio.run(main())
