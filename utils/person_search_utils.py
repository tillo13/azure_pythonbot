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
    logging.debug(f"Cleaned response payload from Google search {url}: {cleaned_response_text}")  
  
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
  
def extract_main_content(url, user_name):  
    headers = {'User-Agent': USER_AGENT}  
    response = requests.get(url, headers=headers)  
    if response.status_code != 200:  
        return None, None  
  
    # Clean the response text to remove unnecessary HTML and CSS  
    cleaned_response_text = clean_html_content(response.text)  
  
    # Log the cleaned response text  
    logging.debug(f"Cleaned response payload from {url}: {cleaned_response_text}")  
  
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
        logging.error(f"Error during content moderation: {e}")  
  
    # Apply the filter_phrases function to clean the content  
    return filter_phrases(text_content), author  
  
async def search_person(query):  
    # Perform LinkedIn search  
    linkedin_results = google_search_linkedin_posts(query)  
      
    # Perform non-LinkedIn search  
    non_linkedin_query = f'{query} -site:linkedin.com'  
    non_linkedin_results = google_search(non_linkedin_query)  
  
    # Limit the number of responses to MAX_NUMBER_OF_RESPONSE for each search  
    linkedin_results = linkedin_results[:MAX_NUMBER_OF_RESPONSE]  
    non_linkedin_results = non_linkedin_results[:MAX_NUMBER_OF_RESPONSE]  
  
    user_name = query.split()[0]  # Assume the first word in the query is the user's name  
  
    # Process LinkedIn results  
    for result in linkedin_results:  
        content, author = extract_main_content(result['link'], user_name)  
        result['content'] = content  
        result['author'] = author  
  
    # Process non-LinkedIn results  
    for result in non_linkedin_results:  
        content, author = extract_main_content(result['link'], user_name)  
        result['content'] = content  
        result['author'] = author  
  
    # Filter valid results  
    valid_linkedin_results = [result for result in linkedin_results if result['content']]  
    valid_non_linkedin_results = [result for result in non_linkedin_results if result['content']]  
  
    if not valid_linkedin_results and not valid_non_linkedin_results:  
        return "No valid results found for the given query.", "placeholder_model", 0, 0, []  
  
    # Prepare the content for OpenAI  
    linkedin_results_text = ' '.join(json.dumps(result) for result in valid_linkedin_results)  
    non_linkedin_results_text = ' '.join(json.dumps(result) for result in valid_non_linkedin_results)  
  
    # Collect URLs  
    linkedin_urls = [result['link'] for result in valid_linkedin_results]  
    non_linkedin_urls = [result['link'] for result in valid_non_linkedin_results]  
  
    # Send LinkedIn data in one request to OpenAI  
    linkedin_messages = [{"role": "system", "content": "You are a helpful assistant that summarizes career events of a user from a set of web content. Ensure the content is specifically about the person being searched and avoid making incorrect inferences."},  
                         {"role": "user", "content": f"Use up to 20 bullet points to describe this person's work history and abilities based on the provided LinkedIn content. Make sure to verify the context and avoid including irrelevant information: {linkedin_results_text[:5000]}"}]  
  
    client = openai.AzureOpenAI(  
        azure_endpoint=AZURE_OPENAI_ENDPOINT,  
        api_key=OPENAI_API_KEY,  
        api_version=AZURE_OPENAI_API_VERSION  
    )  
    linkedin_response = client.chat.completions.create(  
        model=OPENAI_MODEL,  
        messages=linkedin_messages,  
        temperature=0.5,  
        max_tokens=2000,  
        top_p=0.95,  
        frequency_penalty=0,  
        presence_penalty=0  
    )  
  
    if linkedin_response and linkedin_response.choices:  
        linkedin_career_summary = linkedin_response.choices[0].message.content  
        linkedin_model_name = linkedin_response.model  
        linkedin_input_tokens = linkedin_response.usage.prompt_tokens  
        linkedin_output_tokens = linkedin_response.usage.completion_tokens  
    else:  
        linkedin_career_summary = "Could not generate a summary for the given LinkedIn query."  
        linkedin_model_name = "placeholder_model"  
        linkedin_input_tokens = 0  
        linkedin_output_tokens = 0  
  
    # Send non-LinkedIn data in another request to OpenAI  
    non_linkedin_messages = [{"role": "system", "content": "You are a helpful assistant that summarizes personal information of a user from a set of web content. Ensure the content is specifically about the person being searched and avoid making incorrect inferences."},  
                             {"role": "user", "content": f"Use up to 20 bullet points to describe this person's personal information based on the provided non-LinkedIn content. Make sure to verify the context and avoid including irrelevant information: {non_linkedin_results_text[:5000]}"}]  
  
    non_linkedin_response = client.chat.completions.create(  
        model=OPENAI_MODEL,  
        messages=non_linkedin_messages,  
        temperature=0.5,  
        max_tokens=2000,  
        top_p=0.95,  
        frequency_penalty=0,  
        presence_penalty=0  
    )  
  
    if non_linkedin_response and non_linkedin_response.choices:  
        non_linkedin_summary = non_linkedin_response.choices[0].message.content  
        non_linkedin_model_name = non_linkedin_response.model  
        non_linkedin_input_tokens = non_linkedin_response.usage.prompt_tokens  
        non_linkedin_output_tokens = non_linkedin_response.usage.completion_tokens  
    else:  
        non_linkedin_summary = "Could not generate a summary for the given non-LinkedIn query."  
        non_linkedin_model_name = "placeholder_model"  
        non_linkedin_input_tokens = 0  
        non_linkedin_output_tokens = 0  
  
    return (linkedin_career_summary, linkedin_model_name, linkedin_input_tokens, linkedin_output_tokens, linkedin_urls,  
            non_linkedin_summary, non_linkedin_model_name, non_linkedin_input_tokens, non_linkedin_output_tokens, non_linkedin_urls)  
