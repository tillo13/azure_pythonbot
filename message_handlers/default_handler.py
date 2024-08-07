import logging  
from botbuilder.core import TurnContext  
from botbuilder.schema import Attachment, Activity, ActivityTypes  
from utils.openai_utils import get_openai_response  
from utils.footer_utils import generate_footer  
from utils.datetime_utils import get_current_time, calculate_elapsed_time  
from utils.uploaded_file_utils import handle_image_attachment, handle_text_attachment, handle_pdf_attachment  
from utils.special_commands_utils import handle_special_commands  
from constants import *  
import json  
  
logging.basicConfig(level=logging.DEBUG)  
  
def create_adaptive_card(main_message: str, footer: str) -> Attachment:  
    card_json = {  
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",  
        "type": "AdaptiveCard",  
        "version": "1.2",  
        "body": [  
            {  
                "type": "TextBlock",  
                "text": main_message,  
                "wrap": True  
            },  
            {  
                "type": "TextBlock",  
                "text": "---",  
                "wrap": True,  
                "separator": True  
            },  
            {  
                "type": "TextBlock",  
                "text": footer,  
                "wrap": True,  
                "spacing": "None"  
            }  
        ]  
    }  
    return Attachment(content_type="application/vnd.microsoft.card.adaptive", content=card_json)  
  
async def handle_attachments(turn_context, attachments):  
    """Handles processing of different types of attachments."""  
    for attachment in attachments:  
        logging.debug(f"Processing attachment: {attachment.content_type}")  
        if attachment.content_type.startswith("image/"):  
            await handle_image_attachment(turn_context, attachment)  
        elif attachment.content_type == "text/plain":  
            await handle_text_attachment(turn_context, attachment)  
        elif attachment.content_type == "application/pdf":  
            await handle_pdf_attachment(turn_context, attachment)  
  
async def handle_default_message(turn_context: TurnContext):  
    try:  
        logging.debug("Handling default message")  
        user_message = turn_context.activity.text  
        logging.debug(f"User message: {user_message}")  
  
        # Check for special commands  
        if await handle_special_commands(turn_context):  
            return  
  
        # Check for attachments  
        if turn_context.activity.attachments:  
            await handle_attachments(turn_context, turn_context.activity.attachments)  
            return  
  
        # Start timing before the call to OpenAI  
        start_time = get_current_time()  
  
        # Get response from OpenAI with source parameter  
        openai_response_data, model_name = get_openai_response(user_message, source="from_default_handler")  
        logging.debug("Full JSON response from OpenAI:")  
        logging.debug(json.dumps(openai_response_data, indent=2))  
  
        # Extract token usage from the response  
        input_tokens = openai_response_data.get('usage', {}).get('prompt_tokens', 0)  
        output_tokens = openai_response_data.get('usage', {}).get('completion_tokens', 0)  
  
        # Parse the OpenAI response  
        try:  
            if 'choices' in openai_response_data and isinstance(openai_response_data['choices'], list):  
                if len(openai_response_data['choices']) > 0 and 'message' in openai_response_data['choices'][0]:  
                    if 'content' in openai_response_data['choices'][0]['message']:  
                        bot_response = openai_response_data['choices'][0]['message']['content']  
                    else:  
                        raise KeyError("Key 'content' not found in the OpenAI response 'message'.")  
                else:  
                    raise KeyError("Key 'message' not found in the OpenAI response 'choices'.")  
            else:  
                raise KeyError("Key 'choices' not found or is not a list in the OpenAI response.")  
        except (KeyError, TypeError, IndexError) as e:  
            logging.error(f"Error parsing OpenAI response: {e}")  
            await turn_context.send_activity("There was an error processing the response from OpenAI.")  
            return  
  
        # Calculate the response time  
        response_time = calculate_elapsed_time(start_time)  
  
        # Generate the footer with the response time and token counts  
        footer = generate_footer("webchat", response_time, model_name, input_tokens, output_tokens)  
  
        # Create an Adaptive Card with the response and footer  
        adaptive_card = create_adaptive_card(bot_response, footer)  
        logging.debug(f"Adaptive Card: {json.dumps(adaptive_card.content, indent=2)}")  
  
        # Send the Adaptive Card as a response  
        await turn_context.send_activity(Activity(type=ActivityTypes.message, attachments=[adaptive_card]))  
    except Exception as e:  
        logging.error(f"Error in default handler: {e}")  
        await turn_context.send_activity(MSG_ERROR)  
        await turn_context.send_activity(MSG_FIX_BOT)  
