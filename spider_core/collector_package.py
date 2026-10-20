"""Explicit, portable source-file manifests for multi-file collectors."""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re


def package_hashes(collector: Path, *, metadata: dict | None = None,
                   require_declared_imports: bool = False) -> dict[str, str] | None:
    folder = collector.parent.resolve()
    if metadata is None:
        path = folder / "capability.json"
        metadata = json.loads(path.read_text("utf-8")) if path.is_file() else {}
    if not isinstance(metadata, dict):
        raise ValueError("capability metadata must be a JSON object")
    declared = metadata.get("files")
    if "files" in metadata and (not isinstance(declared, list) or
            any(not isinstance(name, str) for name in declared)):
        raise ValueError("capability.files must be a list of relative file names")
    names = [collector.name, *(declared or [])]
    if len({name.casefold() for name in names}) != len(names):
        raise ValueError("capability.files contains duplicate files or the implicit entrypoint")
    hashes = {}
    for name in names:
        relative = PurePosixPath(name)
        if (relative.is_absolute() or ".." in relative.parts or not relative.parts
                or ":" in name or "\\" in name or name != relative.as_posix()
                or any(part.startswith('.') or part.casefold() in {"runs", "outputs", "tmp", "node_modules", "__pycache__", "local_credentials"}
                       for part in relative.parts)
                or relative.name.casefold() in {"capability.json", "proof.json", "task.example.json"}
                or relative.name.casefold().startswith(('cookies', 'credentials'))
                or relative.suffix.lower() not in {".py", ".js", ".mjs", ".cjs", ".json", ".txt", ".toml"}):
            raise ValueError("unsafe capability.files path")
        path = folder / name
        if (not path.is_file() or not path.resolve().is_relative_to(folder)
                or os.path.normcase(os.path.realpath(path)) != os.path.normcase(str(path.absolute()))):
            raise ValueError("capability.files must name existing unlinked source files")
        content = path.read_bytes()
        if re.search(rb'gh[pousr]_[A-Za-z0-9]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', content):
            raise ValueError("capability.files contains a credential-like value")
        if path.suffix.lower() == ".json":
            value = json.loads(content)
            def sensitive(item):
                if isinstance(item, dict):
                    return any(re.search(r'cookie|token|authorization|password|secret|api.?key|credential', str(k), re.I)
                               or sensitive(v) for k, v in item.items())
                return isinstance(item, list) and any(sensitive(v) for v in item)
            if sensitive(value):
                raise ValueError("capability.files JSON contains secret-like keys")
        hashes[name] = hashlib.sha256(content).hexdigest()
    if require_declared_imports or declared is not None:
        def require_source(path: Path) -> None:
            if path.is_file() and path.relative_to(folder).as_posix() not in hashes:
                raise ValueError(
                    f"declare local helper {path.relative_to(folder).as_posix()} in "
                    "capability.files and rerun the collector before registration")

        def local_module(base: Path, parts: list[str]) -> Path | None:
            # Inspect only literal local Python imports; never add files implicitly.
            if not base.is_relative_to(folder):
                return None
            for parent in (base, *base.parents):
                if parent == folder:
                    break
                require_source(parent / '__init__.py')
            for index, part in enumerate(parts):
                candidate = base / part
                initializer = candidate / '__init__.py'
                module = base / (part + '.py')
                if initializer.is_file():
                    require_source(initializer)
                elif module.is_file():
                    require_source(module)
                    return module if index == len(parts) - 1 else None
                elif not candidate.is_dir():
                    return None
                base = candidate
            return base

        for name in names:
            path = folder / name
            if path.suffix != ".py":
                continue
            for node in ast.walk(ast.parse(path.read_text("utf-8-sig"))):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        local_module(folder, alias.name.split('.'))
                elif isinstance(node, ast.ImportFrom):
                    base = path.parent if node.level else folder
                    for _ in range(max(0, node.level - 1)):
                        base = base.parent
                    imported = local_module(base, node.module.split('.') if node.module else [])
                    # 'from module import attribute' does not import a sibling file.
                    if imported is not None and imported.is_dir():
                        for alias in node.names:
                            if alias.name != '*':
                                local_module(imported, [alias.name])
    return dict(sorted(hashes.items())) if declared is not None else None
