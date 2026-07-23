import ast
from pathlib import Path

import pytest


pytestmark = pytest.mark.architecture
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = PROJECT_ROOT / "src"

FORBIDDEN_IMPORTS = {
    "application": {"agent_app", "agent_runtime", "infrastructure", "integrations"},
    "core": {
        "agent_app",
        "agent_runtime",
        "analytics",
        "application",
        "infrastructure",
        "integrations",
    },
    "infrastructure": {"agent_app", "agent_runtime", "integrations"},
}


def _top_level_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    return imports


def test_layer_dependencies_point_inward() -> None:
    violations: list[str] = []

    for package, forbidden in FORBIDDEN_IMPORTS.items():
        for path in sorted((SOURCE_ROOT / package).rglob("*.py")):
            invalid = sorted(_top_level_imports(path) & forbidden)
            if invalid:
                relative = path.relative_to(PROJECT_ROOT)
                violations.append(f"{relative}: {', '.join(invalid)}")

    assert violations == [], "Forbidden layer imports:\n" + "\n".join(violations)


def test_database_repositories_do_not_commit_transactions() -> None:
    violations: list[str] = []
    repository_root = SOURCE_ROOT / "infrastructure" / "database" / "repositories"

    for path in sorted(repository_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "commit"
            ):
                violations.append(f"{path.relative_to(PROJECT_ROOT)}:{node.lineno}")

    assert violations == [], "Repository commit calls found:\n" + "\n".join(violations)
