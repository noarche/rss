import os
import json
import time
import feedparser
import threading
import argparse
import random
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
from datetime import timezone
from colorama import Fore, Style
from dateutil import parser as date_parser
from tqdm import tqdm
import requests
from http.server import SimpleHTTPRequestHandler, HTTPServer

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PAGES_DIR = os.path.join(BASE_DIR, 'pages')
SRC_DIR = os.path.join(BASE_DIR, 'src')
DEFAULT_CONFIG_FILE = os.path.join(SRC_DIR, 'config.json')
INDEX_FILE = os.path.join(PAGES_DIR, 'index.html')
HOMEPAGE_TEMPLATE = os.path.join(SRC_DIR, 'template_homepage_dark.html')
UPDATE_INTERVAL = 43200 # 28800 is 8hr and 43200 is 12hr and 86400 is 24hr

if not os.path.exists(PAGES_DIR):
    os.makedirs(PAGES_DIR)

# Import USER_AGENTS from user_agents.py
try:
    from user_agents import USER_AGENTS
except ImportError:
    print(Fore.RED + "Error: Could not find user_agents.py or USER_AGENTS list." + Style.RESET_ALL)
    USER_AGENTS = []

proxies = None

# Import timezone info from tzinfos.py
try:
    from tzinfos import TZINFOS
except ImportError:
    TZINFOS = {}

def load_config(config_file):
    try:
        with open(config_file, 'r') as file:
            return json.load(file)
    except json.JSONDecodeError as e:
        print(Fore.RED + f"Error parsing {config_file}: {e}" + Style.RESET_ALL)
        return {}

def fetch_rss_feed(url):
    try:
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        response = requests.get(url, headers=headers, proxies=proxies)
        response.raise_for_status()
        return feedparser.parse(response.content)
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

def update_rss_feeds(config, template_file, per_feed_sleep):
    homepage_content = ""
    max_entries = 80085691337

    rss_links = config.get('rss_links', [])
    with tqdm(total=len(rss_links), desc="Updating RSS Feeds", unit="page") as progress:
        for rss_info in rss_links:
            rss_url = rss_info.get('url')
            rss_title = rss_info.get('title', rss_url)
            rss_filename = rss_title.replace(" ", "_").lower() + '.html'
            rss_file_path = os.path.join(PAGES_DIR, rss_filename)

            if os.path.exists(rss_file_path):
                with open(rss_file_path, 'r', encoding='utf-8') as file:
                    existing_html = file.read()
            else:
                existing_html = ""

            feed_data = []
            feed = fetch_rss_feed(rss_url)
            if feed:
                for entry in feed.entries:
                    if entry.link not in existing_html:
                        published_date = None
                        if 'published' in entry:
                            published_date = date_parser.parse(entry.published, tzinfos=TZINFOS)
                        elif 'updated' in entry:
                            published_date = date_parser.parse(entry.updated, tzinfos=TZINFOS)
                        else:
                            published_date = datetime.now()

                        if published_date.tzinfo is None:
                            published_date = published_date.replace(tzinfo=timezone.utc)

                        feed_data.append({
                            'title': entry.title,
                            'link': entry.link,
                            'published': published_date,
                            'summary': getattr(entry, 'summary', '')
                        })

                feed_data.sort(key=lambda x: x['published'], reverse=True)

            new_html_content = generate_html(feed_data, template_file)
            combined_html_content = new_html_content + existing_html

            entries = combined_html_content.split('<hr>')
            if len(entries) > max_entries:
                entries = entries[:max_entries]

            combined_html_content = '<hr>'.join(entries)

            with open(rss_file_path, 'w', encoding='utf-8') as file:
                file.write(combined_html_content)

            homepage_content += f'<a href="{rss_filename}">{rss_title}</a><br>\n'
            progress.update(1)

            time.sleep(per_feed_sleep)

    homepage_html = generate_homepage(homepage_content)

    with open(INDEX_FILE, 'w', encoding='utf-8') as homepage_file:
        homepage_file.write(homepage_html)

    print(Fore.GREEN + f"{datetime.now()} - RSS feeds updated and index.html generated." + Style.RESET_ALL)

def start_feed_updater(template_file, config_file):
    while True:
        config = load_config(config_file)
        if not config:
            print(Fore.RED + "Failed to load configuration. Exiting." + Style.RESET_ALL)
            break

        per_feed_sleep = config.get('per_feed_sleep', 32.1)
        update_rss_feeds(config, template_file, per_feed_sleep)
        print(Fore.BLUE + f"Sleeping for {UPDATE_INTERVAL} seconds..." + Style.RESET_ALL)
        time.sleep(UPDATE_INTERVAL)

def start_http_server(port):
    os.chdir(PAGES_DIR)
    handler = SimpleHTTPRequestHandler
    httpd = HTTPServer(("", port), handler)
    print(Fore.GREEN + f"HTTP server started on port {port}." + Style.RESET_ALL)
    httpd.serve_forever()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RSS Feed HTML Generator")
    parser.add_argument("--light", action="store_true", help="Generate a light theme page")
    parser.add_argument("--dark", action="store_true", help="Generate a dark theme page")
    parser.add_argument("-tor", action="store_true", help="Use Tor proxy")
    parser.add_argument("-i2p", action="store_true", help="Use I2P proxy")
    parser.add_argument("-proxy", type=str, help="Use custom proxy in IP:PORT format")
    parser.add_argument("-config", type=str, help="Path to the configuration file", default=DEFAULT_CONFIG_FILE)
    parser.add_argument("-port", type=int, help="Port to run the HTTP server on")

    args = parser.parse_args()

    if args.light:
        TEMPLATE_FILE = os.path.join(SRC_DIR, 'template_light.html')
    elif args.dark:
        TEMPLATE_FILE = os.path.join(SRC_DIR, 'template_dark.html')
    else:
        TEMPLATE_FILE = os.path.join(SRC_DIR, 'template_dark.html')

    if args.tor:
        proxies = {"http": "socks5h://127.0.0.1:9150", "https": "socks5h://127.0.0.1:9150"}
    elif args.i2p:
        proxies = {"http": "http://127.0.0.1:4444", "https": "http://127.0.0.1:4444"}
    elif args.proxy:
        proxies = {"http": f"http://{args.proxy}", "https": f"http://{args.proxy}"}

    if args.port:
        threading.Thread(target=start_http_server, args=(args.port,), daemon=True).start()

    try:
        start_feed_updater(TEMPLATE_FILE, args.config)
    except KeyboardInterrupt:
        print(Fore.YELLOW + "Script terminated by user." + Style.RESET_ALL)
