# Provider factory summary

The provider factory maps validated configuration to OpenAI, vLLM, and mock
adapter instances. The process-wide registry owns the instances after startup.

See [PROVIDER_FACTORY.md](PROVIDER_FACTORY.md) for behavior and
[PROVIDER_FACTORY_API_REFERENCE.md](PROVIDER_FACTORY_API_REFERENCE.md) for the
current call surface.
