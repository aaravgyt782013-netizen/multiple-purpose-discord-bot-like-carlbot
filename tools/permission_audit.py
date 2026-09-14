"""Static permission audit for the current LightCore command tree."""
import ast
from pathlib import Path

EXPECTED={
"ban":"Ban Members","kick":"Kick Members","mute":"Moderate Members","warn":"Moderate Members","purge":"Manage Messages","warnings":"Moderate Members",
"automod":"Manage Server","setlog":"Manage Server","logsetup":"Manage Server","logconfig":"Manage Server",
"levelconfig":"Manage Server","levelconfig rate":"Manage Server","levelconfig cooldown":"Manage Server","levelconfig message":"Manage Server","levelconfig reward":"Manage Server","levelconfig enable":"Manage Server",
"ticketsetup":"Manage Channels","ticketcategory":"Manage Channels","ticketcategory list":"Manage Channels","ticketcategory add":"Manage Channels","ticketcategory delete":"Manage Channels",
"selfrole":"Manage Roles","shopadd":"Manage Server","shopremove":"Manage Server","giveaway":"Manage Server","giveawaybonus":"Manage Server","giveawaypick":"Manage Server",
"customadd":"Manage Server","customremove":"Manage Server","embed":"Manage Messages","announce":"Manage Messages","panel":"Manage Server","setwelcome":"Manage Server","setgoodbye":"Manage Server",
"tempvoice":"Manage Channels","tempvoice setup":"Manage Channels","tempvoice_disable":"Manage Channels","adminpanel":"Manage Server","memberstats":"Manage Server","growth":"Manage Server","retention":"Manage Server",
"applicationcreate":"Manage Server","applicationpanel":"Manage Server","applicationreviewchannel":"Manage Server","applications":"Manage Server",
}
PERM={"ban_members":"Ban Members","kick_members":"Kick Members","moderate_members":"Moderate Members","manage_messages":"Manage Messages","manage_channels":"Manage Channels","manage_guild":"Manage Server","manage_roles":"Manage Roles","administrator":"Administrator","manage_webhooks":"Manage Webhooks"}

def literal(n):
    try:return ast.literal_eval(n)
    except Exception:return None

def scan(path):
    tree=ast.parse(path.read_text(encoding="utf-8")); groups={}; found={}
    for n in ast.walk(tree):
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
            for d in n.decorator_list:
                if isinstance(d,ast.Call) and isinstance(d.func,ast.Attribute) and d.func.attr in {"hybrid_group","group"}:
                    kw={k.arg:literal(k.value) for k in d.keywords}; groups[n.name]=kw.get("name") or n.name
    for n in ast.walk(tree):
        if not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)): continue
        name=None; parent=None; perms=[]
        for d in n.decorator_list:
            if not isinstance(d,ast.Call) or not isinstance(d.func,ast.Attribute): continue
            attr=d.func.attr; kw={k.arg:literal(k.value) for k in d.keywords}
            if attr in {"hybrid_command","command","hybrid_group","group"}:
                name=kw.get("name") or n.name
                if isinstance(d.func.value,ast.Name) and d.func.value.id in groups: parent=groups[d.func.value.id]
            if attr in {"has_permissions","has_guild_permissions"}:
                for k,v in kw.items():
                    if v is True: perms.append(PERM.get(k,k.replace("_"," ").title()))
        if name: found[f"{parent} {name}" if parent else name]=", ".join(perms) if perms else "None"
    return found

def main():
    found={}
    for p in sorted(Path("cogs").glob("*.py")): found.update(scan(p))
    errors=[]
    for k,v in EXPECTED.items():
        if found.get(k)!=v: errors.append(f"{k}: expected {v!r}, found {found.get(k)!r}")
    for k,v in found.items():
        if v!="None" and k not in EXPECTED: errors.append(f"{k}: unexpected permission check {v!r}")
    print(f"Permission audit: {len(found)} command definitions found.")
    if errors: raise SystemExit("Permission audit FAILED:\n"+"\n".join(errors))
    print(f"Permission audit passed: {len(EXPECTED)} protected command paths match.")
if __name__=="__main__": main()
