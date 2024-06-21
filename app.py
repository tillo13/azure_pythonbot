# app.py  
import os  
import logging  
from aiohttp import web  
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext  
from botbuilder.schema import Activity, ActivityTypes  
from dotenv import load_dotenv  
from utils.openai_utils import get_openai_response  
from message_handlers.slack_handler import handle_slack_message  
from message_handlers.default_handler import handle_default_message  
from constants import *  
from utils.uploaded_file_utils import handle_image_attachment, handle_text_attachment, handle_pdf_attachment  
from utils.datetime_utils import get_current_time, calculate_elapsed_time  
from utils.footer_utils import generate_footer  
import json  
  
# Configure logging  
logging.basicConfig(level=logging.DEBUG)  
  
# Load environment variables from .env file  
load_dotenv()  
  
# Configuration  
APP_ID = os.getenv("MICROSOFT_APP_ID")  
APP_PASSWORD = os.getenv("MICROSOFT_APP_PASSWORD")  
PORT = 3978  
  
# Create adapter settings and adapter  
settings = BotFrameworkAdapterSettings(APP_ID, APP_PASSWORD)  
adapter = BotFrameworkAdapter(settings)  
  
# Handle errors  
async def on_error(context: TurnContext, error: Exception):  
    logging.error(f"[on_turn_error] unhandled error: {error}")  
    if context.activity.channel_id == "slack":  
        await context.send_activity(SLACK_MSG_ERROR)  
        await context.send_activity(SLACK_MSG_FIX_BOT)  
    else:  
        await context.send_activity(MSG_ERROR)  
        await context.send_activity(MSG_FIX_BOT)  
  
adapter.on_turn_error = on_error  
  
# Function to handle incoming requests on /api/messages  




async def handle_message(request):  
    # Start timing before processing the request  
    start_time = get_current_time()  
  
    # Get the activity from the request  
    body = await request.json()  
    activity = Activity().deserialize(body)  
  
    # Log the incoming activity  
    logging.debug(f"Received activity: {activity.as_dict()}")  
  
    # Set the response headers  
    headers = {"Content-Type": "application/json"}  
  
    # Bypass authentication for local testing  
    auth_header = request.headers.get("Authorization", "")  
  
    # Process the activity and send a response  
    async def response(turn_context: TurnContext):  
        # Log the received message  
        logging.debug(f"Received message: {turn_context.activity.text}")  
  
        # Check if the activity is a message activity  
        if turn_context.activity.type == ActivityTypes.message:  
            if turn_context.activity.channel_id == "slack":  
                logging.debug(f"Sending message to slack_handler.py with activity: {activity.as_dict()}")  
                # Pass the TurnContext to slack_handler  
                await handle_slack_message(turn_context)  
            else:  
                user_message = turn_context.activity.text  
  
                # Check for attachments  
                if turn_context.activity.attachments:  
                    for attachment in turn_context.activity.attachments:  
                        logging.debug(f"Processing attachment: {attachment.content_type}")  
                        if attachment.content_type.startswith("image/"):  
                            await handle_image_attachment(turn_context, attachment)  
                        elif attachment.content_type == "text/plain":  
                            await handle_text_attachment(turn_context, attachment)  
                        elif attachment.content_type == "application/pdf":  
                            await handle_pdf_attachment(turn_context, attachment)  
                else:  
                    # Route to default handler for OpenAI response  
                    await handle_default_message(turn_context)  
        else:  
            await turn_context.send_activity(MSG_EVENT_DETECTED.format(turn_context.activity.type))  
  
        # Calculate the response time  
        response_time = calculate_elapsed_time(start_time)  
  
        # Generate the footer with the response time  
        footer = generate_footer(turn_context.activity.channel_id, response_time)  
        logging.debug(f"Generated footer: {footer}")  
  
    # Process the activity  
    await adapter.process_activity(activity, auth_header, response)  
  
    # Return a web response  
    return web.Response(text="OK", headers=headers)  
  
# Create the aiohttp application and add the routes  
app = web.Application()  
app.router.add_post("/api/messages", handle_message)  
  
# Run the application  
if __name__ == "__main__":  
    web.run_app(app, port=PORT)  
