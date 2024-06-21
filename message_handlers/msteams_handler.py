from botbuilder.core import TurnContext  
  
async def handle_msteams_message(turn_context: TurnContext):  
    user_message = turn_context.activity.text  
    response_message = f"[MSTeams Handler Response]: {user_message}"  
    await turn_context.send_activity(response_message)  
