# Epic body format

An Epic body has three parts, in this order.

```markdown
<!-- managed:start -->
### Summary
...
Traces to: intent §4 (`emerging`, commit cea3c88), intent §5 (`settled`, commit f6a7222) · [session](../blob/main/discovery/sessions/...) (D5, D12)

### Desired Outcomes / Success Metrics
...

### Capabilities in scope
- **Patient Registration & Identity** — #20. ...
<!-- managed:end -->

### Notes
Free text. People may edit this on GitHub; the skill never rewrites it.

<!-- trace (sync-epics skill; do not edit by hand)
sections: 3, 4, 5
sessions: 2026-10-02-platform-scope-and-first-slice, 2026-10-06-groom-patient-administration
synced-at: cea3c88
managed-sha256: 9c1e…
-->
```

## Managed block

Everything between `<!-- managed:start -->` and `<!-- managed:end -->` is rendered from the repo
by the agent. It keeps the headings of `.github/ISSUE_TEMPLATE/01-epic.yml` (Summary, Desired
Outcomes / Success Metrics, Capabilities in scope), so issues created from the form and issues
maintained by the skill look the same.

The human-readable `Traces to:` line stays inside the block. For each section it cites the status
and the commit on `main` that **last changed** that section (`epic_trace.py sections` lists them),
which for a `settled` section is the commit that settled it, as `intent/README.md` asks.

## Trace block

Hidden HTML comment at the end of the body. GitHub doesn't render it.

| Field | Meaning |
| --- | --- |
| `sections` | Numbers of the `intent/intent.md` sections the Epic is derived from. |
| `sessions` | Slugs (file names without `.md`) of the discovery sessions the Epic cites. |
| `synced-at` | Short SHA on `main` the managed block was last rendered from. Never a branch SHA. |
| `managed-sha256` | SHA-256 of the managed block at that sync, after normalization. |

Normalization before hashing: `\r\n` → `\n`, trailing whitespace stripped from each line, leading
and trailing blank lines dropped. GitHub's web editor changes line endings, and that alone must not
count as an edit.

## How drift is detected

- **Repo moved (stale):** a traced section's text at `synced-at` differs from `origin/main`, or a
  traced session file changed, or a discovery file changed since `synced-at` and the added lines
  mention the Epic (`#4` or its title).
- **GitHub edited:** the hash of the current managed block differs from `managed-sha256`. The
  editor's login doesn't help here: the agent edits through the user's own `gh` account, so the
  hash is what tells a sync from a human edit. To show *what* changed, the script looks through
  the issue's edit history (GraphQL `userContentEdits`, each entry a full body snapshot) for the
  version whose managed block matches `managed-sha256`, and diffs it against the current block.
- **Conflict:** both at once.
