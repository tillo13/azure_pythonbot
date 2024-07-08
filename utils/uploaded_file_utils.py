import logging  
import requests  
import base64  
import hashlib  
from botbuilder.schema import Activity, ActivityTypes  
from utils.openai_utils import process_and_summarize_text, extract_text_from_pdf, get_openai_image_response  
from constants import *  
from utils.azure_postgres_utils import save_or_fetch_file_hash  
  
def generate_file_hash(file_content):  
    """Generate a SHA-256 hash for the given file content."""  
    sha256 = hashlib.sha256()  
    sha256.update(file_content)  
    return sha256.hexdigest()  
  
def download_and_encode_image(url):  
    try:  
        response = requests.get(url)  
        response.raise_for_status()  
        return base64.b64encode(response.content).decode("utf-8")  
    except Exception as e:  
        logging.error(f"Error downloading image: {e}")  
        return None  
  
async def send_message(turn_context, message, thread_ts=None):  
    activity = Activity(  
        type=ActivityTypes.message,  
        text=message  
    )  
    if thread_ts:  
        activity.channel_data = {"thread_ts": thread_ts}  
    await turn_context.send_activity(activity)  
  
async def process_attachment(turn_context, attachment, process_func, success_message, error_message, thread_ts=None):  
    try:  
        # Download the file content  
        response = requests.get(attachment.content_url)  
        response.raise_for_status()  
        file_content = response.content  
  
        # Generate hash for the file content  
        file_hash = generate_file_hash(file_content)  
        logging.info(f"Generated hash for the uploaded document: {file_hash}")  
  
        # Check if we already have a response for this file hash  
        existing_openai_response = save_or_fetch_file_hash(file_hash, None, turn_context.activity.from_property.id)  
  
        if existing_openai_response:  
            logging.info(f"File with hash {file_hash} already exists. Using the existing OpenAI response.")  
            await send_message(turn_context, existing_openai_response, thread_ts)  
        else:  
            # Process the file and get OpenAI response  
            openai_response = process_func(attachment.content_url)  
            save_or_fetch_file_hash(file_hash, openai_response, turn_context.activity.from_property.id)  
  
            await send_message(turn_context, success_message, thread_ts)  
            await turn_context.send_activity(Activity(type=ActivityTypes.typing))  
            await send_message(turn_context, openai_response, thread_ts)  
    except Exception as e:  
        logging.error(f"Error processing attachment: {e}")  
        await send_message(turn_context, error_message, thread_ts)  
  
def process_image(url):  
    base64_image = download_and_encode_image(url)  
    if base64_image:  
        logging.debug(f"Base64 Image Length: {len(base64_image)}")  
        image_data_url = f"data:image/jpeg;base64,{base64_image}"  
        return get_openai_image_response(image_data_url)  
    else:  
        raise ValueError("Failed to download or encode image")  
  
def process_text(url):  
    file_content = requests.get(url).text  
    if file_content:  
        attempt_sizes = [5000, 6000, 7000]  
        return process_and_summarize_text(file_content, "Text file", attempt_sizes)  
    else:  
        raise ValueError("Failed to download or read text file")  
  
def process_pdf(url):  
    response = requests.get(url)  
    if response.status_code == 200:  
        with open("temp.pdf", "wb") as pdf_file:  
            pdf_file.write(response.content)  
        pdf_text = extract_text_from_pdf("temp.pdf")  
        if pdf_text:  
            attempt_sizes = [5000, 6000, 7000]  
            return process_and_summarize_text(pdf_text, "PDF file", attempt_sizes)  
        else:  
            raise ValueError("Failed to extract text from PDF")  
    else:  
        raise ValueError("Failed to download PDF")  
  
async def handle_image_attachment(turn_context, attachment, thread_ts=None):  
    await process_attachment(turn_context, attachment, process_image, MSG_IMAGE_RECEIVED, MSG_IMAGE_ERROR, thread_ts)  
  
async def handle_text_attachment(turn_context, attachment, thread_ts=None):  
    await process_attachment(turn_context, attachment, process_text, MSG_TEXT_RECEIVED, MSG_TEXT_ERROR, thread_ts)  
  
async def handle_pdf_attachment(turn_context, attachment, thread_ts=None):  
    await process_attachment(turn_context, attachment, process_pdf, MSG_PDF_RECEIVED, MSG_PDF_ERROR, thread_ts)  
