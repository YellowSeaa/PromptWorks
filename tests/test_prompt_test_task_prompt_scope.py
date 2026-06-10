from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.prompt import Prompt, PromptClass, PromptVersion


def _create_prompt_with_versions(
    db_session: Session, *, name: str, versions: tuple[str, ...]
) -> Prompt:
    """创建带多个版本的 Prompt，供测试任务归属校验使用。"""

    prompt_class = PromptClass(name=f"{name}分类")
    prompt = Prompt(name=name, prompt_class=prompt_class)
    db_session.add_all([prompt_class, prompt])
    db_session.flush()

    created_versions = [
        PromptVersion(prompt=prompt, version=version, content=f"{name} {version} 内容")
        for version in versions
    ]
    db_session.add_all(created_versions)
    db_session.flush()
    prompt.current_version = created_versions[-1]
    db_session.commit()
    return prompt


def test_create_prompt_test_task_accepts_versions_from_same_prompt(
    client: TestClient, db_session: Session
):
    """同一个 Prompt 的多个版本可以放在同一个测试任务中。"""

    prompt = _create_prompt_with_versions(
        db_session, name="单Prompt任务", versions=("v1", "v2")
    )
    first, second = prompt.versions[0], prompt.versions[1]

    response = client.post(
        "/api/v1/prompt-test/tasks",
        json={
            "name": "同 Prompt 多版本任务",
            "prompt_version_id": first.id,
            "units": [
                {
                    "name": "版本一单元",
                    "model_name": "gpt-test",
                    "prompt_version_id": first.id,
                },
                {
                    "name": "版本二单元",
                    "model_name": "gpt-test",
                    "prompt_version_id": second.id,
                },
            ],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["prompt_version_id"] == first.id
    assert {unit["prompt_version_id"] for unit in body["units"]} == {
        first.id,
        second.id,
    }


def test_create_prompt_test_task_rejects_units_from_different_prompts(
    client: TestClient, db_session: Session
):
    """同一个测试任务不能混入不同 Prompt 的版本。"""

    prompt_a = _create_prompt_with_versions(
        db_session, name="PromptA", versions=("v1",)
    )
    prompt_b = _create_prompt_with_versions(
        db_session, name="PromptB", versions=("v1",)
    )
    version_a = prompt_a.versions[0]
    version_b = prompt_b.versions[0]

    response = client.post(
        "/api/v1/prompt-test/tasks",
        json={
            "name": "跨 Prompt 任务",
            "prompt_version_id": version_a.id,
            "units": [
                {
                    "name": "PromptA 单元",
                    "model_name": "gpt-test",
                    "prompt_version_id": version_a.id,
                },
                {
                    "name": "PromptB 单元",
                    "model_name": "gpt-test",
                    "prompt_version_id": version_b.id,
                },
            ],
        },
    )

    assert response.status_code == 400
    assert "同一个 Prompt" in response.json()["detail"]


def test_create_prompt_test_unit_rejects_version_from_different_prompt(
    client: TestClient, db_session: Session
):
    """为既有任务新增单元时也要保持单 Prompt 归属。"""

    prompt_a = _create_prompt_with_versions(
        db_session, name="追加PromptA", versions=("v1",)
    )
    prompt_b = _create_prompt_with_versions(
        db_session, name="追加PromptB", versions=("v1",)
    )
    version_a = prompt_a.versions[0]
    version_b = prompt_b.versions[0]

    task_response = client.post(
        "/api/v1/prompt-test/tasks",
        json={
            "name": "待追加任务",
            "prompt_version_id": version_a.id,
            "units": [
                {
                    "name": "PromptA 单元",
                    "model_name": "gpt-test",
                    "prompt_version_id": version_a.id,
                }
            ],
        },
    )
    assert task_response.status_code == 201
    task_id = task_response.json()["id"]

    response = client.post(
        f"/api/v1/prompt-test/tasks/{task_id}/units",
        json={
            "name": "跨 Prompt 追加单元",
            "model_name": "gpt-test",
            "prompt_version_id": version_b.id,
        },
    )

    assert response.status_code == 400
    assert "同一个 Prompt" in response.json()["detail"]
