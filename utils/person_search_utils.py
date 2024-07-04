import requests  
from bs4 import BeautifulSoup  
import re  
import os  
from dotenv import load_dotenv  
import json  
import tiktoken  
import logging  
from .openai_utils import moderate_content, openai, AZURE_OPENAI_ENDPOINT, OPENAI_API_KEY, AZURE_OPENAI_API_VERSION, OPENAI_MODEL  
  
# Load environment variables from .env file  
load_dotenv()  
  
# GLOBAL VARIABLES  
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'  
SEARCH_URL = 'https://www.google.com/search?q='  
WHITELISTED_DOMAINS = ["linkedin.com", "twitter.com", "medium.com", "about.me", "facebook.com", "youtube.com"]  
GPT_MODEL = "gpt-4-turbo"  
MAX_NUMBER_OF_RESULTS_FROM_LINKEDIN = 5  
MAX_NUMBER_OF_RESULTS_IN_GENERAL = 5  
  
# CATEGORY_THRESHOLDS definition  
CATEGORY_THRESHOLDS = {key: 0.01 for key in [  
    'sexual', 'hate', 'harassment', 'self-harm', 'sexual/minors',  
    'hate/threatening', 'violence/graphic', 'self-harm/intent',  
    'self-harm/instructions', 'harassment/threatening', 'violence'  
]}  
  
# Logging configuration  
logging.basicConfig(level=logging.DEBUG)  
logger = logging.getLogger(__name__)  
  
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
  
def num_tokens(text):  
    return len(tiktoken.encoding_for_model(GPT_MODEL).encode(text))  
  
def filter_phrases(content):  
    for phrase in FILTER_PHRASES:  
        content = content.replace(phrase, '')  
    return re.sub(r'(\s)+', ' ', content).strip()  
  
def clean_linkedin_content(content):  
    for phrase in LINKEDIN_FILTER_PHRASES:  
        content = content.replace(phrase, '')  
    return re.sub(r'(\s)+', ' ', content).strip()  
  
def clean_html_content(html_content):  
    soup = BeautifulSoup(html_content, 'html.parser')  
    for tag in soup(['style', 'script', 'head', 'title', 'meta', '[document]']):  
        tag.decompose()  
    return ' '.join(soup.stripped_strings)  
  
def google_search(query):  
    query = query.replace(' ', '+')  
    headers = {'User-Agent': USER_AGENT}  
    url = f'{SEARCH_URL}{query}'  
    response = requests.get(url, headers=headers)  
    if response.status_code != 200:  
        raise Exception(f'Failed to load page: {response.status_code}')  
  
    # Clean the response text to remove unnecessary HTML and CSS  
    cleaned_response_text = clean_html_content(response.text)  
  
    # Log the cleaned response text  
    logger.debug(f"PERSON_SEARCH_UTILS.PY>>> Cleaned response payload from Google search {url}: {cleaned_response_text}")  
  
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
                logger.error(f"PERSON_SEARCH_UTILS.PY>>> Error during content moderation: {e}")  
                scores, safe = {}, True  
            if safe:  
                results.append({'title': title, 'link': link, 'domain': domain, 'content': None})  
    return results  
  
def google_search_linkedin_posts(query):  
    return google_search(f'{query} site:linkedin.com')  
  
def google_search_linkedin_profile(query):  
    return google_search(f'{query} site:linkedin.com/in/')  
  
def extract_main_content(url, user_name):  
    headers = {'User-Agent': USER_AGENT}  
    response = requests.get(url, headers=headers)  
    if response.status_code != 200:  
        return None, None  
  
    # Clean the response text to remove unnecessary HTML and CSS  
    cleaned_response_text = clean_html_content(response.text)  
  
    # Log the cleaned response text  
    logger.debug(f"PERSON_SEARCH_UTILS.PY>>> Cleaned response payload from {url}: {cleaned_response_text}")  
  
    soup = BeautifulSoup(response.text, 'html.parser')  
    for tag in soup(['script', 'style', 'footer', 'nav', '[class*="ad"]', 'header']):  
        tag.decompose()  
    domain = re.search(r"https?://(www\.)?([^/]+)", url).group(2)  
  
    # Identify and extract the author  
    author = None  
    if 'linkedin.com' in url:  
        author_tag = soup.find('span', {'class': 'feed-shared-actor__name'})  
        if author_tag:  
            author = author_tag.get_text().strip()  
  
    text_content = (' '.join(  
        [container.get_text().strip() for container in soup.find_all(['p', 'div', 'span'])]  
    ) if 'linkedin.com' not in url else clean_linkedin_content(  
        ' '.join([post.get_text().strip() for post in soup.find_all('p')]))).strip()  
  
    # Filter irrelevant content  
    if author and user_name not in author:  
        return None, None  
  
    try:  
        if not text_content or len(text_content) < 300 or (domain not in WHITELISTED_DOMAINS and not moderate_content(text_content)['flagged']):  
            return None, author  
    except Exception as e:  
        logger.error(f"PERSON_SEARCH_UTILS.PY>>> Error during content moderation: {e}")  
  
    # Apply the filter_phrases function to clean the content  
    return filter_phrases(text_content), author  
  
async def search_person(query):  
    linkedin_profile_results = google_search_linkedin_profile(query)[:1]  # Try to find the main profile page  
    linkedin_post_results = google_search_linkedin_posts(query)[:MAX_NUMBER_OF_RESULTS_FROM_LINKEDIN - len(linkedin_profile_results)]  
    general_results = google_search(query)[:MAX_NUMBER_OF_RESULTS_IN_GENERAL]  
  
    # Combine results and ensure we get at least 5 LinkedIn and 5 non-LinkedIn URLs  
    combined_results = linkedin_profile_results + linkedin_post_results  
    non_linkedin_results = [result for result in general_results if 'linkedin.com' not in result['domain']]  
    combined_results += non_linkedin_results[:5 - len(linkedin_post_results)]  
    if len(combined_results) < 10:  
        combined_results += general_results[:10 - len(combined_results)]  
  
    user_name = query.split()[0]  # Assume the first word in the query is the user's name  
    for result in combined_results:  
        content, author = extract_main_content(result['link'], user_name)  
        result['content'] = content  
        result['author'] = author  
  
    valid_results = [result for result in combined_results if result['content']]  
    if not valid_results:  
        return "No valid results found for the given query.", "placeholder_model", 0, 0, []  
  
    all_results_text = ' '.join(json.dumps(result) for result in valid_results)  
    # Collect URLs  
    urls = [result['link'] for result in valid_results]  
  
    # Send all data in one request to OpenAI  
    messages = [  
        {  
            "role": "system",  
            "content": "You are a helpful assistant that summarizes the topics a user talks about online from a set of web content. Ensure the content is specifically about the person being searched and avoid making incorrect inferences. Do not mention the blurred face in the response."  
        },  
        {  
            "role": "user",  
            "content": f"Use up to 20 bullet points to describe some of the topics this person talks about online based on the provided content. For each topic, include a citation mentioning where and what was talked about in a sentence or two: {all_results_text[:5000]}"  
        }  
    ]  
  
    client = openai.AzureOpenAI(  
        azure_endpoint=AZURE_OPENAI_ENDPOINT,  
        api_key=OPENAI_API_KEY,  
        api_version=AZURE_OPENAI_API_VERSION  
    )  
    response = client.chat.completions.create(  
        model=OPENAI_MODEL,  
        messages=messages,  
        temperature=0.5,  
        max_tokens=2000,  
        top_p=0.95,  
        frequency_penalty=0,  
        presence_penalty=0  
    )  
  
    if response and response.choices:  
        career_summary = response.choices[0].message.content  
        model_name = response.model  
        input_tokens = response.usage.prompt_tokens  
        output_tokens = response.usage.completion_tokens  
    else:  
        career_summary = "Could not generate a summary for the given user query."  
        model_name = "placeholder_model"  
        input_tokens = 0  
        output_tokens = 0  
  
    return career_summary, model_name, input_tokens, output_tokens, urls  
