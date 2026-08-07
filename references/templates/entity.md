# <Entity> — domain object

**Defined in:** `<path/to/model-or-schema>`
**Status:** code at commit `<hash>`, YYYY-MM-DD
**Appears on:** [pages/<Name>.md](../pages/<Name>.md), [pages/<Other>.md](../pages/<Other>.md)

---

## What it is

<One or two sentences in business language: what real-world thing this object stands for, and
who creates it.>

## Fields

| Field | Type | Required | Meaning | Shown as |
|-------|------|----------|---------|----------|

<"Shown as" carries the UI label, quoted exactly. Fields that exist in the model but appear in no
screen are worth their own line — they are usually either dead weight or an unfinished feature.>

## Enumerations

| Value | Meaning | Label |
|-------|---------|-------|

<Status and type enums, straight from the code. Never paraphrase an enum value.>

## Lifecycle

<Which states the object moves through, what triggers each transition, and which screen or job
performs it. Omit if the object is a flat reference record.>

## Relations

| Related entity | Cardinality | Via |
|----------------|-------------|-----|

## Where it comes from

| Method | Endpoint | Returns |
|--------|----------|---------|

## Assumptions

> assumed, needs verification — <statement>
