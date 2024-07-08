import logging  
from .openai_utils import calculate_cost  # Use relative import  
  
APP_VERSION = "1.0707.1205"  
  
def generate_footer(platform: str, response_time: float, model_name: str = "gpt-4o", input_tokens: int = 0, output_tokens: int = 0) -> str:  
    """Generates a footer string with application version, OpenAI model information, cost, and response time.  
      
    Args:  
        platform (str): The platform for which the footer is being generated (e.g., "slack", "webchat").  
        response_time (float): The response time for the call.  
        model_name (str, optional): The name of the OpenAI model used. Defaults to "gpt-4o".  
        input_tokens (int, optional): The number of input tokens used. Defaults to 0.  
        output_tokens (int, optional): The number of output tokens used. Defaults to 0.  
  
    Returns:  
        str: The formatted footer string.  
    """  
    logging.debug(f"Generating footer for platform: {platform} with response time: {response_time:.3f}s and model: {model_name}")  
    logging.debug(f"Received input tokens: {input_tokens}, output tokens: {output_tokens}")  
  
    # Check if the model name contains "gpt-4o" and set the cost accordingly  
    if "gpt-4o" in model_name:  
        logging.debug(f"Model name contains 'gpt-4o'. Setting model_name to 'gpt-4o'")  
        model_name = "gpt-4o"  
    else:  
        logging.debug(f"Model name does not contain 'gpt-4o'. Using model name: {model_name}")  
  
    logging.debug(f"Calculating cost for model {model_name} with input tokens {input_tokens} and output tokens {output_tokens}")  
    estimated_cost = calculate_cost(model_name, input_tokens, output_tokens)  
    logging.debug(f"Calculated cost for model {model_name}: input_cost={input_tokens}, output_cost={output_tokens}, total_cost={estimated_cost:.4f}")  
  
    footer = f"App Version: {APP_VERSION} | OpenAI Model: {model_name} (Cost: ~${estimated_cost:.4f}) | Response Time: {response_time:.3f}s"  
  
    if platform == "slack":  
        footer = f"*App Version*: `{APP_VERSION}` | *OpenAI Model*: `{model_name}` (Cost: ~`${estimated_cost:.4f}`) | *Response Time*: `{response_time:.3f}s`"  
  
    logging.debug(f"Generated footer: {footer}")  
    return footer  
