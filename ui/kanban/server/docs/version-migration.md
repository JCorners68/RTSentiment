# API Version Migration Guide

This document provides guidance on migrating between different versions of the Evidence Management System API.

## Version Overview

| Version | Status | Release Date | End-of-Life | Description |
|---------|--------|--------------|-------------|-------------|
| v1      | Stable | 2025-01-01   | N/A         | Initial stable release with full evidence management capabilities |
| v2      | Beta   | 2025-05-01   | N/A         | Enhanced version with AI and analytics features |

## Feature Support by Version

| Feature                   | v1     | v2     | Notes |
|---------------------------|--------|--------|-------|
| Evidence CRUD operations  | ✅     | ✅     | |
| Evidence search           | ✅     | ✅     | Enhanced in v2 |
| Attachments management    | ✅     | ✅     | |
| Batch operations          | ✅     | ✅     | |
| Evidence relationships    | ✅     | ✅     | |
| AI-powered categorization | ❌     | ✅     | New in v2 |
| Analytics & insights      | ❌     | ✅     | New in v2 |

## Accessing Versioned APIs

### URL Path Versioning

The recommended approach is to use explicit version in the URL path:

```
/api/v1/kanban/evidence
```

### Accept Header Versioning

You can also request a specific version using the Accept header:

```
Accept: application/json; version=v1
```

### Explicit Version Header

Alternatively, you can use the X-API-Version header:

```
X-API-Version: v1
```

## Migrating from Unversioned API to v1

The unversioned API routes (e.g., `/api/kanban/evidence`) are now deprecated but remain functional for backward compatibility. These routes are equivalent to the v1 API.

### Migration Steps

1. Update all API endpoint URLs to include the version prefix (`/api/v1/`) 
2. Test your application thoroughly
3. No data format changes are required as the payload format is identical

Example:
- Old: `http://localhost:3000/api/kanban/evidence`
- New: `http://localhost:3000/api/v1/kanban/evidence`

## Migrating from v1 to v2

The v2 API introduces several enhancements including structured metadata, expanded evidence relationships, and AI-powered features.

### Breaking Changes

1. Evidence structure changes:
   - Added `metadata` object for extended properties
   - System tags moved to metadata
   - Enhanced relationship model

2. Query parameter changes:
   - Advanced filtering syntax
   - Expanded search capabilities

### Migration Steps

1. Update all API endpoints to use the v2 prefix
2. Update evidence creation to include metadata structure
3. Modify search queries to use the enhanced filtering syntax
4. Test your application thoroughly with the new endpoints

### Example: Evidence Structure Changes

v1 Format:
```json
{
  "id": "EVID-12345678",
  "title": "User Authentication Bug",
  "description": "Users being logged out unexpectedly",
  "category": "BUG",
  "subcategory": "Frontend",
  "relevance_score": 8,
  "tags": ["authentication", "frontend", "system:high-priority"],
  "source": "User Feedback"
}
```

v2 Format:
```json
{
  "id": "EVID-12345678",
  "title": "User Authentication Bug",
  "description": "Users being logged out unexpectedly",
  "category": "BUG",
  "subcategory": "Frontend",
  "relevance_score": 8,
  "tags": ["authentication", "frontend"],
  "metadata": {
    "tags": ["system:high-priority"],
    "source_information": "User Feedback",
    "ai_analysis": {
      "suggested_category": "Authentication",
      "impact_score": 0.85,
      "similar_issues": ["EVID-87654321"]
    }
  }
}
```

## Backward Compatibility

The API maintains backward compatibility through:

1. **Version negotiation** - Request specific version via Accept header
2. **Automatic data transformation** - Server converts between formats as needed
3. **Legacy endpoint support** - Unversioned routes remain functional
4. **Version-specific validation** - Different validation rules per version

When using newer client with older API version, or vice versa, data is automatically transformed to maintain compatibility.

## Deprecation Policy

1. API versions will be supported for at least 12 months after a newer version is released
2. Deprecated versions will emit warning headers before removal
3. End-of-life announcements will be made at least 6 months in advance
4. After end-of-life, the version will be removed in a future release

## Version Detection

You can check your current API version:

```
GET /api/version
```

Response:
```json
{
  "current_version": "1.0.0",
  "default_version": "v1",
  "versions": {
    "v1": {
      "version": "1.0.0",
      "status": "stable",
      "releaseDate": "2025-01-01",
      "endOfLife": null,
      "supportsFeatures": [...]
    },
    "v2": {
      "version": "2.0.0",
      "status": "beta",
      "releaseDate": "2025-05-01",
      "endOfLife": null,
      "supportsFeatures": [...]
    }
  }
}
```

## Compatibility Checking

You can check compatibility with a specific version:

```
GET /api/version/compatibility?version=1.0.0
```

Response:
```json
{
  "compatible": true,
  "recommended_version": "v1",
  "features": [...]
}
```

## Best Practices

1. Always specify the API version explicitly in URLs or headers
2. Monitor for Warning headers indicating deprecation
3. Test your application against multiple API versions
4. Plan version migrations in advance
5. Use the compatibility endpoint to detect version issues

## Support

For assistance with API version migration, contact support@realsenti.com or open an issue in the project repository.
