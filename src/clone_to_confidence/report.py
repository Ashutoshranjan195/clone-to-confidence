import json
from .checks import PASS,FAIL,WARN
def summary(cs):return {s:sum(c.status==s for c in cs) for s in (PASS,FAIL,WARN,"SKIPPED","UNSUPPORTED")}
def report(cs,root,fmt="text"):
 if fmt=="json":return json.dumps({"repository":str(root),"checks":[c.to_dict() for c in cs],"summary":summary(cs)},indent=2)
 lines=["CLONE TO CONFIDENCE",f"Repository: {root.name}",""]+[f"{c.status:11} {c.name}" for c in cs]; s=summary(cs); lines += ["",f"Result: {s['PASS']} PASS | {s['FAIL']} FAIL | {s['WARN']} WARN"]
 bad=[c for c in cs if c.status in (FAIL,WARN)]
 if bad:
  lines += ["","Problems and next steps:"]
  for c in bad:lines.append(f"- {c.name}: {c.explanation} " + ("Evidence: "+", ".join(c.evidence)+". " if c.evidence else "") + c.remediation)
 return "\n".join(lines)
