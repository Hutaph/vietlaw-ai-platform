## Why

To rigorously validate the effectiveness of our Agentic RAG system in the legal domain, we must move beyond manual "eyeballing" and qualitative Ablation Studies. Integrating the Ragas (Retrieval Augmented Generation Assessment) framework allows us to quantitatively measure Context Precision, Context Recall, Faithfulness, and Answer Relevance. Using the VLSP2025-LegalSML dataset provides a gold-standard benchmark to accurately assess the system's performance and ensure legal accuracy.

## What Changes

- Add a script to download and parse the VLSP2025-LegalSML Multiple Choice Question dataset from HuggingFace.
- Transform the MCQ format into Generative QA pairs (`question`, `ground_truth`, `relevant_articles`) suitable for Ragas evaluation.
- Implement an evaluation pipeline that feeds the dataset questions through the `/chat` endpoint and collects the LLM responses and retrieved contexts.
- Integrate the `ragas` library to score the collected outputs against the 4 core metrics.
- Output evaluation results in a CSV/DataFrame for reporting.

## Capabilities

### New Capabilities
- `ragas-evaluation`: Defines the requirements and workflow for automatically evaluating the RAG pipeline using the Ragas framework and VLSP2025 dataset.

### Modified Capabilities


## Impact

- **Dependencies**: Adds `ragas`, `datasets`, and `pandas` to backend test requirements.
- **Backend structure**: Adds a new `backend/evaluation/` directory containing the evaluation scripts and dataset parsing utilities.
- **Workflow**: Enables automated benchmarking of the RAG system, making it easier to track improvements or regressions when tweaking retrieval/generation parameters.
