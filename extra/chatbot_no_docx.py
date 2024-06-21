# chatbot.py  
from flask import Flask, request, jsonify, render_template  
import utils.openai_utils as openai_utils  
import json  
import time  
from datetime import datetime  
import base64  
  
app = Flask(__name__)  
  
def calculate_cost(input_tokens, output_tokens, model='gpt-4o'):  
    # Pricing for GPT-4o as per the provided information  
    price_per_million_input_tokens = 5.00  # $ per 1M input tokens  
    price_per_million_output_tokens = 15.00  # $ per 1M output tokens  
  
    input_cost = (input_tokens / 1_000_000) * price_per_million_input_tokens  
    output_cost = (output_tokens / 1_000_000) * price_per_million_output_tokens  
  
    total_cost = input_cost + output_cost  
    return total_cost  
  
@app.route('/')  
def home():  
    return render_template('home.html')  
  
@app.route('/chat', methods=['POST'])  
def chat():  
    user_message = request.form.get('message')  
    file = request.files.get('file')  
  
    if not user_message and not file:  
        return jsonify({"error": "No message or file provided"}), 400  
  
    chat_history = openai_utils.load_chat_history()  
  
    if file:  
        file_content = file.read()  
        content_type = file.content_type  
        response_message = ""  
  
        if content_type.startswith("image/"):  
            base64_image = base64.b64encode(file_content).decode("utf-8")  
            image_data_url = f"data:{content_type};base64,{base64_image}"  
            openai_response = openai_utils.get_openai_image_response(image_data_url)  
            response_message = openai_response  
        elif content_type == "text/plain":  
            try:  
                file_text = file_content.decode('utf-8')  
            except UnicodeDecodeError:  
                try:  
                    file_text = file_content.decode('latin-1')  
                except UnicodeDecodeError:  
                    return jsonify({"error": "Unsupported text encoding in file"}), 400  
  
            attempt_sizes = [5000, 6000, 7000]  
            summary_with_processing_summary = openai_utils.process_and_summarize_text(file_text, "Text file", attempt_sizes)  
            response_message = summary_with_processing_summary  
        elif content_type == "application/pdf":  
            with open("temp.pdf", "wb") as pdf_file:  
                pdf_file.write(file_content)  
            pdf_text = openai_utils.extract_text_from_pdf("temp.pdf")  
            if pdf_text:  
                attempt_sizes = [5000, 6000, 7000]  
                summary_with_processing_summary = openai_utils.process_and_summarize_text(pdf_text, "PDF file", attempt_sizes)  
                response_message = summary_with_processing_summary  
            else:  
                response_message = "Could not extract text from PDF"  
        else:  
            response_message = "Unsupported file type"  
  
        return jsonify({"response": response_message})  
  
    start_time = time.time()  
    bot_response_data = openai_utils.get_openai_response(user_message, chat_history)  
    end_time = time.time()  
  
    round_trip_time = round(end_time - start_time, 2)  # Round-trip time in seconds  
  
    # Print the raw response for debugging  
    print("Raw OpenAI response:", bot_response_data)  
  
    try:  
        bot_response = bot_response_data['choices'][0]['message']['content']  
        total_tokens = bot_response_data['usage']['total_tokens']  
        completion_tokens = bot_response_data['usage']['completion_tokens']  
        prompt_tokens = bot_response_data['usage']['prompt_tokens']  
        model_name = bot_response_data['model']  # Extract the model name  
    except (KeyError, TypeError) as e:  
        print("Error processing OpenAI response:", e)  
        return jsonify({"error": "Error processing OpenAI response"}), 500  
  
    openai_utils.update_chat_history(chat_history, user_message, bot_response)  
  
    # Log detailed interaction information with timestamps  
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  
    print(f"[{timestamp}] You: {user_message}")  
    print(f"[{timestamp}] Bot: {bot_response}")  
  
    # Calculate estimated cost  
    estimated_cost = calculate_cost(prompt_tokens, completion_tokens)  
    estimated_cost_str = f"{estimated_cost:.8f}".rstrip('0').rstrip('.')  
  
    formatted_response = {  
        "response": bot_response,  
        "timestamp": timestamp,  
        "round_trip_time": round_trip_time,  
        "total_tokens": total_tokens,  
        "completion_tokens": completion_tokens,  
        "prompt_tokens": prompt_tokens,  
        "estimated_cost": estimated_cost_str,  
        "model": model_name  # Include the model name in the response  
    }  
  
    return jsonify(formatted_response)  
  
if __name__ == '__main__':  
    app.run(debug=True)  
