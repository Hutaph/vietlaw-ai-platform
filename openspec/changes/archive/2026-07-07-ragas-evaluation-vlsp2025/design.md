## Context
Currently, the system is evaluated manually without robust quantitative metrics. We aim to integrate Ragas, using the VLSP2025-LegalSML dataset. The dataset is in an MCQ format which must be converted into Generative QA pairs to work effectively with Ragas evaluation metrics.

## Goals / Non-Goals
**Goals:**
- Implement a pipeline to fetch the VLSP2025 dataset and transform the MCQs into Ragas-compatible format (`question`, `ground_truth`, `relevant_articles`).
- Implement an evaluation script that runs these questions against the backend `/chat` endpoint.
- Calculate 4 metrics: Context Precision, Context Recall, Faithfulness, and Answer Relevance.
- Export results to CSV.

**Non-Goals:**
- Do not build a dashboard or front-end UI for the evaluation metrics yet.

## Decisions

**Decision 1: Use Generative QA transformation for MCQ**
- *Why?* Ragas evaluates generated text quality. By extracting the correct answer text from the MCQ options and using it as `ground_truth`, we can measure `Faithfulness` and `Answer Relevance`. The `relevant_articles` are used directly as ground-truth context for `Context Precision` and `Context Recall`.

**Decision 2: Use the existing `/chat` endpoint**
- *Why?* Evaluating the actual `/chat` API ensures we are testing the entire RAG pipeline end-to-end, including query rewriting, retrieval, and LLM generation.

## Risks / Trade-offs
- **Risk:** High latency due to sequentially evaluating hundreds of queries against the `/chat` API.
  - *Mitigation:* Limit the default evaluation run to a small sample (e.g., 10-20 questions) and provide an option to run the full dataset as a background job.
