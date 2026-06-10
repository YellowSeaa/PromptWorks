from types import SimpleNamespace

from app.services.llm_context import truncate_messages_for_context


def test_truncate_messages_returns_normalized_messages_without_context_length():
    messages = ({"role": "user", "content": "不需要截断"},)

    result = truncate_messages_for_context(
        messages,
        SimpleNamespace(context_length=None),
        {"max_tokens": 10},
    )

    assert result == [{"role": "user", "content": "不需要截断"}]
    assert result[0] is not messages[0]


def test_truncate_messages_ignores_invalid_context_length():
    messages = [{"role": "user", "content": "原始内容"}]

    assert (
        truncate_messages_for_context(
            messages,
            SimpleNamespace(context_length=0),
        )
        == messages
    )
    assert (
        truncate_messages_for_context(
            messages,
            SimpleNamespace(context_length="128"),
        )
        == messages
    )


def test_truncate_messages_keeps_messages_when_budget_is_enough():
    messages = [{"role": "user", "content": "短内容"}]

    result = truncate_messages_for_context(
        messages,
        SimpleNamespace(context_length=100),
        {"max_tokens": 5},
    )

    assert result == messages


def test_truncate_messages_preserves_system_and_recent_messages_first():
    old_content = "old-" * 20
    latest_content = "最新回答"
    messages = [
        {"role": "system", "content": "系统指令"},
        {"role": "user", "content": old_content},
        {"role": "assistant", "content": latest_content},
    ]

    result = truncate_messages_for_context(
        messages,
        SimpleNamespace(context_length=6),
    )

    assert result[0]["content"] == "系统指令"
    assert result[2]["content"] == latest_content
    assert (
        result[1]["content"]
        == old_content[-(24 - len("系统指令") - len(latest_content)) :]
    )


def test_truncate_messages_reserves_output_tokens_from_parameters():
    messages = [{"role": "user", "content": "abcdefghijklmnopqrstuvwxyz"}]

    result = truncate_messages_for_context(
        messages,
        SimpleNamespace(context_length=8),
        {"max_completion_tokens": 5.1},
    )

    assert result == [{"role": "user", "content": "stuvwxyz"}]


def test_truncate_messages_uses_first_valid_output_token_parameter():
    messages = [{"role": "user", "content": "abcdefghijklmnopqrstuvwxyz"}]

    result = truncate_messages_for_context(
        messages,
        SimpleNamespace(context_length=10),
        {"max_tokens": "bad", "max_completion_tokens": "6"},
    )

    assert result == [{"role": "user", "content": "klmnopqrstuvwxyz"}]


def test_truncate_messages_handles_non_mapping_parameters_and_empty_content():
    messages = [
        {"role": "user", "content": None},
        {"role": "assistant", "content": "abcdef"},
        {"role": "user", "content": "ghijkl"},
    ]

    result = truncate_messages_for_context(
        messages,
        SimpleNamespace(context_length=1),
        object(),
    )

    assert result == [
        {"role": "user", "content": ""},
        {"role": "assistant", "content": ""},
        {"role": "user", "content": "ijkl"},
    ]


def test_truncate_messages_serializes_non_string_content_when_truncating():
    messages = [
        {
            "role": "user",
            "content": {"items": ["alpha", "beta", "gamma"]},
        }
    ]

    result = truncate_messages_for_context(
        messages,
        SimpleNamespace(context_length=3),
    )

    assert result[0]["content"] == 'a","gamma"]}'


def test_truncate_messages_falls_back_to_str_for_non_json_content():
    class NonJsonContent:
        def __str__(self) -> str:
            return "不可序列化内容"

    messages = [{"role": "user", "content": NonJsonContent()}]

    result = truncate_messages_for_context(
        messages,
        SimpleNamespace(context_length=2),
    )

    assert result == [{"role": "user", "content": "不可序列化内容"}]
