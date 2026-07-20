## 1. Environment Setup

- [x] 1.1 Update `backend/requirements.txt` to include `ragas`, `datasets`, and `pandas`.
- [x] 1.2 Create directory `backend/evaluation/` for scripts.

## 2. Dataset Preparation

- [x] 2.1 Create `backend/evaluation/prepare_dataset.py` to download `VLSP2025-LegalSML` dataset using HuggingFace `datasets` library.
- [x] 2.2 In `prepare_dataset.py`, add logic to parse the MCQ format and extract the text of the correct option as `ground_truth`.
- [x] 2.3 Save the parsed dataset (containing `question`, `ground_truth`, and `relevant_articles`) to `backend/evaluation/dataset.json`.

## 3. Evaluation Pipeline

- [x] 3.1 Create `backend/evaluation/evaluate.py`.
- [x] 3.2 In `evaluate.py`, write a loop that reads `dataset.json` and sends each `question` to the local `/chat` endpoint.
- [x] 3.3 For each response, extract `response_text` and `context_used`, formatting them as `answer` and `contexts` for Ragas.
- [x] 3.4 Initialize Ragas metrics (Context Precision, Context Recall, Faithfulness, Answer Relevance) and run the evaluation on the collected dataset.
- [x] 3.5 Export the final Ragas score output to `backend/evaluation/results.csv`.
