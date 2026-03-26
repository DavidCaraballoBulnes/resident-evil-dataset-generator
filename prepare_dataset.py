import json
import os

# List of previously generated JSON files (relative paths)
INPUT_FILES = [
    "datasets/re_dataset_history.json",
    "datasets/re_dataset_characters.json",
    "datasets/re_dataset_objects.json",
    "datasets/re_dataset_locations.json",
    "datasets/re_dataset_enemies.json"
]

# Output path for the final unified JSON Lines (JSONL) file
OUTPUT_FILE = "datasets/re_dataset_final.jsonl"

def clean_and_unify():
    """
    Processes the input JSON files, verifies structural integrity
    of the data (system, user, assistant), removes invalid or empty entries,
    and unifies valid results into a single JSONL file.
    """
    total_read = 0
    total_saved = 0
    total_discarded = 0

    print("Starting dataset cleaning and unification...\n")

    # Open the output file in write mode
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file_out:
        
        for file_path in INPUT_FILES:
            if not os.path.exists(file_path):
                root_file_path = file_path.replace("datasets/", "")
                if os.path.exists(root_file_path):
                    file_path = root_file_path
                else:
                    print(f"Warning: File '{file_path}' was not found. It will be skipped.")
                    continue
                
            print(f"Processing file: {file_path}...")
            
            try:
                with open(file_path, "r", encoding="utf-8") as file_in:
                    dataset = json.load(file_in)
            except json.JSONDecodeError:
                print(f"Decoding error in {file_path}. Make sure the JSON format is valid.")
                continue
            except FileNotFoundError:
                print(f"Error: Could not open {file_path}.")
                continue
            
            for item in dataset:
                total_read += 1
                messages = item.get("messages", [])
                
                # Validation for the required structure (roles: system, user, assistant)
                if len(messages) == 3:
                    user_content = messages[1].get("content")
                    assistant_content = messages[2].get("content")
                    
                    # Sanitization: ensure string type and trim whitespace
                    user_content = str(user_content).strip() if user_content else ""
                    assistant_content = str(assistant_content).strip() if assistant_content else ""
                    
                    # Filtering: Keep only interactions with valid question and answer
                    if user_content and assistant_content:
                        json_line = json.dumps(item, ensure_ascii=False)
                        file_out.write(json_line + "\n")
                        total_saved += 1
                    else:
                        total_discarded += 1
                else:
                    total_discarded += 1

    # Execution summary in console
    print("\n" + "="*40)
    print("OPERATION SUMMARY")
    print("="*40)
    print(f"Total entries read:           {total_read}")
    print(f"Empty/null entries deleted:   {total_discarded}")
    print(f"Final entries saved:          {total_saved}")
    print(f"Final file created:           {OUTPUT_FILE}")
    print("="*40)

if __name__ == "__main__":
    clean_and_unify()