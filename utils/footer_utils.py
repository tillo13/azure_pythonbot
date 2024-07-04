import logging  
from .openai_utils import calculate_cost  # Use relative import  
  
APP_VERSION = "1.0703.2210"  
  
def generate_footer(platform: str, response_time: float, model_name: str = "placeholder_model", input_tokens: int = 0, output_tokens: int = 0) -> str:  
    """Generates a footer string with application version, OpenAI model information, cost, and response time.  
      
    Args:  
        platform (str): The platform for which the footer is being generated (e.g., "slack", "webchat").  
        response_time (float): The response time for the call.  
        model_name (str, optional): The name of the OpenAI model used. Defaults to "placeholder_model".  
        input_tokens (int, optional): The number of input tokens used. Defaults to 0.  
        output_tokens (int, optional): The number of output tokens used. Defaults to 0.  
          
    Returns:  
        str: The formatted footer string.  
    """  
    logging.debug(f"Generating footer for platform: {platform} with response time: {response_time:.3f}s and model: {model_name}")  
  
    estimated_cost = calculate_cost(model_name, input_tokens, output_tokens)  
    footer = f"App Version: {APP_VERSION} | OpenAI Model: {model_name} (Cost: ~${estimated_cost:.4f}) | Response Time: {response_time:.3f}s"  
      
    if platform == "slack":  
        footer = f"*App Version*: `{APP_VERSION}` | *OpenAI Model*: `{model_name}` (Cost: ~`${estimated_cost:.4f}`) | *Response Time*: `{response_time:.3f}s`"  
      
    logging.debug(f"Generated footer: {footer}")  
    return footer  
