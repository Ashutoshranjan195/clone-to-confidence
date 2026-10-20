from pathlib import Path
def proposals(root):
 out=[]
 if not (root/".env.example").exists():out.append(("create",".env.example","# Copy to .env and fill in locally\n# APP_SETTING=YOUR_VALUE_HERE\n"))
 if not (root/".python-version").exists() and (root/"pyproject.toml").exists():out.append(("create",".python-version","3.12\n"))
 return out
def apply(root,dry_run=True):
 changes=proposals(root)
 if not dry_run:
  for action,rel,content in changes:
   p=root/rel
   if action=="create" and not p.exists():p.write_text(content)
 return changes
