# Sequence Diagram Patterns & Template

Reference patterns for Mermaid sequenceDiagram in API documentation.

---

## Pattern 1: Simple CRUD (Create with Validation)

```mermaid
sequenceDiagram
    participant Client
    participant Controller
    participant Service
    participant DB as Repository/DB
    
    Client->>Controller: POST /api/resources
    activate Controller
    
    Note over Controller: Parse & Validate Input
    alt Invalid Input
        Controller-->>Client: 400 InvalidInput
    else Valid
        Controller->>Service: Create(model)
        activate Service
        
        Note over Service: Check Business Rules
        alt Business Rule Violation
            Service-->>Controller: InvalidAction
        else Valid
            Service->>DB: Insert(data)
            activate DB
            DB-->>Service: id
            deactivate DB
            Service-->>Controller: Success
        end
        deactivate Service
        
        Controller->>Controller: Map to Response DTO
        Controller-->>Client: 201 Created + Data
    end
    deactivate Controller
```

---

## Pattern 2: Read with Cache-First Strategy

```mermaid
sequenceDiagram
    participant Client
    participant Controller
    participant Service
    participant Cache as Cache/Redis
    participant DB
    
    Client->>Controller: GET /api/resources/{id}
    activate Controller
    
    Note over Controller: Extract ID Parameter
    Controller->>Service: GetById(id)
    activate Service
    
    Service->>Cache: Get(key)
    alt Cache Hit
        Cache-->>Service: Return cached data
        Note over Service: Data found in cache
    else Cache Miss
        Service->>DB: Query(id)
        activate DB
        alt Record Not Found
            DB-->>Service: null
            deactivate DB
            Service-->>Controller: ResourceNotFound
            Controller-->>Client: 404 Not Found
        else Found
            DB-->>Service: data
            deactivate DB
            Service->>Cache: Set(key, data, ttl)
            Note over Cache: Store for future requests
        end
    end
    
    Service-->>Controller: Return data
    deactivate Service
    
    Controller->>Controller: Map to Response DTO
    Controller-->>Client: 200 OK + Data
    deactivate Controller
```

---

## Pattern 3: Update with Cache Invalidation

```mermaid
sequenceDiagram
    participant Client
    participant Controller
    participant Service
    participant DB
    participant Cache
    
    Client->>Controller: PUT /api/resources/{id}
    activate Controller
    
    Note over Controller: Validate Input
    alt Invalid
        Controller-->>Client: 400 InvalidInput
    else Valid
        Controller->>Service: Update(id, model)
        activate Service
        
        Service->>DB: CheckExists(id)
        activate DB
        alt Not Found
            DB-->>Service: null
            Service-->>Controller: ResourceNotFound
        else Exists
            DB->>DB: Update(data)
            DB-->>Service: Success
            deactivate DB
            
            Service->>Cache: Delete(key)
            Note over Cache: Invalidate old cache
            
            Service-->>Controller: Success
        end
        deactivate Service
        
        Controller-->>Client: 200 OK + Updated Data
    end
    deactivate Controller
```

---

## Pattern 4: Search/Filter with Pagination

```mermaid
sequenceDiagram
    participant Client
    participant Controller
    participant Service
    participant DB
    
    Client->>Controller: GET /api/resources?filter=...&page=1&limit=20
    activate Controller
    
    Note over Controller: Parse Query Parameters
    Controller->>Service: Search(filter, pageInfo)
    activate Service
    
    Note over Service: Validate Filter Criteria
    alt Invalid Criteria
        Service-->>Controller: InvalidInput
    else Valid
        Service->>DB: QueryWithPagination(filter, page, limit)
        activate DB
        DB->>DB: Execute Query + Count Total
        DB-->>Service: {items[], totalCount}
        deactivate DB
        
        Note over Service: Map DTOs & Calculate PageInfo
        Service-->>Controller: Success + PagedResult
    end
    deactivate Service
    
    Controller-->>Client: 200 OK + Items + Pagination Metadata
    deactivate Controller
```

---

## Pattern 5: Complex Operation with External Service Call

```mermaid
sequenceDiagram
    participant Client
    participant Controller
    participant Service
    participant Cache
    participant DB
    participant External as External API
    
    Client->>Controller: POST /api/process
    activate Controller
    
    Controller->>Service: Process(request)
    activate Service
    
    Service->>Cache: CheckCachedResult(requestHash)
    alt Cached
        Cache-->>Service: Return cached result
    else Cache Miss
        Service->>DB: LoadRelatedData()
        activate DB
        DB-->>Service: data
        deactivate DB
        
        Note over Service: Prepare Payload
        Service->>External: CallAPI(payload)
        activate External
        
        alt External Error
            External-->>Service: Error
            Service-->>Controller: ResetContent
        else Success
            External-->>Service: Result
            deactivate External
            
            Service->>DB: SaveResult(data)
            activate DB
            DB-->>Service: Success
            deactivate DB
            
            Service->>Cache: Set(result, ttl)
        end
    end
    
    Service-->>Controller: Return result
    deactivate Service
    
    Controller-->>Client: 200 OK + Response
    deactivate Controller
```

---

## Pattern 6: Batch Operation with Partial Success

```mermaid
sequenceDiagram
    participant Client
    participant Controller
    participant Service
    participant DB
    
    Client->>Controller: POST /api/batch-process
    activate Controller
    
    Note over Controller: Validate Batch Array (Max 100 items)
    alt Exceeds Max
        Controller-->>Client: 400 InvalidInput
    else Valid Count
        Controller->>Service: BatchProcess(items)
        activate Service
        
        Note over Service: Initialize Result Tracking
        loop For Each Item
            Service->>DB: ProcessItem(item)
            activate DB
            alt Success
                DB-->>Service: Success
            else Failure
                DB-->>Service: Error
            end
            deactivate DB
            Service->>Service: Track Result + Error
        end
        
        Note over Service: Aggregate Results
        Service-->>Controller: {successCount, failureCount, errors[]}
        deactivate Service
        
        alt All Failed
            Controller-->>Client: 400 InvalidInput + Error Details
        else Mixed Results
            Controller-->>Client: 207 Multi-Status + Partial Results
        else All Succeeded
            Controller-->>Client: 200 OK + Results
        end
    end
    deactivate Controller
```

---

## Pattern 7: Async Processing with Callback

```mermaid
sequenceDiagram
    participant Client
    participant Controller
    participant Service
    participant JobQueue as Job Queue
    participant Worker
    participant DB
    
    Client->>Controller: POST /api/long-operation
    activate Controller
    
    Controller->>Service: StartAsyncJob(request)
    activate Service
    
    Note over Service: Create Job Record
    Service->>DB: InsertJob(status: pending)
    activate DB
    DB-->>Service: jobId
    deactivate DB
    
    Note over Service: Enqueue for Processing
    Service->>JobQueue: Enqueue(jobId, params)
    
    Service-->>Controller: Return jobId (Accepted)
    deactivate Service
    
    Note over Controller: Return 202 Accepted
    Controller-->>Client: 202 + jobId
    deactivate Controller
    
    Note over JobQueue: Process Asynchronously
    Worker->>JobQueue: Dequeue()
    JobQueue-->>Worker: jobId, params
    activate Worker
    
    Note over Worker: Execute Long-Running Task
    Worker->>DB: UpdateJob(status: processing)
    
    Note over Worker: Perform Work...
    
    alt Success
        Worker->>DB: UpdateJob(status: completed, result)
    else Error
        Worker->>DB: UpdateJob(status: failed, errorMsg)
    end
    deactivate Worker
    
    Note over Client: Poll for Status
    Client->>Controller: GET /api/job/{jobId}
    Controller->>Service: GetJobStatus(jobId)
    Service->>DB: Query(jobId)
    DB-->>Service: Job Record
    Service-->>Controller: Status + Result
    Controller-->>Client: 200 OK + Status
```

---

## Common Elements to Include

### Activation Boxes
- Start with `activate [Actor]`
- End with `deactivate [Actor]`
- Shows when component is active/processing

### Notes
```
Note over Component: Description of what's happening
```

### Alternatives (Decision branching)
```
alt Condition 1
    [Happy Path]
else Condition 2
    [Alternative Path]
else
    [Fallback Path]
end
```

### Loops
```
loop For Each Item
    [Repeated Action]
end
```

### Parallel Operations
```
par Task 1
    [Action 1]
and Task 2
    [Action 2]
end
```

### Break (Exit sequence)
```
break When Condition True
    [Terminating Action]
    Note over: Stop here
end
```

---

## Best Practices

1. **Keep diagrams focused**: One flow per diagram (happy path, error path separate)
2. **Show all actors**: Client, API, Service, Cache, DB, External systems
3. **Include validation gates**: Use alt/else to show rejection paths
4. **Label transitions**: Use descriptive method names and parameters
5. **Add notes**: Explain non-obvious processing steps
6. **Represent errors**: Show error responses and fallback behaviors
7. **Show caching patterns**: explicit Get/Set operations to Cache
8. **Order by dependency**: Left to right typically follows data flow
9. **Keep timing implicit**: Mermaid adds time progression automatically

---

## Mermaid Reference

For more details, see: [Mermaid Sequence Diagram Docs](https://mermaid.js.org/syntax/sequenceDiagram.html)
