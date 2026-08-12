# Provider factory

`ProviderFactory.create_provider(config)` creates one adapter from a validated
`ProviderConfig`:

- `openai` creates `OpenAIAdapter` and requires the configured API-key
  environment variable.
- `vllm` creates `VLLMAdapter`.
- `mock` creates `MockOpenAIAdapter` or `MockVLLMAdapter` based on the provider
  name; other names default to the OpenAI mock.
- Any other type raises `ValueError`.

The factory passes timeout, retry, URL, model, and mock streaming settings from
the Pydantic model into the adapter configuration. `ProviderConfig` validates
numeric bounds but does not validate URL safety or connectivity.

The factory does not cache instances. The application-level `ProviderRegistry`
creates enabled providers at startup and retains them. Factory latency, memory
use, and thread-safety are not benchmarked in this repository.
