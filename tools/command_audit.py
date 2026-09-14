"""Static command collision audit for every loaded LightCore cog."""
import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
MAIN = ROOT / "main.py"


def loaded_cogs():
    tree = ast.parse(MAIN.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "COGS":
                    return [x.value for x in node.value.elts if isinstance(x, ast.Constant)]
    raise RuntimeError("Could not find COGS in main.py")


def literal(node, default=None):
    try:
        return ast.literal_eval(node)
    except Exception:
        return default


def decorator_command_info(node):
    """Return (qualified_name, aliases) for a command decorator."""
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    attr = func.attr if isinstance(func, ast.Attribute) else ""
    if attr in {"hybrid_command", "hybrid_group", "command", "group"}:
        parent = None
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            parent = func.value.id if attr in {"command", "group"} else None
        kw = {k.arg: literal(k.value) for k in node.keywords if k.arg}
        name = kw.get("name")
        aliases = kw.get("aliases") or []
        return name, aliases, parent
    return None


def scan_file(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for deco in node.decorator_list:
            info = decorator_command_info(deco)
            if not info:
                continue
            name, aliases, parent = info
            name = name or node.name
            qualified = f"{parent} {name}" if parent else name
            found.append((qualified.lower(), path.name, node.name, False))
            for alias in aliases:
                found.append((str(alias).lower(), path.name, node.name, True))
    return found


def main():
    collisions = {}
    total = 0
    for cog in loaded_cogs():
        path = ROOT / "cogs" / f"{cog}.py"
        if not path.exists():
            raise RuntimeError(f"Loaded cog file is missing: {path}")
        for name, filename, function, is_alias in scan_file(path):
            total += 1
            collisions.setdefault(name, []).append((filename, function, is_alias))
    duplicates = {name: owners for name, owners in collisions.items() if len(owners) > 1}
    if duplicates:
        lines = ["Command name/alias collisions detected:"]
        for name, owners in sorted(duplicates.items()):
            lines.append(f"- {name}: " + ", ".join(f"{f}:{fn}{' [alias]' if a else ''}" for f, fn, a in owners))
        print("\n".join(lines), file=sys.stderr)
        return 1
    print(f"Command audit passed: {len(loaded_cogs())} loaded cogs, {total} command/alias registrations, 0 collisions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
