# Evidence Management System API Error Documentation

This document provides detailed information on the errors returned by the Evidence Management System API and how to handle them.

## Error Response Format

All API errors follow a consistent format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "A human-readable error message",
    "details": {
      // Additional error-specific details
    }
  }
}
```

## HTTP Status Codes

The API uses the following HTTP status codes:

| Status Code | Description | Common Scenarios |
|-------------|-------------|-----------------|
| 200 | OK | Successful GET, PUT, or DELETE |
| 201 | Created | Successful POST creating a new resource |
| 400 | Bad Request | Invalid input, missing required fields |
| 401 | Unauthorized | Authentication failure |
| 403 | Forbidden | Permission denied |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource already exists |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server-side error |
| 503 | Service Unavailable | Service temporarily offline |

## Common Error Codes

### Authentication and Authorization Errors

| Error Code | Description | HTTP Status | Resolution |
|------------|-------------|-------------|------------|
| `AUTH_REQUIRED` | Authentication is required | 401 | Include a valid API key in the X-API-Key header |
| `INVALID_API_KEY` | Invalid API key | 401 | Check that the API key is correct |
| `API_KEY_EXPIRED` | API key has expired | 401 | Renew your API key |
| `INSUFFICIENT_PERMISSIONS` | Insufficient permissions | 403 | Request appropriate permissions or use a different API key |

### Validation Errors

| Error Code | Description | HTTP Status | Resolution |
|------------|-------------|-------------|------------|
| `INVALID_INPUT` | Invalid input data | 400 | Check the error details for specific field errors |
| `MISSING_REQUIRED_FIELD` | Required field missing | 400 | Include all required fields in the request |
| `INVALID_FIELD_FORMAT` | Field format is invalid | 400 | Format the field according to the API specifications |
| `FIELD_TOO_LONG` | Field exceeds maximum length | 400 | Shorten the field value |
| `FIELD_TOO_SHORT` | Field below minimum length | 400 | Lengthen the field value |

### Resource Errors

| Error Code | Description | HTTP Status | Resolution |
|------------|-------------|-------------|------------|
| `RESOURCE_NOT_FOUND` | Resource not found | 404 | Check that the ID is correct |
| `RESOURCE_ALREADY_EXISTS` | Resource already exists | 409 | Use a different identifier or update the existing resource |
| `RESOURCE_DELETED` | Resource has been deleted | 410 | Create a new resource |
| `RELATED_RESOURCE_NOT_FOUND` | Related resource not found | 422 | Check related resource IDs |

### Rate Limiting Errors

| Error Code | Description | HTTP Status | Resolution |
|------------|-------------|-------------|------------|
| `RATE_LIMIT_EXCEEDED` | Rate limit exceeded | 429 | Wait before making additional requests |
| `CONCURRENT_REQUESTS_LIMIT` | Too many concurrent requests | 429 | Reduce the rate of parallel requests |

### Server Errors

| Error Code | Description | HTTP Status | Resolution |
|------------|-------------|-------------|------------|
| `INTERNAL_ERROR` | Internal server error | 500 | Contact support with request details |
| `SERVICE_UNAVAILABLE` | Service temporarily unavailable | 503 | Retry the request after a delay |
| `DATABASE_ERROR` | Database error | 500 | Contact support with request details |

## Evidence-Specific Errors

| Error Code | Description | HTTP Status | Resolution |
|------------|-------------|-------------|------------|
| `INVALID_EVIDENCE_ID` | Invalid evidence ID format | 400 | Use the correct format (EVD-XXX) |
| `INVALID_CATEGORY` | Invalid evidence category | 400 | Use one of the supported categories |
| `MAX_ATTACHMENTS_EXCEEDED` | Maximum number of attachments exceeded | 400 | Remove some attachments before adding more |
| `ATTACHMENT_TOO_LARGE` | Attachment file size too large | 400 | Reduce file size or split into multiple files |
| `INVALID_ATTACHMENT_TYPE` | Invalid attachment file type | 400 | Use one of the supported file types |
| `EVIDENCE_LOCKED` | Evidence is locked for editing | 409 | Wait until the evidence is unlocked |
| `CIRCULAR_REFERENCE` | Circular reference in evidence relationships | 400 | Remove the circular reference |

## Webhook-Specific Errors

| Error Code | Description | HTTP Status | Resolution |
|------------|-------------|-------------|------------|
| `WEBHOOK_DELIVERY_FAILED` | Webhook delivery failed | 422 | Check the webhook URL and retry |
| `INVALID_WEBHOOK_URL` | Invalid webhook URL | 400 | Provide a valid HTTP or HTTPS URL |
| `WEBHOOK_TIMEOUT` | Webhook request timed out | 422 | Optimize the webhook endpoint for faster response |
| `WEBHOOK_RATE_LIMITED` | Webhook endpoint rate limited | 422 | Reduce webhook delivery frequency or contact endpoint owner |

## Error Handling Best Practices

1. **Always check the HTTP status code** before processing the response.
2. **Parse the error code** to handle specific errors programmatically.
3. **Display the error message** to users for clarity.
4. **Log detailed error information** for troubleshooting.
5. **Implement exponential backoff** for 429 and 503 errors.

## Example Error Handling

### JavaScript

```javascript
async function getEvidence(id) {
  try {
    const response = await fetch(`/api/kanban/evidence/${id}`);
    
    if (!response.ok) {
      const errorData = await response.json();
      
      // Handle specific error cases
      switch (errorData.error.code) {
        case 'RESOURCE_NOT_FOUND':
          console.error(`Evidence ${id} not found`);
          // Handle not found case
          break;
        case 'RATE_LIMIT_EXCEEDED':
          console.error('Rate limit exceeded, retrying after delay');
          // Implement retry with backoff
          break;
        default:
          console.error(`API Error: ${errorData.error.message}`);
          // Handle generic error
      }
      
      throw new Error(errorData.error.message);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching evidence:', error);
    throw error;
  }
}
```

### Python

```python
import requests
import time

def get_evidence(id, max_retries=3):
    retries = 0
    backoff_factor = 1
    
    while retries < max_retries:
        try:
            response = requests.get(f"/api/kanban/evidence/{id}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as err:
            if response.status_code == 429:  # Rate limited
                retry_after = int(response.headers.get('Retry-After', backoff_factor))
                print(f"Rate limited. Retrying after {retry_after} seconds")
                time.sleep(retry_after)
                retries += 1
                backoff_factor *= 2  # Exponential backoff
            elif response.status_code == 404:  # Not found
                print(f"Evidence {id} not found")
                raise
            else:
                error_data = response.json()
                print(f"API Error: {error_data['error']['message']}")
                raise
        except Exception as err:
            print(f"Error: {err}")
            raise
    
    raise Exception(f"Failed after {max_retries} retries")
```

## Common Troubleshooting

### Authentication Issues

If you're experiencing authentication issues:

1. **Verify your API key** is correct and not expired
2. **Check that you're sending the API key** in the correct header (`X-API-Key`)
3. **Ensure your API key has the required permissions** for the endpoint you're accessing

### Rate Limiting

If you're being rate limited:

1. **Implement retry logic with exponential backoff**
2. **Check the `Retry-After` header** for the recommended wait time
3. **Consider batching requests** to reduce API calls
4. **Cache responses** when appropriate to reduce unnecessary requests

### "Resource Not Found" Errors

If you're getting "Resource Not Found" errors:

1. **Verify the resource ID** is correct
2. **Check if the resource has been deleted**
3. **Ensure you have permission** to access the resource

## Getting Help

If you continue to experience issues with the API:

1. **Check the [API documentation](./api-docs.html)** for the latest information
2. **Review your request logs** for detailed error information
3. **Contact support** with:
   - The specific API endpoint you're calling
   - The complete error response
   - Your request payload (with sensitive information redacted)
   - Timestamps of when the issue occurred
