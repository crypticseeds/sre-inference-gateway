# Manual testing

Configure Doppler once, then run the gateway directly:

```bash
doppler setup --project sre-inference-gateway --config dev_personal
doppler run -- uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Import `postman_collection.json` into Postman. Run **Health & status**, **Chat
(mock, no keys)**, and **Observability** first. To test a real provider, change
only that provider's `enabled` value to `true`, restart the gateway, and run its
requests in **Chat (real providers, pinned)**. For RunPod, also replace
`REPLACE_POD_ID` with the pod ID. The collection rejects a 200 response that
contains the mock fallback marker. Restore the checked-in mock-only configuration
afterward:

```bash
git checkout -- config.yaml
```

## How to be certain the response is real

Every successful completion response includes `X-Served-By` with the provider
that actually served it. For verification and debugging, send
`X-No-Failover: 1` (case-insensitive `true` is also accepted) so the first
selected provider's error is returned as-is; production clients should leave
failover on. This makes upstream failures visible rather than allowing a mock to
mask them, such as OpenRouter returning 401 for a placeholder key or Moonshot
returning 429 for insufficient balance.

Run **Failover drill** only after setting `FAILOVER_DRILL_ADMIN=1`. This
non-secret flag may be Doppler-managed or supplied as an inline prefix, for
example `FAILOVER_DRILL_ADMIN=1 doppler run -- uv run uvicorn ...`.
