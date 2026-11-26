# whatsapp-order-extractor

Turns free-text WhatsApp messages into structured orders. FastAPI + an LLM, with an
evaluation suite that measures how often the extraction is actually right.

## The problem

A bakery takes its orders as plain WhatsApp messages: *"2 tres leches para el sábado
a las 5, que diga Feliz Cumple Ana"*. Someone reads that and types it into a system by
hand. This service does that step, and measures how often it gets it right.

## Pipeline

```
message -> classifier -> extractor -> validated Order
```

- `app/agents/classifier.py` decides whether the message is an order at all.
- `app/agents/extractor.py` pulls out items, quantities, delivery date and time.
- Prompts live in versioned files under `app/prompts/`, not inline in the code.
- The message content is substituted last, so it cannot alter the prompt template.
- The model output is validated against Pydantic schemas. On a schema violation the
  service raises instead of returning invented data.
- `app/llm.py` is the only place that talks to the model, with an explicit timeout
  and retries. The provider is set in `.env`, so changing it does not touch the code.

## Evaluation

This is the part the project is built around. `evals/run.py` runs a golden set of
23 cases, N times each, and reports accuracy per field.

```
python evals/run.py --runs 3
```

Latest run (2026-11-23, 23 cases x 3 runs):

| field | correct |
|---|---|
| delivery_date | 55/55 |
| delivery_time | 55/55 |
| items_count | 55/55 |
| quantities | 55/55 |
| delivery | 53/55 |
| classification | 64/67 |

Running every case several times separates three things that a single pass confuses:

- **stable pass** — correct in every run (20 cases)
- **stable fail** — wrong in every run; a real defect (1 case)
- **unstable** — differs between runs at temperature 0 (2 cases)

The distinction matters. A case that passes once and fails once is not a fixed bug,
and treating it as one means tuning prompts against noise.

Two prompt changes, measured on the same 24-case set, took `delivery_date` from
51/60 to 57/60 (85% to 95%): the prompt now states the current date and weekday
explicitly, and gives a worked example of a relative date.

Every run is written to `evals/results/` and committed, so the measurement history
is part of the repository rather than something to take on trust.

## Subagents

`.claude/agents/` holds two Claude Code subagents used while building this:

- `code-reviewer` — reviews changes against the project's conventions
- `prompt-adversary` — writes adversarial cases for the golden set

## Setup

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

`.env` takes an OpenAI-compatible endpoint:

```
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=
```

## Status

In development.

Working: `POST /extract`, classifier, extractor, schema validation, completeness
check, and the evaluation suite. 19 unit tests, none of which call the model:

```
python -m pytest -q
```

Pending: an LLM judge for the free-text fields, catalog resolution and a Dockerfile.
