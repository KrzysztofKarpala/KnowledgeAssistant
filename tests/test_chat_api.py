async def test_retrieve_returns_indexed_document(api_client, monkeypatch):
    from app.api import documents_route
    from app.services import retrieval_service
    from tests.test_documents_api import EmbeddingClientMock

    monkeypatch.setattr(documents_route, "EmbeddingClient", EmbeddingClientMock)
    monkeypatch.setattr(retrieval_service, "EmbeddingClient", EmbeddingClientMock)

    created_response = await api_client.post(
        "/documents",
        json={
            "title": "Retrieval Test Document",
            "content": "The blue hammer is used for the small screw.",
            "version": "1.0",
        },
    )
    assert created_response.status_code == 201

    retrieve_response = await api_client.post(
        "/chat/retrieve",
        json={
            "question": "Which hammer is used for the small screw?",
            "limit": 3,
            "active_only": True,
        },
    )

    assert retrieve_response.status_code == 200
    results = retrieve_response.json()["results"]
    assert len(results) == 1
    assert results[0]["document_title"] == "Retrieval Test Document"


async def test_retrieve_includes_parent_document_for_child_match(api_client, monkeypatch):
    from app.api import documents_route
    from app.services import retrieval_service
    from tests.test_documents_api import EmbeddingClientMock

    monkeypatch.setattr(documents_route, "EmbeddingClient", EmbeddingClientMock)
    monkeypatch.setattr(retrieval_service, "EmbeddingClient", EmbeddingClientMock)

    parent_response = await api_client.post(
        "/documents",
        json={
            "title": "Parent Retrieval Test",
            "content": "Parent rule: supervisor approval is required.",
            "version": "1.0",
            "effective_from": "2026-01-01",
        },
    )
    assert parent_response.status_code == 201

    child_response = await api_client.post(
        "/documents",
        json={
            "title": "Child Retrieval Test",
            "content": "Child rule: senior operator self-release is allowed.",
            "parent_id": parent_response.json()["id"],
            "version": "1.0",
            "effective_from": "2026-02-01",
        },
    )
    assert child_response.status_code == 201

    retrieve_response = await api_client.post(
        "/chat/retrieve",
        json={
            "question": "Can a senior operator self-release?",
            "limit": 1,
            "active_only": True,
        },
    )

    assert retrieve_response.status_code == 200
    results = retrieve_response.json()["results"]
    titles = {result["document_title"] for result in results}
    source_roles = {result["document_title"]: result["source_role"] for result in results}

    assert "Child Retrieval Test" in titles
    assert "Parent Retrieval Test" in titles
    assert source_roles["Parent Retrieval Test"] == "hierarchy_parent"
