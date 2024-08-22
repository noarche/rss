import os
import json
import time
import feedparser
import threading
import argparse
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
from colorama import Fore, Style

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'src', 'config.json')
HTML_FILE = os.path.join(BASE_DIR, 'rss_feed.html')
UPDATE_INTERVAL = 3600  # Default to 1 hour if not specified in config

def load_config():
    with open(CONFIG_FILE, 'r') as file:
        config = json.load(file)
    return config

def fetch_rss_feed(url):
    try:
        return feedparser.parse(url)
    except Exception as e:
        print(Fore.RED + f"Error fetching RSS feed: {e}" + Style.RESET_ALL)
        return None

def generate_html(feed_data, template_file):
    env = Environment(loader=FileSystemLoader(os.path.join(BASE_DIR, 'src')))
    template = env.get_template(os.path.basename(template_file))
    return template.render(feeds=feed_data)

def update_rss_feeds(config, template_file):
    # Load existing content if it exists
    if os.path.exists(HTML_FILE):
        with open(HTML_FILE, 'r', encoding='utf-8') as file:
            existing_html = file.read()
    else:
        existing_html = ""

    # Fetch new feed data
    feed_data = []
    for rss_link in config.get('rss_links', []):
        feed = fetch_rss_feed(rss_link)
        if feed:
            for entry in feed.entries:
                if entry.link not in existing_html:
                    feed_data.append({
                        'title': entry.title,
                        'link': entry.link,
                        'published': entry.published,
                        'summary': entry.summary
                    })

    # Generate new HTML content and append it
    new_html_content = generate_html(feed_data, template_file)
    combined_html_content = existing_html + new_html_content

    with open(HTML_FILE, 'w', encoding='utf-8') as file:
        file.write(combined_html_content)

    print(Fore.GREEN + f"{datetime.now()} - HTML updated with latest RSS feeds." + Style.RESET_ALL)

def start_feed_updater(template_file):
    while True:
        config = load_config()
        update_interval = config.get('update_interval', UPDATE_INTERVAL)
        update_rss_feeds(config, template_file)
        print(Fore.BLUE + f"Sleeping for {update_interval} seconds..." + Style.RESET_ALL)
        time.sleep(update_interval)
        print(Fore.BLUE + "Restarting feed update process..." + Style.RESET_ALL)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RSS Feed HTML Generator")
    parser.add_argument("--light", action="store_true", help="Generate a light theme page")
    parser.add_argument("--dark", action="store_true", help="Generate a dark theme page")
    
    args = parser.parse_args()

    if args.light:
        TEMPLATE_FILE = os.path.join(BASE_DIR, 'src', 'template_light.html')
    elif args.dark:
        TEMPLATE_FILE = os.path.join(BASE_DIR, 'src', 'template_dark.html')
    else:
        TEMPLATE_FILE = os.path.join(BASE_DIR, 'src', 'template_light.html')  # Default to light theme

    try:
        while True:
            start_feed_updater(TEMPLATE_FILE)
            time.sleep(3600)  # Restart script after sleeping for 1 hour
    except KeyboardInterrupt:
        print(Fore.YELLOW + "Script terminated by user." + Style.RESET_ALL)
