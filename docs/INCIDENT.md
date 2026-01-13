
## Sample `INCIDENT.md` (Outage Report)
## Incident Summary

**Incident ID:** INC-2026-001  
**Date:** 2026-01-12  
**Duration:** 17 minutes  
**Severity:** SEV-2 (Partial service degradation)

A partial outage occurred when the primary inference provider (OpenAI) experienced elevated error rates. The inference gateway detected failures and routed traffic to the local vLLM provider.

## Impact

- ~35% of requests experienced increased latency
- No complete service outage
- No client-side errors returned
- Token usage remained within budget limits

## Timeline

**T+00:00** – OpenAI provider begins returning HTTP 5xx errors  
**T+00:30** – Error rate exceeds circuit breaker threshold  
**T+00:31** – Circuit breaker opens for OpenAI provider  
**T+00:32** – Traffic is rerouted to local vLLM provider  
**T+02:00** – Latency increases due to local model warm-up  
**T+10:00** – OpenAI health checks recover  
**T+12:00** – Circuit breaker transitions to half-open  
**T+17:00** – Traffic gradually restored to OpenAI  

## Detection

The incident was detected automatically via:

- Elevated error-rate metrics
- Circuit breaker state change
- Increased latency observed in Prometheus dashboards

No manual intervention was required to detect or mitigate the failure.

## Root Cause

The upstream OpenAI API experienced a transient outage, returning repeated 5xx responses. This was outside the control of the gateway.

## Mitigation

- Circuit breaker prevented repeated retries against the failing provider
- Weighted routing shifted traffic to the local vLLM provider
- Rate limiting prevented request amplification
- Clients received successful responses throughout the incident

## What Went Well

- Automatic failover worked as designed
- No client-facing errors
- Clear observability and traceability
- Cost limits were enforced during degraded mode

## What Didn’t Go Well

- Local vLLM cold start caused elevated latency
- No pre-warmed local capacity for sudden failover
- No alerting configured for latency SLO breaches (metrics only)

## Action Items

| Item | Owner | Priority |
|--||-|
| Add warm-up hook for local provider | Platform | High |
| Add latency SLO alerts | Platform | Medium |
| Improve provider health scoring | Platform | Low |

## Lessons Learned

- Failover without warm capacity still impacts user experience
- Circuit breakers are essential for external AI dependencies
- Observability must include latency SLOs, not just availability

## Conclusion

The gateway successfully contained the blast radius of an upstream AI provider outage.  
The incident validated the design choice of centralizing reliability, routing, and policy enforcement in a single control plane.

This incident demonstrates how SRE principles apply directly to modern AI inference systems.
