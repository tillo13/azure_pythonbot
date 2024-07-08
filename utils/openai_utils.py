import os  
import base64  
import openai  
import re  
import time  
import datetime  
import PyPDF2  
from dotenv import load_dotenv  
import tiktoken  
from azure.identity import DefaultAzureCredential, get_bearer_token_provider  
import json  
from docx import Document  
import io  
import logging  
  
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')  
  
# Load environment variables from .env file  
load_dotenv()  
  
### GLOBAL VARIABLES ###  
# API and Model Configuration  
OPENAI_API_KEY = os.environ.get("APPSETTING_2024may22_GPT4o_API_KEY")  
AZURE_OPENAI_ENDPOINT = os.environ.get("APPSETTING_AZURE_OPENAI_ENDPOINT")  
AZURE_OPENAI_API_VERSION = os.environ.get("APPSETTING_AZURE_OPENAI_API_VERSION")  
OPENAI_MODEL = os.environ.get("APPSETTING_CHAT_COMPLETIONS_DEPLOYMENT_NAME")  
# Messages and Prompts  
SYSTEM_PROMPT_TEXT = "You are an astute AI assistant."  
IMAGE_PROMPT_TEXT = "Describe this image in as much detail as possible."  
INITIAL_SUMMARIZATION_PROMPT = "We will be creating a patent for teradata, I want you to summarize all the key points into bullet points of top takeaways from this document in up to 20 bullet points of key things to consider"  
FINAL_SUMMARIZATION_PROMPT = "Provide a verbose summary of the text given citing key topics if possible, and highlighting the most important points with up to 20 bullet points capturing the key takeaways . Even if some context is missing or have statements saying incomplete, make your most informed analysis based on the available data."  
BRIEF_SUMMARIZATION_PROMPT = "This text is relatively brief, but attempt to extract as much relevant and valuable information as you can."  
  
# Initialize Tiktoken encoder  
encoding = tiktoken.encoding_for_model("gpt-4")  
# Pricing details for openai as of 2024july3PRICING = {  
PRICING = {  
    "gpt-4o": {"input": 5.00, "output": 15.00},  
    "gpt-4o-2024-05-13": {"input": 5.00, "output": 15.00},  
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},  
    "gpt-3.5-turbo-0125": {"input": 0.50, "output": 1.50},  
    # Add more models and pricing as needed  
}  
  
def calculate_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:  
    logging.debug(f"Calculating cost for model {model_name} with input tokens {input_tokens} and output tokens {output_tokens}")  
  
    # Default to "gpt-4o" pricing if model name contains "gpt-4o"  
    if "gpt-4o" in model_name:  
        model_pricing = PRICING["gpt-4o"]  
    else:  
        model_pricing = PRICING.get(model_name, PRICING["gpt-4o"])  
  
    input_cost_per_million = model_pricing["input"]  
    output_cost_per_million = model_pricing["output"]  
  
    input_cost = (input_tokens / 1_000_000) * input_cost_per_million  
    output_cost = (output_tokens / 1_000_000) * output_cost_per_million  
    total_cost = input_cost + output_cost  
  
    # Set minimum cost display threshold  
    if total_cost < 0.0001:  
        total_cost = 0.0001  
  
    logging.debug(f"Calculated cost for model {model_name}: input_cost={input_cost}, output_cost={output_cost}, total_cost={total_cost}")  
    return total_cost  
  
def num_tokens_from_string(string: str) -> int:  
    """Returns the number of tokens in a text string."""  
    num_tokens = len(encoding.encode(string))  
    return num_tokens  
  
def num_tokens_from_messages(messages, model="gpt-4"):  
    """Return the number of tokens used by a list of messages."""  
    tokens_per_message = 3  
    tokens_per_name = 1  
    num_tokens = 0  
    for message in messages:  
        num_tokens += tokens_per_message  
        for key, value in message.items():  
            num_tokens += len(encoding.encode(value))  
            if key == "name":  
                num_tokens += tokens_per_name  
    num_tokens += 3  # every reply is primed with  
    return num_tokens  
  
# Function to call OpenAI API for text messages  
def get_openai_response(user_message, chat_history=None, source=None):  
    logging.debug("Entered get_openai_response function")  
    try:  
        client = openai.AzureOpenAI(  
            azure_endpoint=AZURE_OPENAI_ENDPOINT,  
            api_key=OPENAI_API_KEY,  
            api_version=AZURE_OPENAI_API_VERSION  
        )  
  
        messages = [{"role": "system", "content": SYSTEM_PROMPT_TEXT}]  
        if chat_history:  
            messages.extend(chat_history)  
  
        if not chat_history or chat_history[-1]['content'] != user_message:  
            messages.append({"role": "user", "content": user_message})  
  
        input_token_count = num_tokens_from_messages(messages)  
        max_response_tokens = min(128000 - input_token_count, 4000)  # Default to 4000 if under the limit  
  
        logging.debug("Sending completion request to OpenAI")  
        completion = client.chat.completions.create(  
            model=OPENAI_MODEL,  
            messages=messages,  
            temperature=0.5,  
            max_tokens=max_response_tokens,  
            top_p=0.95,  
            frequency_penalty=0,  
            presence_penalty=0,  
            stop=None  
        )  
        completion_response = completion.dict()  
  
        # Log the full JSON response  
        logging.debug("Full JSON response from OpenAI:")  
        logging.debug(json.dumps(completion_response, indent=2))  
  
        # Extract the model name  
        model_name = completion_response.get('model', OPENAI_MODEL)  
  
        if 'choices' in completion_response and len(completion_response['choices']) > 0:  
            response_message = completion_response['choices'][0]['message']['content']  
            if source:  
                completion_response['source'] = source  
            logging.debug("Exiting get_openai_response function")  
            return {"choices": [{"message": {"content": response_message}}], "usage": completion_response.get("usage", {})}, model_name  # Return the response message, usage, and model name  
        else:  
            return {"error": "No choices in response."}, OPENAI_MODEL  
  
    except Exception as e:  
        if 'content_filter' in str(e):  
            return {"error": "Your message triggered the content filter. Please modify your message and try again."}, OPENAI_MODEL  
        logging.error(f"Error calling OpenAI API: {e}")  
        return {"error": f"Sorry, I couldn't process your request. Error: {e}"}, OPENAI_MODEL  
  
def moderate_content(content):  
    logging.debug("Entered moderate_content function")  
    try:  
        client = openai.AzureOpenAI(  
            azure_endpoint=AZURE_OPENAI_ENDPOINT,  
            api_key=OPENAI_API_KEY,  
            api_version=AZURE_OPENAI_API_VERSION  
        )  
        response = client.moderations.create(input=content)  
        if response is None:  
            logging.error("Received None response from moderation API")  
            return None  
        moderation_result = response['results'][0]  
        logging.debug(f"Moderation result: {moderation_result}")  
        return moderation_result  
    except Exception as e:  
        logging.error(f"Error during content moderation: {e}")  
        return None  
  
# Function to call OpenAI API for image messages  
def get_openai_image_response(image_data_url):  
    try:  
        client = openai.AzureOpenAI(  
            azure_endpoint=AZURE_OPENAI_ENDPOINT,  
            api_key=OPENAI_API_KEY,  
            api_version=AZURE_OPENAI_API_VERSION  
        )  
        message_text = [  
            {  
                "role": "user",  
                "content": [  
                    {  
                        "type": "text",  
                        "text": IMAGE_PROMPT_TEXT  
                    },  
                    {  
                        "type": "image_url",  
                        "image_url": {  
                            "url": image_data_url  
                        }  
                    }  
                ]  
            }  
        ]  
  
        # Log the message payload  
        print("Sending a payload to OpenAI... (debug by #uncommenting openai_utils.py...)")  
  
        completion = client.chat.completions.create(  
            model=OPENAI_MODEL,  
            messages=message_text,  
            temperature=0.5,  
            max_tokens=800,  
            top_p=0.95,  
            frequency_penalty=0,  
            presence_penalty=0,  
            stop=None  
        )  
        completion_response = completion.dict()  
        return completion_response['choices'][0]['message']['content']  
    except Exception as e:  
        print(f"Error calling OpenAI API: {e}")  
        return "Sorry, I couldn't process your request."  
  
# Function to call OpenAI API for text summarization  
def summarize_text_with_openai(chunk, instruction):  
    try:  
        client = openai.AzureOpenAI(  
            azure_endpoint=AZURE_OPENAI_ENDPOINT,  
            api_key=OPENAI_API_KEY,  
            api_version=AZURE_OPENAI_API_VERSION  
        )  
        message_text = [  
            {"role": "system", "content": instruction},  
            {"role": "user", "content": chunk}  
        ]  
        print("Sending the following input to OpenAI:")  
        print(message_text)  # Print the message being sent to OpenAI  
  
        input_token_count = num_tokens_from_messages(message_text)  
        max_response_tokens = min(128000 - input_token_count, 4000)  # Default to 4000 if under the limit  
  
        completion = client.chat.completions.create(  
            model=OPENAI_MODEL,  
            messages=message_text,  
            temperature=0.5,  
            max_tokens=max_response_tokens,  
            top_p=0.95,  
            frequency_penalty=0,  
            presence_penalty=0,  
            stop=None  
        )  
        completion_response = completion.dict()  
        print("Received the following response from OpenAI:")  
        print(completion_response)  # Print the response received from OpenAI  
  
        if 'choices' in completion_response and len(completion_response['choices']) > 0:  
            return completion_response['choices'][0]['message']['content'], completion_response.get('usage', {})  
        else:  
            return None, None  
    except Exception as e:  
        print(f"Error processing chunk with the instruction '{instruction}': {e}")  
        return None, None  
  
# Function to chunk text  
def chunk_text(text, max_chunk_size):  
    words = text.split()  
    chunks = []  
    current_chunk = []  
    current_length = 0  
  
    for word in words:  
        word_length = len(encoding.encode(word))  
        if current_length + word_length + 1 <= max_chunk_size:  
            current_chunk.append(word)  
            current_length += word_length + 1  
        else:  
            chunks.append(' '.join(current_chunk))  
            current_chunk = [word]  
            current_length = word_length + 1  
    chunks.append(' '.join(current_chunk))  
    return chunks  
  
# Function to estimate tokens from characters  
def estimate_tokens_from_chars(char_count):  
    return char_count // 4  
  
# Function to estimate cost  
def estimate_cost(input_tokens, output_tokens, input_cost_per_million=0.50, output_cost_per_million=1.50):  
    input_cost = (input_tokens / 1_000_000) * input_cost_per_million  
    output_cost = (output_tokens / 1_000_000) * output_cost_per_million  
    total_cost = input_cost + output_cost  
    return input_cost, output_cost, total_cost  
  
# Function to summarize text  
def process_and_summarize_text(input_text, source, attempt_sizes):  
    start_time = time.time()  
    char_count = len(input_text)  
    token_estimate = estimate_tokens_from_chars(char_count)  
    print(f"Size of input text: {char_count} characters")  
    print(f"Initial token estimate: {token_estimate} tokens")  
  
    chunks = chunk_text(input_text, 127000)  # Updated chunk size for 127,000 tokens  
    chunk_responses = []  
    total_completion_tokens = 0  
    total_prompt_tokens = 0  
    total_tokens = 0  
  
    for i, chunk in enumerate(chunks):  
        print(f"Processing chunk {i + 1}/{len(chunks)}")  
        response, usage = summarize_text_with_openai(chunk, INITIAL_SUMMARIZATION_PROMPT)  
        if response:  
            chunk_responses.append(response)  
            if usage:  
                completion_tokens = usage.get('completion_tokens', 0)  
                prompt_tokens = usage.get('prompt_tokens', 0)  
                total_completion_tokens += completion_tokens  
                total_prompt_tokens += prompt_tokens  
                total_tokens += completion_tokens + prompt_tokens  
                print(f"Chunk {i + 1}/{len(chunks)} processed: {completion_tokens} completion tokens, {prompt_tokens} prompt tokens")  
  
    second_input = ' '.join(filter(None, chunk_responses))  
    final_summary_logic = FINAL_SUMMARIZATION_PROMPT if len(second_input) > 100 else BRIEF_SUMMARIZATION_PROMPT  
    final_summary_response, final_usage = summarize_text_with_openai(second_input, final_summary_logic)  
  
    if final_summary_response:  
        final_summary = final_summary_response  
        if final_usage:  
            total_completion_tokens += final_usage.get('completion_tokens', 0)  
            total_prompt_tokens += final_usage.get('prompt_tokens', 0)  
            total_tokens += final_usage.get('total_tokens', 0)  
    else:  
        final_summary = None  
  
    elapsed_time = time.time() - start_time  
    elapsed_time_str = str(datetime.timedelta(seconds=elapsed_time))  
    input_cost, output_cost, total_cost = estimate_cost(total_prompt_tokens, total_completion_tokens)  
  
    processing_summary = (  
        f"**====PROCESSING SUMMARY====**\n"  
        f"**Source:** {source}\n | "  
        f"**Size of input text:** {char_count} characters\n | "  
        f"**Initial token estimate:** {token_estimate} tokens\n | "  
        f"**Total completion tokens (OpenAI):** {total_completion_tokens}\n | "  
        f"**Total prompt tokens (OpenAI):** {total_prompt_tokens}\n | "  
        f"**Total tokens (OpenAI):** {total_tokens}\n | "  
        f"**Actual cost based on total tokens:** ${total_cost:.4f}\n | "  
        f"**Total execution time:** {elapsed_time_str}\n | "  
    )  
  
    return final_summary + "\n\n" + processing_summary if final_summary else processing_summary  
  
# Function to read file contents  
def read_file_contents(file_path):  
    try:  
        with open(file_path, 'r') as file:  
            return file.read()  
    except FileNotFoundError:  
        print(f"File {file_path} not found.")  
        return None  
    except Exception as e:  
        print(f"An error occurred: {e}")  
        return None  
  
# Function to extract text from PDF  
def extract_text_from_pdf(pdf_path):  
    try:  
        with open(pdf_path, 'rb') as file:  
            reader = PyPDF2.PdfReader(file)  
            text = "".join([page.extract_text() for page in reader.pages])  
            return text  
    except Exception as e:  
        print(f"Error reading PDF file {pdf_path}: {e}")  
        return None  
  
def extract_text_from_docx(file_content):  
    try:  
        # Create a file-like object from the byte stream  
        file_like_object = io.BytesIO(file_content)  
        document = Document(file_like_object)  
        docx_text = "\n".join([para.text for para in document.paragraphs])  
        return docx_text  
    except Exception as e:  
        print(f"Error reading DOCX file: {e}")  
        return None  
  
#####CHATBOT SPECIFIC CODE#####  
# Function to load chat history from a JSON file  
def load_chat_history():  
    try:  
        with open('chat_history.json', 'r') as file:  
            return json.load(file)  
    except FileNotFoundError:  
        return []  
    except Exception as e:  
        print(f"Error loading chat history: {e}")  
        return []  
  
# Function to save chat history to a JSON file  
def save_chat_history(chat_history):  
    try:  
        with open('chat_history.json', 'w') as file:  
            json.dump(chat_history, file)  
    except Exception as e:  
        print(f"Error saving chat history: {e}")  
  
# Function to update chat history  
def update_chat_history(chat_history, user_message, bot_response):  
    chat_history.append({"role": "user", "content": user_message})  
    chat_history.append({"role": "assistant", "content": bot_response})  
    save_chat_history(chat_history)  
#####END OF CHATBOT SPECIFIC CODE#####  
