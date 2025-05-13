# Evidence Management API Documentation

## Overview

The Evidence Management API provides a comprehensive system for managing structured evidence with metadata, categorization, tagging, and attachment support. This API is part of the Sentimark Kanban system and allows for detailed tracking and verification of task evidence.

## Base URL

All API endpoints are relative to the base URL: `http://localhost:8000`

## Authentication

Currently, the API does not require authentication. In a production environment, appropriate authentication mechanisms should be implemented.

## Data Models

### Evidence

The core model representing a piece of evidence attached to a task.

```json
{
  "id": "string",                 // Unique identifier for the evidence
  "task_id": "string",            // ID of the task this evidence belongs to
  "type": "text",                 // Type of evidence (see EvidenceType)
  "content": "string",            // Evidence content/description
  "status": "unverified",         // Verification status (see EvidenceStatus)
  "metadata": {                   // Evidence metadata
    "created_by": "string",       // User who created the evidence
    "created_at": "datetime",     // Evidence creation timestamp
    "updated_at": "datetime",     // Evidence last update timestamp
    "verified_by": "string",      // User who verified the evidence
    "verified_at": "datetime",    // Evidence verification timestamp
    "source": "string",           // Source of the evidence
    "location": "string",         // Location where evidence was collected
    "tool": "string",             // Tool used to generate the evidence
    "version": "string"           // Version of the system when evidence was collected
  },
  "tags": ["string"],             // Tags for categorizing the evidence
  "attachments": [                // Attachments to the evidence
    {
      "id": "string",             // Unique identifier for the attachment
      "name": "string",           // Name of the attachment
      "type": "string",           // MIME type of the attachment
      "url": "string",            // URL to the attachment if stored externally
      "content": "string",        // Base64 encoded content if stored inline
      "created": "datetime"       // Attachment creation timestamp
    }
  ]
}
```

### EvidenceType

Enum representing the types of evidence that can be attached to a task.

```
TEXT         - Plain text evidence
CODE         - Code snippets or source code
IMAGE        - Image files
LINK         - URLs or links to external resources
FILE         - General file attachments
TEST_RESULT  - Test results or reports
COMMIT       - Git commit information
PR           - Pull request information
REVIEW       - Code review feedback
OTHER        - Other types of evidence
```

### EvidenceStatus

Enum representing the verification status of evidence.

```
UNVERIFIED      - Evidence has not been verified
VERIFIED        - Evidence has been verified
REJECTED        - Evidence has been rejected
NEEDS_MORE_INFO - Evidence needs more information
```

## API Endpoints

### Create Evidence

Creates a new evidence entry for a task.

- **URL**: `/evidence/{task_id}`
- **Method**: `POST`
- **URL Parameters**: 
  - `task_id`: ID of the task to add evidence to
- **Request Body**:
  ```json
  {
    "type": "text",           // Required: Type of evidence
    "content": "string",      // Required: Evidence content/description
    "created_by": "string",   // Required: User who created the evidence
    "tags": ["string"],       // Optional: Tags for categorizing the evidence
    "source": "string",       // Optional: Source of the evidence
    "location": "string",     // Optional: Location where evidence was collected
    "tool": "string",         // Optional: Tool used to generate the evidence
    "version": "string"       // Optional: Version of the system when evidence was collected
  }
  ```
- **Success Response**:
  - **Code**: 201 Created
  - **Content**: Evidence object

### Get Evidence

Retrieves a specific evidence entry by ID.

- **URL**: `/evidence/{evidence_id}`
- **Method**: `GET`
- **URL Parameters**:
  - `evidence_id`: ID of the evidence to retrieve
- **Success Response**:
  - **Code**: 200 OK
  - **Content**: Evidence object
- **Error Response**:
  - **Code**: 404 Not Found
  - **Content**: `{"detail": "Evidence '{evidence_id}' not found"}`

### Get Evidence for Task

Retrieves all evidence entries for a specific task.

- **URL**: `/evidence/task/{task_id}`
- **Method**: `GET`
- **URL Parameters**:
  - `task_id`: ID of the task to get evidence for
- **Success Response**:
  - **Code**: 200 OK
  - **Content**: Array of Evidence objects

### Update Evidence

Updates an existing evidence entry.

- **URL**: `/evidence/{evidence_id}`
- **Method**: `PUT`
- **URL Parameters**:
  - `evidence_id`: ID of the evidence to update
- **Request Body**:
  ```json
  {
    "type": "text",           // Optional: Type of evidence
    "content": "string",      // Optional: Evidence content/description
    "status": "verified",     // Optional: Verification status
    "tags": ["string"],       // Optional: Tags for categorizing the evidence
    "verified_by": "string",  // Optional: User who verified the evidence
    "location": "string",     // Optional: Location where evidence was collected
    "tool": "string",         // Optional: Tool used to generate the evidence
    "version": "string"       // Optional: Version of the system when evidence was collected
  }
  ```
- **Success Response**:
  - **Code**: 200 OK
  - **Content**: Updated Evidence object
- **Error Response**:
  - **Code**: 404 Not Found
  - **Content**: `{"detail": "Evidence '{evidence_id}' not found"}`

### Delete Evidence

Deletes an evidence entry.

- **URL**: `/evidence/{evidence_id}`
- **Method**: `DELETE`
- **URL Parameters**:
  - `evidence_id`: ID of the evidence to delete
- **Success Response**:
  - **Code**: 204 No Content
- **Error Response**:
  - **Code**: 404 Not Found
  - **Content**: `{"detail": "Evidence '{evidence_id}' not found"}`

### Add Attachment

Adds an attachment to an evidence entry.

- **URL**: `/evidence/{evidence_id}/attachments`
- **Method**: `POST`
- **URL Parameters**:
  - `evidence_id`: ID of the evidence to add the attachment to
- **Request Body**:
  ```json
  {
    "name": "string",      // Required: Name of the attachment
    "type": "string",      // Required: MIME type of the attachment
    "url": "string",       // Optional: URL to the attachment if stored externally
    "content": "string"    // Optional: Base64 encoded content if stored inline
  }
  ```
- **Success Response**:
  - **Code**: 200 OK
  - **Content**: EvidenceAttachment object
- **Error Response**:
  - **Code**: 404 Not Found
  - **Content**: `{"detail": "Evidence '{evidence_id}' not found"}`

### Upload Attachment

Uploads a file as an attachment to an evidence entry.

- **URL**: `/evidence/{evidence_id}/attachments/upload`
- **Method**: `POST`
- **URL Parameters**:
  - `evidence_id`: ID of the evidence to add the attachment to
- **Request Body**: Multipart form data with a file field
- **Success Response**:
  - **Code**: 200 OK
  - **Content**: EvidenceAttachment object
- **Error Response**:
  - **Code**: 404 Not Found
  - **Content**: `{"detail": "Evidence '{evidence_id}' not found"}`

### Delete Attachment

Deletes an attachment from an evidence entry.

- **URL**: `/evidence/{evidence_id}/attachments/{attachment_id}`
- **Method**: `DELETE`
- **URL Parameters**:
  - `evidence_id`: ID of the evidence the attachment belongs to
  - `attachment_id`: ID of the attachment to delete
- **Success Response**:
  - **Code**: 204 No Content
- **Error Response**:
  - **Code**: 404 Not Found
  - **Content**: `{"detail": "Attachment '{attachment_id}' not found"}`

### Get Attachment

Retrieves an attachment file by filename.

- **URL**: `/evidence/attachments/{filename}`
- **Method**: `GET`
- **URL Parameters**:
  - `filename`: Name of the attachment file
- **Success Response**:
  - **Code**: 200 OK
  - **Content**: The attachment file
- **Error Response**:
  - **Code**: 404 Not Found
  - **Content**: `{"detail": "Attachment '{filename}' not found"}`

### Search Evidence

Searches for evidence entries based on various criteria.

- **URL**: `/evidence/search`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "task_id": "string",          // Optional: Filter by task ID
    "type": "text",               // Optional: Filter by evidence type
    "status": "verified",         // Optional: Filter by verification status
    "tags": ["string"],           // Optional: Filter by tags (any match)
    "all_tags": ["string"],       // Optional: Filter by tags (all must match)
    "created_by": "string",       // Optional: Filter by creator
    "verified_by": "string",      // Optional: Filter by verifier
    "created_after": "datetime",  // Optional: Filter by creation date (after)
    "created_before": "datetime", // Optional: Filter by creation date (before)
    "search_text": "string",      // Optional: Search in evidence content
    "source": "string",           // Optional: Filter by evidence source
    "tool": "string"              // Optional: Filter by tool used
  }
  ```
- **Success Response**:
  - **Code**: 200 OK
  - **Content**: Array of Evidence objects

### Get Evidence Statistics

Retrieves statistics about evidence entries.

- **URL**: `/evidence/stats`
- **Method**: `GET`
- **Success Response**:
  - **Code**: 200 OK
  - **Content**: Evidence statistics

### Get Evidence Statistics for Task

Retrieves statistics about evidence entries for a specific task.

- **URL**: `/evidence/stats/{task_id}`
- **Method**: `GET`
- **URL Parameters**:
  - `task_id`: ID of the task to get statistics for
- **Success Response**:
  - **Code**: 200 OK
  - **Content**: Evidence statistics for the task

### Verify Evidence

Marks an evidence entry as verified.

- **URL**: `/evidence/{evidence_id}/verify`
- **Method**: `POST`
- **URL Parameters**:
  - `evidence_id`: ID of the evidence to verify
- **Request Body**:
  ```json
  {
    "verified_by": "string"  // Required: User who verified the evidence
  }
  ```
- **Success Response**:
  - **Code**: 200 OK
  - **Content**: Updated Evidence object
- **Error Response**:
  - **Code**: 404 Not Found
  - **Content**: `{"detail": "Evidence '{evidence_id}' not found"}`

### Reject Evidence

Marks an evidence entry as rejected.

- **URL**: `/evidence/{evidence_id}/reject`
- **Method**: `POST`
- **URL Parameters**:
  - `evidence_id`: ID of the evidence to reject
- **Request Body**:
  ```json
  {
    "verified_by": "string",  // Required: User who rejected the evidence
    "reason": "string"        // Required: Reason for rejection
  }
  ```
- **Success Response**:
  - **Code**: 200 OK
  - **Content**: Updated Evidence object
- **Error Response**:
  - **Code**: 404 Not Found
  - **Content**: `{"detail": "Evidence '{evidence_id}' not found"}`

### Request More Information

Marks an evidence entry as needing more information.

- **URL**: `/evidence/{evidence_id}/request-more-info`
- **Method**: `POST`
- **URL Parameters**:
  - `evidence_id`: ID of the evidence that needs more information
- **Request Body**:
  ```json
  {
    "verified_by": "string",  // Required: User who requested more information
    "request": "string"       // Required: Specific information requested
  }
  ```
- **Success Response**:
  - **Code**: 200 OK
  - **Content**: Updated Evidence object
- **Error Response**:
  - **Code**: 404 Not Found
  - **Content**: `{"detail": "Evidence '{evidence_id}' not found"}`

### Migrate Legacy Evidence

Migrates legacy evidence (plain text) to the new structured format.

- **URL**: `/evidence/migrate/{task_id}`
- **Method**: `POST`
- **URL Parameters**:
  - `task_id`: ID of the task the evidence belongs to
- **Request Body**:
  ```json
  {
    "legacy_evidence": "string",  // Required: Legacy evidence text
    "created_by": "string"        // Optional: User who created the evidence (default: "system")
  }
  ```
- **Success Response**:
  - **Code**: 200 OK
  - **Content**: Created Evidence object
- **Error Response**:
  - **Code**: 500 Internal Server Error
  - **Content**: `{"detail": "Failed to migrate legacy evidence: {error}"}`

## Error Handling

All API endpoints return appropriate HTTP status codes:

- `200 OK`: The request was successful
- `201 Created`: The resource was successfully created
- `204 No Content`: The request was successful but there is no content to return
- `400 Bad Request`: The request was invalid
- `404 Not Found`: The requested resource was not found
- `500 Internal Server Error`: An error occurred on the server

Error responses include a detail message explaining the error:

```json
{
  "detail": "Error message"
}
```

## Pagination

Currently, the API does not support pagination. For large datasets, pagination should be implemented to improve performance.

## Rate Limiting

Currently, the API does not implement rate limiting. In a production environment, appropriate rate limiting should be implemented to prevent abuse.

## Examples

### Creating Evidence

```bash
curl -X POST "http://localhost:8000/evidence/SENTI-1234567890" \
     -H "Content-Type: application/json" \
     -d '{
           "type": "text",
           "content": "Task completed successfully. All tests passing.",
           "created_by": "john.doe",
           "tags": ["completed", "tested"],
           "source": "manual",
           "tool": "pytest"
         }'
```

### Searching Evidence

```bash
curl -X POST "http://localhost:8000/evidence/search" \
     -H "Content-Type: application/json" \
     -d '{
           "status": "verified",
           "tags": ["tested"],
           "created_after": "2025-01-01T00:00:00"
         }'
```

### Uploading an Attachment

```bash
curl -X POST "http://localhost:8000/evidence/3fa85f64-5717-4562-b3fc-2c963f66afa6/attachments/upload" \
     -F "file=@test_results.pdf"
```
