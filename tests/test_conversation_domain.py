import pytest

from app.models.conversation import (
    CONVERSATION_TITLE_MAX_LENGTH,
    Conversation,
)


def test_conversation_title_validation_lives_on_domain_object():
    conversation = Conversation(title=f"  {'A' * CONVERSATION_TITLE_MAX_LENGTH}  ")

    assert conversation.title == "A" * CONVERSATION_TITLE_MAX_LENGTH

    with pytest.raises(ValueError, match="80 characters or fewer"):
        Conversation(title="A" * (CONVERSATION_TITLE_MAX_LENGTH + 1))
