---
name: discovery
description: Run a requirement-elicitation / discovery session for the Hospital Management System — interview the user to clarify an area of the project intent, surface gaps, ambiguities and conflicts, record what was decided and what is still open, and propose status-tracked refinements to intent/intent.md. Use this whenever the user wants to do discovery, elicit or clarify requirements, explore a domain area (e.g. patient registration, billing, pharmacy, government integration), work through open questions, "figure out what we need", firm up a section of the intent, or asks what's still unclear about the project — even if they don't say "discovery" explicitly. Not for writing GitHub issues from already-settled intent or for architecture/design work.
---

# Discovery — requirement elicitation

This project is an AI-DLC practice environment: eliciting and clarifying requirements *is* one of the
exercises. The point of a session is not to produce a finished spec fast; it is to ask good questions,
make the reasoning visible, and leave a trail that later work (Epics → Capabilities → Features → Stories)
can trace back to.

Two things follow from that and shape everything below:

- **The user decides; you ask.** You bring healthcare and software domain knowledge, but anything you
  contribute is a *suggestion* until the user confirms it. Never write your own idea into the record as
  a decision. A hospital system invented by the model and rubber-stamped is exactly the failure this
  exercise is meant to catch.
- **"Not yet known" is a valid outcome.** `intent/intent.md` is deliberately high level and evolves.
  Don't push to settle things the user isn't ready to settle — record them as open questions and move on.

## Where things live

```
intent/intent.md              traceability root; sections carry exploratory | emerging | settled
intent/README.md              status meanings + the `intent:` commit convention (read it)
discovery/sessions/           one record per session: YYYY-MM-DD-<topic-slug>.md
discovery/questions.md        running register of open questions across sessions (Q-### ids)
discovery/glossary.md         domain terms the user has defined
```

Create `discovery/` files lazily, the first time they're needed. Use `templates/session.md` for session
records and `templates/questions.md` for the register's header.

## Workflow

### 1. Orient

Read `intent/intent.md`, `intent/README.md`, `discovery/questions.md` and the most recent few session
records if they exist. You want to know which sections are exploratory/emerging, which questions are
already open, and what past sessions concluded, so you don't re-ask settled things.

### 2. Frame the session

Agree on scope with the user in one short exchange:

- **Topic** — an intent section, a domain area, or a specific open question (`Q-###`).
- **Which intent section it serves** — every session should be traceable to one. If the topic doesn't fit
  any existing section, that itself is a finding (the intent may need a new `exploratory` section).
- **Depth** — a quick pass to map the territory, or a deep dive into one area.

If the user just says "let's do discovery" with no topic, propose 2–3 candidates drawn from the
least-settled parts of the intent and the oldest open questions, and let them pick.

### 3. Elicit in rounds

Ask a small batch per round — 2 to 4 questions — then listen, reflect back, and go again. Long
questionnaires get shallow answers.

For each question:

- **Say why it matters** in one line — what it unblocks or what goes wrong if it's left vague.
  This is how the user learns to see gaps themselves.
- **Choose the form deliberately.** When the answer space is genuinely enumerable (e.g. "which
  jurisdiction's regulations apply?"), use AskUserQuestion with concrete options. When it's open
  (e.g. "walk me through what happens when a patient arrives at the ED"), ask in prose. Options you
  offer are illustrative — don't lead the user toward the answer you'd have picked.
- **Prefer concrete scenarios over abstractions.** "A patient is transferred from ward A to ward B at
  2am — who needs to know, and how?" surfaces more than "what are the notification requirements?"

Use the lenses in `references/lenses.md` to decide *what* to ask: stakeholder perspectives, the
lifecycle of the core entities, non-functional concerns, and the gap-detection checklist. Don't march
through every lens — pick the ones that bite for this topic.

After each round, **reflect back** what you heard as short statements and ask the user to correct
anything wrong. Misunderstandings caught here are cheap.

### 4. Probe for gaps as you go

While listening, watch for (details in `references/lenses.md`):

- vague qualifiers ("fast", "secure", "easy", "real-time") → ask what measurable thing is meant
- undefined domain terms → ask for a definition; add to the glossary once given
- missing actors, missing unhappy paths, missing "who owns this data"
- conflicts with the intent or earlier sessions → name the conflict explicitly and ask which wins
- implicit assumptions (yours or theirs) → surface them as questions

Label clearly when you're offering domain knowledge: "In many hospitals X works like Y — is that
true here, or do you want something different?" The user's answer, not your framing, is what gets recorded.

### 5. Close the session

When the user wants to stop, or the topic is exhausted for now:

1. **Summarize** in chat: decisions made, assumptions accepted, questions still open, candidate
   requirements that emerged.
2. **Write the session record** to `discovery/sessions/YYYY-MM-DD-<topic-slug>.md` from the template.
   Keep the user's words where precision matters. Keep your suggestions that were *not* confirmed out of
   the Decisions section.
3. **Update `discovery/questions.md`** — add new open questions with the next `Q-###` id; mark
   answered ones `answered` with a link to this session; mark ones the user parked as `deferred`.
4. **Update `discovery/glossary.md`** if terms were defined.
5. **Propose intent changes, don't just make them.** Show the specific edits to `intent/intent.md` —
   new or reworded text, and any status transition (e.g. `exploratory -> emerging`) — with the reason
   for each. Status can move backward too if a finding undermines something marked settled. Only apply
   the edits the user approves. Keep intent text high level: the detail lives in the session record,
   the intent carries the conclusion.
6. **Offer to commit**, following the convention in `intent/README.md`: the discovery record in its own
   commit first, then one `intent:` commit whose `Trigger:` line points at the session file. Only commit
   when the user says so.

If a section reaches `settled`, mention that Epics can now be derived from it (see `intent/README.md`),
but don't create issues as part of discovery — that's a separate step.

## What good looks like

- Every recorded decision is something the user actually said or confirmed.
- Every open question says why it matters and what it blocks.
- The intent change (if any) is small, high level, and traceable to the session record.
- The user came away having thought about something they hadn't before.
