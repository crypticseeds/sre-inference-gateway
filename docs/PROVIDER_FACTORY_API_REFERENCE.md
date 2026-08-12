# Provider factory API reference

```python
class ProviderFactory:
    @staticmethod
    def create_provider(config: ProviderConfig) -> BaseProvider: ...
```

Supported `ProviderConfig.type` values are `openai`, `vllm`, and `mock`.
Construction behavior and limitations are documented in
[PROVIDER_FACTORY.md](PROVIDER_FACTORY.md).

Provider registration is separate:

```python
await provider_registry.initialize_from_config(gateway_config.providers)
provider = provider_registry.get_provider("mock_openai")
names = provider_registry.list_providers()
providers = provider_registry.get_all_providers()
```

`initialize_from_config()` closes old instances, clears the registry, skips
disabled entries, and logs then skips individual construction failures.
