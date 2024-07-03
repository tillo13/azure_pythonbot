# person_search_utils.py  
import requests  
from bs4 import BeautifulSoup  
import re  
import os  
from dotenv import load_dotenv  
import json  
import tiktoken  
import logging  
from .openai_utils import moderate_content, openai, AZURE_OPENAI_ENDPOINT, OPENAI_API_KEY, AZURE_OPENAI_API_VERSION, OPENAI_MODEL  # Import the necessary variables and functions  
  
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
            try:  
                scores, safe = ({}, True) if domain in WHITELISTED_DOMAINS else moderate_content(title)  
                if scores is None:  # Handle the case where moderate_content returns None  
                    safe = True  # Default to safe if content moderation fails  
            except Exception as e:  
                logging.error(f"Error during content moderation: {e}")  
                scores, safe = {}, True  
            if safe:  
                results.append({'title': title, 'link': link, 'domain': domain, 'content': None})  
    return results  
  
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
    try:  
        if not text_content or len(text_content) < 300 or (domain not in WHITELISTED_DOMAINS and not moderate_content(text_content)['flagged']):  
            return None  
    except Exception as e:  
        logging.error(f"Error during content moderation: {e}")  
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
        client = openai.AzureOpenAI(  
            azure_endpoint=AZURE_OPENAI_ENDPOINT,  
            api_key=OPENAI_API_KEY,  
            api_version=AZURE_OPENAI_API_VERSION  
        )  
        response = client.chat.completions.create(  
            model=OPENAI_MODEL,  
            messages=messages,  
            temperature=0.5,  
            max_tokens=1000,  
            top_p=0.95,  
            frequency_penalty=0,  
            presence_penalty=0  
        )  
        if response and response.choices:  
            identified_person_info += response.choices[0].message.content  
      
    if not identified_person_info:  
        return "Could not identify any relevant information for the given query."  
      
    return identified_person_info  