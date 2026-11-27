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
- The message content is substituted last, so it cannot alter the prompt template,
  and the delimiter around it carries a random value per call so the message
  cannot close it (`app/prompting.py`).
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

Latest run (2026-11-26, 23 cases x 3 runs):

| field | correct |
|---|---|
| delivery_date | 58/58 |
| delivery_time | 58/58 |
| items_count | 58/58 |
| quantities | 58/58 |
| delivery | 58/58 |
| classification | 67/69 |

Running every case several times separates three things that a single pass confuses:

- **stable pass** — correct in every run (22 cases)
- **stable fail** — wrong in every run; a real defect (0 cases)
- **unstable** — differs between runs at temperature 0 (1 case)

The distinction matters. A case that passes once and fails once is not a fixed bug,
and treating it as one means tuning prompts against noise.

Two rounds of work so far, each measured before and after on the same case set.

**Dates.** Two prompt changes took `delivery_date` from 51/60 to 57/60 (85% to
95%) on the 24-case set: the prompt now states the current date and weekday
explicitly, and gives a worked example of a relative date.

**Prompt injection.** The golden set has cases that paste a fake `</mensaje>`
tag and a line imitating this prompt's own "Hoy es ..." header, to move the
delivery date and the quantity. The delimiter around the customer's message now
carries a random value per call (`<mensaje-a7f3c91b>`), so a message cannot
close it. On the same 23-case set this took stable failures from 1 to 0 and
perfect cases from 20/23 to 22/23; `classification` went from 64/67 to 67/69
and `delivery` from 53/55 to 58/58. Measured over three runs each, before and
after.

## Known limitation

Case `c021` is unstable: it passes in roughly one run out of three.

It is a real order ("me das un pastel de 3 leches pal sabado") with injected
text pasted after it. Case `007` is the opposite: injected text with no order
in it at all. The classifier has to send the first to `ORDER` and the second to
`OTHER`, and three rounds of prompt wording moved the two together rather than
apart — hardening toward `ORDER` fixed `c021` and broke `007`, and the reverse.
The current prompt, which asks the model to set the pasted text aside and look
for a product, holds `007` at 3/3 and `c021` at 1/3.

The injection itself does not succeed: on the runs where `c021` is classified
as an order, the extracted date and quantity are correct. What fails is the
classification, and the failure is the safe direction — a real order is
dropped rather than an attack being processed.

Resolving it properly needs more than prompt wording, and is left open rather
than papered over by relaxing the expected value.

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
