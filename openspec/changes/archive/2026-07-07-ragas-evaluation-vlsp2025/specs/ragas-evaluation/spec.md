## ADDED Requirements

### Requirement: VLSP2025 Dataset Parsing
The system SHALL provide a utility to download the VLSP2025-LegalSML Multiple Choice Question dataset and parse it into a Generative QA format containing `question`, `ground_truth` (the correct answer text), and a list of `relevant_articles`.

#### Scenario: Successfully transforming an MCQ question
- **WHEN** the dataset contains a question with options and a correct answer letter
- **THEN** the utility extracts the text of the correct option and maps it to `ground_truth`

### Requirement: End-to-End RAG Evaluation
The system SHALL provide a script that takes the parsed dataset, sends each `question` to the RAG backend, and collects the generated response and retrieved context.

#### Scenario: Running the evaluation loop
- **WHEN** the evaluation script is executed
- **THEN** it sends requests to the `/chat` API, records the `response_text` and `context_used`, and compiles the results into an evaluation dataset

### Requirement: Ragas Metric Scoring
The system SHALL use the Ragas framework to score the collected outputs against Context Precision, Context Recall, Faithfulness, and Answer Relevance.

#### Scenario: Calculating and exporting scores
- **WHEN** the evaluation dataset is complete
- **THEN** the system calculates the 4 metrics for each question and exports the final scores and averages to a CSV file
