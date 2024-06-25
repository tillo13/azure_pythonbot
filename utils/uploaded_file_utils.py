import logging  
import requests  
import base64  
from botbuilder.schema import Activity, ActivityTypes  
from utils.openai_utils import process_and_summarize_text, extract_text_from_pdf, get_openai_image_response  
from constants import *  
from utils.slack_utils import get_last_5_messages  # Add this import statement at the top  
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
  
def extract_channel_id(conversation_id):  
    conversation_id_parts = conversation_id.split(":")  
    if len(conversation_id_parts) >= 3:  
        return conversation_id_parts[2]  
    else:  
        logging.error("Unable to extract channel ID from conversation ID")  
        return None  
  
async def handle_image_attachment(turn_context, attachment, thread_ts=None):  
    channel_id = extract_channel_id(turn_context.activity.conversation.id)  
    logging.debug(f"File is being uploaded --invoking the last 5 messages in channel, {channel_id}...")  
    last_5_messages = get_last_5_messages(SLACK_TOKEN, channel_id)  
    logging.debug(f"Last 5 messages in channel {channel_id}: {last_5_messages}")  
  
    print(f"********THE IMAGE FILE UPLOADED WILL PASTE THE RESPONSE IN THIS SUBTHREAD {thread_ts}******")  
    image_url = attachment.content_url  
    base64_image = download_and_encode_image(image_url)  
    if base64_image:  
        print(f"*****PRINTING constants.py message {MSG_IMAGE_RECEIVED} on thread_ts {thread_ts}*****")  
        await turn_context.send_activity(Activity(  
            type=ActivityTypes.message,  
            text=MSG_IMAGE_RECEIVED,  
            channel_data={"thread_ts": thread_ts} if thread_ts else None  
        ))  
        logging.debug(f"Base64 Image Length: {len(base64_image)}")  
        image_data_url = f"data:image/jpeg;base64,{base64_image}"  
        openai_response = get_openai_image_response(image_data_url)  
        print(f"*****PRINTING constants.py message {MSG_IMAGE_DETAILS} on thread_ts {thread_ts}*****")  
        await turn_context.send_activity(Activity(  
            type=ActivityTypes.message,  
            text=MSG_IMAGE_DETAILS,  
            channel_data={"thread_ts": thread_ts} if thread_ts else None  
        ))  
        await turn_context.send_activity(Activity(  
            type=ActivityTypes.message,  
            text=openai_response,  
            channel_data={"thread_ts": thread_ts} if thread_ts else None  
        ))  
    else:  
        print(f"*****PRINTING constants.py message {MSG_IMAGE_ERROR} on thread_ts {thread_ts}*****")  
        await turn_context.send_activity(Activity(  
            type=ActivityTypes.message,  
            text=MSG_IMAGE_ERROR,  
            channel_data={"thread_ts": thread_ts} if thread_ts else None  
        ))  
  
async def handle_text_attachment(turn_context, attachment, thread_ts=None):  
    channel_id = extract_channel_id(turn_context.activity.conversation.id)  
    logging.debug(f"File is being uploaded --invoking the last 5 messages in channel, {channel_id}...")  
    last_5_messages = get_last_5_messages(SLACK_TOKEN, channel_id)  
    logging.debug(f"Last 5 messages in channel {channel_id}: {last_5_messages}")  
  
    print(f"********THE TXT FILE UPLOADED WILL PASTE THE RESPONSE IN THIS SUBTHREAD {thread_ts}******")  
    file_url = attachment.content_url  
    file_content = requests.get(file_url).text  
    if file_content:  
        print(f"*****PRINTING constants.py message {MSG_TEXT_RECEIVED} on thread_ts {thread_ts}*****")  
        await turn_context.send_activity(Activity(  
            type=ActivityTypes.message,  
            text=MSG_TEXT_RECEIVED,  
            channel_data={"thread_ts": thread_ts} if thread_ts else None  
        ))  
        print(f"*****PRINTING constants.py message {MSG_START_SUMMARIZATION} on thread_ts {thread_ts}*****")  
        await turn_context.send_activity(Activity(  
            type=ActivityTypes.message,  
            text=MSG_START_SUMMARIZATION,  
            channel_data={"thread_ts": thread_ts} if thread_ts else None  
        ))  
        print(f"*****PRINTING constants.py message {MSG_CHUNK_PROCESSING} on thread_ts {thread_ts}*****")  
        await turn_context.send_activity(Activity(  
            type=ActivityTypes.message,  
            text=MSG_CHUNK_PROCESSING,  
            channel_data={"thread_ts": thread_ts} if thread_ts else None  
        ))  
        await turn_context.send_activity(Activity(type=ActivityTypes.typing))  
        attempt_sizes = [5000, 6000, 7000]  
        summary_with_processing_summary = process_and_summarize_text(file_content, "Text file", attempt_sizes)  
        await turn_context.send_activity(Activity(  
            type=ActivityTypes.message,  
            text=summary_with_processing_summary,  
            channel_data={"thread_ts": thread_ts} if thread_ts else None  
        ))  
    else:  
        print(f"*****PRINTING constants.py message {MSG_TEXT_ERROR} on thread_ts {thread_ts}*****")  
        await turn_context.send_activity(Activity(  
            type=ActivityTypes.message,  
            text=MSG_TEXT_ERROR,  
            channel_data={"thread_ts": thread_ts} if thread_ts else None  
        ))  
  
async def handle_pdf_attachment(turn_context, attachment, thread_ts=None):  
    channel_id = extract_channel_id(turn_context.activity.conversation.id)  
    logging.debug(f"File is being uploaded --invoking the last 5 messages in channel, {channel_id}...")  
    last_5_messages = get_last_5_messages(SLACK_TOKEN, channel_id)  
    logging.debug(f"Last 5 messages in channel {channel_id}: {last_5_messages}")  
  
    print(f"********THE PDF FILE UPLOADED WILL PASTE THE RESPONSE IN THIS SUBTHREAD {thread_ts}******")  
    file_url = attachment.content_url  
    response = requests.get(file_url)  
    if response.status_code == 200:  
        with open("temp.pdf", "wb") as pdf_file:  
            pdf_file.write(response.content)  
        pdf_text = extract_text_from_pdf("temp.pdf")  
        if pdf_text:  
            print(f"*****PRINTING constants.py message {MSG_PDF_RECEIVED} on thread_ts {thread_ts}*****")  
            await turn_context.send_activity(Activity(  
                type=ActivityTypes.message,  
                text=MSG_PDF_RECEIVED,  
                channel_data={"thread_ts": thread_ts} if thread_ts else None  
            ))  
            print(f"*****PRINTING constants.py message {MSG_START_SUMMARIZATION} on thread_ts {thread_ts}*****")  
            await turn_context.send_activity(Activity(  
                type=ActivityTypes.message,  
                text=MSG_START_SUMMARIZATION,  
                channel_data={"thread_ts": thread_ts} if thread_ts else None  
            ))  
            print(f"*****PRINTING constants.py message {MSG_CHUNK_PROCESSING} on thread_ts {thread_ts}*****")  
            await turn_context.send_activity(Activity(  
                type=ActivityTypes.message,  
                text=MSG_CHUNK_PROCESSING,  
                channel_data={"thread_ts": thread_ts} if thread_ts else None  
            ))  
            await turn_context.send_activity(Activity(type=ActivityTypes.typing))  
            attempt_sizes = [5000, 6000, 7000]  
            summary_with_processing_summary = process_and_summarize_text(pdf_text, "PDF file", attempt_sizes)  
            await turn_context.send_activity(Activity(  
                type=ActivityTypes.message,  
                text=summary_with_processing_summary,  
                channel_data={"thread_ts": thread_ts} if thread_ts else None  
            ))  
        else:  
            print(f"*****PRINTING constants.py message {MSG_PDF_ERROR} on thread_ts {thread_ts}*****")  
            await turn_context.send_activity(Activity(  
                type=ActivityTypes.message,  
                text=MSG_PDF_ERROR,  
                channel_data={"thread_ts": thread_ts} if thread_ts else None  
            ))  
    else:  
        print(f"*****PRINTING constants.py message {MSG_DOWNLOAD_PDF_ERROR} on thread_ts {thread_ts}*****")  
        await turn_context.send_activity(Activity(  
            type=ActivityTypes.message,  
            text=MSG_DOWNLOAD_PDF_ERROR,  
            channel_data={"thread_ts": thread_ts} if thread_ts else None  
        ))  