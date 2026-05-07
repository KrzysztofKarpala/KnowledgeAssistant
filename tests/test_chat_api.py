async def test_retrieve_returns_indexed_document(api_client, monkeypatch):
    from app.api import documents as documents_api
    from app.services import retrieval as retrieval_service
    from tests.test_documents_api import FakeEmbeddingClient

    monkeypatch.setattr(documents_api, "EmbeddingClient", FakeEmbeddingClient)
    monkeypatch.setattr(retrieval_service, "EmbeddingClient", FakeEmbeddingClient)

    created_response = await api_client.post(
        "/documents",
        json={
            "title": "Retrieval Test Document",
            "content": "The blue hammer is used for the small screw.",
            "status": "active",
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
