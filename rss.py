import os
import json
import time
import feedparser
import threading
import argparse
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
from colorama import Fore, Style
from dateutil import parser as date_parser
from dateutil.tz import gettz

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'src', 'config.json')
INDEX_FILE = os.path.join(BASE_DIR, 'index.html')
HOMEPAGE_TEMPLATE = os.path.join(BASE_DIR, 'src', 'template_homepage_dark.html')  # Dark theme by default
UPDATE_INTERVAL = 3600  # Default to 1 hour if not specified in config

TZINFOS = {
    'GMT': gettz('GMT'),
    'UTC': gettz('UTC'),
    'EST': gettz('America/New_York'),
    'EDT': gettz('America/New_York'),
    'CST': gettz('America/Chicago'),
    'CDT': gettz('America/Chicago'),
    'MST': gettz('America/Denver'),
    'MDT': gettz('America/Denver'),
    'PST': gettz('America/Los_Angeles'),
    'PDT': gettz('America/Los_Angeles'),
    'HST': gettz('Pacific/Honolulu'),
    'AKST': gettz('America/Anchorage'),
    'AKDT': gettz('America/Anchorage'),
    'AST': gettz('America/Halifax'),
    'ADT': gettz('America/Halifax'),
    'NST': gettz('America/St_Johns'),
    'NDT': gettz('America/St_Johns'),
    'BST': gettz('Europe/London'),
    'CET': gettz('Europe/Paris'),
    'CEST': gettz('Europe/Paris'),
    'EET': gettz('Europe/Athens'),
    'EEST': gettz('Europe/Athens'),
    'IST': gettz('Asia/Kolkata'),
    'PKT': gettz('Asia/Karachi'),
    'WAT': gettz('Africa/Lagos'),
    'WET': gettz('Europe/Lisbon'),
    'WEST': gettz('Europe/Lisbon'),
    'CST-Asia': gettz('Asia/Shanghai'),
    'JST': gettz('Asia/Tokyo'),
    'KST': gettz('Asia/Seoul'),
    'AEST': gettz('Australia/Sydney'),
    'AEDT': gettz('Australia/Sydney'),
    'ACST': gettz('Australia/Adelaide'),
    'ACDT': gettz('Australia/Adelaide'),
    'AWST': gettz('Australia/Perth'),
    'NZST': gettz('Pacific/Auckland'),
    'NZDT': gettz('Pacific/Auckland'),
}


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

def generate_homepage(homepage_content):
    env = Environment(loader=FileSystemLoader(os.path.join(BASE_DIR, 'src')))
    template = env.get_template(os.path.basename(HOMEPAGE_TEMPLATE))
    return template.render(homepage_content=homepage_content)

def update_rss_feeds(config, template_file):
    homepage_content = ""
    max_entries = 1000  # Set the maximum number of entries allowed on each feed page

    for rss_info in config.get('rss_links', []):
        rss_url = rss_info.get('url')
        rss_title = rss_info.get('title', rss_url)
        rss_filename = rss_title.replace(" ", "_").lower() + '.html'
        rss_file_path = os.path.join(BASE_DIR, rss_filename)

        # Load existing content if it exists
        if os.path.exists(rss_file_path):
            with open(rss_file_path, 'r', encoding='utf-8') as file:
                existing_html = file.read()
        else:
            existing_html = ""

        # Fetch new feed data
        feed_data = []
        feed = fetch_rss_feed(rss_url)
        if feed:
            for entry in feed.entries:
                if entry.link not in existing_html:
                    # Use dateutil.parser to parse the date with tzinfos
                    published_date = date_parser.parse(entry.published, tzinfos=TZINFOS)
                    feed_data.append({
                        'title': entry.title,
                        'link': entry.link,
                        'published': published_date,
                        'summary': getattr(entry, 'summary', '')  # Use default empty string if summary doesn't exist
                    })

            # Sort the feed data by published date in descending order (most recent first)
            feed_data.sort(key=lambda x: x['published'], reverse=True)

        # Generate new HTML content and prepend it to the existing content
        new_html_content = generate_html(feed_data, template_file)
        combined_html_content = new_html_content + existing_html

        # Split the combined content into individual entries
        entries = combined_html_content.split('<hr>')  # Assuming each entry is separated by <hr> in the template
        if len(entries) > max_entries:
            entries = entries[:max_entries]  # Keep only the most recent entries

        # Combine the entries back into HTML
        combined_html_content = '<hr>'.join(entries)

        with open(rss_file_path, 'w', encoding='utf-8') as file:
            file.write(combined_html_content)

        homepage_content += f'<a href="{rss_filename}">{rss_title}</a><br>\n'

    homepage_html = generate_homepage(homepage_content)

    with open(INDEX_FILE, 'w', encoding='utf-8') as homepage_file:
        homepage_file.write(homepage_html)

    print(Fore.GREEN + f"{datetime.now()} - RSS feeds updated and index.html generated." + Style.RESET_ALL)


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
