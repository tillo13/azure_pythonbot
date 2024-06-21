import os  
from flask import Flask, request, jsonify, render_template  
import utils.openai_utils as openai_utils  
import json  
import time  
from datetime import datetime  
import base64  
import textract  
import re  
  
app = Flask(__name__)  
  
def calculate_cost(input_tokens, output_tokens, model='gpt-4o'):  
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
    total_tokens = 0  
    prompt_tokens = 0  
    completion_tokens = 0  
  
    if file:  
        file_content = file.read()  
        content_type = file.content_type  
        response_message = ""  
        user_action = f"You uploaded a file: {file.filename} ({content_type})"  
  
        start_time = time.time()  # Start timing here to include file processing time  
        if content_type.startswith("image/"):  
            # Handle image files  
            base64_image = base64.b64encode(file_content).decode("utf-8")  
            image_data_url = f"data:{content_type};base64,{base64_image}"  
            openai_response = openai_utils.get_openai_image_response(image_data_url)  
            response_message = openai_response  
            total_tokens = len(openai_response.split())  # Rough estimate for token count  
            prompt_tokens = total_tokens // 2  # Rough split between prompt and completion tokens  
            completion_tokens = total_tokens - prompt_tokens  
        elif content_type == "application/pdf":  
            # Handle PDF files  
            with open("temp.pdf", "wb") as pdf_file:  
                pdf_file.write(file_content)  
            pdf_text = openai_utils.extract_text_from_pdf("temp.pdf")  
            if pdf_text:  
                attempt_sizes = [5000, 6000, 7000]  
                summary_with_processing_summary = openai_utils.process_and_summarize_text(pdf_text, "PDF file", attempt_sizes)  
                response_message = summary_with_processing_summary  
                # Extract token usage and other stats from the processing summary  
                match = re.search(r'Total completion tokens \(OpenAI\): (\d+)\| Total prompt tokens \(OpenAI\): (\d+)\| Total tokens \(OpenAI\): (\d+)\|', summary_with_processing_summary)  
                if match:  
                    completion_tokens = int(match.group(1))  
                    prompt_tokens = int(match.group(2))  
                    total_tokens = int(match.group(3))  
                else:  
                    print("Token stats not found in PDF processing summary")  
            else:  
                response_message = "Could not extract text from PDF"  
        elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":  
            # Handle DOCX files  
            docx_text = openai_utils.extract_text_from_docx(file_content)  
            if docx_text:  
                attempt_sizes = [5000, 6000, 7000]  
                summary_with_processing_summary = openai_utils.process_and_summarize_text(docx_text, "DOCX file", attempt_sizes)  
                response_message = summary_with_processing_summary  
                # Extract token usage and other stats from the processing summary  
                match = re.search(r'Total completion tokens \(OpenAI\): (\d+)\| Total prompt tokens \(OpenAI\): (\d+)\| Total tokens \(OpenAI\): (\d+)\|', summary_with_processing_summary)  
                if match:  
                    completion_tokens = int(match.group(1))  
                    prompt_tokens = int(match.group(2))  
                    total_tokens = int(match.group(3))  
                else:  
                    print("Token stats not found in DOCX processing summary")  
            else:  
                response_message = "Could not extract text from DOCX"  
        elif content_type == "text/plain":  
            # Handle TXT files  
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
            # Extract token usage and other stats from the processing summary  
            match = re.search(r'Total completion tokens \(OpenAI\): (\d+)\| Total prompt tokens \(OpenAI\): (\d+)\| Total tokens \(OpenAI\): (\d+)\|', summary_with_processing_summary)  
            if match:  
                completion_tokens = int(match.group(1))  
                prompt_tokens = int(match.group(2))  
                total_tokens = int(match.group(3))  
            else:  
                print("Token stats not found in TXT processing summary")  
        else:  
            try:  
                # Attempt to extract text using textract for non-image, non-PDF, non-DOCX, non-TXT files  
                extracted_text = textract.process(file.filename, input_data=file_content).decode('utf-8')  
                attempt_sizes = [5000, 6000, 7000]  
                summary_with_processing_summary = openai_utils.process_and_summarize_text(extracted_text, "Uploaded file", attempt_sizes)  
                response_message = summary_with_processing_summary  
  
                # Extract token usage and other stats from the processing summary  
                match = re.search(r'Total completion tokens \(OpenAI\): (\d+)\| Total prompt tokens \(OpenAI\): (\d+)\| Total tokens \(OpenAI\): (\d+)\|', summary_with_processing_summary)  
                if match:  
                    completion_tokens = int(match.group(1))  
                    prompt_tokens = int(match.group(2))  
                    total_tokens = int(match.group(3))  
                else:  
                    print("Token stats not found in generic file processing summary")  
  
            except Exception as e:  
                print(f"Error processing file {file.filename}: {e}")  
                response_message = "This is an unsupported file type that we couldn't parse. Please try to make it a text file and upload again."  
  
        end_time = time.time()  
        round_trip_time = round(end_time - start_time, 2)  # Round-trip time in seconds  
  
        # Debug prints to verify token values  
        print(f"Total Tokens: {total_tokens}, Prompt Tokens: {prompt_tokens}, Completion Tokens: {completion_tokens}")  
  
        # Update chat history with user's file upload action and bot's response  
        chat_history.append({"role": "user", "content": user_action})  
        chat_history.append({"role": "assistant", "content": response_message})  
        openai_utils.save_chat_history(chat_history)  
  
        # Calculate estimated cost  
        estimated_cost = calculate_cost(prompt_tokens, completion_tokens)  
        estimated_cost_str = f"{estimated_cost:.8f}".rstrip('0').rstrip('.')  
  
        formatted_response = {  
            "response": response_message,  
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  
            "round_trip_time": round_trip_time,  
            "total_tokens": total_tokens,  
            "completion_tokens": completion_tokens,  
            "prompt_tokens": prompt_tokens,  
            "estimated_cost": estimated_cost_str,  
            "model": "gpt-4o-2024-05-13"  # Example model name; adjust as needed  
        }  
  
        return jsonify(formatted_response)  
  
    start_time = time.time()  
    bot_response_data = openai_utils.get_openai_response(user_message, chat_history)  
    end_time = time.time()  
    round_trip_time = round(end_time - start_time, 2)  # Round-trip time in seconds  
  
    # Print the raw response for debugging  
    print("Raw OpenAI response:", bot_response_data)  
  
    if 'error' in bot_response_data:  
        bot_response = bot_response_data['error']  
        total_tokens = 0  
        completion_tokens = 0  
        prompt_tokens = 0  
        model_name = "N/A"  # No model used due to error  
  
        # Handle content filter error  
        if "content filter" in bot_response:  
            # Rename the current chat history file  
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')  
            os.rename('chat_history.json', f'chat_history_{timestamp}.json')  
              
            # Inform the user that a new chat session has started  
            bot_response = "Your message triggered the content filter. A new chat session has started. Please modify your message and try again."  
            chat_history = []  # Clear chat history  
  
    else:  
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
  
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  
    print(f"[{timestamp}] You: {user_message}")  
    print(f"[{timestamp}] Bot: {bot_response}")  
  
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
