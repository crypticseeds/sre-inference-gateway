# Public completion models

The HTTP endpoint validates requests with `app.models.requests.ChatCompletionRequest`.
Provider adapters use separate internal models from `app.providers.base`.

## Request

Required fields:

- `model`: string. No nonempty-string validator is implemented.
- `messages`: nonempty list of messages. Each message requires string `role` and
  `content`; `name` is optional. Allowed roles are `system`, `user`, `assistant`,
  `function`, and `tool`.

Optional fields and enforced ranges:

| Field | Default | Constraint |
| --- | --- | --- |
| `temperature` | `1.0` | 0 through 2 |
| `max_tokens` | `null` | Positive integer when present |
| `max_completion_tokens` | `null` | Positive integer when present |
| `top_p` | `1.0` | 0 through 1 |
| `frequency_penalty` | `0.0` | -2 through 2 |
| `presence_penalty` | `0.0` | -2 through 2 |
| `stream` | `false` | Boolean |
| `stream_options` | `null` | String-to-boolean object when present |
| `user` | `null` | String when present |

`stream: false` returns `ChatCompletionResponse`. `stream: true` returns provider
SSE bytes and bypasses the non-streaming response model.

## Non-streaming response

`ChatCompletionResponse` requires `id`, `model`, `choices`, and `usage`. It
defaults `object` to `chat.completion` and `created` to the current Unix time.
The model provides field types but does not enforce an ID prefix, nonempty
choices, timestamp validity, or nonnegative token counts.
