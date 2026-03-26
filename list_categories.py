import requests

WIKI_API = "https://residentevil.fandom.com/es/api.php"

def get_all_categories():
    """
    Fetches all available categories in the Resident Evil Wiki
    using paginated calls to its official API, with network error handling.
    
    Returns:
        list: A list of strings containing the category names.
    """
    categories = []
    params = {
        "action": "query",
        "list": "allcategories",
        "aclimit": "500",  # Maximum number of results per request allowed by the API
        "format": "json"
    }

    print("Fetching all categories from the wiki...")
    
    while True:
        try:
            response = requests.get(WIKI_API, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Extract category names from the response block
            if "query" in data and "allcategories" in data["query"]:
                for category_item in data["query"]["allcategories"]:
                    categories.append("Categoría:" + category_item["*"])
            
            # Pagination handling
            if "continue" in data and "accontinue" in data["continue"]:
                params["accontinue"] = data["continue"]["accontinue"]
            else:
                break # Exit loop if there are no more pages to process
                
        except requests.exceptions.Timeout:
            print("Error: The API request timed out.")
            break
        except requests.exceptions.RequestException as e:
            print(f"Network error while contacting the API: {e}")
            break
        except ValueError:
            print("Error: Could not decode the JSON response from the API.")
            break
            
    return categories

if __name__ == "__main__":
    all_categories = get_all_categories()

    if all_categories:
        print(f"\nFinished. A total of {len(all_categories)} categories were found.")
        print("Complete list:")
        for category in all_categories:
            print(f" - {category}")
    else:
        print("\nCould not fetch categories due to a previous error.")