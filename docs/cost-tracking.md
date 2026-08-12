# Cost tracking

The gateway exports Prometheus counters for provider-reported usage on successful
chat completions:

- `gateway_tokens_total{provider,model,type="prompt|completion"}`
- `gateway_cost_usd_total{provider,model}`
- `gateway_unpriced_requests_total{provider,model,reason}`

Cost accounting is server-usage-only. The gateway never estimates tokens and
never tokenizes request or response text. Non-streaming usage comes from
`response.usage`. Streaming usage is read from the final usage SSE event after
the stream ends. If the provider does not report valid usage, no token or cost
value is invented and the request is counted as unpriced.

Pricing is configured by model in USD per million tokens:

```yaml
pricing:
  mock-model:
    input_per_1m: 0.15
    output_per_1m: 0.60
```

The unpriced reasons are `missing_usage`, `invalid_usage`, and
`missing_pricing`. Valid provider usage still increments token counters when a
model has no configured price, but the cost counter does not move.
