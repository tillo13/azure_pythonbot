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
MAX_NUMBER_OF_RESPONSE = 10  # Maximum number of articles to process  
  
# CATEGORY_THRESHOLDS definition  
CATEGORY_THRESHOLDS = {key: 0.01 for key in [  
    'sexual', 'hate', 'harassment', 'self-harm', 'sexual/minors',  
    'hate/threatening', 'violence/graphic', 'self-harm/intent',  
    'self-harm/instructions', 'harassment/threatening', 'violence'  
]}  
  
# Logging configuration  
logging.basicConfig(level=logging.DEBUG)  
  
# Define phrases to filter out  
FILTER_PHRASES = [  
    "Skip to main content", "Follow to get new release updates",  
    "Get to Know Us", "Make Money with Us", "Amazon Payment Products",  
    "Let Us Help You", "Sign in to view", "Sign in", "By clicking Continue to join or sign in",  
    "New to LinkedIn? Join now", "Forgot password?", "Sign in", "or"  
]  
  
LINKEDIN_FILTER_PHRASES = [  
    "By clicking Continue to join or sign in, you agree to LinkedIn’s User Agreement, Privacy Policy, and Cookie Policy.",  
    "By clicking Continue to join sign in, you agree LinkedIn’s User Agreement, Privacy Policy, and Cookie Policy.",  
    "New to LinkedIn? Join now", "Agree & Join LinkedIn"  
]  
  
def filter_phrases(content):  
    for phrase in FILTER_PHRASES:  
        content = content.replace(phrase, '')  
    return re.sub(r'(\s)+', ' ', content).strip()  
  
def clean_linkedin_content(content):  
    for phrase in LINKEDIN_FILTER_PHRASES:  
        content = content.replace(phrase, '')  
    return re.sub(r'(\s)+', ' ', content).strip()  
  
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
  
def google_search_linkedin_posts(query):  
    return google_search(f'{query} site:linkedin.com')  
  
def extract_main_content(url):  
    headers = {'User-Agent': USER_AGENT}  
    response = requests.get(url, headers=headers)  
    if response.status_code != 200:  
        return None  
    soup = BeautifulSoup(response.text, 'html.parser')  
    for tag in soup(['script', 'style', 'footer', 'nav', '[class*="ad"]', 'header']):  
        tag.decompose()  
    domain = re.search(r"https?://(www\.)?([^/]+)", url).group(2)  
    text_content = (' '.join(  
        [container.get_text().strip() for container in soup.find_all(['p', 'div', 'span'])]  
    ) if 'linkedin.com' not in url else clean_linkedin_content(  
        ' '.join([post.get_text().strip() for post in soup.find_all('p')]))).strip()  
    try:  
        if not text_content or len(text_content) < 300 or (domain not in WHITELISTED_DOMAINS and not moderate_content(text_content)['flagged']):  
            return None  
    except Exception as e:  
        logging.error(f"Error during content moderation: {e}")  
    # Apply the filter_phrases function to clean the content  
    return filter_phrases(text_content)  
  
def num_tokens(text):  
    return len(tiktoken.encoding_for_model(GPT_MODEL).encode(text))  
  
async def search_person(query):  
    # Professional career (LinkedIn focus)  
    linkedin_results = google_search_linkedin_posts(query)  
    linkedin_results = linkedin_results[:MAX_NUMBER_OF_RESPONSE]  
    for result in linkedin_results:  
        content = extract_main_content(result['link'])  
        result['content'] = content  
    valid_linkedin_results = [result for result in linkedin_results if result['content']]  
      
    if valid_linkedin_results:  
        linkedin_text = ' '.join(json.dumps(result) for result in valid_linkedin_results)  
        linkedin_messages = [{"role": "system", "content": "You are a helpful assistant that summarizes professional career events from web content."},  
                             {"role": "user", "content": f"Summarize the following professional career information in less than 2500 characters: {linkedin_text[:1000]}"}]  
        client = openai.AzureOpenAI(  
            azure_endpoint=AZURE_OPENAI_ENDPOINT,  
            api_key=OPENAI_API_KEY,  
            api_version=AZURE_OPENAI_API_VERSION  
        )  
        linkedin_response = client.chat.completions.create(  
            model=OPENAI_MODEL,  
            messages=linkedin_messages,  
            temperature=0.5,  
            max_tokens=1000,  
            top_p=0.95,  
            frequency_penalty=0,  
            presence_penalty=0  
        )  
        if linkedin_response and linkedin_response.choices:  
            professional_summary = linkedin_response.choices[0].message.content  
        else:  
            professional_summary = "Could not generate a professional career summary for the given query."  
    else:  
        professional_summary = "No valid LinkedIn results found for the given query."  
  
    # Personal life (other websites focus)  
    other_results = google_search(query)  
    other_results = other_results[:MAX_NUMBER_OF_RESPONSE]  
    for result in other_results:  
        content = extract_main_content(result['link'])  
        result['content'] = content  
    valid_other_results = [result for result in other_results if result['content']]  
      
    if valid_other_results:  
        other_text = ' '.join(json.dumps(result) for result in valid_other_results)  
        other_messages = [{"role": "system", "content": "You are a helpful assistant that summarizes personal life events from web content."},  
                          {"role": "user", "content": f"Summarize the following personal life information in less than 2500 characters: {other_text[:1000]}"}]  
        other_response = client.chat.completions.create(  
            model=OPENAI_MODEL,  
            messages=other_messages,  
            temperature=0.5,  
            max_tokens=1000,  
            top_p=0.95,  
            frequency_penalty=0,  
            presence_penalty=0  
        )  
        if other_response and other_response.choices:  
            personal_summary = other_response.choices[0].message.content  
        else:  
            personal_summary = "Could not generate a personal life summary for the given query."  
    else:  
        personal_summary = "No valid non-LinkedIn results found for the given query."  
  
    return professional_summary, personal_summary  
