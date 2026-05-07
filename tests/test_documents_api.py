from app.core.config import settings


class FakeEmbeddingClient:
    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [[0.01] * settings.embedding_dimension for _ in texts]


async def test_document_crud(api_client):
    create_response = await api_client.post(
        "/documents?index=false",
        json={
            "title": "Document CRUD Test",
            "content": "Plain document content.",
            "status": "active",
            "version": "1.0",
            "metadata": {"kind": "test"},
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["chunks_created"] == 0

    get_response = await api_client.get(f"/documents/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["title"] == "Document CRUD Test"

    patch_response = await api_client.patch(
        f"/documents/{created['id']}",
        json={"title": "Document CRUD Test Updated"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["title"] == "Document CRUD Test Updated"

    delete_response = await api_client.delete(f"/documents/{created['id']}")
    assert delete_response.status_code == 204

    missing_response = await api_client.get(f"/documents/{created['id']}")
    assert missing_response.status_code == 404


async def test_create_document_archives_existing_active_document_with_same_title(api_client):
    title = "Versioned Document Test"

    first_response = await api_client.post(
        "/documents?index=false",
        json={
            "title": title,
            "content": "First version.",
            "status": "active",
            "version": "1.0",
        },
    )
    second_response = await api_client.post(
        "/documents?index=false",
        json={
            "title": title,
            "content": "Second version.",
            "status": "active",
            "version": "2.0",
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    first = await api_client.get(f"/documents/{first_response.json()['id']}")
    second = await api_client.get(f"/documents/{second_response.json()['id']}")

    assert first.json()["status"] == "archived"
    assert second.json()["status"] == "active"


async def test_create_document_with_index_stores_chunks(api_client, monkeypatch):
    from app.api import documents as documents_api

    monkeypatch.setattr(documents_api, "EmbeddingClient", FakeEmbeddingClient)

    response = await api_client.post(
        "/documents",
        json={
            "title": "Indexed Document Test",
            "content": "This document should be split and indexed.",
            "status": "active",
            "version": "1.0",
        },
    )

    assert response.status_code == 201
    assert response.json()["chunks_created"] == 1
