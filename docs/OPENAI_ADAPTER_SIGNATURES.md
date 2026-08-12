# OpenAI adapter interface

Current public lifecycle methods inherited or implemented by `OpenAIAdapter`:

```python
class OpenAIAdapter:
    async def chat_completion(
        self,
        request: ChatCompletionRequest,
        request_id: str,
    ) -> ChatCompletionResponse: ...

    async def chat_completion_stream(
        self,
        request: ChatCompletionRequest,
        request_id: str,
    ) -> AsyncIterator[bytes]: ...

    async def health_check(self) -> ProviderHealth: ...

    async def close(self) -> None: ...
```

The public completion and health methods are resilience-wrapped by
`BaseProvider`. The adapter implements `_chat_completion_impl()`,
`_chat_completion_stream_impl()`, and `_health_check_impl()`.

The internal provider request model carries `model`, `messages`, `temperature`,
`max_tokens`, `max_completion_tokens`, `top_p`, `frequency_penalty`,
`presence_penalty`, `stream`, `stream_options`, and `user`.

See [OPENAI_PROVIDER_SUMMARY.md](OPENAI_PROVIDER_SUMMARY.md) for behavior and
[streaming.md](streaming.md) for the streaming contract.
