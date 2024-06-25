import logging  
import requests  
import base64  
from botbuilder.schema import Activity, ActivityTypes  
from utils.openai_utils import process_and_summarize_text, extract_text_from_pdf, get_openai_image_response  
from utils.slack_utils import post_message_to_slack, add_reaction_to_message, remove_reaction_from_message, extract_thread_ts, extract_channel_id, SLACK_TOKEN  
from constants import *  
  
def download_and_encode_image(url):  
    try:  
        response = requests.get(url)  
        response.raise_for_status()  
        return base64.b64encode(response.content).decode("utf-8")  
    except Exception as e:  
        logging.error(f"Error downloading image: {e}")  
        return None  
  
async def send_message_to_slack(token, channel_id, message, thread_ts=None):  
    response_data_list = post_message_to_slack(  
        token=token,  
        channel=channel_id,  
        text=message,  
        thread_ts=thread_ts  
    )  
    for response_data in response_data_list:  
        if not response_data.get("ok"):  
            logging.error(f"Error posting message to Slack: {response_data.get('error')}")  
  
async def process_attachment(turn_context, attachment, process_func, success_message, error_message, thread_ts=None):  
    channel_id = extract_channel_id(turn_context.activity.conversation.id)  
    token = SLACK_TOKEN  
  
    try:  
        await send_message_to_slack(token, channel_id, success_message, thread_ts)  
        await turn_context.send_activity(Activity(type=ActivityTypes.typing, channel_data={"thread_ts": thread_ts} if thread_ts else {}))  
        result = process_func(attachment.content_url)  
        await send_message_to_slack(token, channel_id, result, thread_ts)  
    except Exception as e:  
        logging.error(f"Error processing attachment: {e}")  
        await send_message_to_slack(token, channel_id, error_message, thread_ts)  
  
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
  
async def handle_image_attachment(turn_context, attachment):  
    thread_ts = extract_thread_ts(turn_context.activity) or turn_context.activity.timestamp  
    channel_id = extract_channel_id(turn_context.activity.conversation.id)  
    token = SLACK_TOKEN  
  
    add_reaction_to_message(token, channel_id, thread_ts, "hourglass")  
    await process_attachment(turn_context, attachment, process_image, MSG_IMAGE_RECEIVED, MSG_IMAGE_ERROR, thread_ts)  
    remove_reaction_from_message(token, channel_id, thread_ts, "hourglass")  
    add_reaction_to_message(token, channel_id, thread_ts, "white_check_mark")  
  
async def handle_text_attachment(turn_context, attachment):  
    thread_ts = extract_thread_ts(turn_context.activity) or turn_context.activity.timestamp  
    channel_id = extract_channel_id(turn_context.activity.conversation.id)  
    token = SLACK_TOKEN  
  
    add_reaction_to_message(token, channel_id, thread_ts, "hourglass")  
    await process_attachment(turn_context, attachment, process_text, MSG_TEXT_RECEIVED, MSG_TEXT_ERROR, thread_ts)  
    remove_reaction_from_message(token, channel_id, thread_ts, "hourglass")  
    add_reaction_to_message(token, channel_id, thread_ts, "white_check_mark")  
  
async def handle_pdf_attachment(turn_context, attachment):  
    thread_ts = extract_thread_ts(turn_context.activity) or turn_context.activity.timestamp  
    channel_id = extract_channel_id(turn_context.activity.conversation.id)  
    token = SLACK_TOKEN  
  
    add_reaction_to_message(token, channel_id, thread_ts, "hourglass")  
    await process_attachment(turn_context, attachment, process_pdf, MSG_PDF_RECEIVED, MSG_PDF_ERROR, thread_ts)  
    remove_reaction_from_message(token, channel_id, thread_ts, "hourglass")  
    add_reaction_to_message(token, channel_id, thread_ts, "white_check_mark")  
