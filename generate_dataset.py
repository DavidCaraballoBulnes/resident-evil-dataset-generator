import requests
from bs4 import BeautifulSoup
import json
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

# ======================
# GENERAL CONFIGURATION
# ======================

WIKI_API = "https://residentevil.fandom.com/es/api.php"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3:instruct"

# Note: Categories remain in Spanish to match the ES Fandom API perfectly.
CATEGORIES = [
    # 1. Story, Lore and Documents
    "Categoría:Acontecimientos", "Categoría:Archivos", "Categoría:Continuidades",
    "Categoría:Entradas en el Blog Experience Kijuju", "Categoría:Entradas en el Blog de Robert S.T.A.R.S.",
    "Categoría:Eventos", "Categoría:Línea de Tiempo", "Categoría:Reportes",
    # 2. Characters and Factions
    "Categoría:Antagonistas", "Categoría:B.S.A.A.", "Categoría:Corporación Umbrella",
    "Categoría:D.S.O.", "Categoría:Equipo Alpha", "Categoría:Equipo Bravo",
    "Categoría:F.B.C.", "Categoría:Grupos", "Categoría:Jefes", "Categoría:Los Iluminados",
    "Categoría:Miembros de S.T.A.R.S.", "Categoría:Niños", "Categoría:Organización",
    "Categoría:Organizaciones Criminales", "Categoría:Personajes", "Categoría:Personajes fallecidos",
    "Categoría:Personajes Jugables Especiales", "Categoría:Presidentes", "Categoría:Protagonistas",
    "Categoría:Proyecto Wesker", "Categoría:Spec Ops", "Categoría:Subpáginas de Ada Wong",
    "Categoría:TerraSave", "Categoría:U.B.C.S.", "Categoría:Umbrella Corps", "Categoría:Umbrella Security Service",
    # 3. Biological Threats and Enemies
    "Categoría:Agentes patógenos", "Categoría:Agentes Virales", "Categoría:Animales",
    "Categoría:B.O.W.", "Categoría:Criaturas", "Categoría:Enemigos", "Categoría:Ganados",
    "Categoría:Holomorfos", "Categoría:Hunters", "Categoría:Las Plagas", "Categoría:Lickers",
    "Categoría:Majini", "Categoría:Moho", "Categoría:T-Abyss", "Categoría:T-Phalaris",
    "Categoría:T-Phobos", "Categoría:T-Veronica", "Categoría:Tipos de Zombis", "Categoría:Tyrant",
    "Categoría:Uroboros", "Categoría:Virus Executer", "Categoría:Virus Progenitor", "Categoría:Virus-A",
    "Categoría:Virus-C", "Categoría:Virus-G", "Categoría:Virus-T", "Categoría:Virus-T Fálaris", "Categoría:Zombis",
    # 4. Locations and Geography
    "Categoría:Ecliptic Express", "Categoría:Escenarios", "Categoría:Localizaciones",
    "Categoría:Mansión Spencer", "Categoría:Mapas", "Categoría:R.P.D.", "Categoría:Residencia Baker",
    # 5. Survival, Weapons and Items
    "Categoría:Accesorios de armas", "Categoría:Acertijos", "Categoría:Ametralladoras",
    "Categoría:Armas", "Categoría:Armas de Cuerpo a Cuerpo", "Categoría:Armas especiales",
    "Categoría:Armas infinitas", "Categoría:Ballestas", "Categoría:Curas y Vacunas",
    "Categoría:Escopetas", "Categoría:Fusiles de asalto", "Categoría:Granadas",
    "Categoría:Lanzacohetes", "Categoría:Lanzagranadas", "Categoría:Lanzallamas",
    "Categoría:Llaves", "Categoría:Magnums", "Categoría:Objetos", "Categoría:Objetos de salud",
    "Categoría:Objetos especiales", "Categoría:Pistolas", "Categoría:Plantas",
    "Categoría:Químicos", "Categoría:Quimicos", "Categoría:Rifles", "Categoría:Subfusiles", "Categoría:Tesoros"
]

CHUNK_SIZE = 900
MAX_WORKERS = 4
GENERATIONS_PER_CHUNK = 1

OUTPUT_FILE = "datasets/re_dataset_group-name.json"

seen_questions = set()

# ======================
# DATA FETCHING FUNCTIONS
# ======================

def get_category_pages(category):
    """Fetches the titles of the pages belonging to a specific category with error handling."""
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": category,
        "cmlimit": "500",
        "format": "json"
    }
    try:
        response = requests.get(WIKI_API, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        if "query" in data and "categorymembers" in data["query"]:
            return [page["title"] for page in data["query"]["categorymembers"]]
    except requests.exceptions.RequestException as e:
        print(f"Warning: Network error fetching pages for '{category}': {e}")
    except ValueError:
        print(f"Warning: Error decoding JSON for the category '{category}'.")
    return []

def get_page_html(title):
    """Downloads the raw HTML code of a specific page with fail-safes."""
    params = {"action": "parse", "page": title, "prop": "text", "format": "json"}
    try:
        response = requests.get(WIKI_API, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data["parse"]["text"]["*"]
    except requests.exceptions.RequestException as e:
        print(f"Warning: Network error downloading the page '{title}': {e}")
    except (ValueError, KeyError) as e:
        print(f"Warning: Error reading the content of the page '{title}': {e}")
    return ""

def clean_html(html_content):
    """Cleans the HTML by removing unnecessary tags and extracts only readable text."""
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(["script", "style", "sup", "table", "nav", "aside", "div.infobox"]):
        tag.decompose()
    return " ".join(soup.get_text().split())

def extract_infobox(html_content):
    """Extracts structured information from the data table (infobox) of a character or item."""
    soup = BeautifulSoup(html_content, "html.parser")
    infobox = soup.find("table", class_="infobox") or soup.find("div", class_="pi-data")
    if not infobox:
        return None
    
    extracted_info = {}
    for row in soup.find_all("div", class_="pi-item pi-data"):
        header = row.find("h3", class_="pi-data-label")
        data = row.find("div", class_="pi-data-value")
        if header and data:
            extracted_info[header.get_text(strip=True)] = data.get_text(" ", strip=True)
    return extracted_info

def chunk_text(text):
    """Splits a large text into smaller chunks to avoid exceeding the AI's context window."""
    words = text.split()
    chunks = [" ".join(words[i:i+CHUNK_SIZE]) for i in range(0, len(words), CHUNK_SIZE)]
    return [chunk for chunk in chunks if len(chunk) > 50]

# ======================
# AI GENERATION FUNCTIONS
# ======================

def build_prompt(chunk):
    """Builds the structured prompt to guide the LLM in QA generation."""
    return f"""
You are an AI training data creator specialized in Resident Evil. Your goal is to generate educational and objective question/answer pairs based on the text.

STRICT RULES:
1. DO NOT ROLEPLAY. Under no circumstances should you act as a game character.
2. In the "conversation" section, the "user" is a fan asking, and the "assistant" is you, an objective encyclopedia AI. DO NOT write fictional dialogues.
3. Use ONLY the information from the provided text. Do not invent anything.
4. Write the answers in Spanish naturally, clearly, and without mechanically repeating the question.

Types of data to extract:
- qa: Direct factual questions.
- reasoning: "Why" or "How" questions that require explaining causes/consequences.
- comparison: Differences or similarities between mentioned elements.
- conversation: A small thread where the user asks for more details and the AI explains.
- timeline: Questions about dates or chronological events.

Return ONLY valid JSON with this exact format:
{{
"qa":[{{"question":"","answer":""}}],
"reasoning":[{{"question":"","answer":""}}],
"comparison":[{{"question":"","answer":""}}],
"conversation":[{{"user":"","assistant":""}}],
"timeline":[{{"question":"","answer":""}}]
}}

Source text:
{chunk}
"""

def generate_examples(chunk):
    """Sends the text chunk to Ollama and returns the generated JSON, handling possible crashes."""
    payload = {
        "model": MODEL,
        "prompt": build_prompt(chunk),
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.8, "top_p": 0.95}
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        response_data = response.json()
        return json.loads(response_data["response"])
    except requests.exceptions.Timeout:
        return None
    except requests.exceptions.RequestException as e:
        print(f"Connection error with Ollama. Check the server: {e}")
        return None
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        print(f"Warning: Ollama did not return a valid JSON: {e}")
        return None

def convert_examples(generated_example, category, subject):
    """Converts the raw JSON generated by the LLM into the final conversational (Instruct) format."""
    formatted_data = []
    
    # System message is kept in Spanish to match the target language of the dataset.
    system_msg = f"Eres un asistente de IA experto, objetivo y enciclopédico sobre Resident Evil. Bajo ninguna circunstancia asumas el rol de los personajes de la saga ni inventes diálogos de ficción. Contexto de la consulta: {subject} ({category})."

    if not generated_example: 
        return formatted_data

    combined_qa = generated_example.get("qa", []) + generated_example.get("reasoning", []) + generated_example.get("comparison", [])
    for qa_pair in combined_qa:
        question = qa_pair.get("question", "")
        if question and question not in seen_questions:
            seen_questions.add(question)
            formatted_data.append({
                "category": category, "subject": subject,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": qa_pair.get("answer", "")}
                ]
            })

    for conversation in generated_example.get("conversation", []):
        if "user" in conversation and "assistant" in conversation:
            formatted_data.append({
                "category": category, "subject": subject,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": conversation["user"]},
                    {"role": "assistant", "content": conversation["assistant"]}
                ]
            })

    for timeline_event in generated_example.get("timeline", []):
        question = timeline_event.get("question", "")
        if question and question not in seen_questions:
            seen_questions.add(question)
            formatted_data.append({
                "category": category, "subject": subject,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": timeline_event.get("answer", "")}
                ]
            })

    return formatted_data

def format_character_dataset(info_dict, category, subject):
    """Generates dataset entries based on structured infobox data."""
    character_data = []
    system_msg = f"Eres un asistente de IA experto, objetivo y enciclopédico sobre Resident Evil. Bajo ninguna circunstancia asumas el rol de los personajes de la saga. Contexto de la consulta: {subject} ({category})."
    
    # Keys like "Nombre" and "Estado" are in Spanish because they are scraped from the ES wiki.
    character_name = info_dict.get("Nombre") or info_dict.get("Nombre original") or ""
    if character_name:
        biography = f"{character_name} es una entidad/personaje en el universo de Resident Evil."
        if "Afiliación" in info_dict or "Organización" in info_dict:
            affiliation = info_dict.get('Afiliación', info_dict.get('Organización'))
            biography += f" Su afiliación principal es: {affiliation}."
        if "Estado" in info_dict:
            biography += f" Su estado actual es: {info_dict['Estado']}."

        character_data.append({
            "category": category, "subject": subject,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": f"¿Quién o qué es {character_name}?"},
                {"role": "assistant", "content": biography}
            ]
        })
    return character_data

# ======================
# MAIN BLOCK
# ======================

def main():
    print("Fetching Resident Evil categories...")
    page_to_category = {page: category for category in CATEGORIES for page in get_category_pages(category)}
    print("Total unique pages to process:", len(page_to_category))

    chunk_info_list, final_dataset = [], []

    print("Extracting text from the Wiki...")
    for page_title, category in tqdm(page_to_category.items()):
        try:
            html_content = get_page_html(page_title)
            for chunk in chunk_text(clean_html(html_content)):
                chunk_info_list.append((chunk, category, page_title))
            
            infobox_info = extract_infobox(html_content)
            if infobox_info: 
                final_dataset.extend(format_character_dataset(infobox_info, category, page_title))
        except Exception: 
            pass

    print("Total chunks generated:", len(chunk_info_list))
    print("Generating dataset with Ollama (this process will take time)...")

    with ThreadPoolExecutor(MAX_WORKERS) as executor:
        futures = [(executor.submit(generate_examples, chunk), category, page_title) for chunk, category, page_title in chunk_info_list for _ in range(GENERATIONS_PER_CHUNK)]
        for future, category, page_title in tqdm(futures):
            try:
                result = future.result()
                if result:
                    final_dataset.extend(convert_examples(result, category, page_title))
            except Exception: 
                pass

    print("Final dataset size:", len(final_dataset))
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file_out:
        json.dump(final_dataset, file_out, indent=2, ensure_ascii=False)
        
    print(f"Dataset successfully saved at: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()