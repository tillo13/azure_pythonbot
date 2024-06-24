# Azure Python Bot  
  
## Overview  
  
This repository contains an Azure-based chatbot application that leverages OpenAI's GPT-4 model for various functionalities. The chatbot is designed to handle multiple types of inputs, including text messages, image files, PDF documents, and more. It can respond to Slack messages, provide summaries of uploaded files, and interact with JIRA to fetch issue details. 

## CI/CD Pipeline  configuration
  
This repository uses a CI/CD pipeline to automate the deployment process. The pipeline involves two `git_push` scripts:  
  
1. **`projects/azure_pythonbot/git_push.sh`**: This script is responsible for pushing changes to the `azure_pythonbot` repository. It also copies specified files to the `tillo13_github/azure_pythonbot` directory and invokes the second `git_push` script.  
    
2. **`projects/tillo13_github/azure_pythonbot/git_push.sh`**: This script pushes changes to the `tillo13_github/azure_pythonbot` repository. This repository is integrated with GitHub Actions through the Azure Bot Portal's Deployment Center. When changes are pushed to the `main` branch, it triggers a GitHub Action workflow that deploys the code to the production environment.  
  
### Deployment Center Configuration  
  
- **Source**: GitHub  
- **Repository**: azure_pythonbot  
- **Branch**: main  
- **Build Provider**: GitHub Actions  
- **Runtime Stack**: Python  
- **Version**: Python 3.11  
  
For more details on how the Deployment Center works, please refer to the [Azure Portal](https://portal.azure.com/#@tdlabsazure.onmicrosoft.com/resource/subscriptions/54a986d9-0035-4390-95e3-34d953f9099a/resourceGroups/Tillo-OpenAI/providers/Microsoft.Web/sites/2024may23-pythonbot-tillo/vstscd).  
  
## Features  
  
- **Text Message Handling**: The bot can process and respond to text messages using OpenAI's GPT-4 model.  
- **Image Processing**: Upload an image, and the bot will describe it in detail.  
- **PDF Summarization**: Upload a PDF document, and the bot will extract text and provide a summary.  
- **Slack Integration**: The bot can respond to messages on Slack, including handling threads and reactions.  
- **JIRA Integration**: Fetch and display details of JIRA issues.  
- **Special Commands**: The bot can execute special commands prefixed with `$`, such as `$jira ISSUE_KEY`.  
  
## Directory Structure  
  
```plaintext  
azure_pythonbot/  
├── __pycache__/  
├── constants.py  
├── local_chatbot.py  
├── static/  
├── app.py  
├── extra/  
├── message_handlers/  
│   ├── slack_handler.py  
│   └── default_handler.py  
├── templates/  
├── azure_pythonbot.bot  
├── git_push.sh  
├── requirements.txt  
├── utils/  
│   ├── uploaded_file_utils.py  
│   ├── openai_utils.py  
│   ├── datetime_utils.py  
│   ├── footer_utils.py  
│   ├── jira_utils.py  
│   ├── slack_utils.py  
│   └── special_commands_utils.py  
└── temp.pdf  
 
## Setup  
  
### Prerequisites  
  
- Python 3.8+  
- `pip` (Python package installer)  
  
### Installation  
  
1. **Clone the repository**:  
    ```bash  
    git clone https://github.com/yourusername/azure_pythonbot.git  
    cd azure_pythonbot  
    ```  
  
2. **Create a virtual environment**:  
    ```bash  
    python -m venv .venv  
    source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`  
    ```  
  
3. **Install dependencies**:  
    ```bash  
    pip install -r requirements.txt  
    ```  
  
4. **Set up environment variables**:  
    Create a `.env` file in the project root and add the necessary environment variables:  
    ```plaintext  
    APPSETTING_MICROSOFT_APP_ID=your_app_id  
    APPSETTING_MICROSOFT_APP_PASSWORD=your_app_password  
    APPSETTING_SLACK_TOKEN=your_slack_token  
    APPSETTING_2023sept8_JIRA_SERVER=your_jira_server  
    APPSETTING_2023sept8_JIRA_USERNAME=your_jira_username  
    APPSETTING_2023sept8_JIRA_TOKEN=your_jira_token  
    APPSETTING_2023sept8_JIRA_PARENT_KEY=your_jira_parent_key  
    APPSETTING_2023sept8_JIRA_PROJECT_NAME=your_jira_project_name  
    APPSETTING_2023oct6_JIRA_DEFAULT_USER_ACCOUNT_ID=your_jira_default_user_account_id  
    APPSETTING_2023oct6_JIRA_DEFAULT_LABEL_TITLE=your_jira_default_label_title  
    APPSETTING_2024may22_GPT4o_API_KEY=your_openai_api_key  
    APPSETTING_AZURE_OPENAI_ENDPOINT=your_azure_openai_endpoint  
    APPSETTING_AZURE_OPENAI_API_VERSION=your_azure_openai_api_version  
    APPSETTING_CHAT_COMPLETIONS_DEPLOYMENT_NAME=your_openai_model_deployment_name  
    ```  
  
## Usage  
  
### Running the Application  
  
**To run the bot server**:  
```bash  
python app.py  
```### Special Commands  
  
- `$hello`: The bot will greet you.  
- `$world`: The bot will provide information about the world.  
- `$test`: The bot will acknowledge that the special test path was invoked.  
- `$jira ISSUE_KEY`: Fetch and display details for the specified JIRA issue key.  
  
### File Uploads  
  
- **Image Files**: The bot will describe the uploaded image.  
- **PDF Files**: The bot will extract text and provide a summary of the PDF document.  
- **Text Files**: The bot will process and summarize the text file.  
  
## Detailed Explanation of Key Files  
  
### `app.py`  
  
This is the main entry point for the bot, which handles incoming HTTP requests and processes messages using the Bot Framework Adapter. It routes messages to the appropriate handlers based on the message type and channel.  
  
### `local_chatbot.py`  
  
A Flask-based local chatbot application that allows for interaction with the bot through a web interface. It supports file uploads and text inputs.  
  
### `constants.py`  
  
Contains various constant messages used throughout the application for different types of responses, including error messages and Slack-specific messages.  
  
### `message_handlers/slack_handler.py`  
  
Handles incoming messages from Slack. It can process text, images, and file attachments, and respond accordingly. It also adds and removes reactions to messages.  
  
### `message_handlers/default_handler.py`  
  
Handles default message processing for non-Slack channels. It routes messages to OpenAI and processes responses.  
  
### `utils/openai_utils.py`  
  
Contains utility functions for interacting with OpenAI's API, including sending messages, processing image responses, and summarizing text.  
  
### `utils/uploaded_file_utils.py`  
  
Handles the processing of various file types, including images, PDFs, and text files. It sends the extracted content to OpenAI for further processing and summarization.  
  
### `utils/footer_utils.py`  
  
Generates footer information for responses, including application version, OpenAI model details, and response times.  
  
### `utils/jira_utils.py`  
  
Contains functions for interacting with JIRA, including fetching issue details and formatting the response for display.  
  
### `utils/slack_utils.py`  
  
Provides utility functions for interacting with Slack, including posting messages, adding/removing reactions, and formatting messages.  
  
### `utils/special_commands_utils.py`  
  
Handles special commands prefixed with `$`, such as fetching JIRA issue details or executing predefined commands.  