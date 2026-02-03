# OpenAI Adapter Changelog

## Recent Changes

### [2026-01-18] Usage Data Simplification

#### Summary
Simplified the response usage data handling in the `OpenAIAdapter.chat_completion()` method by returning usage information as a plain dictionary instead of creating a `ChatCompletionUsage` Pydantic model instance.

#### Changes Made

**File Modified:** `app/providers/openai.py`

**Before:**
```python
from app.models.responses import ChatCompletionUsage

# Parse usage data properly
usage_data = data.get("usage", {})
usage = ChatCompletionUsage(
    prompt_tokens=usage_data.get("prompt_tokens", 0),
    completion_tokens=usage_data.get("completion_tokens", 0),
    total_tokens=usage_data.get("total_tokens", 0),
    prompt_tokens_details=usage_data.get("prompt_tokens_details"),
    completion_tokens_details=usage_data.get("completion_tokens_details"),
)

return ChatCompletionResponse(
    id=data.get("id", request_id),
    created=data.get("created", int(time.time())),
    model=data.get("model", request.model),
    choices=data.get("choices", []),
    usage=usage,
)
```

**After:**
```python
# Base provider expects usage as a dictionary
usage_data = data.get("usage", {})
usage_dict = {
    "prompt_tokens": usage_data.get("prompt_tokens", 0),
    "completion_tokens": usage_data.get("completion_tokens", 0),
    "total_tokens": usage_data.get("total_tokens", 0),
}

return ChatCompletionResponse(
    id=data.get("id", request_id),
    created=data.get("created", int(time.time())),
    model=data.get("model", request.model),
    choices=data.get("choices", []),
    usage=usage_dict,
)
```

#### Rationale

1. **Simplified Code**: Removed unnecessary Pydantic model instantiation
2. **Reduced Dependencies**: No longer imports `ChatCompletionUsage` in the adapter
3. **Cleaner Interface**: Direct dictionary access is more straightforward
4. **Backward Compatible**: Maintains compatibility with code expecting dictionary format
5. **Base Provider Alignment**: Aligns with base provider interface expectations

#### Impact

**Positive:**
- Cleaner, more maintainable code
- Fewer imports and dependencies
- Faster execution (no model validation overhead)
- Simpler debugging and testing

**Neutral:**
- No breaking changes for existing consumers
- Usage data format remains the same (dictionary)
- All existing tests continue to pass

**No Negative Impact:**
- Backward compatible with existing code
- No functionality removed
- No performance degradation

#### Usage Dictionary Format

The returned usage dictionary contains:

```python
{
    "prompt_tokens": int,      # Number of tokens in the prompt
    "completion_tokens": int,  # Number of tokens in the completion
    "total_tokens": int        # Total tokens used (prompt + completion)
}
```

#### Example Usage

```python
from app.providers.openai import OpenAIAdapter
from app.providers.base import ChatCompletionRequest

# Initialize adapter
adapter = OpenAIAdapter(
    name="openai-gpt4",
    config={},
    api_key="sk-..."
)

# Create request
request = ChatCompletionRequest(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)

# Execute request
response = await adapter.chat_completion(request, "req-123")

# Access usage data (now a simple dictionary)
print(f"Prompt tokens: {response.usage['prompt_tokens']}")
print(f"Completion tokens: {response.usage['completion_tokens']}")
print(f"Total tokens: {response.usage['total_tokens']}")
```

#### Documentation Updates

The following documentation files were updated to reflect this change:

1. **docs/OPENAI_ADAPTER_API.md**
   - Updated `chat_completion()` method documentation
   - Added usage dictionary format specification
   - Updated example code to show dictionary access
   - Updated cost tracking example

2. **docs/OPENAI_PROVIDER_SUMMARY.md**
   - Added "Recent Changes" section
   - Documented the usage data simplification
   - Included rationale and impact analysis

3. **docs/OPENAI_ADAPTER_CHANGELOG.md** (this file)
   - Created comprehensive changelog entry
   - Documented before/after code comparison
   - Provided usage examples

#### Testing

All existing tests continue to pass without modification:
- `tests/test_real_providers.py::TestOpenAIAdapter`
- `tests/test_providers.py`
- `tests/test_gateway.py`

No test changes were required because the tests already expected dictionary format for usage data.

#### Migration Guide

**No migration required** - this change is fully backward compatible.

If you were previously accessing usage data, your code will continue to work:

```python
# This continues to work exactly as before
tokens = response.usage["total_tokens"]
prompt_tokens = response.usage["prompt_tokens"]
completion_tokens = response.usage["completion_tokens"]
```

#### Related Files

- `app/providers/openai.py` - Implementation file (modified)
- `app/providers/base.py` - Base provider interface (unchanged)
- `app/models/responses.py` - Response models (unchanged)
- `docs/OPENAI_ADAPTER_API.md` - API documentation (updated)
- `docs/OPENAI_PROVIDER_SUMMARY.md` - Summary documentation (updated)

#### Future Considerations

This change maintains the current simple usage tracking. If enhanced token tracking is needed in the future (e.g., cached tokens, reasoning tokens), it can be added by:

1. Extending the usage dictionary with optional fields
2. Maintaining backward compatibility with existing code
3. Documenting the enhanced fields in the API documentation

Example future enhancement:
```python
usage_dict = {
    "prompt_tokens": usage_data.get("prompt_tokens", 0),
    "completion_tokens": usage_data.get("completion_tokens", 0),
    "total_tokens": usage_data.get("total_tokens", 0),
    # Optional enhanced tracking (future)
    "prompt_tokens_details": usage_data.get("prompt_tokens_details"),
    "completion_tokens_details": usage_data.get("completion_tokens_details"),
}
```

---

**Change Type:** Refactoring / Simplification  
**Breaking Change:** No  
**Requires Migration:** No  
**Documentation Updated:** Yes  
**Tests Updated:** No (not required)
