# Kanban CLI Data Model Documentation

This document details the data models used in the Kanban CLI application, with particular focus on the Evidence Management System which is a priority feature.

## Table of Contents

- [Overview](#overview)
- [File Structure](#file-structure)
- [Task Model](#task-model)
- [Epic Model](#epic-model)
- [Board Model](#board-model)
- [Evidence Management System](#evidence-management-system) (Priority Feature)
  - [Evidence Model](#evidence-model)
  - [Attachment Model](#attachment-model)
  - [Evidence Storage](#evidence-storage)
  - [Evidence Relationships](#evidence-relationships)
  - [Security Considerations](#security-considerations)

## Overview

The Kanban CLI application uses a structured data model to represent tasks, epics, boards, and evidence items. All data is stored in JSON format for easy serialization, versioning, and interoperability.

## File Structure

The application stores data in the following directory structure:

```
data/
├── tasks/
│   ├── index.json        # Index of all tasks
│   ├── TSK-123.json      # Individual task files
│   └── ...
├── epics/
│   ├── index.json        # Index of all epics
│   ├── EPC-123.json      # Individual epic files
│   └── ...
├── boards/
│   ├── index.json        # Index of all boards
│   ├── BRD-123.json      # Individual board files
│   └── ...
└── evidence/             # Priority feature
    ├── index/
    │   ├── main.json     # Main evidence index
    │   ├── tags.json     # Tag-based index
    │   ├── categories.json # Category-based index
    │   └── relations.json  # Relationship index
    ├── EVD-123.json      # Individual evidence files
    ├── ...
    └── attachments/      # Evidence attachment files
        ├── ATT-123/      # Directories for each attachment
        │   └── file.pdf  # Actual attachment files
        └── ...
```

## Task Model

Tasks are the basic unit of work in the Kanban system, representing individual work items.

### Task Schema

```json
{
  "id": "TSK-123",
  "title": "Implement evidence search",
  "description": "Create search functionality for the evidence system",
  "status": "In Progress",
  "priority": "High",
  "epic_id": "EPC-456",
  "assignee": "John Smith",
  "complexity": 3,
  "tags": ["evidence-system", "search", "priority"],
  "due_date": "2025-06-15T00:00:00",
  "created_at": "2025-05-01T10:00:00",
  "updated_at": "2025-05-10T14:30:00",
  "related_evidence_ids": ["EVD-123", "EVD-456"]
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique identifier (format: TSK-*) |
| title | string | Task title |
| description | string | Task description |
| status | string | Current status (Backlog, Ready, In Progress, Review, Done) |
| priority | string | Priority level (Low, Medium, High, Critical) |
| epic_id | string | Parent epic ID (optional) |
| assignee | string | Person assigned to the task (optional) |
| complexity | integer | Task complexity (1-5) |
| tags | array | List of tag strings |
| due_date | string | ISO date string (optional) |
| created_at | string | ISO date string |
| updated_at | string | ISO date string |
| related_evidence_ids | array | List of evidence IDs related to this task |

## Epic Model

Epics group related tasks together, representing larger work items or features.

### Epic Schema

```json
{
  "id": "EPC-456",
  "title": "Evidence Management System Enhancement",
  "description": "Enhance the evidence system with improved search and categorization",
  "status": "In Progress",
  "owner": "Jane Doe",
  "start_date": "2025-05-01T00:00:00",
  "end_date": "2025-06-30T00:00:00",
  "created_at": "2025-04-25T09:00:00",
  "updated_at": "2025-05-10T15:45:00",
  "related_evidence_ids": ["EVD-123", "EVD-456", "EVD-789"]
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique identifier (format: EPC-*) |
| title | string | Epic title |
| description | string | Epic description |
| status | string | Current status (Open, In Progress, Closed) |
| owner | string | Epic owner (optional) |
| start_date | string | ISO date string (optional) |
| end_date | string | ISO date string (optional) |
| created_at | string | ISO date string |
| updated_at | string | ISO date string |
| related_evidence_ids | array | List of evidence IDs related to this epic |

## Board Model

Boards define the structure of Kanban boards, including columns and visualization settings.

### Board Schema

```json
{
  "id": "BRD-123",
  "name": "Main Kanban Board",
  "columns": ["Backlog", "Ready", "In Progress", "Review", "Done"],
  "created_at": "2025-04-20T08:00:00",
  "updated_at": "2025-05-05T11:30:00"
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique identifier (format: BRD-*) |
| name | string | Board name |
| columns | array | List of column names |
| created_at | string | ISO date string |
| updated_at | string | ISO date string |

## Evidence Management System

> **Priority Feature**: The Evidence Management System is a priority feature of this application.

The Evidence Management System provides structured storage, categorization, and retrieval of evidence items, with support for attachments, relationships, and advanced searching.

### Evidence Model

Evidence items represent documented proof, information, or artifacts related to tasks and epics.

#### Evidence Schema

```json
{
  "id": "EVD-123",
  "title": "User Requirements Document",
  "description": "Comprehensive document detailing user requirements for the evidence system",
  "source": "Product Manager Interview",
  "category": "Requirement",
  "subcategory": "Functional Requirements",
  "relevance_score": "High",
  "date_collected": "2025-04-25T14:30:00",
  "tags": ["evidence-system", "requirements", "priority-feature"],
  "project_id": "PRJ-001",
  "epic_id": "EPC-456",
  "task_id": "TSK-789",
  "related_evidence_ids": ["EVD-456", "EVD-789"],
  "attachments": [
    {
      "id": "ATT-123",
      "file_path": "requirements/evidence_reqs.pdf",
      "file_name": "evidence_reqs.pdf",
      "file_type": "application/pdf",
      "file_size": 256000,
      "description": "PDF document with detailed requirements",
      "created_at": "2025-04-25T15:00:00",
      "uploaded_by": "John Smith"
    }
  ],
  "created_at": "2025-04-25T14:30:00",
  "updated_at": "2025-05-10T16:45:00",
  "created_by": "John Smith",
  "metadata": {
    "version": "1.0",
    "status": "Approved",
    "priority": "High"
  }
}
```

#### Evidence Fields

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique identifier (format: EVD-*) |
| title | string | Evidence title |
| description | string | Evidence description |
| source | string | Source of the evidence (e.g., interview, document, system) |
| category | string | Primary category (Requirement, Bug, Design, Test, Result, Reference, User Feedback, Decision, Other) |
| subcategory | string | More specific categorization (optional) |
| relevance_score | string | Importance/relevance level (Low, Medium, High, Critical) |
| date_collected | string | ISO date string when evidence was collected |
| tags | array | List of tag strings for filtering |
| project_id | string | ID of related project (optional) |
| epic_id | string | ID of related epic (optional) |
| task_id | string | ID of related task (optional) |
| related_evidence_ids | array | List of related evidence IDs |
| attachments | array | List of attachment objects |
| created_at | string | ISO date string |
| updated_at | string | ISO date string |
| created_by | string | User who created the evidence |
| metadata | object | Additional metadata as key-value pairs |

### Attachment Model

Attachments represent files associated with evidence items.

#### Attachment Schema

```json
{
  "id": "ATT-123",
  "file_path": "requirements/evidence_reqs.pdf",
  "file_name": "evidence_reqs.pdf",
  "file_type": "application/pdf",
  "file_size": 256000,
  "content_preview": "This document outlines the requirements for...",
  "description": "PDF document with detailed requirements",
  "created_at": "2025-04-25T15:00:00",
  "uploaded_by": "John Smith"
}
```

#### Attachment Fields

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique identifier (format: ATT-*) |
| file_path | string | Path to the attachment file (relative to attachments dir) |
| file_name | string | Original filename |
| file_type | string | File MIME type |
| file_size | integer | File size in bytes |
| content_preview | string | Plain text preview of content (if applicable, optional) |
| description | string | Description of the attachment |
| created_at | string | ISO date string |
| uploaded_by | string | User who uploaded the attachment (optional) |

### Evidence Storage

The Evidence Management System uses a structured storage approach for efficient retrieval:

1. **Individual Evidence Files**: Each evidence item is stored as a separate JSON file.
2. **Index Files**: Multiple index files optimize search performance:
   - `main.json`: Main index of all evidence items
   - `tags.json`: Index of evidence items by tag
   - `categories.json`: Index of evidence items by category
   - `relations.json`: Index of relationships between evidence items and tasks/epics
3. **Attachment Storage**: 
   - Attachments are stored in individual directories named after their ID
   - Original filenames are preserved within the attachment directory
   - Metadata is stored in the parent evidence item

### Evidence Relationships

The Evidence Management System supports relationships between different entities:

1. **Evidence-to-Task**: Links evidence to specific tasks
2. **Evidence-to-Epic**: Links evidence to broader epics
3. **Evidence-to-Evidence**: Links related evidence items together
4. **Evidence-to-Project**: Links evidence to entire projects

These relationships are stored in both the evidence items themselves and in the `relations.json` index file for efficient querying.

### Security Considerations

The Evidence Management System implements several security measures:

1. **Path Sanitization**: All file paths are sanitized to prevent directory traversal attacks
2. **File Validation**: Attachments are validated for size, type, and content
3. **Secure Storage**: Attachment storage follows system security best practices
4. **Audit Logging**: All operations on evidence items are logged for audit purposes

## File Format Details

### Index Files

Index files use a consistent format:

```json
{
  "items": [
    {
      "id": "ITEM-123",
      "created_at": "2025-05-01T10:00:00",
      "updated_at": "2025-05-10T14:30:00"
    }
  ],
  "count": 1,
  "last_updated": "2025-05-10T14:30:00"
}
```

### Tag Index

The tag index provides fast lookups by tag:

```json
{
  "tags": {
    "priority": ["TSK-123", "TSK-456"],
    "evidence-system": ["TSK-123", "EVD-456"]
  },
  "last_updated": "2025-05-10T14:30:00"
}
```

### Category Index

The category index provides fast lookups by evidence category:

```json
{
  "categories": {
    "Requirement": ["EVD-123", "EVD-456"],
    "Design": ["EVD-789"]
  },
  "last_updated": "2025-05-10T14:30:00"
}
```

### Relationship Index

The relationship index tracks connections between items:

```json
{
  "evidence_to_task": {
    "EVD-123": ["TSK-456", "TSK-789"],
    "EVD-456": ["TSK-123"]
  },
  "evidence_to_epic": {
    "EVD-123": ["EPC-456"],
    "EVD-456": ["EPC-456", "EPC-789"]
  },
  "evidence_to_evidence": {
    "EVD-123": ["EVD-456", "EVD-789"],
    "EVD-456": ["EVD-123"]
  },
  "last_updated": "2025-05-10T14:30:00"
}
```
