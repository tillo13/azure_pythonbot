import logging  
import requests  
import base64  
from botbuilder.schema import Activity, ActivityTypes  
from utils.openai_utils import process_and_summarize_text, extract_text_from_pdf, get_openai_image_response  
from constants import *  
  
def download_and_encode_image(url):  
    try:  
        response = requests.get(url)  
        response.raise_for_status()  
        return base64.b64encode(response.content).decode("utf-8")  
    except Exception as e:  
        logging.error(f"Error downloading image: {e}")  
        return None  
  
async def send_message(turn_context, message):  
    await turn_context.send_activity(Activity(  
        type=ActivityTypes.message,  
        text=message  
    ))  
  
async def handle_image_attachment(turn_context, attachment):  
    image_url = attachment.content_url  
    base64_image = download_and_encode_image(image_url)  
    if base64_image:  
        await send_message(turn_context, MSG_IMAGE_RECEIVED)  
        logging.debug(f"Base64 Image Length: {len(base64_image)}")  
        image_data_url = f"data:image/jpeg;base64,{base64_image}"  
        openai_response = get_openai_image_response(image_data_url)  
        await send_message(turn_context, MSG_IMAGE_DETAILS)  
        await send_message(turn_context, openai_response)  
    else:  
        await send_message(turn_context, MSG_IMAGE_ERROR)  
  
async def handle_text_attachment(turn_context, attachment):  
    file_url = attachment.content_url  
    file_content = requests.get(file_url).text  
    if file_content:  
        await send_message(turn_context, MSG_TEXT_RECEIVED)  
        await send_message(turn_context, MSG_START_SUMMARIZATION)  
        await send_message(turn_context, MSG_CHUNK_PROCESSING)  
        await turn_context.send_activity(Activity(type=ActivityTypes.typing))  
        attempt_sizes = [5000, 6000, 7000]  
        summary_with_processing_summary = process_and_summarize_text(file_content, "Text file", attempt_sizes)  
        await send_message(turn_context, summary_with_processing_summary)  
    else:  
        await send_message(turn_context, MSG_TEXT_ERROR)  
  
async def handle_pdf_attachment(turn_context, attachment):  
    file_url = attachment.content_url  
    response = requests.get(file_url)  
    if response.status_code == 200:  
        with open("temp.pdf", "wb") as pdf_file:  
            pdf_file.write(response.content)  
        pdf_text = extract_text_from_pdf("temp.pdf")  
        if pdf_text:  
            await send_message(turn_context, MSG_PDF_RECEIVED)  
            await send_message(turn_context, MSG_START_SUMMARIZATION)  
            await send_message(turn_context, MSG_CHUNK_PROCESSING)  
            await turn_context.send_activity(Activity(type=ActivityTypes.typing))  
            attempt_sizes = [5000, 6000, 7000]  
            summary_with_processing_summary = process_and_summarize_text(pdf_text, "PDF file", attempt_sizes)  
            await send_message(turn_context, summary_with_processing_summary)  
        else:  
            await send_message(turn_context, MSG_PDF_ERROR)  
    else:  
        await send_message(turn_context, MSG_DOWNLOAD_PDF_ERROR)  
