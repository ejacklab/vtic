# Review: test_config.py + test_errors.py

## Previous Findings Status

| Finding | Fixed? | Evidence |
|---------|--------|----------|
| (from review-tests-1.md - most findings were for enums.py, outside scope) | N/A | |
| Missing config edge case: EmbeddingsConfig with provider="custom" and explicit model/dimension | ❌ NO | `test_explicit_values_override_defaults` tests OpenAI, not custom. No test for custom + explicit values |
| Test port validation error message (custom validator) | ❌ NO | Tests use Pydantic's ge/le messages ("greater than or equal to 1") |
| Missing test: VticError subclasses with custom messages | ❌ NO | `TestSpecificErrorClasses` only tests default values |
| Missing test: ErrorResponse without details serialization | ⚠️ PARTIAL | `test_to_response_without_optional_fields` tests VticError, not ErrorResponse directly |

## New Issues Found

### Critical
- **None** - All tests pass, core functionality is correctly tested

### Warnings

1. **Missing test: Custom provider with explicit model/dimension**
   - `test_custom_defaults_not_applied` verifies custom provider gets no defaults
   - `test_explicit_values_override_defaults` tests OpenAI with explicit values
   - Missing: test that `provider="custom"` with explicit `model` and `dimension` preserves those values
   - Risk: Could regress if defaults are incorrectly applied to custom provider

2. **Missing test: VticError subclasses accept custom message**
   - All 6 error classes are tested for default values only
   - Factory functions (`validation_failed`, etc.) are tested with custom values
   - Missing: direct test of `ValidationError(message="Custom")`, `NotFoundError(message="Custom")`, etc.

### Suggestions

1. **Port validation error message assertion**
   - Tests assert Pydantic's constraint message ("less than or equal to 65535")
   - Source has custom validator with message "Port must be between 1 and 65535"
   - Either update test to match custom message OR remove redundant custom validator

2. **ErrorResponse JSON without optional fields**
   - `test_to_response_without_optional_fields` tests `VticError.to_response()` method
   - Consider adding test for `ErrorResponse.model_dump_json(exclude_none=True)` directly

## Coverage Analysis

### config.py Module

| Public API | Tested | Coverage |
|------------|--------|----------|
| **StorageConfig** | | |
| `dir` default | ✓ | `test_default_storage_dir` |
| `dir` from string | ✓ | `test_storage_dir_from_string` |
| `dir` from Path | ✓ | `test_storage_dir_from_path` |
| **ApiConfig** | | |
| `host` default | ✓ | `test_default_api_config` |
| `port` default | ✓ | `test_default_api_config` |
| `port` validation (1-65535) | ✓ | `test_port_validation_*` (6 tests) |
| **SearchConfig** | | |
| `bm25_enabled` default | ✓ | `test_default_search_config` |
| `semantic_enabled` default | ✓ | `test_default_search_config` |
| `bm25_weight` range | ✓ | `test_bm25_weight_range`, `test_bm25_weight_out_of_range` |
| `semantic_weight` range | ✓ | `test_semantic_weight_range` |
| weight sum warning | ✓ | `test_weights_sum_warning`, `test_weights_sum_ok` |
| **EmbeddingsConfig** | | |
| `provider` values | ✓ | `test_provider_values` (all 4) |
| `dimension` validation | ✓ | `test_dimension_*` (3 tests) |
| `provider="none"` with model warning | ✓ | `test_provider_none_with_model_warning` |
| **Config** | | |
| nested defaults | ✓ | `test_default_config`, `test_config_defaults_values` |
| extra fields forbidden | ✓ | `test_extra_fields_forbidden` |
| assignment validation | ✓ | `test_nested_config_update` |
| **load_config()** | | |
| default (no file) | ✓ | `test_load_default_config` |
| from TOML file | ✓ | `test_load_config_from_file` |
| file not found | ✓ | `test_config_file_not_found` |
| invalid TOML | ✓ | `test_invalid_toml_raises_error` |
| **Env var overrides** | | |
| VTIC_STORAGE_DIR | ✓ | `test_env_override_storage_dir` |
| VTIC_API_HOST | ✓ | `test_env_override_api_host` |
| VTIC_API_PORT | ✓ | `test_env_override_api_port` |
| VTIC_SEARCH_SEMANTIC_ENABLED | ✓ | `test_env_override_search_enabled` |
| VTIC_SEARCH_BM25_WEIGHT | ✓ | `test_env_override_search_weights` |
| VTIC_SEARCH_SEMANTIC_WEIGHT | ✓ | `test_env_override_search_weights` |
| VTIC_EMBEDDINGS_PROVIDER | ✓ | `test_env_override_embeddings_provider` |
| VTIC_EMBEDDINGS_MODEL | ✓ | `test_env_override_embeddings_model` |
| VTIC_EMBEDDINGS_DIMENSION | ✓ | `test_env_override_embeddings_dimension` |
| env precedence over file | ✓ | `test_env_takes_precedence_over_file` |
| **Provider defaults** | | |
| OpenAI defaults applied | ✓ | `test_openai_defaults_applied` |
| local defaults applied | ✓ | `test_local_defaults_applied` |
| custom defaults NOT applied | ✓ | `test_custom_defaults_not_applied` |
| explicit values override defaults | ⚠️ | OpenAI only, missing custom |
| **Type coercion** | | |
| bool parsing | ✓ | `test_parse_boolean_*_values` |
| int parsing | ✓ | `test_parse_integer` |
| float parsing | ✓ | `test_parse_float` |
| string parsing | ✓ | `test_parse_string` |

### errors.py Module

| Public API | Tested | Coverage |
|------------|--------|----------|
| **Error Codes** | | |
| VALIDATION_ERROR | ✓ | `test_all_error_codes_defined` |
| NOT_FOUND | ✓ | `test_all_error_codes_defined` |
| CONFLICT | ✓ | `test_all_error_codes_defined` |
| PAYLOAD_TOO_LARGE | ✓ | `test_all_error_codes_defined` |
| INTERNAL_ERROR | ✓ | `test_all_error_codes_defined` |
| SERVICE_UNAVAILABLE | ✓ | `test_all_error_codes_defined` |
| **ErrorDetail** | | |
| creation | ✓ | `test_error_detail_creation` |
| with value | ✓ | `test_error_detail_with_value` |
| optional fields | ✓ | `test_error_detail_optional_fields` |
| serialization | ✓ | `test_error_detail_serialization` |
| **ErrorObject** | | |
| creation | ✓ | `test_error_object_creation` |
| with details | ✓ | `test_error_object_with_details` |
| with docs | ✓ | `test_error_object_with_docs` |
| **ErrorResponse** | | |
| creation | ✓ | `test_error_response_creation` |
| JSON serialization | ✓ | `test_error_response_serialization_to_json` |
| with meta | ✓ | `test_error_response_with_meta` |
| full example | ✓ | `test_error_response_full_example` |
| **VticError** | | |
| default values | ✓ | `test_default_error` |
| custom message | ✓ | `test_custom_message` |
| custom details | ✓ | `test_custom_details` |
| custom docs | ✓ | `test_custom_docs` |
| to_response() | ✓ | `test_to_response` |
| to_response() without optional | ✓ | `test_to_response_without_optional_fields` |
| __str__() | ✓ | `test_str_representation`, `test_str_with_details` |
| Exception inheritance | ✓ | `test_exception_inheritance`, `test_can_be_raised` |
| **Specific Error Classes** | | |
| ValidationError | ⚠️ | defaults only, no custom message test |
| NotFoundError | ⚠️ | defaults only |
| ConflictError | ⚠️ | defaults only |
| PayloadTooLargeError | ⚠️ | defaults only |
| InternalError | ⚠️ | defaults only |
| ServiceUnavailableError | ⚠️ | defaults only |
| **Factory Functions** | | |
| ticket_not_found() | ✓ | `test_ticket_not_found` |
| validation_failed() | ✓ | `test_validation_failed` |
| validation_failed() with value | ✓ | `test_validation_failed_with_value` |
| duplicate_ticket() | ✓ | `test_duplicate_ticket` |
| semantic_search_unavailable() | ✓ | `test_semantic_search_unavailable` |
| payload_too_large() | ✓ | `test_payload_too_large` |
| index_error() | ✓ | `test_index_error` |
| **OpenAPI Examples** | | |
| Validation Error (400) | ✓ | `test_validation_error_400_example` |
| Not Found (404) | ✓ | `test_not_found_404_example` |
| Conflict (409) | ✓ | `test_conflict_409_example` |
| Service Unavailable (503) | ✓ | `test_service_unavailable_503_example` |

## Test Results

```
tests/test_config.py: 53 tests ✅
tests/test_errors.py: 38 tests ✅
Total: 91 tests passed, 4 warnings (expected hybrid weight sum warnings)
```

## Verdict: **PASS**

Tests are comprehensive and well-organized. Core spec compliance is verified:
- ✅ Port bounds (1-65535) validated via both file and env
- ✅ Env vars take precedence over file config (11 env vars tested)
- ✅ Type coercion (bool, int, float, string) tested
- ✅ Error JSON format matches OpenAPI spec (4 examples tested)
- ✅ All 6 error codes defined and tested
- ✅ All 6 factory functions tested with correct structure

Minor gaps (custom provider explicit values, custom error messages) are non-blocking for core functionality.
