# Reconciling with the documentation

The walkthrough and the code tell you what works. The documents tell you what was meant and what
the customer was promised. The value of this step is the **difference** between the two: that
difference is the product's real backlog, and it exists nowhere else in one place.

Skipping this step leaves you with a described screen and an invisible backlog.

## Where to look

| Source | What it is good for | What it is not good for |
|--------|--------------------|------------------------|
| Knowledge base / spec space | Intent, business context, mockups, ideas that never got an issue | Current behaviour — specs are written before the build and never revised |
| Issue tracker | What was filed, what shipped, and **the comments**, where scope quietly changed after the description was written | The description field alone — it is the plan, not the outcome |
| User manuals | The customer's mental model and the words they use | Accuracy — manuals lag the product by months |
| Support archive | What people actually get stuck on, and how often | Anything about intent |

Search each source by the screen's canonical name, its URL segment, and the issue keys already
recorded in the map. Read the comments on every relevant issue: the most expensive divergences
between a map and a product start as a comment that changed the scope after the description was
frozen.

## Classifying every finding

| Finding | Where it goes |
|---------|---------------|
| Implementation differs from the issue it shipped under | Page file, section "Divergence from issue \<KEY\>": what the issue says, what the code does, which wins |
| Specified but not built | Map → **Gaps**, with source and issue key |
| Built differently than specified | Map → **Gaps**, phrased as the difference, not as a complaint |
| A manual states something untrue about the product | Not a gap — a defect. File an issue, link it from the map, and fix the manual |
| Built but documented nowhere | Add to the map; close the backlog item if one exists |
| Present in the UI, absent from the code you read | Stop. Stale checkout, different build, or a feature flag. Resolve before writing |

## Unfinished implementation

A stub, a mode with no form, a field with no control, a reference table with no fields — do not
file these as defects and do not design around "fixing" them before checking with the owner.
Half of them are deliberate; the other half are known. A confirmed "intended this way" belongs
in the page file, so the next person mapping the screen does not raise it again.

## Writing gaps that are worth reading

A gap entry is useful when it survives being read six months later by someone who was not there.
Include: what is missing or different, where the claim came from (document, issue key, manual
section), what the code actually does, and — where it exists — the issue tracking the fix.

Group gaps by source, not by severity: severity is re-litigated at planning time anyway, while
provenance is what makes an entry checkable.

## What the documents may never do

They may not establish that a feature works. Only the code, confirmed by the walkthrough, does
that. A document describing a behaviour absent from the code produces a gap entry, not a line in
the map's description of the screen. This is the rule that makes the map worth trusting after the
person who built it has moved on.
