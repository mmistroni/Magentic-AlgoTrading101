# Agent Directory Template

This document outlines the standard directory structure and files for creating a new agent in the `agents/` directory. Each agent should follow this template to maintain consistency across the project.

## Directory Structure

```
agents/
  └── <agent_name>/
      ├── clients/               # Client-related code (in parent directory)
      ├── deployment/            # Deployment-specific code (in parent directory)
      ├── eval/                  # Evaluation scripts and data (in parent directory)
      ├── tests/                 # Unit tests (in parent directory)
      ├── <agent_name>/          # Main agent code directory (unit tests and agent code)
      ├── deploy.py              # Deployment script
      ├── deployment_config.yaml # Configuration for deployment
      ├── pyproject.toml         # Python project configuration
      ├── readme.md              # Agent-specific README
      ├── requirements.txt       # Python dependencies (if not using pyproject.toml)
      └── test_<agent_name>.py   # Integration tests (optional)
```

## Files and Directories Description

- **`<agent_name>/`**: The root directory for the agent, named after the agent (e.g., `adk_gsheet_agent`).
  - **`clients/`**: Code for interacting with external APIs or services.
  - **`deployment/`**: Scripts and configurations for deploying the agent.
  - **`eval/`**: Scripts for evaluating the agent's performance.
  - **`tests/`**: Unit tests for the agent's code.
  - **`<agent_name>/<agent_name>/`**: The main code directory, containing the agent's implementation and unit tests.
- **`deploy.py`**: Python script to deploy the agent.
- **`deployment_config.yaml`**: YAML configuration file for deployment settings.
- **`pyproject.toml`**: Configuration file for Python project management (dependencies, build, etc.).
- **`readme.md`**: Markdown file with documentation for the agent.
- **`requirements.txt`**: List of Python dependencies (alternative to pyproject.toml).
- **`test_<agent_name>.py`**: Optional integration test file.

## Usage

To create a new agent directory based on this template:

1. Replace `<agent_name>` with the actual name of your agent.
2. Create the directories and files as outlined above.
3. Populate the files with appropriate content for your agent.
4. Ensure the agent follows the project's coding standards and includes necessary tests.

## Examples

- For `adk_gsheet_agent`: Follows this structure with Google Sheets integration.
- For `agent_crawler`: Includes a Dockerfile for containerization.

This template ensures all agents have a consistent structure for maintainability and deployment.