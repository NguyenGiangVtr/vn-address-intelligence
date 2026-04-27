# Endpoint Documentation Template

Use this template as a starting point for each API endpoint documentation.

---

## Endpoint: [METHOD] /api/path/to/resource

| Property | Value |
|----------|-------|
| **HTTP Method** | GET / POST / PUT / DELETE |
| **Route** | `/api/v1/resource` |
| **Summary** | [1-2 sentence business purpose] |
| **Auth Type** | JWT / API Key / None |
| **Required Roles** | Admin, User, Anonymous |
| **Status** | Active / Beta / Deprecated |

---

### Request

#### Query/Route Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | int | Yes | Unique resource identifier |
| `filter` | string | No | Filter criteria (e.g., "status:active") |

#### Request Body
| Field | Type | Required | Validation | Description |
|-------|------|----------|-----------|-------------|
| `name` | string | Yes | MaxLength: 256 | Resource name |
| `description` | string | No | MaxLength: 1000 | Detailed description |
| `quantity` | int | No | Min: 0, Max: 999 | Item quantity |
| `isActive` | boolean | No | — | Enable/disable flag |

#### Request Example
```json
{
  "name": "Product Name",
  "description": "A brief description",
  "quantity": 10,
  "isActive": true
}
```

---

### Response

#### Success Response (200 OK / 201 Created)

**Response Body:**
```json
{
  "statusCode": "Success",
  "data": {
    "id": 123,
    "name": "Product Name",
    "description": "A brief description",
    "quantity": 10,
    "isActive": true,
    "createdDate": "2026-03-31T10:30:00Z",
    "lastModifiedDate": "2026-03-31T10:30:00Z"
  },
  "errorMessage": null
}
```

| Field | Type | Description |
|-------|------|-------------|
| `statusCode` | enum | CRUDStatusCodeRes: Success, InvalidInput, ResourceNotFound, InvalidAction, ResetContent |
| `data` | object | Response payload with resource details |
| `errorMessage` | string | Null on success; error description on failure |

#### Error Responses

| HTTP Code | Condition | statusCode | Example Response |
|-----------|-----------|-----------|------------------|
| 400 | Invalid request structure or validation fails | `InvalidInput` | `{statusCode: "InvalidInput", data: null, errorMessage: "Field 'name' is required"}` |
| 401 | Missing or invalid authentication token | `Unauthorized` | `{statusCode: "Unauthorized", data: null, errorMessage: "Access denied"}` |
| 403 | Authenticated but lacks required role | `Forbidden` | `{statusCode: "Forbidden", data: null, errorMessage: "User lacks Admin role"}` |
| 404 | Resource not found | `ResourceNotFound` | `{statusCode: "ResourceNotFound", data: null, errorMessage: "Resource with ID 999 not found"}` |
| 409 | Business rule conflict (e.g., duplicate) | `InvalidAction` | `{statusCode: "InvalidAction", data: null, errorMessage: "Product with name already exists"}` |
| 500 | Unhandled exception or service failure | `InternalServerError` | `{statusCode: "InternalServerError", data: null, errorMessage: "An unexpected error occurred"}` |
| 503 | External dependency unavailable (cache, DB, API) | `ResetContent` | `{statusCode: "ResetContent", data: null, errorMessage: "Redis is not available"}` |

---

### Error Code Reference

| Code | HTTP | Cause | Example |
|------|------|-------|---------|
| `Success` | 200/201 | Operation completed successfully | Resource created/updated |
| `InvalidInput` | 400 | Validation failed or missing required field | null, empty string, invalid type |
| `Unauthorized` | 401 | No authentication provided or token invalid | Bearer token missing/expired |
| `Forbidden` | 403 | User authenticated but lacks permission | User role doesn't match required role |
| `ResourceNotFound` | 404 | Referenced resource doesn't exist | ID doesn't match any record |
| `InvalidAction` | 409 | Business logic violation or conflict | Duplicate entry, state violation |
| `ResetContent` | 503 | External service/dependency failure | Redis down, Database unavailable |
| `InternalServerError` | 500 | Unhandled server-side exception | Null reference, parsing error |

---

### Dependencies & Operational Notes

#### Cache Layer
- **Key**: `promotion:combo:{comboId}` (if applicable)
- **TTL**: 1 hour / until midnight / configurable
- **Invalidation**: On create/update; cache warmup on read miss

#### Database
- **Table(s)**: `[SchemaName].[TableName]`
- **Procedure(s)**: `[SchemaName].[Procedure_Name]`
- **Query Type**: Single read / Batch query / Complex join

#### External Services
- **Third-party API**: Name + endpoint
- **Timeout**: 5000ms default
- **Retry Policy**: Exponential backoff (if applicable)

#### Performance Considerations
- **Async Pattern**: Task-based async/await used
- **Batch Size**: [Number] items per request
- **Pagination**: Limit 100 items per request
- **Caching Strategy**: Cache-first with DB fallback

#### Concurrency & Edge Cases
- **Thread-safety**: Thread-safe due to [reason]
- **Rate Limiting**: [Requests/minute/hour]
- **Bulk Operations**: Max 1000 items per bulk request
- **Fallback Behavior**: If cache unavailable, query DB directly

---

### Business Logic Summary

1. **Validation**: [What is validated and how]
2. **Authorization**: [Permission checks]
3. **Cache Check**: [Cache key and fallback behavior]
4. **Database Operation**: [Query/Insert/Update/Delete logic]
5. **Post-Processing**: [Any data transformation or notification]
6. **Response Mapping**: [DTO conversion and enrichment]

---

### Related Endpoints

- **Create**: POST /api/v1/resources
- **Read Single**: GET /api/v1/resources/{id}
- **Update**: PUT /api/v1/resources/{id}
- **Delete**: DELETE /api/v1/resources/{id}
- **List/Search**: GET /api/v1/resources?filter=...

---

### Notes

- [Implementation note 1]
- [Known limitation or caveat]
- [Deprecation warning if applicable]
- [Future enhancement planned]
