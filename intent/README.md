# Intent — How This Evolves

`intent.md` is the traceability root of this project. Every Epic, and therefore
every Capability, Feature, User Story and Task beneath it, should be answerable
back to a statement of intent. That only works if the intent's own history is
legible.

## Section status

Each section of `intent.md` carries one marker:

| Status | Meaning | Safe to derive issues from? |
| --- | --- | --- |
| `exploratory` | Open question, placeholder, or working hypothesis. | No |
| `emerging` | Direction agreed, details still moving. | Epics only |
| `settled` | Stable. Changes here are significant and need a reason. | Yes |

Status moves forward as discovery resolves questions, and may move *backward*
when a discovery finding invalidates something previously thought settled. Both
directions are recorded the same way.

## Commit convention

One commit per intent refinement — never bundled with unrelated work, so that
`git log -- intent/` reads as the project's decision history.

```
intent: <what changed, imperative>

Trigger: <what prompted this — discovery session, ADR, decision, issue #N>
Sections: <section> (<old status> -> <new status>)
Rationale: <why this, and not the alternative that was on the table>
```

`Trigger` is the important line. Months later the question is rarely *what*
changed — `git diff` answers that — but *what forced the change*.

## Deriving issues

When a section reaches `settled`, the Epics derived from it should reference the
intent commit that settled them. This closes the loop: issue -> intent revision
-> the discovery that produced it.
