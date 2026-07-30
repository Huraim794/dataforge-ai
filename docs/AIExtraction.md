# AI Extraction

## System Overview

The AI extraction system uses a large language model (LLM) to extract structured data from scraped web content. It consists of two components:

- **`AIExtractor`** — builds prompts, invokes the LLM, and parses responses into structured results.
- **`LLMClient`** — abstract HTTP client supporting multiple LLM providers with token accounting and cost tracking.

## Supported Operations

### `extract(content, schema, prompt_template, fields)`

The core extraction method. Accepts web content and one of:
- **`schema`** — a JSON Schema dict describing the desired output structure.
- **`prompt_template`** — a custom string template with `{content}`, `{url}`, `{title}` placeholders.
- **`fields`** — a list of field definitions with `name`, `description`, `data_type`, and `required` flags.

If none are provided, the LLM performs free-form extraction of entities, relationships, and attributes.

When a schema is provided, the response is requested in `json_object` format:

```python
response_format = {"type": "json_object"} if schema else None
```

Content is truncated to 100,000 characters before submission.

### `classify(content, categories)`

Classifies web content into one or more predefined categories. Returns a JSON object with `category`, `subcategories`, `confidence`, and `reasoning`:

```python
response = await extractor.classify(content, ["news", "blog", "product", "review"])
```

### `extract_contacts(content)`

Extracts contact information using a predefined schema (emails, phones, addresses, social links, contact names).

### `extract_table(content, table_selector)`

Extracts tabular data using a predefined schema (headers, rows, row/column counts).

## LLM Provider Configuration

The `LLMClient` supports four providers with configurable models and cost rates:

| Provider | Default Model | Base URL |
|---|---|---|
| `openai` | `gpt-4o` | `https://api.openai.com/v1` |
| `gemini` | `gemini-pro` | `https://generativelanguage.googleapis.com/v1beta` |
| `claude` | `claude-3-haiku` | `https://api.anthropic.com/v1` |
| `deepseek` | `deepseek-chat` | `https://api.deepseek.com/v1` |

Provider-agnostic parameters are set in configuration:
- `llm_provider` — provider name (default `openai`)
- `llm_api_key` — API key (required)
- `llm_model` — model name (default `gpt-4o`)
- `llm_temperature` — sampling temperature (default `0.1`, low for deterministic extraction)
- `llm_max_tokens` — max response tokens (default `4096`)

## Token Accounting and Cost Tracking

Each provider configuration includes per-1000-token costs for prompt and completion:

```python
"cost_per_1k_prompt": 0.0025,      # $0.0025 per 1K prompt tokens
"cost_per_1k_completion": 0.01,    # $0.01 per 1K completion tokens
```

The `LLMResponse` dataclass tracks fine-grained usage:

| Field | Description |
|---|---|
| `tokens_prompt` | Prompt tokens consumed |
| `tokens_completion` | Completion tokens generated |
| `tokens_total` | Sum of prompt + completion |
| `cost_usd` | Total cost in USD (rounded to 6 decimal places) |

Cost is computed as:
```python
cost = (tokens_prompt / 1000 * cost_per_1k_prompt) +
       (tokens_completion / 1000 * cost_per_1k_completion)
```

Extraction metrics are exposed via Prometheus counters: `extractions_total`, `extraction_tokens_total`, and `extraction_cost_total`.

## Schema-Defined Extraction

When a schema is provided, the `AIExtractor` builds a prompt that describes the JSON schema and instructs the model to extract matching data:

```
Extract data from the following web content according to this JSON schema:
Schema: {schema_json}

Web Content:
{content}
```

The system prompt enforces strict rules:
1. Extract only information explicitly present in the content.
2. Return valid JSON matching the requested schema.
3. Use `null` for missing fields — never fabricate data.
4. Respond with clean JSON only (no markdown or explanations).

After receiving the response, the extractor strips markdown code fences if present and parses JSON. A confidence score is calculated as the ratio of filled required fields to total required fields.

## Classification Mode

Classification uses a separate system prompt that lists the available categories and requests a JSON response:

```python
system_prompt = f"""Classify the following web content into one or more of these categories: {categories}
Return a JSON object with:
- "category": the primary category
- "subcategories": list of applicable subcategories
- "confidence": confidence score 0-1
- "reasoning": brief explanation"""
```

Content is limited to 50,000 characters for classification.

## Configuration Reference

| Setting | Default | Description |
|---|---|---|
| `llm_provider` | `openai` | LLM provider name |
| `llm_api_key` | `None` | API key for the provider |
| `llm_model` | `gpt-4o` | Model identifier |
| `llm_temperature` | `0.1` | Sampling temperature |
| `llm_max_tokens` | `4096` | Maximum response tokens |
| `llm_endpoint` | `None` | Custom API endpoint (optional) |

## Error Handling and Fallbacks

1. **LLM call failures** — the `chat` method wraps each provider call in a try/except block. On failure it returns an `LLMResponse` with `success=False` and the error message.
2. **JSON parse errors** — if the LLM returns non-JSON content, it is stored as `{"raw": content}` in the result rather than discarded.
3. **Empty responses** — if `llm_response.content` is empty, the error is set to `"Empty LLM response"`.
4. **Content truncation** — content exceeding 100,000 characters (50,000 for classification) is silently truncated to prevent token limits.
5. **Metrics** — all failures are logged via the structured logger and recorded in Prometheus metrics for monitoring.
