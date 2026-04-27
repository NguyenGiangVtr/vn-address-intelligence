# Standard Error Codes Reference

Common error codes used across the CoC.API.SCA project for standardized API responses.

---

## HTTP Status Code Mapping

| HTTP | Error Code | Use Case | Meaning |
|------|-----------|----------|---------|
| 200 | `Success` | Request succeeded, resource returned | GET, PUT successful |
| 201 | `Success` | New resource created | POST successful with new resource |
| 204 | `Success` | Request succeeded, no content | DELETE successful |
| 400 | `InvalidInput` | Client error in request format/validation | Malformed JSON, missing required field |
| 401 | `Unauthorized` | Missing/invalid authentication | No JWT token or expired token |
| 403 | `Forbidden` | Valid auth but insufficient permissions | User role lacks required access |
| 404 | `ResourceNotFound` | Requested resource doesn't exist | ID not found in database |
| 409 | `InvalidAction` | Business logic conflict/violation | Duplicate entry, state constraint violated |
| 500 | `InternalServerError` | Unhandled server exception | Null reference, parsing error, uncaught exception |
| 503 | `ResetContent` | External dependency unavailable | Redis down, Database unreachable |

---

## CRUDStatusCodeRes Enumeration

### 2xx Success Codes

#### `Success`
- **HTTP Code**: 200, 201
- **When Returned**: Operation completed successfully
- **Response Structure**: `{statusCode: "Success", data: {...}, errorMessage: null}`
- **Examples**:
  - User retrieved successfully
  - Resource created successfully
  - Cache populated successfully

---

### 4xx Client Error Codes

#### `InvalidInput`
- **HTTP Code**: 400 Bad Request
- **When Returned**: Request validation failed or missing required data
- **Causes**:
  - Required field is null or empty
  - String exceeds MaxLength constraint
  - Numeric field outside Min/Max range
  - Enum value invalid
  - JSON deserialization failed
  - Date format invalid
- **Example Response**:
  ```json
  {
    "statusCode": "InvalidInput",
    "data": null,
    "errorMessage": "Field 'name' is required and must be non-empty"
  }
  ```

#### `Unauthorized`
- **HTTP Code**: 401 Unauthorized
- **When Returned**: Authentication failed or missing
- **Causes**:
  - No Authorization header
  - JWT token missing or malformed
  - JWT signature invalid
  - JWT token expired
  - API key invalid or missing
- **Example Response**:
  ```json
  {
    "statusCode": "Unauthorized",
    "data": null,
    "errorMessage": "Authorization header missing or invalid"
  }
  ```

#### `Forbidden`
- **HTTP Code**: 403 Forbidden
- **When Returned**: Authenticated but lacks required permission
- **Causes**:
  - User role doesn't match [Authorize(Roles = "...")] requirement
  - User doesn't have read permission on resource
  - User doesn't have write permission on resource
  - Store/tenant mismatch
- **Example Response**:
  ```json
  {
    "statusCode": "Forbidden",
    "data": null,
    "errorMessage": "User lacks 'Admin' role required for this operation"
  }
  ```

#### `ResourceNotFound`
- **HTTP Code**: 404 Not Found
- **When Returned**: Requested resource doesn't exist
- **Causes**:
  - ID doesn't match any record in database
  - Resource was deleted
  - Resource belongs to different tenant/store
  - Foreign key reference invalid
- **Example Response**:
  ```json
  {
    "statusCode": "ResourceNotFound",
    "data": null,
    "errorMessage": "Product with ID 9999 not found"
  }
  ```

#### `InvalidAction`
- **HTTP Code**: 409 Conflict
- **When Returned**: Business logic rule violation or state conflict
- **Causes**:
  - Duplicate entry (unique constraint)
  - State machine violation (e.g., can't delete confirmed order)
  - Business rule violation (e.g., discount > 100%)
  - Referential integrity violation
  - Concurrent modification conflict
  - Invalid operation for current state
- **Example Response**:
  ```json
  {
    "statusCode": "InvalidAction",
    "data": null,
    "errorMessage": "Product with name 'Coca Cola' already exists in store"
  }
  ```

---

### 5xx Server Error Codes

#### `InternalServerError`
- **HTTP Code**: 500 Internal Server Error
- **When Returned**: Unhandled exception in server code
- **Causes**:
  - Null reference exception
  - Type casting error
  - Uncaught application exception
  - DateTime parsing failure
  - Numeric overflow
  - String manipulation error
- **Appearance**: Typically caught by global error handler
- **Example Response**:
  ```json
  {
    "statusCode": "InternalServerError",
    "data": null,
    "errorMessage": "An unexpected error occurred. Please contact support."
  }
  ```

#### `ResetContent`
- **HTTP Code**: 503 Service Unavailable
- **When Returned**: External dependency failure (non-recoverable in request)
- **Causes**:
  - Redis connection failed
  - Database connection timeout
  - Third-party API timeout/error
  - Network unavailable
  - Service dependency down
- **Pattern**: Used for dependencies that can't be bypassed
- **Example Response**:
  ```json
  {
    "statusCode": "ResetContent",
    "data": null,
    "errorMessage": "Redis cache is not available. Please retry later."
  }
  ```

---

## Exception Mapping Guide

### How Services Map Exceptions to Status Codes

```csharp
try 
{
    // Business logic here
}
catch (ValidationException ex)
{
    return new CRUDResult 
    { 
        StatusCode = CRUDStatusCodeRes.InvalidInput,
        ErrorMessage = ex.Message
    };
}
catch (ResourceNotFoundException ex)
{
    return new CRUDResult 
    { 
        StatusCode = CRUDStatusCodeRes.ResourceNotFound,
        ErrorMessage = ex.Message
    };
}
catch (BusinessRuleException ex)
{
    return new CRUDResult 
    { 
        StatusCode = CRUDStatusCodeRes.InvalidAction,
        ErrorMessage = ex.Message
    };
}
catch (RepositoryException ex) // DB/Cache failure
{
    return new CRUDResult 
    { 
        StatusCode = CRUDStatusCodeRes.ResetContent,
        ErrorMessage = "External dependency failure",
        Data = ex
    };
}
catch (Exception ex)
{
    return new CRUDResult 
    { 
        StatusCode = CRUDStatusCodeRes.InternalServerError,
        ErrorMessage = "An unexpected error occurred"
    };
}
```

---

## Error Code Decision Tree

Choose the appropriate error code based on the condition:

```
Does the request have correct format and all required fields?
├─ No → InvalidInput (400)
└─ Yes → Is the user authenticated?
         ├─ No → Unauthorized (401)
         └─ Yes → Does the user have required role/permission?
                  ├─ No → Forbidden (403)
                  └─ Yes → Does the resource exist?
                           ├─ No → ResourceNotFound (404)
                           └─ Yes → Do business rules allow this operation?
                                    ├─ No → InvalidAction (409)
                                    └─ Yes → Did an external dependency fail?
                                             ├─ Yes → ResetContent (503)
                                             └─ No → Success (200/201) or InternalServerError (500)
```

---

## Validation Rules & Error Messages

### Best Practices for Error Messages

1. **Be Specific**: "Field 'email' is invalid format" → better than "Invalid input"
2. **Name the Field**: Include the problematic field name
3. **Suggest Fix**: "Maximum length is 256 characters" → more helpful than "Input too long"
4. **Avoid Sensitive Data**: Don't expose database structure or internal logic
5. **Keep Concise**: 1-2 sentences max

### Common Validation Errors

```
// Required field missing
"Field '{FieldName}' is required"

// String length violation
"Field '{FieldName}' must not exceed {MaxLength} characters"

// Numeric range violation
"Field '{FieldName}' must be between {Min} and {Max}"

// Format/pattern violation
"Field '{FieldName}' has invalid format. Expected: {Pattern}"

// Enum violation
"Field '{FieldName}' must be one of: {Value1}, {Value2}..."

// Date format
"Field '{FieldName}' must be valid ISO 8601 datetime in UTC"

// Constraint violation (server-side logic)
"{ResourceName} with name '{Value}' already exists"

// State constraint
"Cannot {Action} {ResourceName} in '{CurrentState}' state. Must be in: {RequiredStates}"
```

---

## Content Type & Response Headers

### Request Headers (Expected)
```
Content-Type: application/json
Authentication: Bearer {JWT_TOKEN}
X-Request-ID: {UUID} (optional, for tracking)
```

### Response Headers (Provided)
```
Content-Type: application/json; charset=utf-8
Cache-Control: [public|private], max-age={seconds}
X-Request-ID: {UUID} (echo request ID for tracing)
Vary: Accept-Encoding
```

---

## Retry Policies by Error Code

| Code | HTTP | Retriable? | Strategy | Delay |
|------|------|-----------|----------|-------|
| Success | 2xx | N/A | No retry needed | — |
| InvalidInput | 400 | No | Fix request and retry | — |
| Unauthorized | 401 | Maybe | Refresh token and retry once | 1x |
| Forbidden | 403 | No | User/role issue; don't retry | — |
| ResourceNotFound | 404 | No | Resource doesn't exist | — |
| InvalidAction | 409 | Maybe | Brief wait, limited retries | 1-5 seconds |
| InternalServerError | 500 | Yes | Exponential backoff | 1s, 2s, 4s, 8s |
| ResetContent | 503 | Yes | Exponential backoff | 5s, 10s, 20s |

---

## Testing Error Codes

When testing endpoints, verify:

1. ✅ Success path returns `Success` with correct data
2. ✅ Missing required field returns `InvalidInput` with field name
3. ✅ Invalid value type returns `InvalidInput`
4. ✅ No auth header returns `Unauthorized`
5. ✅ Expired JWT returns `Unauthorized`
6. ✅ Invalid role returns `Forbidden`
7. ✅ Non-existent ID returns `ResourceNotFound`
8. ✅ Duplicate entry returns `InvalidAction`
9. ✅ Database down returns `ResetContent`
10. ✅ Unhandled exception return `InternalServerError` (without details)

---

## References

- [HTTP Status Code Meanings](https://httpwg.org/specs/rfc9110.html#status.codes)
- [RFC 7231 HTTP Semantics](https://tools.ietf.org/html/rfc7231#section-6)
- [Microsoft REST Guidelines](https://restfulapi.net/http-status-codes/)
