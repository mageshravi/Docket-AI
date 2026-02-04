# Extracting events

## What is an Event?

An event is a specific occurrence anchored in time. It must involve a **Trigger** (the action), **Participants** (the entities), and a **Temporal Anchor** (when it happened).

Unlike a "fact" (e.g., "the company is based in London"), an event is **anchored in time**. If you can't ask "When did this happen?", it's likely an entity attribute rather than an event.

Argument | Description | Example
--- | --- | ---
**Trigger** | The word or phrase that expresses the event occurrence | "scheduled", "purchased", "met"
**Participants** | The entities involved (People, Orgs, Products) | "Alice", "Acme Corp"
**Temporal Anchor** | The date, time, or duration of the event | "2026-02-03", "Next Tuesday"
**Spatial Anchor** | The physical or virtual location | "Conference Room B", "Zoom"
**Attributes** | Modifiers like status or modality | "Confirmed", "Canceled", "Tentative"

Events can be extracted from,

1. Uploaded file
1. Parsed email
1. Parsed email attachment

Events have the following attributes extracted from files,

- title
- description
- event_date
- place (optional)

Users can update/override the title and description. However, retain the original values.

## Data model

Field | Data type | Constraints | Comments
--- | --- | --- | ---
title | VARCHAR | NOT NULL | _N/A_
description | TEXT | NOT NULL | A brief sentence containing the details about trigger, participants, temporal & spatial anchors and attributes.
event_date | DATETIME | NOT NULL | Date and time of the occurrence.
place | VARCHAR | _NULL_ | _N/A_
custom_title | VARCHAR | _NULL_ | Custom title assigned by user
custom_description | TEXT | _NULL_ | Custom description assigned by user
data | JSON | NOT NULL | The original JSON returned by the LLM
source_entity | ENUM | NOT NULL | UPLOADED_FILE, PARSED_EMAIL or PARSED_EMAIL_ATTACHMENT
source_entity_id | INTEGER | Positive, NOT NULL | ID of the source entity

## Implementation

### Task Queue

Implement a shared task (queue) `extract_events` that extracts events from any source (uploaded file, parsed email or parsed email attachment) and saves to database. The task receives two arguments - `entity_type` and `entity_id`.

`entity_type` - The entity to extract events from. `uploaded_file`, `parsed_email` or `parsed_email_attachment`.
`entity_id` - The primary key of the entity.

Entity | Task call | Description
--- | --- | ---
Uploaded file | `extract_events('uploaded_file', 101)` | Extracts events from uploaded file with ID 101.
Parsed email | `extract_events('parsed_email', 1001)` | Extract events from parsed email with ID 1001.
Parsed email attachment | `extract_events('parsed_email_attachment', 10001)` | Extract events from parsed email attachment with ID 10001.

The shared task calls one of the three management commands to perform the extraction.

### Management Commands

Implement a management command `extract_events_from_uploaded_file`.

If the file is a regular file (doc, spreadsheet, presentation, pdf, text or csv), then read the contents and pass-on to LLM for event extraction. The LLM must return event data in the following JSON format,

```json
{
  "title": "Suitable title not exceeding 255 characters",
  "description": "Parsed description in TEXT format",
  "event_date": "<datetime> of the occurrence",
  "place": "",
  "trigger": "<trigger>",
  "participants": [
    "Participant 1",
    "Participant 2",
  ],
  "attributes": "<attributes>",
  "confidence_score": "Confidence score assigned by LLM (from 0.0 to 1.0)"
}
```

If the file is an email, then read the contents and pass-on to LLM for event extraction. Additionally, if the email has attachments, then iterate through the attachments and extract events.
