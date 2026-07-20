import json
import os
from pathlib import Path

try:
    from datasets import load_dataset
except ImportError:
    print("Please install 'datasets' library: pip install datasets")
    exit(1)

def prepare_vlsp2025_dataset():
    print("Downloading VLSP2025-LegalSML dataset...")
    # Load dataset (Public-Test split train, config multichoice_questions)
    try:
        dataset = load_dataset("VLSP2025-LegalSML/Public-Test", "multichoice_questions", split="train")
    except Exception as e:
        print(f"Error downloading dataset: {e}")
        return

    parsed_data = []
    
    print(f"Loaded {len(dataset)} examples. Parsing...")
    
    for item in dataset:
        # Structure varies, handle common variations
        question = item.get("question", "")
        
        # Sometimes options is a list, sometimes a dict
        options = item.get("options", {})
        answer_key = item.get("answer", "")
        
        ground_truth = str(answer_key)
        
        # Try to map answer key to option text
        if isinstance(options, dict) and answer_key in options:
            ground_truth = options[answer_key]
        elif isinstance(options, list):
            # If options is list of strings and answer_key is an index or letter
            if answer_key in ["A", "B", "C", "D"] and len(options) >= ord(answer_key) - 65 + 1:
                idx = ord(answer_key) - 65
                ground_truth = options[idx]
            else:
                ground_truth = str(options)
                
        # Handle references (relevant articles)
        relevant_articles = item.get("relevant_articles", [])
        if not relevant_articles:
            relevant_articles = item.get("references", [])
            
        # Optional: ensure relevant articles is a list of strings
        cleaned_articles = []
        for art in relevant_articles:
            if isinstance(art, dict):
                # if it's a dict like {"law_id": "...", "article_id": "..."}
                cleaned_articles.append(str(art))
            else:
                cleaned_articles.append(str(art))
                
        parsed_data.append({
            "question": question,
            "ground_truth": ground_truth,
            "relevant_articles": cleaned_articles
        })
        
    out_dir = Path(__file__).parent
    out_dir.mkdir(exist_ok=True, parents=True)
    out_file = out_dir / "dataset.json"
    
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(parsed_data, f, ensure_ascii=False, indent=2)
        
    print(f"Saved {len(parsed_data)} parsed examples to {out_file}")

if __name__ == "__main__":
    prepare_vlsp2025_dataset()
