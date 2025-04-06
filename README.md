# AI Content Generation Service for LMS

## Overview

This project is a Python backend service (using FastAPI) designed to generate educational content for Learning Management Systems (LMS). It provides an API endpoint that accepts a topic and content type (`paragraph`, `multiple_choice_question`, `quiz`) and uses the Google Gemini API (`gemini-1.5-flash` model) to generate the corresponding content. The output is returned as structured JSON.

The service is built for easy integration and suitable for serverless deployment.

## Core Features

*   AI content generation via Google Gemini (`gemini-1.5-flash`).
*   Supports paragraphs, multiple-choice questions (MCQs), and quizzes (title + 3 MCQs).
*   Accepts optional context to guide generation.
*   Returns structured JSON output specific to each content type.
*   Built with FastAPI for async performance and easy API docs.
*   Includes basic error handling and logging.

## Tech Stack

*   Python (3.11)
*   FastAPI, Uvicorn
*   `google-generativeai` SDK
*   Pydantic, `python-dotenv`

## Setup & Running Locally

1.  **Clone:** `git clone <[[your-repository-url](https://github.com/yehuda-yu/ai-content-generation-service)](https://github.com/yehuda-yu/ai-content-generation-service)>` & `cd <repository-directory-name>`
2.  **Environment:**
    *   `conda create --name ai_content_env python=3.11`
    *   `conda activate ai_content_env`
    *(Or use standard Python `venv`)*
3.  **Install:** `pip install -r requirements.txt`
4.  **Configure API Key:**
    *   Copy `.env.example` to `.env` (`copy .env.example .env` on Windows).
    *   Edit `.env` and add your `GEMINI_API_KEY="YOUR_KEY_HERE"`.
    *   **Do NOT commit `.env`**.
5.  **Run:** `uvicorn main:app --reload`
6.  **Access:** API available at `http://127.0.0.1:8000`. Interactive docs at `http://127.0.0.1:8000/docs`.

## API Usage

*   **Endpoint:** `POST /generate`
*   **Request Body (JSON):**
    ```json
    {
      "topic": "string", // Required
      "content_type": "string", // Required: 'paragraph', 'multiple_choice_question', 'quiz'
      "context": "string" // Optional
    }
    ```
*   **Success Response (Examples):**
    *   **Paragraph:** `{"type": "paragraph", "content": "..."}`
    *   **MCQ:** `{"type": "multiple_choice_question", "question_text": "...", "options": [...], "correct_answer_index": ...}`
    *   **Quiz:** `{"type": "quiz", "title": "...", "questions": [ <list of MCQ objects> ]}`
*   **Error Responses:** Standard HTTP codes (400, 422, 500, 503) indicate issues (invalid input, LLM API failure, parsing failure). Check server logs for details.

## Implementation Notes

*   **Prompt Engineering:** Specific prompts guide the LLM to generate content in a structured text format suitable for parsing.
*   **Parsing:** Python functions parse the LLM's text output based on expected keywords and structure (e.g., `Question:`, `A:`, `Correct Answer:`). Relies on LLM adherence to prompts.
*   **Serverless Design:** Uses environment variables for configuration and standard logging, making it suitable for platforms like Google Cloud Run.
