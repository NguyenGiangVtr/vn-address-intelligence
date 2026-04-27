# API Documentation Generator Skill

Professional API documentation generation from C# source code.

## Quick Start

### Using the Skill

In VS Code Chat, invoke with:

```
/api-documentation-generator

Analyze these files:
- Controllers/YourController.cs
- Services/YourService.cs
- DTO files: Request/Response models

Task: Generate complete API specification with endpoint details, request/response schemas, error codes, and Mermaid sequence diagrams
```

### File Structure

```
.github/skills/api-documentation-generator/
├── SKILL.md                           # Main skill definition (procedures, templates)
├── README.md                          # This file
└── templates/                         # Reference templates and patterns
    ├── endpoint-template.md           # Single endpoint documentation template
    ├── sequence-diagram-patterns.md   # Reusable Mermaid diagram patterns
    └── error-codes-reference.md       # Standard error codes & HTTP mapping
```

## What This Skill Does

Generates professional, standardized API documentation by analyzing C# Controllers, Services, and DTOs.

**Input**: File paths to C# source files
**Output**: Markdown document with:
- Complete API specification (endpoints, auth, requests, responses, errors)
- Mermaid sequence diagrams showing data flow and logic patterns
- Operational notes (dependencies, caching, performance)
- Error handling reference

## Documentation Format

### Section 1: API Specification
For **each endpoint**:
- HTTP verb and route path
- Authentication & authorization requirements  
- Request parameters (table with type, required, validation)
- Response structure (success + error codes)
- Error scenarios (400, 401, 403, 404, 409, 500, 503)

### Section 2: Logic Flows
For **each major flow**:
- Mermaid sequence diagram
- All actors (Client, Controller, Service, Cache, DB, External)
- Validation gates and error branches
- Cache interactions and database operations
- Response mapping

### Section 3: Operational Notes
- **Dependencies**: Redis cache keys/TTL, database tables/procedures, third-party APIs
- **Performance**: Async patterns, batch sizes, caching strategies
- **Concurrency**: Thread-safety, rate limiting, edge cases

## Key Patterns Included

1. **Create with Validation** → InvalidInput, InvalidAction errors
2. **Get with Cache** → Cache-first, DB fallback pattern
3. **Update with Invalidation** → Trigger cache refresh
4. **Search/Filter with Pagination** → Query optimization
5. **External Service Call** → Timeout, retry, error handling
6. **Batch Operations** → Partial success (207), error aggregation
7. **Async Processing** → Job queue, polling, callback pattern

## Templates Reference

| Template | Purpose | When to Use |
|----------|---------|------------|
| `endpoint-template.md` | Single endpoint documentation | Document one endpoint; copy-paste for consistency |
| `sequence-diagram-patterns.md` | Mermaid diagram patterns | Build flow diagrams for endpoints |
| `error-codes-reference.md` | Error code mapping & meanings | Standardize error documentation across API |

## Checklist: Quality Assurance

Before finalizing documentation, verify:

- [ ] ✅ All endpoints documented (GET, POST, PUT, DELETE, PATCH)
- [ ] ✅ Authorization extracted from [Authorize] attributes
- [ ] ✅ Request parameters match controller method signature
- [ ] ✅ Response models match actual DTO structures  
- [ ] ✅ Error codes traced from service implementation (try/catch blocks)
- [ ] ✅ All external dependencies identified (Cache, DB, APIs)
- [ ] ✅ Sequence diagram covers happy path + error branches
- [ ] ✅ JSON examples validated and realistic
- [ ] ✅ Tables formatted consistently with | separators
- [ ] ✅ No placeholder or TODO sections remain
- [ ] ✅ Markdown renders without syntax errors

## Example Workflow

### Step 1: Code Analysis
```csharp
// PromotionComboController.cs
[Authorize(Roles = "Admin")]
[HttpPost("api/v1/promotions/combo/apply")]
public async Task<IActionResult> ApplyComboForOrder(
    [FromBody] ApplyComboForOrderReq request)
{
    var result = await _service.ApplyComboForOrder(request);
    return Ok(result);
}
```

### Step 2: Extract Info
- **Endpoint**: POST /api/v1/promotions/combo/apply
- **Auth**: JWT + Admin role
- **Request**: ApplyComboForOrderReq (from DTO file)
- **Response**: CRUDResult<ApplyComboForOrderRes>
- **Errors**: InvalidInput (400), Unauthorized (401), InvalidAction (409)

### Step 3: Generate Documentation
```markdown
## Endpoint: POST /api/v1/promotions/combo/apply

| Property | Value |
|----------|-------|
| **HTTP Method** | POST |
| **Route** | /api/v1/promotions/combo/apply |
| **Summary** | Apply promotion combos to customer order |
| **Auth Type** | JWT |
| **Required Roles** | Admin |

### Request
...
```

### Step 4: Create Sequence Diagram
```mermaid
sequenceDiagram
    participant Client
    participant Controller
    participant Service
    participant Cache
    participant DB
    
    Client->>Controller: POST /api/v1/promotions/combo/apply
    ...
```

## Best Practices

### Documentation
- ✅ Use **clear, concise** field descriptions
- ✅ Include **JSON examples** that are complete and valid
- ✅ Document **all error scenarios** explicitly
- ✅ Add **notes** for non-obvious business logic

### Diagrams
- ✅ Keep **one diagram per major flow** (separate happy path from errors)
- ✅ Show **all actors** (Client, API, Service, Cache, DB, External)
- ✅ Include **validation gates** (alt/else for rejection paths)
- ✅ Use **clear labels** on transitions (method names + params)

### Error Handling
- ✅ Map **exception types** to `CRUDStatusCodeRes` codes
- ✅ Document **business rule violations** (InvalidAction)
- ✅ Include **dependency failures** (ResetContent)
- ✅ Explain **retry policies** for each error code

## Integration with Development

1. **Code Review**: Share generated docs with PR reviewers for verification
2. **Postman/Swagger**: Can be converted to OpenAPI spec format
3. **Client Onboarding**: Provide generated docs to integration partners
4. **Internal Wiki**: Archive docs in project knowledge base
5. **Version Control**: Commit generated docs to git with code changes

## Troubleshooting

### Issue: "Cannot find endpoint definition"
**Solution**: Verify controller file includes [HttpGet/Post/Put/Delete] attributes

### Issue: "Missing request/response schema"
**Solution**: Ensure DTO classes are properly documented with DataAnnotations

### Issue: "Sequence diagram unclear"
**Solution**: Break into separate diagrams (happy path → success, error path → failures, cache scenarios separate)

### Issue: "Error codes incomplete"
**Solution**: Trace through service try/catch blocks to catch all possible exceptions

## Related Skills

- **Code Analysis**: Understand C# projects structure  
- **Technical Writing**: API documentation best practices
- **Mermaid Diagrams**: Advanced visualization patterns

## Support & Feedback

For issues or improvements:
1. Update templates with new patterns
2. Expand error-codes-reference as new codes are discovered
3. Share documentation examples with team
