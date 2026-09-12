# Safety Guardian Arm

The Safety Guardian Arm protects against PII leakage, prompt injection, and malicious content.

## Overview

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Detection**: Regex patterns + ML models (Presidio)
- **Capabilities**: PII detection, prompt injection blocking, content filtering

## Security Features

- **PII Detection**: 18+ types (SSN, email, phone, credit cards, etc.)
- **Auto-Redaction**: Replace sensitive data with `[REDACTED]` tokens
- **Injection Prevention**: Block SQL injection, command injection, prompt manipulation
- **Content Filtering**: NSFW, violent, illegal content detection
- **Audit Logging**: All detections logged for compliance

## Development

```bash
cd services/arms/safety-guardian
poetry install
poetry run pytest tests/ -v
poetry run uvicorn src.main:app --reload --port 8005
```

## References

- [Safety Guardian Specification](../../../docs/components/arms/safety-guardian.md)
- [PII Protection Guide](../../../docs/security/pii-protection.md)
- [Threat Model](../../../docs/security/threat-model.md)
