# Extracting Events

Version: 2.0
Date Created: 27 Feb 2026
Status: Active

## 1. Definition of an Event

An **Event** is:

> A discrete real-world occurrence, decision, communication, or commitment that happened (or was formally planned or inferred) at a specific time and moved the situation forward.

An event MUST satisfy:

### ✅ Required Conditions

1. **Temporal Anchor**
    - Exact date/time OR
    - Date OR
    - Reliably inferred time from context
1. **Observable Change**<br>
The event must represent at least one:
    - action performed
    - communication exchanged
    - decision made
    - agreement formed
    - request issued
    - obligation created
    - transaction executed
    - plan scheduled
    - knowledge formally communicated
1. **Actor Presence**<br>
At least one identifiable actor (person, organization, or system).
1. **Evidence Support**<br>
The event must be supported by the provided material.

### ❌ NOT Events

Do NOT extract:

- background facts
- descriptions without action
- opinions or allegations
- legal arguments
- repeated headers/signatures
- document metadata alone

Example:

- ❌ “The vendor was unreliable.”
- ✅ “Client emailed vendor complaining about delay on 12 May 2024.”

## 2. Event Neutrality Rule (CRITICAL)

Events must be written as **verifiable facts**.

Never infer intent, blame, motive, or legality.

Bad:

> Defendant intentionally delayed delivery.

Good:

> Delivery occurred 14 days after agreed deadline.

## 3. Event Types (Classification Model)

Each event implicitly belongs to one category:

- Communication — email, call, message, meeting discussion
- Decision — approval, rejection, confirmation
- Action — work performed or operational step
- Transaction — payment, invoice, financial transfer
- Planning — scheduling or proposal of future activity
- Request / Query — asking for action or information
- Obligation — commitment, assignment, contractual duty
- Knowledge — party formally informed or notified
- Document Event — document or email creation/sending

(You do NOT need to output the category unless requested, but use it internally.)

## 4. Granularity Rule (MACRO LEVEL)

Extract meaningful outcome-level events, not every sentence.

### Example

Email states:

> “We reviewed the draft, approved budget, and scheduled deployment.”

Extract:

- Budget approved
- Deployment scheduled

Do NOT create separate events for greetings, acknowledgements, or signatures.

## 5. Inferred Events (Allowed with Constraints)

You MAY create inferred events ONLY when:

- timing is clear from context, AND
- occurrence is logically necessary, AND
- evidence strongly implies it.

Mark inference explicitly in description using:

> "(Date inferred from context)"

Never invent missing actors, decisions, or actions.

If inference is weak → DO NOT create event.

## 6. Duplicate Prevention (VERY IMPORTANT)

Before creating an event:

- Compare with Existing Events.
- If same real-world occurrence appears multiple times:
    - create ONLY ONE event.
    - prefer earliest or most direct evidence.

Two descriptions referring to the same occurrence = ONE event.

## 7. Temporal Rules

### Relative Dates

Resolve using reference date:

- Documents → published date (or upload date)
- Emails → sent timestamp
- Attachments → parent email timestamp

Mark inferred dates clearly in description.

### Date Ranges

Convert into TWO events:

- Start event
- End event

### Multiple Dates

Create separate events.

## 8. Source Representation Events (MANDATORY)

Always include ONE event representing the source itself.

### Documents

- trigger: "Published"
- title: document title (or inferred)
- description: neutral summary of purpose/content
- event_date: published/upload date

### Emails

- title:
  - "Email Sent: <Subject>"
  - or "Email Received: <Subject>" (client perspective)
- trigger: "Email"
- description: neutral summary + attachment names
- event_date: sent timestamp

## 9. Writing Rules (Legal Quality)

### Title

- concise
- factual
- no opinions
- ≤255 characters

### Description

One neutral sentence containing:

- trigger/action
- participants
- time anchor
- place (if known)
- key outcome

Avoid adjectives unless factual.

## 10. Event Deduplication Heuristic

Treat events as identical if they share:

- same actors
- same action
- same outcome
- same or very close timestamp

Different documents referencing same meeting = ONE event.

## 11. Output Schema

Return ONLY NEW events:

```
{
  "title": "",
  "description": "",
  "event_date": "YYYY-MM-DDTHH:MM:SS",
  "place": "",
  "trigger": "",
  "participants": [],
  "attributes": "",
  "source": {
    "type": "document | email | attachment",
    "id": ""
  }
}
```

## 12. Output Rules

- Return JSON array only.
- No explanations.
- No markdown.
- No duplicate events.
- If none found → `[]`.

## Two-Pass Architecture Prompt

### Why Two Passes Are Necessary

Single-pass LLM extraction causes:

| Problem              | Why it happens                                    |
| -------------------- | ------------------------------------------------- |
| Duplicate events     | Same event described differently across documents |
| Fragmented events    | Pieces extracted separately                       |
| Timeline noise       | Every email becomes an event                      |
| Weak inference       | Model lacks global context                        |
| Poor legal usability | Events not normalized                             |

Two-pass fixes this by separating:

```
PASS 1 → Evidence Extraction (Recall)
PASS 2 → Event Reconstruction (Precision)
```

Think:

> Pass 1 = Investigator collecting notes<br>
> Pass 2 = Lawyer building the official timeline

### System Architecture

```
Documents
   ↓
PASS 1: Candidate Event Extraction
   ↓
Candidate Events (raw, redundant, granular)
   ↓
PASS 2: Event Normalization & Merging
   ↓
Court-Usable Timeline Events
```

### PASS 1 — Candidate Event Extraction (High Recall)

Goal:

> Extract EVERYTHING that might be an event.

Do NOT worry about duplicates yet.

#### Mental Model for LLM

You are an **evidence collector**, not a timeline builder.

### PASS 2 — Event Reconstruction (The Magic Step)

This is where Exhibit AI becomes powerful.

Goal:

> Convert candidate events into canonical legal timeline events.

### Optional (VERY Powerful)

Add internally:

```
supporting_candidate_ids: []
```

This gives audit traceability later.

Lawyers LOVE this.

### Key Design Insight

You are building:

```
Upload → Evidence Graph → Timeline Projection
```

Not document summarization.

### First Principle (Important)

> **Event extraction should NOT run automatically per file anymore.**

Why?

Because:

- Pass-2 needs global context
- Many files contain zero events
- Litigation timelines are intentional workflows, not ingestion side-effects
- Avoid unnecessary LLM cost

👉 Timeline generation should become a user-triggered workflow.

### New Mental Model

Separate two systems

| System                | Purpose          |
| --------------------- | ---------------- |
| Evidence Processing   | Always automatic |
| Timeline Construction | On-demand        |

### High-level flow

#### Phase A — Evidence Ingestion (unchanged mostly)

When user uploads file:

```
Upload
 ↓
Validate
 ↓
Store file
 ↓
Extract text
 ↓
Chunk + vectorize
 ↓
Save searchable evidence
```

🚫 **NO event extraction here anymore**

#### Phase B — Timeline Workspace (NEW)

User explicitly creates or updates a timeline.

Example UI:

```
[ Create Timeline ]
Select Exhibits:
☑ Email threads
☑ Contracts
☐ Financial statements
☑ Meeting minutes
```

Not all files contain events. User provides semantic filtering cheaply.

### Database Model

```
Timeline

- id
- case_id
- name
- status
- created_by
- total_exhibits
- processed_exhibits
- failed_exhibits
- pass1_started_at
- pass2_started_at
```

Values for `status`

1. Pending
1. Pass 1 running
1. Pass 1 completed
1. Pass 2 running
1. Completed
1. Failed

```
TimelineExhibit

- timeline_id
- uploaded_file_id
```

```
CandidateEvent

- id
- timeline_id
- exhibit_id
- action_phrase
- raw_description
- event_date
- date_confidence
- actors (json)
- evidence_excerpt
- confidence
- embedding (optional)
```

_CandidateEvent is the PASS-1 output._

```
TimelineEvent

- id
- timeline_id
- title
- description
- event_date
- place
- trigger
- participants
- attributes
```

_TimelineEvent is the PASS-2 output._

### NEW Processing Flow

#### Step 1 – User selects files (exhibits)

1. User clicks "Generate Timeline"
1. System creates:

```
Timeline(status="processing")
```

#### Step 2 - PASS 1 (Parallel per exhibit)

Worker queue:

```python
for exhibit in timeline.exhibits:
    run_pass_1(timeline, exhibit)
```

Each worker:

```
Retrieve chunks
↓
LLM Pass 1
↓
Store CandidateEvents
```

After every exhibit is processed (PASS-1 worker finishes), the timeline's `processed_exhibits` field is updated atomically.

```python
def run_pass_1(timeline, exhibit):
  extract_candidate_events(exhibit)
  mark_exhibit_complete(timline)
```

```python
from django.db.models import F

Timeline.objects.filter(id=timeline_id).update(
    processed_exhibits=F("processed_exhibits") + 1
)
# Using F() avoids race conditions.

# If failed, update the "failed_exhibits" field
```

Considerations:

- ✅ Parallelizable
- ✅ Cheap retries
- ✅ Scales cleanly

#### Step 3: Trigger PASS 2 (Fan-out Fan-in workflow)

1. **Fan-out**: Pass-1 runs per exhibit (parallel)
1. **Fan-in**: Pass-2 starts only after all required Pass-1 jobs finish

**Pass-2 should be triggered by timeline state, not by workers directly.**

Workers finish work.

The **timeline orchestrator** decides when Pass-2 runs.

Never let individual workers trigger Pass-2.

Immediately after increment:

```python
timeline = Timeline.objects.get(id=timeline_id)

if timeline.processed_exhibits + timeline.failed_exhibits == timeline.total_exhibits:
  trigger_pass2(timeline_id)
```

📌 Multiple workers may reach this condition simultaneously.

So Pass-2 trigger must be idempotent.

```python
updated = Timeline.objects.filter(
  id=timeline_id,
  status="pass1_running"
).update(status="pass1_complete")

if updated:
  run_pass2.delay(timeline_id)
```

Why this works:

- Only ONE worker successfully changes status.
- Others update 0 rows → do nothing.

This is the cleanest distributed lock you can have in Django.

#### Step 4: PASS 2 Worker

```python
def run_pass2(timeline_id):
  Timeline.objects.filter(id=timeline_id).update(
    status="pass2_running"
  )

  candidates = CandidateEvent.objects.filter(
    timeline_id=timeline_id
  )

  reconstruct_events(candidates)

  Timeline.objects.filter(id=timeline_id).update(
    status="completed"
  )
```
