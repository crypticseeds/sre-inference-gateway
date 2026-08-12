# Resilience configuration

`config.yaml` supplies one `ResilienceConfig` shared by provider operations.

## Circuit breaker

| Field | Model default | Checked-in value | Effect |
| --- | --- | --- | --- |
| `failure_threshold` | `5` | `2` | Consecutive failures required to OPEN the circuit. |
| `recovery_timeout` | `60.0` | `5.0` | Seconds before an OPEN circuit may admit one HALF_OPEN probe. |
| `expected_exception` | `Exception` | `Exception` | Parsed but not consulted by the current breaker implementation. |

The breaker counts any exception escaping the retry wrapper. A CLOSED success
resets the failure count. A HALF_OPEN success closes the circuit; failure reopens
it. Only one concurrent HALF_OPEN probe is admitted.

## Retry

| Field | Model default | Checked-in value | Effect |
| --- | --- | --- | --- |
| `max_attempts` | `3` | `1` | Total outer attempts, including the first call. |
| `min_wait` | `1.0` | `1.0` | Minimum Tenacity exponential wait. |
| `max_wait` | `10.0` | `10.0` | Maximum Tenacity exponential wait. |
| `exponential_base` | `2.0` | `2.0` | Passed as the `wait_exponential` multiplier when `jitter` is true. |
| `jitter` | `true` | `true` | Selects Tenacity `wait_exponential`; no random jitter is added. |

HTTP 5xx, connection errors, timeouts, and `RetryableException` are retryable.
HTTP 4xx, `ValueError`, `TypeError`, `NonRetryableException`, and unknown
exceptions are not. Provider adapters also contain local retry behavior, so
raising the outer attempts can multiply total backend attempts.

The circuit breaker wraps the retry handler. For streaming, the wrapped call
ends when the byte iterator is returned, not when the iterator completes.
