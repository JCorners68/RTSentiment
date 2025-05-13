# Sentimark Kanban Board System

## Quick Start: Launch the Kanban UI
./start_web_ui.sh
http://127.0.0.1:5500/kanban/kanban.html
```

A lightweight task tracking system for the Sentimark project, offering both CLI and REST API interfaces.

## Interfaces

Choose the interface that best fits your needs and environment:

### 1. Command Line Interface (CLI)

```bash
# Use the simple bash commands directly
./kanban.sh [command] [options]
./cca-task.sh [command] [options]

# OR use the text-based interactive UI
./run_simple_app.sh
```

See [README_SIMPLE_APP.md](README_SIMPLE_APP.md) for details on the text-based UI.

### 2. Web UI with FastAPI Backend

The easiest way to use the web UI is with the provided script:

```bash
# Start both the FastAPI backend and open the HTML UI
./start_web_ui.sh

# To stop the server when done
# Press Ctrl+C in the terminal where the server is running
```

This will:
1. Start the FastAPI backend server
2. Open the API documentation in your browser
3. Open the Kanban HTML UI in your browser

The web interface features:
- Interactive Kanban board with task management
- Task cards with color-coding by task type
- Detailed task view with full history and evidence
- Filtering by column, task type, and search term
- Task creation, editing, and deletion
- Evidence tracking with Markdown support
- Column-based workflow visualization
- Responsive interface for all devices
- Gemini API integration for generating Claude prompts

#### Manual Setup (if needed)

You can also start the components manually:

```bash
# Start the FastAPI server
cd api
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Then open `kanban.html` in your browser.

The API server will be available at:
- API: http://127.0.0.1:8000
- Interactive API documentation (Swagger UI): http://127.0.0.1:8000/docs
- Alternative API documentation (ReDoc): http://127.0.0.1:8000/redoc

#### Stopping the Server

To stop the FastAPI server:

```bash
# If running in the foreground (with output displayed in the terminal)
Press Ctrl+C in the terminal where the server is running

# If running in the background or if Ctrl+C doesn't work
# Find the process ID
ps aux | grep "uvicorn"

# Kill the process (replace PID with the actual process ID number)
kill PID

# If that doesn't work, force kill
kill -9 PID
```

See [api/README.md](api/README.md) for more details on the REST API.

## Features

- JSON-based task tracking with predefined workflow columns
- Task management (add, move, edit, delete)
- Evidence tracking and verification steps
- Claude AI integration for task processing
- Gemini API integration for generating detailed prompts
- Multiple interfaces sharing the same data store
- Support for different task types and priorities
- Search functionality
- Task filtering and organization
- "Prompt Ready" task listing and management
- Prompt viewing and processing tools
- RESTful API for integration with other tools
- Responsive HTML UI with modern interface

## Setup

1. Ensure you have `jq` installed (required for CLI tools):
   - For Ubuntu/Debian: `sudo apt-get install jq`
   - For macOS: `brew install jq`
   - For Windows (with Chocolatey): `choco install jq`

2. Make the scripts executable (in WSL/Linux/macOS):
   ```bash
   chmod +x kanban.sh cca-task.sh run_simple_app.sh simple_app.py
   ```

3. For the FastAPI interface, see [api/README.md](api/README.md) for setup instructions.

## Core Command Line Usage

### Basic Kanban Commands

```bash
# Create a new task
./kanban.sh add "Task Title" "Task Description" "Task Type"

# View the entire board
./kanban.sh board

# List all tasks
./kanban.sh list

# List tasks in a specific column
./kanban.sh list "In Progress"

# View task details
./kanban.sh show TASK-ID

# Move a task to a different column
./kanban.sh move TASK-ID "Column Name"

# Add evidence of completion
./kanban.sh evidence TASK-ID "Evidence of completion with verification steps"

# Display help
./kanban.sh help
```

### Claude Integration

```bash
# Prepare a task for Claude (manual mode)
./cca-task.sh process TASK-ID

# Complete a task with evidence
./cca-task.sh complete TASK-ID "Evidence of completion"

# Display help for Claude integration
./cca-task.sh help
```

### Prompt Management

```bash
# List all tasks in the "Prompt Ready" column
./simple_app.py prompt-ready
# Or use the shorthand
./simple_app.py pr

# View the full prompt for a specific task
./simple_app.py prompt-view TASK-ID
# Or use the shorthand
./simple_app.py pv TASK-ID

# Interactive prompt processing (list tasks, then select one to process)
./process_prompt.sh

# Process a specific task
./process_prompt.sh process TASK-ID

# View a specific prompt
./process_prompt.sh view TASK-ID

# Show help for prompt processing
./process_prompt.sh help
```

## Workflow

1. Create tasks using `./kanban.sh add` or through one of the interfaces
2. Process tasks with Claude using `./cca-task.sh process`
3. Claude provides implementation and verification steps
4. Evidence is captured and the task is moved to "Needs Review"
5. Review the task and move it to "Done" if acceptable

## File Structure

- `kanban.json` - JSON file storing the Kanban board data
- `kanban.sh` - Main script for Kanban board management
- `cca-task.sh` - Script for Claude AI integration
- `simple_app.py` - Text-based UI for terminal environments
- `run_simple_app.sh` - Script to launch the text-based UI
- `kanban.html` - HTML UI that connects to the FastAPI backend
- `start_web_ui.sh` - Script to start the FastAPI backend and open the HTML UI
- `README_SIMPLE_APP.md` - Documentation for the text-based UI
- `api/` - FastAPI REST API implementation
  - `main.py` - FastAPI application entry point
  - `models.py` - Pydantic models for data validation
  - `services.py` - Business logic for the Kanban board
  - `routers/` - API route definitions
  - `tests/` - Unit tests
  - `README.md` - API documentation

## Notes

- All interfaces work with the same underlying data in `kanban.json`
- When using Claude, ensure it provides a TASK-EVIDENCE line at the end of its response
- This line will be automatically extracted and added to the task
- The task will be moved to "Needs Review" automatically
- If no TASK-EVIDENCE line is found, you'll need to add it manually
- The system allows for seamless switching between interfaces as needed

## Gemini API Key Configuration

To enable the Gemini prompt generation feature in the web interface, you need to configure a Google Gemini API key:

1. **Create a Gemini API key**:
   - Visit [Google AI Studio](https://ai.google.dev/)
   - Create or sign in to your Google account
   - Create an API key from the API Keys section

2. **Configure the API key** (choose one method):
   - **Recommended**: Create a config file:
     ```bash
     # Create the file from the template
     cp config/api_keys.template.json config/api_keys.json

     # Edit the file to add your API key
     nano config/api_keys.json
     ```
   - **Alternative**: Set an environment variable:
     ```bash
     export GEMINI_API_KEY=your-api-key-here
     ./start_web_ui.sh
     ```
   - **One-time use**: Enter the API key in the web UI when generating a prompt

3. **Security notes**:
   - The `config/api_keys.json` file is excluded from git via `.gitignore`
   - Keep your API key secure and never commit it to version control
   - The app will never store your API key in the code or in logs