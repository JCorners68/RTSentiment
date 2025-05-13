# Authentication and Authorization Guide

This guide explains how to authenticate with the Evidence Management System API and understand the permission model.

## Authentication Methods

The Evidence Management System API uses API keys for authentication. This provides a simple yet secure way to authenticate API requests.

### API Key Authentication

All authenticated requests must include an API key in the `X-API-Key` header:

```
X-API-Key: your_api_key_here
```

#### Obtaining an API Key

API keys can be obtained through the following methods:

1. **Command Line Interface**:
   ```bash
   python -m src.main kanban auth generate-key --user="username" --expiry="30d"
   ```

2. **Admin Dashboard**:
   Navigate to Settings > API Keys in the admin dashboard to generate a new key.

#### API Key Best Practices

1. **Never share your API key**: Treat your API key like a password.
2. **Set an expiration date**: Limit the lifetime of your keys for security.
3. **Use environment variables**: Store API keys in environment variables, not in code.
4. **Use different keys for different environments**: Separate keys for development, testing, and production.
5. **Rotate keys regularly**: Change keys periodically to limit the impact of compromised keys.

#### Example API Key Implementation

**JavaScript**:
```javascript
const fetchEvidence = async (id) => {
  const response = await fetch(`/api/kanban/evidence/${id}`, {
    headers: {
      'X-API-Key': process.env.API_KEY
    }
  });
  return response.json();
};
```

**Python**:
```python
import requests
import os

def fetch_evidence(evidence_id):
    headers = {
        'X-API-Key': os.environ.get('API_KEY')
    }
    response = requests.get(
        f'/api/kanban/evidence/{evidence_id}',
        headers=headers
    )
    response.raise_for_status()
    return response.json()
```

## Authorization Model

The Evidence Management System uses a role-based access control (RBAC) system to determine what operations users can perform.

### Roles

The system defines the following roles, each with increasing levels of permissions:

| Role | Description |
|------|-------------|
| `viewer` | Can view evidence items |
| `contributor` | Can create and update evidence items |
| `manager` | Can manage evidence relationships and categories |
| `admin` | Full access to all resources |

### Permissions

Permissions are mapped to API endpoints as follows:

| Endpoint | Viewer | Contributor | Manager | Admin |
|----------|--------|-------------|---------|-------|
| GET /api/kanban/evidence | ✅ | ✅ | ✅ | ✅ |
| POST /api/kanban/evidence | ❌ | ✅ | ✅ | ✅ |
| PUT /api/kanban/evidence/{id} | ❌ | ✅ | ✅ | ✅ |
| DELETE /api/kanban/evidence/{id} | ❌ | ❌ | ✅ | ✅ |
| POST /api/kanban/attachments/{evidenceId} | ❌ | ✅ | ✅ | ✅ |
| DELETE /api/kanban/attachments/{evidenceId}/{attachmentId} | ❌ | ✅ | ✅ | ✅ |
| POST /api/kanban/batch | ❌ | ❌ | ✅ | ✅ |
| POST /api/kanban/webhooks | ❌ | ❌ | ❌ | ✅ |

### Permission Checks

The API performs permission checks at two levels:

1. **Endpoint Level**: Verifies the user has the appropriate role to access the endpoint
2. **Resource Level**: Verifies the user has permission for the specific resource

### Unauthorized Access

When a user attempts to access a resource without the required permissions, the API returns:

- HTTP status code `403 Forbidden`
- Error code `INSUFFICIENT_PERMISSIONS`
- A message explaining the required permissions

Example:
```json
{
  "error": {
    "code": "INSUFFICIENT_PERMISSIONS",
    "message": "You do not have permission to delete evidence items",
    "details": {
      "required_role": "manager",
      "current_role": "contributor"
    }
  }
}
```

## Token Expiration and Refresh

API keys have a configurable expiration period, after which they will no longer be valid.

### Handling Expired Tokens

When an API key expires, requests will receive:
- HTTP status code `401 Unauthorized`
- Error code `API_KEY_EXPIRED`

```json
{
  "error": {
    "code": "API_KEY_EXPIRED",
    "message": "API key has expired",
    "details": {
      "expired_at": "2023-12-31T23:59:59Z"
    }
  }
}
```

### Refreshing API Keys

API keys should be refreshed before they expire using the following methods:

1. **Command Line Interface**:
   ```bash
   python -m src.main kanban auth refresh-key --key-id="key_id"
   ```

2. **API Endpoint** (requires admin role):
   ```
   POST /api/kanban/auth/refresh-key
   ```
   
   Payload:
   ```json
   {
     "key_id": "your_key_id",
     "expiry": "30d"
   }
   ```

## Multi-Environment Authentication

For applications that need to interact with multiple environments (development, staging, production), we recommend the following approach:

1. **Use environment-specific keys**: Generate separate API keys for each environment
2. **Configure environment variables**: Set up environment-specific variables

Example configuration file for a Node.js application:

```javascript
// config.js
module.exports = {
  development: {
    apiUrl: 'http://localhost:3000',
    apiKey: process.env.DEV_API_KEY
  },
  staging: {
    apiUrl: 'https://staging-api.example.com',
    apiKey: process.env.STAGING_API_KEY
  },
  production: {
    apiUrl: 'https://api.example.com',
    apiKey: process.env.PROD_API_KEY
  }
};
```

## Rate Limiting

API requests are subject to rate limiting to ensure system stability. Rate limits are applied per API key.

The standard rate limits are:
- 100 requests per minute for normal operations
- 30 requests per minute for batch operations
- 10 requests per minute for webhook operations

When rate limits are exceeded, the API returns:
- HTTP status code `429 Too Many Requests`
- `Retry-After` header indicating seconds to wait

## Security Considerations

### TLS/SSL Requirements

All API requests must be made using HTTPS (except for local development). HTTP requests will be rejected.

### API Key Security

1. **Never expose API keys in client-side code** or public repositories
2. **Restrict API key usage** to only the necessary endpoints
3. **Monitor API key usage** for suspicious activity

### IP Restrictions

For additional security, you can restrict API key usage to specific IP addresses:

```bash
python -m src.main kanban auth update-key --key-id="key_id" --allowed-ips="192.168.1.1,10.0.0.1"
```

### Audit Logging

All authentication and authorization activities are logged and can be reviewed in the audit log.

To review authentication logs:

```bash
python -m src.main kanban logs auth --days=7
```

## Troubleshooting

### Common Authentication Issues

1. **"Invalid API Key" error**
   - Ensure the API key is correctly formatted and included in the `X-API-Key` header
   - Verify the API key hasn't been revoked or expired

2. **"Insufficient Permissions" error**
   - Confirm your API key is associated with the correct role
   - Check if you need elevated permissions for the operation

3. **Rate limit exceeded**
   - Implement exponential backoff retry logic
   - Consider optimizing to reduce the number of API calls

### Getting Help

If you continue experiencing authentication issues:

1. **Check key validity**:
   ```bash
   python -m src.main kanban auth check-key --key="your_api_key"
   ```

2. **Verify your role and permissions**:
   ```bash
   python -m src.main kanban auth list-permissions
   ```

3. **Contact support** with details of your authentication issue, including error messages and timestamps.
