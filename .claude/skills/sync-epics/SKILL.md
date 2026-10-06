---
name: sync-epics
description: Keep the GitHub Epics (#4–#15) in step with the repo — detect Epics that are stale because intent/intent.md or discovery records changed on main, detect Epics that someone edited directly on GitHub, propose updated Epic text for the user to approve, and turn GitHub-side edits into discovery questions instead of overwriting them. Use this whenever the user asks to sync, update, refresh or check Epics or issues after intent or discovery changes, asks whether an Epic is out of date or was edited on GitHub, after an `intent:` or `discovery:` PR is squash-merged, or wants to add the trace block to an Epic (backfill). Not for creating new Epics (they map 1:1 to intent §4 and already exist) or for running discovery itself.
---

# Sync Epics — keep GitHub Epics anchored to the repo

The repo is the source of truth for *what* the platform should do: `intent/intent.md`, the discovery
records and the decisions in them. A GitHub Epic is a **view** of that, plus the work tracking that
only GitHub has (status, sub-issues, board, comments). Information flows one way:

```
repo (intent, discovery) ──render──▶ Epic managed block
GitHub edit to an Epic   ──discovery question──▶ user decides ──▶ repo commit ──▶ re-render
```

A GitHub edit is never copied straight into the repo and never silently overwritten. It is input
to discovery, like anything else a stakeholder says.

Two rules from `CLAUDE.md` apply throughout:

- **The user decides; you ask.** Show proposed Epic text and get approval before every `gh issue edit`.
  Never add requirements to an Epic that the repo doesn't contain.
- **Derive only from the right status.** `emerging` sections may feed Epics; `settled` sections may
  feed everything below. A section moving *backward* (e.g. `settled -> emerging`) is something to
  flag: the Capabilities, Features and Stories under the Epic were derived from text that is no
  longer settled.

## Where things live

```
references/trace-format.md   body layout: managed block, trace block, hashing, drift rules (read it)
scripts/epic_trace.py        check / stamp / hash / sections; read-only towards GitHub
intent/README.md             status meanings and the intent: commit convention
discovery/questions.md       where GitHub-side edits become Q-### entries
```

Run the script from the repo root: `python3 .claude/skills/sync-epics/scripts/epic_trace.py ...`.
It runs `git fetch origin main` and compares against `origin/main`, so the result reflects what is
merged, not your working tree or branch.

## Workflow

### 1. Check

```bash
python3 .claude/skills/sync-epics/scripts/epic_trace.py check 4          # one Epic
python3 .claude/skills/sync-epics/scripts/epic_trace.py check $(seq 4 15) # all of them
```

Each report has a `state`:

| State | Meaning | Go to |
| --- | --- | --- |
| `clean` | Repo unchanged for this Epic, nobody edited it on GitHub. | Report and stop. |
| `stale` | Traced intent sections or discovery records changed on main. | §2 |
| `edited-on-github` | Managed block differs from the last sync. | §3 |
| `conflict` | Both. | §3 first, then §2 |
| `unanchored` | No trace block yet. | §4 (backfill) |
| `error` | `synced-at` is not on main (a branch SHA was cited). | Ask the user which main SHA to use. |

Summarize the results for the user in a short table before doing anything else. With many Epics,
lead with the ones that need action.

### 2. Stale: propose the update

From the report, read `repo.sections[].diff`, `repo.intent_commits` (their `Trigger:` lines say
*why* the text changed) and `repo.discovery_changes`. Read the changed discovery files themselves.

Then:

1. Draft the new managed block. Change only what the repo change requires; keep the rest of the
   wording. Keep it at Epic level: the conclusion and a pointer to the session (`D#`/`G#` ids), not
   the detail.
2. Update the `Traces to:` line: status and last-changed commit per section
   (`repo.sections[].last_changed_on_main`), and any new session links.
3. Flag status moves. Forward to `settled` → mention that Capabilities and below can now be derived.
   Backward → list the open child issues that may need review (`gh issue view N --json subIssues`
   is not always available; `gh api repos/{owner}/{repo}/issues/N/sub_issues` is).
4. If `repo.other_sections_changed` lists a section the Epic doesn't trace but plausibly should,
   ask whether to add it to `sections`; don't add it yourself.
5. Show the user a diff of old vs new managed block and wait for approval.
6. Apply (see §5).

### 3. Edited on GitHub: don't overwrite

Show the user `github.diff` (last sync → GitHub now) and who edited when (`github.edits`). Then
ask which of these it is, using AskUserQuestion:

- **New or changed requirement.** Record it in `discovery/questions.md` as a new `Q-###`
  (next free id; ids are never reused) with the Epic number, the edited text, why it matters, and
  "Raised by: edit to Epic #N on GitHub, <date>". The repo is now the place to settle it, via the
  `discovery` skill and an `intent:` commit whose `Trigger:` cites the issue. Until then, ask
  whether to keep the GitHub text in place (restamp, so it's not flagged again) or revert it.
- **Cosmetic** (typo, formatting, link fix). Keep it: restamp the current body as is.
- **Wrong / accidental.** Re-render the block from the repo, approved as in §2.

For a `conflict`, settle the GitHub edit first, then do §2 on top of the result.

### 4. Backfill: anchor an existing Epic

Epics created before this convention have no markers. To anchor one:

1. Read its body and its `Traces to:` line (`traces_to_line` in the report).
2. Propose the trace fields: `sections` from the sections it cites, plus §4 (every Epic maps to a
   §4 scope area); `sessions` from the session files it links; `synced-at` = current `origin/main`
   short SHA, but only if the body actually reflects main. If it doesn't, run §2 first.
3. Wrap the template sections (Summary, Desired Outcomes, Capabilities in scope) in the managed
   markers. Anything else stays outside, as free text.
4. Show the user the result and apply on approval (§5). Backfill changes no wording.

Epics #5–#15 cite no sections or sessions yet; for them the trace is `sections: 4`, `sessions:`
(empty), and they turn stale whenever §4 changes.

### 5. Apply

```bash
gh issue view N --json body -q .body > "$SCRATCH/epic-N.md"   # $SCRATCH = session scratchpad
# edit the managed block (or wrap it, for a backfill)
python3 .claude/skills/sync-epics/scripts/epic_trace.py stamp "$SCRATCH/epic-N.md" \
  --synced-at <main sha> [--sections 3,4,5] [--sessions slug-a,slug-b]
gh issue edit N --body-file "$SCRATCH/epic-N.md"
python3 .claude/skills/sync-epics/scripts/epic_trace.py check N   # expect: clean
```

`stamp` refuses a SHA that isn't on main and recomputes the hash, so always stamp **after** the
last edit to the block. Never edit the trace block by hand.

If the sync added a `Q-###`, that is a repo change: offer to commit it as `discovery: ...` on a
branch and open a PR. Commit only when the user says so, without a `Co-Authored-By: Claude` trailer.

## Scope

Epics only for now. Capabilities, Features and Stories can use the same body format later; the
script is not Epic-specific apart from the `[Epic] ` title prefix it strips when looking for mentions.
