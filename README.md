# Resident Evil Dataset Generator

## About
A Python pipeline to extract canonical lore from the Resident Evil Fandom API and generate a factual, conversational dataset for LLM fine-tuning using LLaMA 3.

This repository contains the scripts used to scrape, process, and generate a synthetic, instruction-following dataset based exclusively on the Resident Evil universe. The goal is to provide AI systems with highly specialized, hallucination-free knowledge about the saga's lore, avoiding roleplay and non-canon information.

## Repository Structure

The pipeline is divided into three main scripts:

* `list_categories.py`: Connects to the Resident Evil Wiki API (`https://residentevil.fandom.com/es/api.php`) to fetch and list all available encyclopedic categories.
* `generate_dataset.py`: The core pipeline. It downloads HTML content from the wiki, cleans it, extracts structured data (infoboxes), and uses local LLM inference (Ollama + LLaMA 3) to generate synthetic Question & Answer pairs based strictly on the extracted text.
* `prepare_dataset.py`: A post-processing script that reads the generated JSON files, validates the conversational structure (system, user, assistant), removes empty or invalid entries, and compiles everything into a final `.jsonl` file.

## Prerequisites

To run these scripts locally, you will need:

1.  **Python 3.8+**
2.  **Ollama**: Installed and running locally ([Download Ollama](https://ollama.com/)).
3.  **LLaMA 3 Model**: Pulled via Ollama. Run the following command in your terminal:
    ```bash
    ollama run llama3:instruct
    ```
4.  **Python Packages**: Install the required dependencies:
    ```bash
    pip install requests beautifulsoup4 tqdm
    ```

## Usage

Follow these steps to generate the dataset from scratch:

1.  **Explore Categories (Optional):** Run `list_categories.py` to see all available categories on the wiki. Update the `CATEGORIES` list in the main generation script based on your needs.
2.  **Generate Data:** Run `generate_dataset.py`. Inside the code, the categories are separated into 5 thematic groups using comments, originally intended to be executed in 5 separate runs. However, due to the high hardware demands and the significant time required for this task, it is highly recommended to split the categories even further and run the script more times with fewer categories per run. To do this, simply create different scripts (or modify the main one) and change the `OUTPUT_FILE` variable name for each batch (e.g., `datasets/re_dataset_part1.json`).
3.  **Clean and Unify:** Run `prepare_dataset.py` to filter out bad generations and unify the temporal JSON files into a single, ready-to-use JSON Lines (`.jsonl`) file.

## Output Format

The final pipeline outputs a `.jsonl` file compatible with the standard OpenAI / ChatML format, ready for fine-tuning. Example structure:

```json
{
  "category": "Categoría:Personajes",
  "subject": "Leon S. Kennedy",
  "messages": [
    {
      "role": "system",
      "content": "Eres un asistente de IA experto, objetivo y enciclopédico sobre Resident Evil..."
    },
    {
      "role": "user",
      "content": "¿Quién o qué es Leon S. Kennedy?"
    },
    {
      "role": "assistant",
      "content": "Leon S. Kennedy es una entidad/personaje en el universo de Resident Evil..."
    }
  ]
}
```

## Dataset Availability

The final generated dataset is available on Hugging Face:
[[DavidCaraballoBulnes/ResidentEvil-Data-Instruct](https://huggingface.co/datasets/DavidCaraballoBulnes/ResidentEvil-Data-Instruct)]

## License
The code in this repository is open-source. The scraped data belongs to Capcom and the contributors of the Resident Evil Fandom Wiki.
