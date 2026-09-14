import ast
from pathlib import Path

EXPECTED = {
    "ban": "Ban Members", "kick": "Kick Members", "mute": "Moderate Members", "warn": "Moderate Members", "purge": "Manage Messages", "warnings": "Moderate Members",
    "automod": "Manage Server", "setlog": "Manage Server", "logsetup": "Manage Server", "logconfig": "Manage Server",
    "levelconfig": "Manage Server", "levelconfig rate": "Manage Server", "levelconfig cooldown": "Manage Server", "levelconfig message": "Manage Server", "levelconfig reward": "Manage Server", "levelconfig enable": "Manage Server",
    "selfrole": "Manage Roles", "role add": "Manage Roles", "role remove": "Manage Roles", "autorole": "Manage Server",
    "shopadd": "Manage Server", "shopremove": "Manage Server",
    "giveaway": "Manage Server", "giveawaybonus": "Manage Server", "giveawaypick": "Manage Server",
    "customadd": "Manage Server", "customremove": "Manage Server", "embed": "Manage Messages", "announce": "Manage Messages",
    "panel": "Manage Server", "setwelcome": "Manage Server", "setgoodbye": "Manage Server",
    "tempvoice": "Manage Channels", "tempvoice setup": "Manage Channels", "tempvoice_disable": "Manage Channels",
    "adminpanel": "Manage Server", "memberstats": "Manage Server", "growth": "Manage Server", "retention": "Manage Server",
    "applicationcreate": "Manage Server", "applicationpanel": "Manage Server", "applicationreviewchannel": "Manage Server", "applications": "Manage Server",
    "ticket setup": "Manage Channels", "ticket panel": "Manage Channels", "ticket list": "Manage Channels", "ticket add": "Manage Channels", "ticket remove": "Manage Channels", "ticket rename": "Manage Channels",
}


def call_name(node):
    if isinstance(node, ast.Name): return node.id
    if isinstance(node, ast.Attribute): return node.attr
    return ""


def kw_string(call, key):
    for kw in call.keywords:
        if kw.arg == key and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str): return kw.value.value
    return None


def audit_file(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    group_names = {}
    nodes = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)): continue
        for dec in node.decorator_list:
            if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr in {"hybrid_group", "group"}:
                group_names[node.name] = kw_string(dec, "name") or node.name
                break
        nodes.append(node)

    found = {}
    for node in nodes:
        command_name = None; parent = None; permissions = []
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute): continue
            attr = dec.func.attr
            if attr in {"hybrid_command", "command", "hybrid_group", "group"}:
                explicit = kw_string(dec, "name")
                if attr in {"hybrid_group", "group"}: command_name = explicit or node.name
                elif isinstance(dec.func.value, ast.Name) and dec.func.value.id in group_names:
                    parent = group_names[dec.func.value.id]; command_name = explicit or node.name
                elif isinstance(dec.func.value, ast.Name) and dec.func.value.id == "commands": command_name = explicit or node.name
            if attr in {"has_permissions", "has_guild_permissions"}:
                for kw in dec.keywords:
                    if kw.arg and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        permissions.append({
                            "ban_members": "Ban Members", "kick_members": "Kick Members", "moderate_members": "Moderate Members",
                            "manage_messages": "Manage Messages", "manage_channels": "Manage Channels", "manage_guild": "Manage Server",
                            "manage_roles": "Manage Roles", "administrator": "Administrator", "manage_webhooks": "Manage Webhooks",
                        }.get(kw.arg, kw.arg.replace("_", " ").title()))
        if command_name:
            found[f"{parent} {command_name}" if parent else command_name] = ", ".join(permissions) if permissions else "None"
    return found


def main():
    found = {}
    for path in sorted(Path("cogs").glob("*.py")):
        if path.name != "__init__.py": found.update(audit_file(path))
    errors = []
    for command, expected in EXPECTED.items():
        actual = found.get(command)
        if actual != expected: errors.append(f"{command}: expected {expected!r}, found {actual!r}")
    for command, actual in found.items():
        if actual != "None" and command not in EXPECTED: errors.append(f"{command}: has permission check {actual!r} but is missing from EXPECTED")
    print(f"Permission audit: {len(found)} command definitions found.")
    for command in sorted(found): print(f"{command} -> {found[command]}")
    if errors: raise SystemExit("Permission audit FAILED:\n" + "\n".join(errors))
    print(f"Permission audit passed: {len(EXPECTED)} protected commands match their expected permission checks.")


if __name__ == "__main__": main()
