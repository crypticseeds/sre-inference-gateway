# OpenAI provider

`OpenAIAdapter` implements the `BaseProvider` completion, stream-establishment,
and health-check contracts with one shared `httpx.AsyncClient`.

## Configuration

```yaml
providers:
  - name: openai
    type: openai
    enabled: false
    weight: 0.5
    base_url: https://api.openai.com/v1
    api_key_env: OPENAI_API_KEY
    timeout: 30.0
    max_retries: 3
```

The factory reads the environment variable named by `api_key_env`. Construction
fails if the variable is absent, and registry initialization continues with
other enabled providers.

## Behavior

- Non-streaming requests use the OpenAI chat completions endpoint and convert a
  successful JSON response to `ChatCompletionResponse`.
- Streaming requests send `Accept-Encoding: identity`, establish an `httpx`
  streamed response, and return its byte iterator to the shared SSE passthrough.
- Streaming request mapping includes both token-limit names and `stream_options`
  when set. Non-streaming mapping includes both token-limit names but currently
  omits `stream_options`.
- The adapter has provider-local retry and status mapping in addition to the
  outer resilience wrapper.
- `close()` releases the shared HTTP client.

The checked-in provider is disabled by default. Enable it in `config.yaml`, set
its credential environment variable, and restart the gateway.

## Limitations

- Error bodies are not byte-faithful upstream passthroughs.
- Provider enablement does not hot-reload into the registry.
- Circuit-breaker accounting covers stream establishment only.
- This repository contains mocked adapter tests, not live OpenAI service tests or
  provider latency benchmarks.
