import logging  
from botbuilder.core import TurnContext  
from utils.openai_utils import get_openai_response  
from constants import *  
from utils.uploaded_file_utils import handle_image_attachment, handle_text_attachment, handle_pdf_attachment  
from utils.slack_utils import (  
    post_message_to_slack,  
    get_conversation_replies,  
    add_reaction_to_message,  
    remove_reaction_from_message,  
    create_slack_message,  
    parse_chat_history,  
    convert_openai_response_to_slack_mrkdwn,  
    get_user_id  
)  
from utils.footer_utils import generate_footer  
from utils.datetime_utils import get_current_time, calculate_elapsed_time  
from utils.special_commands_utils import handle_special_commands  
from utils.azure_postgres_utils import log_invocation_to_db  # Import the new utility  
import json  
import os  
from utils.approved_users import is_user_approved  
  
SLACK_TOKEN = os.environ.get("APPSETTING_SLACK_TOKEN")  
  
def extract_channel_id(conversation_id):  
    conversation_id_parts = conversation_id.split(":")  
    if len(conversation_id_parts) >= 3:  
        return conversation_id_parts[2]  
    else:  
        logging.error("Unable to extract channel ID from conversation ID")  
        return None  
  
def get_parent_thread_ts(activity):  
    event_data = activity.channel_data.get("SlackMessage", {}).get("event", {})  
    thread_ts = event_data.get("thread_ts")  
    if thread_ts:  
        logging.debug(f"Parent thread_ts: {thread_ts}")  
        return thread_ts  
    else:  
        ts = event_data.get("ts")  
        if ts:  
            logging.debug(f"Parent ts: {ts}")  
            return ts  
        else:  
            logging.error("Both thread_ts and ts are None, cannot proceed.")  
            return None  
  
def get_event_ts(activity):  
    event_data = activity.channel_data.get("SlackMessage", {}).get("event", {})  
    event_ts = event_data.get("ts")  
    if event_ts:  
        logging.debug(f"Event ts: {event_ts}")  
        return event_ts  
    else:  
        logging.error("Event timestamp (ts) is None, cannot proceed.")  
        return None  
  
def add_reaction(token, channel, timestamp, reaction):  
    response = add_reaction_to_message(token, channel, timestamp, reaction)  
    if not response.get("ok"):  
        logging.error(f"Failed to add reaction: {response.get('error')}")  
    return response  
  
def remove_reaction(token, channel, timestamp, reaction):  
    response = remove_reaction_from_message(token, channel, timestamp, reaction)  
    if not response.get("ok"):  
        logging.error(f"Failed to remove reaction: {response.get('error')}")  
    return response  
  
def fetch_conversation_history(token, channel, thread_ts, bot_user_id):  
    conversation_history = get_conversation_replies(token, channel, thread_ts)  
    if conversation_history.get("ok"):  
        logging.debug(f"Conversation history: {conversation_history['messages']}")  
        return parse_chat_history(conversation_history["messages"], bot_user_id)  
    else:  
        logging.error(f"Error fetching conversation history: {conversation_history.get('error')}")  
        return [{"role": "system", "content": "This is the first and only message in this chat."}]  
  
async def handle_attachments(turn_context, attachments, thread_ts):  
    for attachment in attachments:  
        logging.debug(f"Processing attachment: {attachment.content_type}")  
        if attachment.content_type.startswith("image/"):  
            await handle_image_attachment(turn_context, attachment, thread_ts)  
        elif attachment.content_type == "text/plain":  
            await handle_text_attachment(turn_context, attachment, thread_ts)  
        elif attachment.content_type == "application/pdf":  
            await handle_pdf_attachment(turn_context, attachment, thread_ts)  
  
async def handle_slack_message(turn_context: TurnContext):  
    activity = turn_context.activity  
    try:  
        logging.debug(f"Payload passed from app.py via slack_handler.py")  
        user_message = activity.text  
        logging.debug(f"Received message")  
  
        # Log invocation details  
        invocation_data = {  
            "channel_id": activity.channel_id,  
            "message_type": activity.type,  
            "message_id": activity.id,  
            "timestamp_from_endpoint": activity.timestamp,  
            "local_timestamp_from_endpoint": get_current_time(),  
            "local_timezone_from_endpoint": "UTC",  # You can adjust this based on your needs  
            "service_url": activity.service_url,  
            "from_id": activity.from_property.id,  
            "from_name": activity.from_property.name,  
            "conversation_id": activity.conversation.id,  
            "attachment_exists": bool(activity.attachments),  
            "recipient_id": activity.recipient.id,  
            "recipient_name": activity.recipient.name,  
            "channeldata_slack_app_id": activity.channel_data.get("SlackMessage", {}).get("event", {}).get("app_id"),  
            "channeldata_slack_event_id": activity.channel_data.get("SlackMessage", {}).get("event", {}).get("event_id"),  
            "channeldata_slack_event_time": activity.channel_data.get("SlackMessage", {}).get("event", {}).get("event_time"),  
            "message_payload": json.dumps(activity.as_dict()),  
            "interacting_user_id": get_user_id(activity),  
            "channeldata_slack_thread_ts": get_parent_thread_ts(activity)  
        }  
        log_invocation_to_db(invocation_data)  
  
        if await handle_special_commands(turn_context):  
            return  
  
        channel_id = extract_channel_id(activity.conversation.id)  
        if not channel_id:  
            return  
        logging.debug(f"Extracted channel_id: {channel_id}")  
  
        thread_ts = get_parent_thread_ts(activity)  
        if not thread_ts:  
            return  
        logging.debug(f"Using thread_ts for response: {thread_ts}")  
  
        event_ts = get_event_ts(activity)  
        if not event_ts:  
            return  
        logging.debug(f"Using event_ts for reactions: {event_ts}")  
  
        add_reaction(SLACK_TOKEN, channel_id, event_ts, "hourglass")  
        user_id = get_user_id(activity)  
        if user_id:  
            user_mention = f"<@{user_id}>"  
            is_approved = is_user_approved(user_id)  
            if is_approved:  
                logging.info(f"User {user_id} is approved.")  
            else:  
                logging.info(f"User {user_id} is not approved.")  
        else:  
            user_mention = "User"  
  
        chat_history = fetch_conversation_history(SLACK_TOKEN, channel_id, thread_ts, activity.recipient.id)  
        if activity.attachments:  
            await handle_attachments(turn_context, activity.attachments, thread_ts)  
        else:  
            start_time = get_current_time()  
            logging.debug("Calling get_openai_response")  
            openai_response_data, model_name = get_openai_response(user_message, chat_history=chat_history, source="from_slack_handler")  
            logging.debug("Returned from get_openai_response")  
  
            logging.debug("Full JSON response from OpenAI:")  
            logging.debug(json.dumps(openai_response_data, indent=2))  
  
            bot_response = openai_response_data['choices'][0]['message']['content']  
            logging.debug(f"OpenAI response: {bot_response}")  
  
            usage = openai_response_data.get('usage', {})  
            input_tokens = usage.get('prompt_tokens', 0)  
            output_tokens = usage.get('completion_tokens', 0)  
  
            formatted_bot_response = convert_openai_response_to_slack_mrkdwn(bot_response)  
            response_time = calculate_elapsed_time(start_time)  
  
            footer = generate_footer("slack", response_time, model_name, input_tokens, output_tokens)  
            logging.debug(f"Generated footer: {footer}")  
  
            full_response = f"{user_mention} {formatted_bot_response}"  
            slack_message = create_slack_message(full_response, footer)  
            logging.debug(f"Slack message: {slack_message}")  
  
            response_data_list = post_message_to_slack(  
                token=SLACK_TOKEN,  
                channel=channel_id,  
                text=full_response,  
                blocks=slack_message['blocks'],  
                thread_ts=thread_ts  
            )  
            for response_data in response_data_list:  
                if not response_data.get("ok"):  
                    await turn_context.send_activity(response_data.get("error", "An error occurred while posting the message to Slack."))  
                    break  
  
        remove_reaction(SLACK_TOKEN, channel_id, event_ts, "hourglass")  
        add_reaction(SLACK_TOKEN, channel_id, event_ts, "white_check_mark")  
  
    except (KeyError, TypeError) as e:  
        logging.error(f"Error processing OpenAI response: {e}")  
        await turn_context.send_activity(SLACK_MSG_ERROR)  
        await turn_context.send_activity(SLACK_MSG_FIX_BOT)  
        footer = generate_footer("slack", 0)  
        await turn_context.send_activity(f"Footer: {footer}")  
  
    except Exception as e:  
        logging.error(f"Error in handle_slack_message: {e}")  
        await turn_context.send_activity(SLACK_MSG_ERROR)  
        await turn_context.send_activity(SLACK_MSG_FIX_BOT)  
        footer = generate_footer("slack", 0)  
        await turn_context.send_activity(f"Footer: {footer}")  
