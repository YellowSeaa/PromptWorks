from __future__ import annotations

import ast
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_release_config() -> dict:
    return json.loads((ROOT / ".releaserc").read_text(encoding="utf-8"))


def test_semantic_release_enables_beta_prereleases_on_dev():
    config = load_release_config()

    assert config["branches"] == [
        "main",
        {"name": "dev", "prerelease": "beta"},
    ]


def test_release_prepare_uses_next_release_version_for_version_artifacts():
    config = load_release_config()
    exec_plugin = next(
        plugin
        for plugin in config["plugins"]
        if isinstance(plugin, list) and plugin[0] == "@semantic-release/exec"
    )

    prepare_cmd = exec_plugin[1]["prepareCmd"]

    assert "${nextRelease.version}" in prepare_cmd
    assert "package.json" not in prepare_cmd


def test_release_version_prepare_script_persists_release_version_artifacts():
    version_file = ROOT / "frontend" / "src" / "version.json"
    package_file = ROOT / "package.json"
    package_lock_file = ROOT / "package-lock.json"
    original = version_file.read_text(encoding="utf-8")
    original_package = package_file.read_text(encoding="utf-8")
    original_package_lock = package_lock_file.read_text(encoding="utf-8")

    try:
        subprocess.run(
            ["node", "scripts/prepare_release_version.js", "1.2.3-beta.4"],
            cwd=ROOT,
            check=True,
        )

        assert json.loads(version_file.read_text(encoding="utf-8")) == {
            "version": "v1.2.3-beta.4"
        }
        assert (
            json.loads(package_file.read_text(encoding="utf-8"))["version"]
            == "1.2.3-beta.4"
        )

        package_lock = json.loads(package_lock_file.read_text(encoding="utf-8"))
        assert package_lock["version"] == "1.2.3-beta.4"
        assert package_lock["packages"][""]["version"] == "1.2.3-beta.4"
    finally:
        version_file.write_text(original, encoding="utf-8")
        package_file.write_text(original_package, encoding="utf-8")
        package_lock_file.write_text(original_package_lock, encoding="utf-8")


def test_release_commit_tracks_version_artifacts():
    config = load_release_config()
    git_plugin = next(
        plugin
        for plugin in config["plugins"]
        if isinstance(plugin, list) and plugin[0] == "@semantic-release/git"
    )

    assert git_plugin[1]["assets"] == [
        "CHANGELOG.md",
        "package.json",
        "package-lock.json",
        "frontend/src/version.json",
    ]


def test_ci_runs_semantic_release_on_main_and_dev_and_tags_images_by_release_version():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "执行 semantic-release" in workflow
    release_step_start = workflow.index("- name: 执行 semantic-release")
    release_step_end = workflow.index("- name: 启用 QEMU")
    release_step = workflow[release_step_start:release_step_end]
    assert "refs/heads/main" not in release_step
    assert "RELEASE_VERSION=" in workflow
    assert "RELEASE_PUBLISHED=true" in workflow
    assert 'if [[ "${RELEASE_PUBLISHED}" == "true" ]]' in workflow
    assert 'IMAGE_VERSION="v${RELEASE_VERSION}"' in workflow
    assert 'IMAGE_VERSION="${TARGET_BRANCH}-${GITHUB_SHA}"' in workflow
    assert "image_version=${IMAGE_VERSION}" in workflow
    assert "backend-v${RELEASE_VERSION}" in workflow
    assert "frontend-v${RELEASE_VERSION}" in workflow


def test_ci_uses_resolvable_setup_uv_version_tag():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    match = re.search(r"uses:\s+astral-sh/setup-uv@(v[^\s]+)", workflow)

    assert match is not None
    assert re.fullmatch(r"v\d+\.\d+\.\d+", match.group(1))


def test_ci_uses_node24_ready_action_versions():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "uses: actions/checkout@v6" in workflow
    assert "uses: actions/setup-python@v6" in workflow
    assert "uses: actions/setup-node@v6" in workflow
    assert "uses: docker/setup-qemu-action@v4" in workflow
    assert "uses: docker/setup-buildx-action@v4" in workflow
    assert "uses: docker/login-action@v4" in workflow
    assert "uses: docker/build-push-action@v7" in workflow


def test_alembic_revision_ids_fit_version_column_limit():
    for migration_path in sorted((ROOT / "alembic" / "versions").glob("*.py")):
        module = ast.parse(migration_path.read_text(encoding="utf-8"))
        revision = None

        for node in module.body:
            if not isinstance(node, ast.AnnAssign):
                continue
            if not isinstance(node.target, ast.Name) or node.target.id != "revision":
                continue
            revision = ast.literal_eval(node.value)
            break

        assert revision is not None, f"{migration_path.name} 缺少 revision 定义"
        assert len(revision) <= 32, (
            f"{migration_path.name} 的 revision 过长({len(revision)}): {revision}"
        )
