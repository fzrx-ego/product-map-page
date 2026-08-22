# Hidden logic: what to look for in the code, and how to write it down

The most valuable part of a product map is the part that is not on the screen. Open this file at Step 3 (read the code) and keep it open through Step 5 (write the page).

A map that lists fields and buttons repeats the screenshot. Two layers on top of the inventory make it worth reading:

1. **What it does for the person using the screen** — which of their jobs the field closes. Not "field `max_price`, number", but "the ceiling on a single purchase; set it below your most expensive item and the machine stops selling that item".
2. **What the system does** — when fields appear, what the input accepts, side effects, delays, refusals. This is the layer that generates support tickets.

## Field format: three columns

```markdown
| Field | Label | What it gives the user | Under the hood |
```

- **Label** — quoted verbatim from the template or the locale files. Never translated, never improved.
- **What it gives the user** — one or two sentences in the language of their work. Mine the product's own tooltips and inline notes for this: they were written by whoever owns the feature and often hold an explanation that exists nowhere else. Pull the whole tooltip section out of the locale file.
- **Under the hood** — from the checklist below. Leaving it empty is not allowed: if a field has no hidden mechanics, write "plain text input, no constraints".

## Checklist: what to look for

### Front end, forms

- **Conditional fields.** A field shows only for a certain value of another field. Always record what happens on the way back: does it reset or keep its value.
- **Cascades.** A field unlocks the next one only once filled. Check what clearing a middle link does to the rest of the chain.
- **Inverted values.** The field is named "disable" and labelled "enable". Look for `!value`, `invert*` option lists, and a second inversion on the server.
- **Two controls, one field.** Different labels writing into the same form control and overwriting each other.
- **Dead controls.** A dropdown or switch with no binding to the form. Looks functional, does nothing. Worst when someone later added a tooltip to it.
- **Fields with no control.** A value that travels from response back into request untouched: the mechanism exists on the server, the screen does not. These are candidates for the map's "Gaps" section, not defects.
- **Normalisation on load.** The value from the server is replaced by "the nearest allowed one", so the screen sometimes shows something other than what is stored.
- **Pseudo-modes and pseudo-values.** An option that does not exist on the server, assembled in the browser from another value plus a flag, and recognised back by a heuristic. Write down which behaviour this makes look like a bug while being intended.
- **Silent wipes on switching.** Changing a mode rebuilds the payload and drops whatever the new mode has no room for. Read the code that assembles the payload, not the visible form.
- **Hidden sub-forms that still submit.** Sub-forms hidden with `display` rather than unmounted end up in the request.
- **Mutated shared constants.** A component writing into an object declared as a module-level constant: state leaks between instances and between screens.
- **Input locales.** Numeric fields on the same screen can carry different locales — and therefore different decimal separators.
- **Client limits versus server limits.** Compare `maxlength`, `min`, decimal places against the validation in the request DTO. A mismatch is an error the user only meets after pressing Save, when it could have been shown while typing.
- **Money maths in the browser.** Multiplying by 100 (or similar) on the client rather than the server breaks on the first currency with a different number of decimals.
- **What a button does besides the obvious.** A link or a marketing banner may quietly fire a request that changes a setting. Read the click handler to the end.
- **Result messages.** Is success shown before the server answers. Are warnings rendered as success. Which status codes are handled, and which leave the screen blank with no explanation.

### Back end, writes

- **The chain of checks.** Where the framework composes handlers (decorators, middleware, pipelines), the order decides which error the user actually sees. Write it as a table: check → refusal text.
- **What the server really accepts.** The client often posts the whole form, disabled fields included. The map lists the fields of the request DTO, not the fields of the form.
- **Freshness rules and locks.** "Data must have been synchronised within N minutes", locks held for the duration of processing, their TTL, and who releases them. Such rules refuse writes while the interface looks perfectly healthy — the first cause of "the button does nothing" tickets.
- **Rate limits.** Per-user request counters and the status code on exceeding them.
- **Side effects of a write.** Changing one field may reset a status, raise a "re-send initial configuration" flag, or enqueue a job to an external system. Record which field changes make the external system aware, and which stay local.
- **Asynchrony and delays.** What goes to a queue, how long the handler takes, which sleeps are hardcoded, when data is re-read from the external system. If "saved" comes back before the change is applied, that is a fact for the support-facing section.
- **Actions the system takes by itself.** It may send a reboot or re-push settings on its own. Users read that as a malfunction unless it is documented.
- **Several settings encoded into one value.** Bit masks, packed packets, "decimals + 4" tricks. Write both directions of the conversion.
- **Grouped changes.** If editing one field ships the whole group to the external system, that explains "unexpected" consequences such as a reboot triggered by a harmless setting.
- **Units.** Where major becomes minor, where seconds become milliseconds, how many conversion points exist and whether they agree.
- **A missing permission check.** Compare the sibling operations of the same screen: if three of four check ownership and the fourth does not, that is a finding, not a convention.
- **Diffs.** If the server compares the payload against current state and does nothing when they match, say so plainly: "pressing Save with no edits does nothing".

### Synchronisation with an external system

- What gets overwritten on every pass versus only on record creation. A field that lives only in your database and is rewritten with a default is a ready-made defect.
- What gets deleted when the entity disappears on the other side.
- Which local statuses and flags are protected from being overwritten, and which are not.
- Identifier stability: if records are recreated, internal IDs change, so on a test environment the entity must be found by a business key, not by the ID from a previous run.

## The "what the customer cannot see" section is required

At the end of the page, a two-column table: **what the customer says** → **what is actually happening**. Fill it from the findings above, phrased as real complaints — "I saved it and the card still shows the old values", "the button does nothing", "the device rebooted on its own". This is the one part of the map that support reads every day.

## Telling a finding from a defect

- **Unfinished implementation** — a stub, a mode with no form, a field with no control — is not a defect until the owner says so. Record a confirmed "intended" in the page file so it stops resurfacing.
- **The decision may already exist** in the tracker: search not only for duplicates but for issues closed as "works as intended", and reference that decision instead of filing again.
- **A frame is evidence.** When a finding is visible in a storyboard frame (mismatched separators, the wrong value, a locked field), point at the frame and mark the block. A frame outweighs an argument from reading code.
- **A conclusion drawn from code without checking the running product** must be labelled as such. If checking it requires a write — sending a command, pressing Save — do not check it: describe the scenario for QA and hand it to the owner.
