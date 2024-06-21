# openai_utils.py  
  
import os  
import base64  
import openai  
import re  
import time  
import datetime  
import PyPDF2  
from dotenv import load_dotenv  
import tiktoken  
  
# Load environment variables from .env file  
load_dotenv()  
  
### GLOBAL VARIABLES ###  
# API and Model Configuration  
OPENAI_API_KEY = os.getenv("2024may22_GPT4o_API_KEY")  
AZURE_OPENAI_ENDPOINT = "https://tillo-openai.openai.azure.com/"  
AZURE_OPENAI_API_VERSION = "2024-02-01"  
OPENAI_MODEL = "2024may22_gpt4o_tillo"  
  
# Messages and Prompts  
SYSTEM_PROMPT_TEXT = "You are an AI assistant that helps people find information."  
IMAGE_PROMPT_TEXT = "Describe this image in as much detail as possible."  
INITIAL_SUMMARIZATION_PROMPT = "Analyze the given text and provide insights about the primary aspects discussed, and people involved by name, even if the context seems incomplete."  
FINAL_SUMMARIZATION_PROMPT = "Provide a verbose summary of the text given citing key topics if possible, and highlighting the most important points with up to 20 bullet points capturing the key takeaways. Even if some context is missing or have statements saying incomplete, make your most informed analysis based on the available data."  
BRIEF_SUMMARIZATION_PROMPT = "This text is relatively brief, but attempt to extract as much relevant and valuable information as you can."  
  
# Initialize Tiktoken encoder  
encoding = tiktoken.encoding_for_model("gpt-4")  
  
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
def get_openai_response(user_message):  
    try:  
        client = openai.AzureOpenAI(  
            azure_endpoint=AZURE_OPENAI_ENDPOINT,  
            api_key=OPENAI_API_KEY,  
            api_version=AZURE_OPENAI_API_VERSION  
        )  
        message_text = [  
            {"role": "system", "content": SYSTEM_PROMPT_TEXT},  
            {"role": "user", "content": user_message}  
        ]  
        # Calculate the number of tokens in the input message  
        input_token_count = num_tokens_from_messages(message_text)  
        # Estimate the max tokens for the response to avoid exceeding the model's limit  
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
        return completion_response['choices'][0]['message']['content']  
    except Exception as e:  
        print(f"Error calling OpenAI API: {e}")  
        return "Sorry, I couldn't process your request."  
  
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
        print("Sending the following payload to OpenAI:")  
        print(message_text)  
  
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
      
    # Ensure the processing summary is shown last and separated by new lines  
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
