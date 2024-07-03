# person_search_utils.py  
  
import requests  
from bs4 import BeautifulSoup  
import re  
import openai  
import os  
from dotenv import load_dotenv  
import json  
import tiktoken  
import logging  
  
# Load environment variables from .env file  
load_dotenv()  
  
# GLOBAL VARIABLES  
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'  
SEARCH_URL = 'https://www.google.com/search?q='  
WHITELISTED_DOMAINS = ["linkedin.com", "twitter.com", "medium.com", "about.me", "facebook.com", "youtube.com"]  
GPT_MODEL = "gpt-4-turbo"  
  
# CATEGORY_THRESHOLDS definition  
CATEGORY_THRESHOLDS = {key: 0.01 for key in [  
    'sexual', 'hate', 'harassment', 'self-harm', 'sexual/minors',  
    'hate/threatening', 'violence/graphic', 'self-harm/intent',  
    'self-harm/instructions', 'harassment/threatening', 'violence'  
]}  
  
# OpenAI API Configuration  
OPENAI_API_KEY = os.getenv('APPSETTING_2024may22_GPT4o_API_KEY')  
AZURE_OPENAI_ENDPOINT = os.getenv("APPSETTING_AZURE_OPENAI_ENDPOINT")  
AZURE_OPENAI_API_VERSION = os.getenv("APPSETTING_AZURE_OPENAI_API_VERSION")  
openai.api_key = OPENAI_API_KEY  
  
# Logging configuration  
logging.basicConfig(level=logging.DEBUG)  
  
def google_search(query):  
    query = query.replace(' ', '+')  
    headers = {'User-Agent': USER_AGENT}  
    url = f'{SEARCH_URL}{query}'  
    response = requests.get(url, headers=headers)  
    if response.status_code != 200:  
        raise Exception(f'Failed to load page: {response.status_code}')  
    results = []  
    soup = BeautifulSoup(response.text, 'html.parser')  
    for item in soup.select('.tF2Cxc'):  
        title_element = item.select_one('.DKV0Md')  
        link_element = item.select_one('.yuRUbf a')  
        if title_element and link_element:  
            title, link = title_element.text, link_element['href']  
            domain = re.search(r"https?://(www\.)?([^/]+)", link).group(2)  
            scores, safe = ({}, True) if domain in WHITELISTED_DOMAINS else is_content_safe(title)  
            if safe:  
                results.append({'title': title, 'link': link, 'domain': domain, 'content': None})  
    return results  
  
def is_content_safe(content):  
    response = openai.Moderation.create(input=content)  
    categories = response['results'][0]['categories']  
    category_scores = response['results'][0]['category_scores']  
    scores, flagged = {}, False  
    for category, value in categories.items():  
        score = category_scores[category]  
        scores[category], threshold = score, CATEGORY_THRESHOLDS.get(category, 0.01)  
        if value or score >= threshold:  
            flagged = True  
    return scores, not flagged  
  
def extract_main_content(url):  
    headers = {'User-Agent': USER_AGENT}  
    response = requests.get(url, headers=headers)  
    if response.status_code != 200:  
        return None  
    soup = BeautifulSoup(response.text, 'html.parser')  
    for tag in soup(['script', 'style', 'footer', 'nav', '[class*="ad"]', 'header']):  
        tag.decompose()  
    domain = re.search(r"https?://(www\.)?([^/]+)", url).group(2)  
    text_content = ' '.join([container.get_text().strip() for container in soup.find_all(['p', 'div', 'span'])]).strip()  
    if not text_content or len(text_content) < 300 or (domain not in WHITELISTED_DOMAINS and not is_content_safe(text_content)[1]):  
        return None  
    return text_content  
  
def num_tokens(text):  
    return len(tiktoken.encoding_for_model(GPT_MODEL).encode(text))  
  
def chunk_text(text, max_chunk_size):  
    chunks, current_chunk, current_length = [], [], 0  
    for word in text.split():  
        word_length = num_tokens(word)  
        if current_length + word_length + 1 > max_chunk_size:  
            chunks.append(' '.join(current_chunk))  
            current_chunk, current_length = [word], word_length + 1  
        else:  
            current_chunk.append(word)  
            current_length += word_length + 1  
    if current_chunk:  
        chunks.append(' '.join(current_chunk))  
    return chunks  
  
async def search_person(query):  
    combined_results = google_search(query)  
    for result in combined_results:  
        content = extract_main_content(result['link'])  
        result['content'] = content  
    valid_results = [result for result in combined_results if result['content']]  
    if not valid_results:  
        return "No valid results found for the given query."  
  
    identified_person_info = ""  
    for result in valid_results:  
        messages = [{"role": "system", "content": "You are a helpful assistant that identifies individuals based on web content."},  
                    {"role": "user", "content": f"Pieces of information about '{query}' identified: {json.dumps(result)[:1000]}"}]  
        response = openai.ChatCompletion.create(model=GPT_MODEL, messages=messages)  
        if response and response.choices:  
            identified_person_info += response.choices[0].message['content']  
  
    if not identified_person_info:  
        return "Could not identify any relevant information for the given query."  
  
    return identified_person_info  
