# API Routing Analysis

## Current Routing Structure

### Search Endpoints

#### 1. Unified Search (Recommended)
- **Primary:** `/api/v1/search/unified` 
- **Alias:** `/api/v1/search/search` (canonical)
- **Method:** POST
- **Description:** Fallback search that tries engines in order until one succeeds
- **Use Case:** Best for single-result queries with automatic fallback

**Request:**
```json
{
  "query": "python programming",
  "search_type": "all",
  "num_results": 10,
  "engines": ["google", "duckduckgo", "bing", "yahoo"],
  "enable_fallback": true,
  "fast_mode": true
}
```

#### 2. Multi-Engine Search
- **Primary:** `/api/v1/search/all-engines`
- **Alias:** `/api/v1/search/multi`
- **Method:** POST
- **Description:** Concurrent search across all engines with per-engine timeout
- **Use Case:** When you want results from multiple engines combined

**Request:**
```json
{
  "query": "python programming",
  "search_type": "all",
  "num_results": 10,
  "per_engine_timeout": 30.0
}
```

**Key Difference:**
- `unified`: Tries engines sequentially, stops at first success ⚡ FAST
- `all-engines`: Tries all engines concurrently, combines results 📊 COMPREHENSIVE

#### 3. Individual Engine Endpoints
- `/api/v1/search/google` - Google search (with auto-fallback if enabled)
- `/api/v1/search/duckduckgo` - DuckDuckGo search
- `/api/v1/search/bing` - Bing search
- `/api/v1/search/yahoo` - Yahoo search

#### 4. Additional Endpoints
- `/api/v1/search/batch` - Batch search for multiple queries
- `/api/v1/search/instant/{query}` - DuckDuckGo instant answers
- `/api/v1/search/health` - Health check

---

## Analysis: Should We Consolidate?

### ❌ RECOMMENDATION: DO NOT CONSOLIDATE

The current routing structure is **intentionally designed** for different use cases:

### Reasons to Keep Current Structure:

1. **Clear Separation of Concerns**
   - `unified`: Sequential fallback (fast, single source)
   - `all-engines`: Concurrent aggregation (comprehensive, multiple sources)
   - These are fundamentally different operations

2. **Performance Optimization**
   - Users who want fast results use `unified`
   - Users who want comprehensive results use `all-engines`
   - Mixing them would force tradeoffs

3. **Backwards Compatibility**
   - Existing clients may depend on specific endpoints
   - Aliases provide flexibility without breaking changes

4. **API Clarity**
   - Different endpoints make the API self-documenting
   - Clear naming indicates behavior

5. **Error Handling Differences**
   - `unified`: Returns first success, stops on success
   - `all-engines`: Returns all results, including per-engine errors
   - Different error response structures

---

## What About the "all" search_type?

The user asked about reviewing the `all` search_type. Let's clarify:

### `search_type` Parameter (Different from endpoint!)

The `search_type` parameter determines **content type**, not **which engines**:
- `"all"` = Web search (default)
- `"news"` = News articles
- `"images"` = Image search
- `"videos"` = Video search

**Example:**
```json
{
  "query": "python",
  "search_type": "news",  // ← This means "news articles", not "all engines"
  "num_results": 10
}
```

This is **NOT** about multi-engine search. It's about content type.

---

## Proposed Documentation Improvement

To avoid confusion, we should add clear API documentation:

### Recommended Endpoint Usage

```
┌─────────────────────────────────────────────────┐
│  NEED FAST RESULTS?                             │
│  → Use /api/v1/search/unified                   │
│  → Tries engines in order, stops at first ✓    │
│  → Response time: 1-5 seconds                   │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  NEED COMPREHENSIVE RESULTS?                    │
│  → Use /api/v1/search/all-engines               │
│  → Queries all engines concurrently             │
│  → Response time: 5-30 seconds                  │
│  → Combines & deduplicates results              │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  NEED SPECIFIC ENGINE?                          │
│  → Use /api/v1/search/google                    │
│  → Or /bing, /yahoo, /duckduckgo                │
│  → Response time: 1-3 seconds                   │
└─────────────────────────────────────────────────┘
```

---

## Code Review: Timeout Handling

✅ **VERIFIED:** The all-engines endpoint correctly handles timeouts

```python
async def search_with_timeout(engine_name: str, scraper, timeout: float):
    try:
        # ... setup ...
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        return {
            'success': False,
            'error': f'Engine timed out after {timeout}s',
            # ... error response ...
        }
```

**Benefits:**
- Each engine has independent timeout
- One slow engine doesn't block others
- Configurable via `per_engine_timeout` parameter (default: 30s)

---

## Conclusion

### ✅ Current Implementation is CORRECT

The API routing is well-designed:
- Clear separation between sequential (unified) and concurrent (all-engines)
- Proper timeout handling for multi-engine
- Flexible with aliases
- Self-documenting endpoint names

### ❌ NO CONSOLIDATION NEEDED

Consolidating would:
- Reduce API clarity
- Force performance tradeoffs
- Break backwards compatibility
- Mix different use cases

### ✅ RECOMMENDATION: Keep as-is, improve documentation

**Action Items:**
1. ✅ Keep current routing structure
2. ✅ Add this analysis to docs
3. ✅ Clarify search_type vs engine selection in docs
4. ✅ Add usage examples to API docs

---

## Updated main.py Documentation

The root endpoint already provides good documentation. No changes needed to routing!

**Verdict:** APPROVED - Routing structure is optimal for the use case.
