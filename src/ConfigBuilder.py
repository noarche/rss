import os
import json

# To use config builder put the original config.json file in the same directory as this script. Create a txt file named 'rss_links.txt' with 1 url per link in the format of   rssFeedName:rssFeedURL   and then run this script. It will generate a new_config.json file with all the rss feeds from current config and new rss feeds from txt file with no duplicates and in alphabetical order. Simply rename new_config.json to config.json.

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')
TEXT_FILE = os.path.join(BASE_DIR, 'rss_links.txt')
OUTPUT_FILE = os.path.join(BASE_DIR, 'new_config.json')

def load_config():
    with open(CONFIG_FILE, 'r') as file:
        config = json.load(file)
    return config

def load_text_file():
    links = []
    with open(TEXT_FILE, 'r') as file:
        for line in file:
            if ':' in line:
                title, url = line.strip().split(':', 1)  # Split only at the first colon
                links.append({'title': title.strip(), 'url': url.strip()})
            else:
                print(f"Skipping invalid line: {line.strip()}")
    return links


def merge_and_deduplicate(existing_links, new_links):
    # Combine both lists and remove duplicates by converting to a dictionary
    combined_links = {item['url']: item for item in existing_links + new_links}
    
    # Convert the dictionary back to a list and sort it alphabetically by title
    sorted_links = sorted(combined_links.values(), key=lambda x: x['title'].lower())
    
    return sorted_links

def save_new_config(links):
    new_config = {
        "update_interval": 3600,  # Keeping the default update interval
        "rss_links": links
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as file:
        json.dump(new_config, file, indent=4)
    print(f"New configuration saved to {OUTPUT_FILE}")

def main():
    config = load_config()
    text_links = load_text_file()
    
    existing_links = config.get('rss_links', [])
    combined_links = merge_and_deduplicate(existing_links, text_links)
    
    save_new_config(combined_links)

if __name__ == "__main__":
    main()
