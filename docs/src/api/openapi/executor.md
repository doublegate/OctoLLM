# executor OpenAPI Specification

Complete OpenAPI 3.0 specification for the Executor service.

## Interactive Documentation

When running locally, access interactive API documentation at:

- **Swagger UI**: `http://localhost:XXXX/docs`
- **ReDoc**: `http://localhost:XXXX/redoc`

## OpenAPI YAML Specification

The complete OpenAPI 3.0 specification is available as a YAML file:

**File**: `docs/src/api/openapi-yaml/executor.yaml`

Download: [executor.yaml](../openapi-yaml/executor.yaml)

## Generating Clients

Use OpenAPI Generator to create client SDKs in any language:

```bash
openapi-generator-cli generate \
  -i docs/api/openapi/executor.yaml \
  -g <language> \
  -o clients/<language>
```

Supported languages: python, typescript, java, go, rust, and 50+ others.

## See Also

- [REST API Overview](../rest-api.md)
- [All OpenAPI Specs](../openapi-specs.md)
- [Data Models](../data-models.md)
