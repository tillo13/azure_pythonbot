import requests  
from bs4 import BeautifulSoup  
import re  
import os  
from dotenv import load_dotenv  
import json  
import tiktoken  
import logging  
from .openai_utils import openai, AZURE_OPENAI_ENDPOINT, OPENAI_API_KEY, AZURE_OPENAI_API_VERSION, OPENAI_MODEL  
  
# Load environment variables from .env file  
load_dotenv()  
  
# GLOBAL VARIABLES  
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'  
SEARCH_URL = 'https://www.google.com/search?q='  
WHITELISTED_DOMAINS = ["linkedin.com", "twitter.com", "medium.com", "about.me", "facebook.com", "youtube.com"]  
GPT_MODEL = "gpt-4-turbo"  
MAX_NUMBER_OF_RESULTS_FROM_LINKEDIN = 5  
MAX_NUMBER_OF_RESULTS_IN_GENERAL = 10  
  
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
  
    cleaned_response_text = clean_html_content(response.text)  
    logger.debug(f"PERSON_SEARCH_UTILS.PY>>> Cleaned response payload from Google search {url}: {cleaned_response_text}")  
  
    results = []  
    soup = BeautifulSoup(response.text, 'html.parser')  
    for item in soup.select('.tF2Cxc'):  
        title_element = item.select_one('.DKV0Md')  
        link_element = item.select_one('.yuRUbf a')  
        if title_element and link_element:  
            title, link = title_element.text, link_element['href']  
            domain = re.search(r"https?://(www\.)?([^/]+)", link).group(2)  
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
  
    cleaned_response_text = clean_html_content(response.text)  
    logger.debug(f"PERSON_SEARCH_UTILS.PY>>> Cleaned response payload from {url}: {cleaned_response_text}")  
  
    soup = BeautifulSoup(response.text, 'html.parser')  
    for tag in soup(['script', 'style', 'footer', 'nav', '[class*="ad"]', 'header']):  
        tag.decompose()  
    domain = re.search(r"https?://(www\.)?([^/]+)", url).group(2)  
  
    author = None  
    if 'linkedin.com' in url:  
        author_tag = soup.find('span', {'class': 'feed-shared-actor__name'})  
        if author_tag:  
            author = author_tag.get_text().strip()  
  
    text_content = (' '.join(  
        [container.get_text().strip() for container in soup.find_all(['p', 'div', 'span'])]  
    ) if 'linkedin.com' not in url else clean_linkedin_content(  
        ' '.join([post.get_text().strip() for post in soup.find_all('p')]))).strip()  
  
    if author and user_name not in author:  
        return None, None  
  
    return filter_phrases(text_content), author  
  
def calculate_likelihood_score(query, valid_results):  
    score = 10  # Start with the minimum score  
    max_score = 90  
  
    # Increase score based on the presence of "Teradata"  
    for result in valid_results:  
        if 'teradata' in result['title'].lower() or 'teradata' in result['content'].lower():  
            score += 30  # High weight for Teradata presence  
  
    # Increase score based on author name match  
    for result in valid_results:  
        if result['author'] and query.split()[0].lower() in result['author'].lower():  
            score += 20  # Medium weight for author name match  
  
    # Increase score based on the number of valid results  
    score += len(valid_results) * 5  # Small weight for each valid result  
  
    # Ensure the queried name is mentioned in the content  
    for result in valid_results:  
        if query.lower() in result['content'].lower():  
            score += 10  # Additional weight for name match in content  
  
    # Normalize the score to be within 10 to 90  
    score = min(max(score, 10), max_score)  
  
    return score  
  
def format_for_slack(bullet_points):  
    formatted_text = ""  
    for index, point in enumerate(bullet_points, 1):  
        point = point.strip()  
        if point and not point.startswith(f"{index}."):  
            formatted_text += f"{index}. {point}\n\n"  
    return formatted_text.strip()  
  
async def search_person(query):  
    linkedin_profile_results = google_search_linkedin_profile(query)[:MAX_NUMBER_OF_RESULTS_FROM_LINKEDIN]  
    linkedin_post_results = google_search_linkedin_posts(query)[:MAX_NUMBER_OF_RESULTS_FROM_LINKEDIN]  
    general_results = google_search(query)[:MAX_NUMBER_OF_RESULTS_IN_GENERAL]  
  
    combined_results = linkedin_profile_results + linkedin_post_results + general_results  
    combined_results = combined_results[:10]  
  
    user_name = query.split()[0]  
    for result in combined_results:  
        content, author = extract_main_content(result['link'], user_name)  
        result['content'] = content  
        result['author'] = author  
  
    valid_results = [result for result in combined_results if result['content']]  
  
    # Retry with "Teradata" filter if no valid results found  
    if not valid_results:  
        teradata_query = f"{query} Teradata"  
        linkedin_profile_results = google_search_linkedin_profile(teradata_query)[:MAX_NUMBER_OF_RESULTS_FROM_LINKEDIN]  
        linkedin_post_results = google_search_linkedin_posts(teradata_query)[:MAX_NUMBER_OF_RESULTS_FROM_LINKEDIN]  
        general_results = google_search(teradata_query)[:MAX_NUMBER_OF_RESULTS_IN_GENERAL]  
  
        combined_results = linkedin_profile_results + linkedin_post_results + general_results  
        combined_results = combined_results[:10]  
  
        for result in combined_results:  
            content, author = extract_main_content(result['link'], user_name)  
            result['content'] = content  
            result['author'] = author  
  
        valid_results = [result for result in combined_results if result['content']]  
  
    if not valid_results:  
        return "We tried a few things, but couldn't deduce the person in question. Can you tell me a bit more about them?", "placeholder_model", 0, 0, []  
  
    all_results_text = ' '.join(json.dumps(result) for result in valid_results)  
    urls = [result['link'] for result in valid_results]  
  
    messages = [  
        {  
            "role": "system",  
            "content": "You are a helpful assistant that summarizes the topics a user talks about or interacts with online from a set of web content. Ensure the content is specifically about the person being searched and avoid making incorrect inferences."  
        },  
        {  
            "role": "user",  
            "content": f"Use up to 20 bullet points to describe some of the topics this person talks about or interacts with online based on the provided content. Each topic must mention '{query}' (the person being searched). Do not include any information or make any inferences about other individuals. For each topic, include a citation mentioning where and what was talked about in a sentence or two. Ensure to include 'Source' at the end of each citation. The citation format should be 'Source: {link}'. Here is the content: {all_results_text[:8000]}"  
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
        max_tokens=4096,  
        top_p=0.95,  
        frequency_penalty=0,  
        presence_penalty=0  
    )  
  
    if response and response.choices:  
        career_summary = response.choices[0].message.content  
        model_name = response.model  
        input_tokens = response.usage.prompt_tokens  
        output_tokens = response.usage.completion_tokens  
  
        # Filter out bullet points that do not mention the queried name  
        filtered_summary = []  
        for line in career_summary.split('\n'):  
            if query.lower() in line.lower():  
                filtered_summary.append(line)  
  
        career_summary = '\n'.join(filtered_summary)  
  
        if not filtered_summary:  
            career_summary = "No relevant information found about the person queried."  
        else:  
            bullet_points = career_summary.split('\n')  
            career_summary = format_for_slack(bullet_points)  
  
    else:  
        career_summary = "Could not generate a summary for the given user query."  
        model_name = "placeholder_model"  
        input_tokens = 0  
        output_tokens = 0  
  
    # Calculate likelihood score  
    likelihood_score = calculate_likelihood_score(query, valid_results)  
  
    sources_list = "\n\nHere are some of the URLs we used to deduce this information:\n" + '\n'.join(urls)  
    career_summary += sources_list  
    career_summary += f"\n\n*Estimated Likelihood that this is the correct person:* `{likelihood_score}%`"  
  
    return career_summary, model_name, input_tokens, output_tokens, urls  
