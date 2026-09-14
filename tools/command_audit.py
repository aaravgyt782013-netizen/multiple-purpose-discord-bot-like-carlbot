"""Repo-wide static command/alias collision audit."""
import ast
import pathlib
import sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
MAIN=ROOT/"main.py"

def loaded_cogs():
    tree=ast.parse(MAIN.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name) and target.id=="COGS":
                    return [x.value for x in node.value.elts if isinstance(x,ast.Constant)]
    raise RuntimeError("Could not find COGS in main.py")

def literal(node,default=None):
    try:return ast.literal_eval(node)
    except Exception:return default

def decorator_info(node):
    if not isinstance(node,ast.Call):return None
    func=node.func;attr=func.attr if isinstance(func,ast.Attribute) else ""
    if attr not in {"hybrid_command","hybrid_group","command","group"}:return None
    kw={k.arg:literal(k.value) for k in node.keywords if k.arg};parent=None
    if isinstance(func,ast.Attribute) and isinstance(func.value,ast.Name) and attr in {"command","group"}:parent=func.value.id
    return kw.get("name"),kw.get("aliases") or [],parent

def scan(path):
    tree=ast.parse(path.read_text(encoding="utf-8"),filename=str(path));found=[]
    for node in ast.walk(tree):
        if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
        for deco in node.decorator_list:
            info=decorator_info(deco)
            if not info:continue
            name,aliases,parent=info;name=name or node.name;qualified=f"{parent} {name}" if parent else name
            found.append((qualified.lower(),path.name,node.name,False))
            for alias in aliases:found.append((str(alias).lower(),path.name,node.name,True))
    return found

def main():
    collisions={};loaded=set(loaded_cogs());files=sorted((ROOT/"cogs").glob("*.py"))
    for path in files:
        for name,file,func,is_alias in scan(path):collisions.setdefault(name,[]).append((file,func,is_alias))
    missing=[c for c in sorted(loaded) if not (ROOT/"cogs"/f"{c}.py").exists()]
    if missing:print("Loaded cog files missing: "+", ".join(missing),file=sys.stderr);return 1
    duplicates={n:o for n,o in collisions.items() if len(o)>1}
    if duplicates:
        print("Command name/alias collisions detected across every cog file:",file=sys.stderr)
        for name,owners in sorted(duplicates.items()):print(f"- {name}: "+", ".join(f"{f}:{fn}{' [alias]' if a else ''}" for f,fn,a in owners),file=sys.stderr)
        return 1
    print(f"Repo-wide command audit passed: {len(files)} cog files scanned, {len(collisions)} command/alias registrations, 0 collisions.")
    return 0

if __name__=="__main__":raise SystemExit(main())
