import logging  
import requests  
import base64  
import json  # Add this import  
from botbuilder.schema import Activity, ActivityTypes  
from botbuilder.core import TurnContext  # Add this import  
from utils.openai_utils import process_and_summarize_text, extract_text_from_pdf, get_openai_image_response  
from utils.slack_utils import get_last_5_messages, post_message_to_slack, extract_channel_id, find_latest_file_upload_thread_ts  
from constants import *  
import os  
  
SLACK_TOKEN = os.environ.get("APPSETTING_SLACK_TOKEN")  
  
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
        activity.additional_properties = {"thread_ts": thread_ts}  
    await turn_context.send_activity(activity)  
  
async def process_attachment(turn_context, attachment, process_func, success_message, error_message, thread_ts=None):  
    try:  
        await send_message(turn_context, success_message, thread_ts)  
        await turn_context.send_activity(Activity(type=ActivityTypes.typing))  
        result = process_func(attachment.content_url)  
        await send_message(turn_context, result, thread_ts)  
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
  
def find_latest_file_upload_thread_ts(messages):  
    """Find the latest thread_ts for a file upload from the last 5 messages."""  
    for message in messages:  
        if 'files' in message:  
            return message.get('ts')  
    return None  
  
async def handle_file_uploads(turn_context):  
    activity = turn_context.activity  
    user_message = activity.text.strip().lower()  
    channel_id = extract_channel_id(activity.conversation.id)  
  
    if not channel_id:  
        return  
  
    last_5_messages = get_last_5_messages(SLACK_TOKEN, channel_id)  
    logging.debug(f"Last 5 messages in channel {channel_id}: {json.dumps(last_5_messages, indent=2)}")  
  
    thread_ts = find_latest_file_upload_thread_ts(last_5_messages)  
    if thread_ts:  
        logging.debug(f"Using thread_ts for response: {thread_ts}")  
    else:  
        logging.error("Unable to find thread_ts for file upload from the last 5 messages.")  
  
    if activity.attachments:  
        for attachment in activity.attachments:  
            if attachment.content_type.startswith("image/"):  
                await process_attachment(turn_context, attachment, process_image, MSG_IMAGE_RECEIVED, MSG_IMAGE_ERROR, thread_ts)  
            elif attachment.content_type == "text/plain":  
                await process_attachment(turn_context, attachment, process_text, MSG_TEXT_RECEIVED, MSG_TEXT_ERROR, thread_ts)  
            elif attachment.content_type == "application/pdf":  
                await process_attachment(turn_context, attachment, process_pdf, MSG_PDF_RECEIVED, MSG_PDF_ERROR, thread_ts)  
  
# Example usage in your main handler  
async def handle_slack_message(turn_context: TurnContext):  
    activity = turn_context.activity  
    try:  
        # Log the entire activity payload  
        logging.debug(f"Payload passed from app.py via slack_handler.py: {json.dumps(activity.as_dict(), indent=2)}")  
  
        # Extract user message  
        user_message = activity.text  
        logging.debug(f"Received message: {user_message}")  
  
        # Extract channel_id  
        channel_id = extract_channel_id(activity.conversation.id)  
        if not channel_id:  
            return  
  
        logging.debug(f"Extracted channel_id: {channel_id}")  
  
        # Check for file uploads and handle them  
        if activity.attachments:  
            await handle_file_uploads(turn_context)  
  
        # Handle other types of messages if needed  
        # ...  
  
    except (KeyError, TypeError) as e:  
        logging.error(f"Error processing file upload: {e}")  
        await turn_context.send_activity(SLACK_MSG_ERROR)  
        await turn_context.send_activity(SLACK_MSG_FIX_BOT)  
    except Exception as e:  
        logging.error(f"Error in handle_slack_message: {e}")  
        await turn_context.send_activity(SLACK_MSG_ERROR)  
        await turn_context.send_activity(SLACK_MSG_FIX_BOT)  
