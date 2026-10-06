#!/usr/bin/env python3
"""Drift checks for Epics traced to intent/intent.md.

Read-only towards GitHub: this script never edits an issue. The agent edits
issues with `gh issue edit` after the user approves the new text.

  check <issue> [<issue> ...]   report repo-side and GitHub-side drift as JSON
  stamp <body-file> --synced-at <sha> [--sections 3,4,5] [--sessions a,b]
                                rewrite the trace block in a body file in place
  hash <body-file>              print the managed-block hash of a body file
  sections [--at <ref>]         list intent sections with status and the
                                commit on main that last changed each one

Body format (see references/trace-format.md):

  <!-- managed:start -->
  ...text the agent renders from the repo...
  <!-- managed:end -->

  ...free text people may edit on GitHub...

  <!-- trace (sync-epics skill; do not edit by hand)
  sections: 3, 4, 5
  sessions: 2026-10-02-platform-scope-and-first-slice
  synced-at: cea3c88
  managed-sha256: <hex>
  -->
"""

import argparse
import difflib
import hashlib
import json
import re
import subprocess
import sys

INTENT = "intent/intent.md"
MAIN = "origin/main"

MANAGED_RE = re.compile(r"<!-- managed:start -->\n?(.*?)<!-- managed:end -->", re.S)
TRACE_RE = re.compile(r"<!-- trace\b[^\n]*\n(.*?)-->", re.S)
SECTION_RE = re.compile(r"^## (\d+)\. (.+)$", re.M)
STATUS_RE = re.compile(r"_Status: (\w+)_")


def run(*args, check=True):
    p = subprocess.run(args, capture_output=True, text=True)
    if check and p.returncode != 0:
        sys.exit(f"{' '.join(args)} failed: {p.stderr.strip()}")
    return p.stdout


def on_main(sha):
    return subprocess.run(["git", "merge-base", "--is-ancestor", sha, MAIN], capture_output=True).returncode == 0


def normalize(text):
    # GitHub's web editor saves \r\n and may add trailing whitespace; neither is a content change.
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    return "\n".join(lines).strip("\n")


def managed_block(body):
    m = MANAGED_RE.search(body or "")
    return m.group(1) if m else None


def managed_hash(body):
    block = managed_block(body)
    return None if block is None else hashlib.sha256(normalize(block).encode()).hexdigest()


def parse_trace(body):
    m = TRACE_RE.search(body or "")
    if not m:
        return None
    fields = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    split = lambda v: [x.strip() for x in v.split(",") if x.strip()]
    return {
        "sections": split(fields.get("sections", "")),
        "sessions": split(fields.get("sessions", "")),
        "synced_at": fields.get("synced-at"),
        "managed_sha256": fields.get("managed-sha256"),
    }


def render_trace(trace):
    return (
        "<!-- trace (sync-epics skill; do not edit by hand)\n"
        f"sections: {', '.join(trace['sections'])}\n"
        f"sessions: {', '.join(trace['sessions'])}\n"
        f"synced-at: {trace['synced_at']}\n"
        f"managed-sha256: {trace['managed_sha256']}\n"
        "-->"
    )


# --- intent sections -------------------------------------------------------

def intent_at(ref):
    return run("git", "show", f"{ref}:{INTENT}", check=False)


def split_sections(text):
    out = {}
    matches = list(SECTION_RE.finditer(text))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        raw = text[m.start():end]
        status = STATUS_RE.search(raw)
        body = normalize(re.sub(r"\n---\s*$", "", raw.rstrip()))
        out[m.group(1)] = {"title": m.group(2).strip(), "status": status.group(1) if status else None, "text": body}
    return out


def last_changed(number, ref=MAIN):
    """Newest commit reachable from ref whose version of section `number` differs from its parent's."""
    commits = run("git", "log", "--format=%h", ref, "--", INTENT).split()
    for sha in commits:
        here = split_sections(intent_at(sha)).get(number)
        before = split_sections(intent_at(f"{sha}^")).get(number)
        if here and (before is None or here["text"] != before["text"]):
            return sha
    return None


def intent_commits(since, ref=MAIN):
    log = run("git", "log", "--format=%h%x1f%s%x1f%b%x1e", f"{since}..{ref}", "--", "intent/")
    out = []
    for entry in filter(None, (e.strip() for e in log.split("\x1e"))):
        sha, subject, body = (entry.split("\x1f") + ["", ""])[:3]
        pick = lambda key: next((l.split(":", 1)[1].strip() for l in body.splitlines() if l.startswith(key + ":")), None)
        out.append({"sha": sha, "subject": subject, "trigger": pick("Trigger"), "sections": pick("Sections")})
    return out


# --- repo-side drift -------------------------------------------------------

def repo_drift(number, title, trace):
    since = trace["synced_at"]
    if not on_main(since):
        return {"error": f"synced-at {since} is not on {MAIN}; Epics must cite the squash SHA on main"}

    then, now = split_sections(intent_at(since)), split_sections(intent_at(MAIN))
    sections = []
    for n in trace["sections"]:
        a, b = then.get(n), now.get(n)
        entry = {
            "section": n,
            "title": (b or a or {}).get("title"),
            "status_then": a and a["status"],
            "status_now": b and b["status"],
            "changed": a is None or b is None or a["text"] != b["text"],
            "last_changed_on_main": last_changed(n),
        }
        if entry["changed"] and a and b:
            entry["diff"] = "".join(difflib.unified_diff(
                a["text"].splitlines(True), b["text"].splitlines(True), f"§{n}@{since}", f"§{n}@main"))
        if a and b and a["status"] != b["status"]:
            order = ["exploratory", "emerging", "settled"]
            if a["status"] in order and b["status"] in order:
                entry["status_move"] = "forward" if order.index(b["status"]) > order.index(a["status"]) else "backward"
        sections.append(entry)

    untraced = [n for n, s in now.items() if n not in trace["sections"] and (then.get(n) or {}).get("text") != s["text"]]

    mention = re.compile(rf"#{number}\b|{re.escape(title.removeprefix('[Epic] ').strip())}", re.I)
    discovery = []
    for line in run("git", "diff", "--name-status", f"{since}..{MAIN}", "--", "discovery/").splitlines():
        status, path = line.split("\t", 1)
        slug = path.rsplit("/", 1)[-1].removesuffix(".md")
        added = [l[1:] for l in run("git", "diff", f"{since}..{MAIN}", "--", path).splitlines()
                 if l.startswith("+") and not l.startswith("+++")]
        discovery.append({
            "path": path,
            "change": {"A": "added", "M": "modified", "D": "deleted"}.get(status[0], status),
            "traced": slug in trace["sessions"],
            "mentions_epic": any(mention.search(l) for l in added),
        })

    return {
        "synced_at": since,
        "main": run("git", "rev-parse", "--short", MAIN).strip(),
        "sections": sections,
        "other_sections_changed": untraced,
        "intent_commits": intent_commits(since),
        "discovery_changes": discovery,
        "stale": any(s["changed"] for s in sections)
                 or any(d["traced"] or d["mentions_epic"] for d in discovery),
    }


# --- GitHub-side drift -----------------------------------------------------

def edit_history(owner, name, number):
    query = """query($o:String!,$n:String!,$i:Int!){ repository(owner:$o,name:$n){ issue(number:$i){
      userContentEdits(first:100){ nodes { editedAt editor { login } diff } } } } }"""
    data = json.loads(run("gh", "api", "graphql", "-f", f"query={query}", "-f", f"o={owner}", "-f", f"n={name}",
                          "-F", f"i={number}"))
    nodes = data["data"]["repository"]["issue"]["userContentEdits"]["nodes"]
    return sorted(nodes, key=lambda n: n["editedAt"])


def github_drift(repo, number, body, trace):
    current = managed_hash(body)
    if current is None:
        return {"state": "no-managed-block"}
    if current == trace["managed_sha256"]:
        return {"state": "clean"}

    owner, name = repo.split("/")
    history = edit_history(owner, name, number)
    synced = next((n for n in reversed(history) if managed_hash(n["diff"]) == trace["managed_sha256"]), None)
    result = {"state": "edited-on-github", "edits": [
        {"edited_at": n["editedAt"], "editor": (n["editor"] or {}).get("login")} for n in history[-5:]]}
    if synced:
        result["last_synced_version_at"] = synced["editedAt"]
        result["diff"] = "".join(difflib.unified_diff(
            normalize(managed_block(synced["diff"])).splitlines(True),
            normalize(managed_block(body)).splitlines(True), "last sync", "github now"))
    else:
        result["note"] = "no version in the edit history matches the stamped hash; show the current block to the user"
    return result


# --- commands --------------------------------------------------------------

def cmd_check(args):
    run("git", "fetch", "--quiet", "origin", "main")
    repo = args.repo or run("gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner").strip()
    reports = []
    for number in args.issues:
        issue = json.loads(run("gh", "issue", "view", str(number), "--repo", repo,
                               "--json", "number,title,url,body,labels"))
        report = {"issue": issue["number"], "title": issue["title"], "url": issue["url"],
                  "labels": [l["name"] for l in issue["labels"]]}
        trace = parse_trace(issue["body"])
        if trace is None or not trace["synced_at"]:
            report["state"] = "unanchored"
            report["traces_to_line"] = next((l for l in issue["body"].splitlines() if "Traces to" in l), None)
        else:
            report["trace"] = trace
            report["repo"] = repo_drift(issue["number"], issue["title"], trace)
            report["github"] = github_drift(repo, issue["number"], issue["body"], trace)
            edited = report["github"]["state"] == "edited-on-github"
            stale = report["repo"].get("stale")
            if report["repo"].get("error"):
                report["state"] = "error"
            elif edited and stale:
                report["state"] = "conflict"
            elif edited:
                report["state"] = "edited-on-github"
            elif stale:
                report["state"] = "stale"
            else:
                report["state"] = report["github"]["state"]
        reports.append(report)
    json.dump(reports, sys.stdout, indent=2, ensure_ascii=False)
    print()


def cmd_stamp(args):
    with open(args.body_file, encoding="utf-8") as f:
        body = f.read()
    digest = managed_hash(body)
    if digest is None:
        sys.exit("body has no <!-- managed:start --> ... <!-- managed:end --> block")
    if not on_main(args.synced_at):
        sys.exit(f"{args.synced_at} is not on {MAIN}; stamp with the squash SHA on main")
    old = parse_trace(body) or {"sections": [], "sessions": []}
    trace = {
        "sections": args.sections.split(",") if args.sections else old["sections"],
        "sessions": args.sessions.split(",") if args.sessions else old["sessions"],
        "synced_at": run("git", "rev-parse", "--short", args.synced_at).strip(),
        "managed_sha256": digest,
    }
    trace["sections"] = [s.strip() for s in trace["sections"]]
    trace["sessions"] = [s.strip() for s in trace["sessions"]]
    block = render_trace(trace)
    body = TRACE_RE.sub(lambda _: block, body) if TRACE_RE.search(body) else body.rstrip() + "\n\n" + block + "\n"
    with open(args.body_file, "w", encoding="utf-8") as f:
        f.write(body)
    print(block)


def cmd_hash(args):
    with open(args.body_file, encoding="utf-8") as f:
        print(managed_hash(f.read()) or "no managed block")


def cmd_sections(args):
    for n, s in split_sections(intent_at(args.at)).items():
        print(f"§{n}\t{s['status']}\t{last_changed(n, args.at)}\t{s['title']}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("issues", nargs="+", type=int)
    c.add_argument("--repo")
    c.set_defaults(fn=cmd_check)
    s = sub.add_parser("stamp")
    s.add_argument("body_file")
    s.add_argument("--synced-at", required=True)
    s.add_argument("--sections")
    s.add_argument("--sessions")
    s.set_defaults(fn=cmd_stamp)
    h = sub.add_parser("hash")
    h.add_argument("body_file")
    h.set_defaults(fn=cmd_hash)
    x = sub.add_parser("sections")
    x.add_argument("--at", default=MAIN)
    x.set_defaults(fn=cmd_sections)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
