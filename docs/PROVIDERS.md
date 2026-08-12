# Providers

## Interface

`BaseProvider` wraps three protected adapter methods:

- `_chat_completion_impl()` returns a complete `ChatCompletionResponse`.
- `_chat_completion_stream_impl()` establishes a stream and returns an async
  byte iterator.
- `_health_check_impl()` returns `ProviderHealth`.

The public methods run those operations through the shared resilience layer.

## Implementations

| Config type | Class | Purpose |
| --- | --- | --- |
| `openai` | `OpenAIAdapter` | OpenAI Chat Completions over `httpx`. Requires the configured API-key environment variable. |
| `vllm` | `VLLMAdapter` | OpenAI-compatible vLLM endpoint over `httpx`. |
| `mock` with `openai` in its name | `MockOpenAIAdapter` | No-network JSON and SSE responses. |
| `mock` with `vllm` in its name | `MockVLLMAdapter` | No-network JSON and SSE responses. |

Other mock names default to `MockOpenAIAdapter`.

Real adapters contain provider-specific request mapping, status handling, and
retry behavior. The outer resilience policy can add retries around them, though
checked-in `config.yaml` sets one outer attempt.

## Factory and registry

`ProviderFactory.create_provider(ProviderConfig)` dispatches on the lowercase
`type`. `ProviderRegistry.initialize_from_config()` closes existing providers,
clears the registry, skips disabled entries, and continues if one provider cannot
be constructed. Registered providers are available through `get_provider()`,
`list_providers()`, and `get_all_providers()`.

The global registry is initialized during FastAPI startup. Configuration file
watching does not rebuild it, so provider enablement changes require a restart.

## Routing

`RequestRouter` receives a provider-name-to-weight mapping. It prefers a valid
`X-Provider-Priority` provider, otherwise performs circuit-aware weighted
selection. See [ARCHITECTURE.md](ARCHITECTURE.md#routing-and-failover).

## Streaming limitation

Circuit breakers account for stream establishment, not eventual completion.
See [design-decisions.md](design-decisions.md#circuit-breaker-and-streams).
