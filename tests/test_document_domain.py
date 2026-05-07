import pytest

from app.models.document import Document, DocumentStatus


def test_document_create_returns_active_document():
    document = Document.create(
        title="Domain Factory Test",
        content="Document content.",
        version="1.0",
        effective_from=None,
        metadata={"kind": "test"},
    )

    assert document.status == DocumentStatus.ACTIVE
    assert document.metadata_ == {"kind": "test"}


def test_document_constructor_is_private_for_application_code():
    with pytest.raises(TypeError, match="Use Document.Create"):
        Document(
            title="Direct Constructor Test",
            content="Document content.",
            version=None,
            effective_from=None,
            metadata={},
        )
