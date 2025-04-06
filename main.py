# Core Python libraries
import os
import logging # Import the logging module
from dotenv import load_dotenv
from typing import Literal

# --- Load Environment Variables ---
load_dotenv()

# --- Configure Logging ---
logging.basicConfig(
    level=logging.INFO, # Set the minimum level to log (INFO, DEBUG, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s', # Define log message format
    datefmt='%Y-%m-%d %H:%M:%S' # Define date format
)
# Get a logger instance for this module
logger = logging.getLogger(__name__)

# --- FastAPI & Pydantic ---
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

# --- Google Gemini ---
import google.generativeai as genai

# --- Access and Configure API Keys ---
gemini_api_key = os.getenv("GEMINI_API_KEY")

if gemini_api_key:
    genai.configure(api_key=gemini_api_key)
    logger.info("Gemini API Key loaded and client configured.") # Use logger.info
else:
    # Use logger.warning for configuration issues that aren't fatal errors yet
    logger.warning("GEMINI_API_KEY not found in environment variables.")
    logger.warning("The application will not be able to contact the Gemini API.")

# === LLM Interaction Function ===
async def call_gemini_api(prompt: str) -> Optional[str]:
    """Calls the Gemini API, logging info and errors."""
    if not gemini_api_key:
        logger.error("Cannot call Gemini API: API key is not configured.") # Use logger.error
        return None

    model = genai.GenerativeModel('gemini-2.0-flash')
    logger.info(f"Sending request to Gemini model '{model._model_name}'...") # logger.info
    # logger.debug(f"Full prompt being sent:\n{prompt}") # Example of DEBUG level

    try:
        response = await model.generate_content_async(prompt)
        logger.info("Received response from Gemini API.") # logger.info

        if response.text:
            # logger.debug(f"Raw Response Text Snippet:\n{response.text[:200]}...") # DEBUG level
            return response.text
        else:
            # Log response issues as warnings or errors depending on severity
            logger.warning(f"Gemini response OK but contained no text. Feedback: {response.prompt_feedback}")
            return None

    except Exception as e:
        # Log exceptions with error level
        logger.error(f"Exception during Gemini API call: {type(e).__name__} - {e}", exc_info=True)
        # exc_info=True adds traceback information to the log, very useful!
        return None

# === Parsing Functions ===
def parse_mcq_output(raw_text: str) -> Optional[dict]:
    """Parses MCQ output, logging info and errors."""
    question_text = None
    options = []
    correct_answer_letter = None
    temp_options = {}
    lines = raw_text.strip().split('\n')
    logger.info(f"Attempting to parse MCQ from {len(lines)} lines...") # logger.info

    for line in lines:
        line = line.strip()
        if not line: continue

        try:
            # Using logger.debug for very fine-grained parsing steps might be excessive for INFO level
            # Stick to INFO for major parts found, ERROR for failures
            if line.startswith("Question:"):
                question_text = line.split(":", 1)[1].strip()
            elif line.startswith("A:"): temp_options['A'] = line.split(":", 1)[1].strip()
            elif line.startswith("B:"): temp_options['B'] = line.split(":", 1)[1].strip()
            elif line.startswith("C:"): temp_options['C'] = line.split(":", 1)[1].strip()
            elif line.startswith("D:"): temp_options['D'] = line.split(":", 1)[1].strip()
            elif line.startswith("Correct Answer:"): correct_answer_letter = line.split(":", 1)[1].strip().upper()
        except IndexError:
            logger.warning(f"Could not parse MCQ line: '{line}' - missing text after colon?")
            continue

    if question_text and len(temp_options) == 4 and correct_answer_letter in ['A', 'B', 'C', 'D']:
        options = [temp_options.get('A'), temp_options.get('B'), temp_options.get('C'), temp_options.get('D')]
        if None in options:
             logger.error(f"MCQ Parsing Error: Missing one of the options A, B, C, D. Found: {temp_options}")
             logger.error(f"Raw Text Snippet:\n{raw_text[:200]}...")
             return None
        correct_answer_index = ord(correct_answer_letter) - ord('A')
        logger.info("Successfully parsed all MCQ components.") # logger.info
        return { "type": "multiple_choice_question", "question_text": question_text, "options": options, "correct_answer_index": correct_answer_index }
    else:
        # Use logger.error for parsing failures
        logger.error("MCQ Parsing Error: Failed to find all required components.")
        logger.error(f"  > Question found: {'Yes' if question_text else 'No'}")
        logger.error(f"  > Options found: {len(temp_options)}/4 {list(temp_options.keys())}")
        logger.error(f"  > Correct Answer letter found: {correct_answer_letter if correct_answer_letter else 'No'}")
        logger.error(f"  > Raw Text Snippet:\n{raw_text[:200]}...")
        return None

def parse_quiz_output(raw_text: str) -> Optional[dict]:
    """Parses Quiz output, logging info and errors."""
    title = None
    questions = []
    current_question_lines = []
    lines = raw_text.strip().split('\n')
    expected_questions = 3
    logger.info(f"Attempting to parse Quiz from {len(lines)} lines...") # logger.info

    # --- Find Title ---
    first_line = lines[0].strip() if lines else ""
    if first_line.startswith("Quiz Title:"):
        try:
            title = first_line.split(":", 1)[1].strip()
            logger.info(f"Found Quiz Title: {title}") # logger.info
            lines = lines[1:]
        except IndexError:
             logger.error("Quiz Parsing Error: Found 'Quiz Title:' but no text after it.") # logger.error
             logger.error(f"Raw Text Snippet:\n{raw_text[:200]}...")
             return None
    else:
        logger.error("Quiz Parsing Error: 'Quiz Title:' not found on the first line.") # logger.error
        logger.error(f"Raw Text Snippet:\n{raw_text[:200]}...")
        return None

    # --- Find and Parse Questions ---
    question_count = 0
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped: continue

        if line_stripped and line_stripped[0].isdigit() and '.' in line_stripped.split()[0]:
            question_count += 1
            if current_question_lines:
                logger.info(f"Processing collected lines for quiz question block #{question_count-1}...") # logger.info
                question_block = "\n".join(current_question_lines)
                parsed_mcq = parse_mcq_output(question_block) # Reuses MCQ parsing & logging
                if parsed_mcq:
                    questions.append(parsed_mcq)
                else:
                    logger.error(f"Quiz Parsing Error: Failed to parse question block #{question_count-1}.") # logger.error
                    # Raw block snippet logged by parse_mcq_output failure
                    return None
                current_question_lines = []
            # logger.debug(f"Detected start of question {question_count}: '{line_stripped}'") # DEBUG
        else:
            current_question_lines.append(line)

    # --- Parse the Last Collected Question ---
    if current_question_lines:
        logger.info(f"Processing collected lines for the last quiz question block...") # logger.info
        question_block = "\n".join(current_question_lines)
        parsed_mcq = parse_mcq_output(question_block)
        if parsed_mcq:
            questions.append(parsed_mcq)
        else:
            logger.error(f"Quiz Parsing Error: Failed to parse last question block.") # logger.error
            # Raw block snippet logged by parse_mcq_output failure
            return None

    # --- Final Validation ---
    if len(questions) == expected_questions:
        logger.info(f"Successfully parsed Quiz Title and {len(questions)} questions.") # logger.info
        return { "type": "quiz", "title": title, "questions": questions }
    else:
        logger.error(f"Quiz Parsing Error: Found {len(questions)} questions, but expected {expected_questions}.") # logger.error
        logger.error(f"Raw Text Snippet:\n{raw_text[:200]}...")
        return None


PARAGRAPH_PROMPT_TEMPLATE = """**Role:** You are an AI assistant specialized in creating clear, concise, and informative educational content for a Learning Management System (LMS). Your default tone should be neutral and objective unless specified otherwise by the context.

**Task:** Generate a single block of text forming one paragraph that explains the specified topic.

**Topic:** "{topic}"

**Context/Instructions:** "{context}"
*   Use this context to adapt the explanation's depth, focus, complexity, or tone (e.g., 'for beginners', 'focus on applications', 'use an engaging tone'). If context is 'None provided.', generate a standard, informative paragraph.

**Output Requirements:**
*   **Strictly Output ONLY the paragraph text.**
*   Do NOT include any titles, headings, labels (like "Paragraph:"), or introductory/concluding phrases (like "Here is the paragraph:", "In summary...", etc.).
*   The output must be suitable for direct insertion into an LMS lesson component.
""" # Note the triple quotes ending the string

MCQ_PROMPT_TEMPLATE = """**Role:** You are an AI expert creating high-quality assessment questions for an educational setting (LMS).

**Task:** Generate **ONE** multiple-choice question based on the specified topic and context.

**Topic:** "{topic}"

**Context/Instructions:** "{context}"
*   Use this context to adjust the question's difficulty (e.g., easy recall, challenging application), specific focus area, or target audience. If 'None provided.', generate a standard question testing basic understanding.

**Question Requirements:**
1.  **Clarity:** The question text must be clear and unambiguous.
2.  **Options:** Provide exactly four options.
3.  **Correctness:** Ensure only ONE option is verifiably correct.
4.  **Distractors:** The incorrect options (distractors) must be plausible but clearly wrong. They should ideally relate to common misconceptions or errors associated with the topic.
5.  **Labels:** Options MUST be labeled precisely `A:`, `B:`, `C:`, `D:`.

**Output Format (CRITICAL):**
*   You MUST provide the output *exactly* in the following format, using these precise keywords and structure:
Question: [The question text goes here]
A: [Option A text]
B: [Option B text]
C: [Option C text]
D: [Option D text]
Correct Answer: [Single uppercase letter: A, B, C, or D]
*   **Strictly adhere to this format.** Do NOT add *any* extra text, explanations, introductions, notes, or formatting (like bullet points) before "Question:" or after the "Correct Answer:" line.
"""

QUIZ_PROMPT_TEMPLATE = """**Role:** You are an AI instructional designer expert at creating short, effective quizzes for Learning Management Systems (LMS).

**Task:** Generate a complete quiz including a title and exactly 3 multiple-choice questions about the specified topic.

**Topic:** "{topic}"

**Context/Instructions:** "{context}"
*   Use this context to influence the overall difficulty or specific focus areas covered by the quiz questions. If 'None provided.', create a standard quiz testing basic understanding.

**Quiz Requirements:**
1.  **Title:** Include a short, relevant title for the quiz on the very first line, prefixed with `Quiz Title: `.
2.  **Number of Questions:** Generate **exactly 3** multiple-choice questions.
3.  **Question Variety:** Each question should ideally test a different key aspect or sub-topic related to the main Topic.
4.  **MCQ Format (CRITICAL):** Each of the 3 questions must individually and strictly follow the precise format below:
    ```
    Question: [The question text goes here]
    A: [Option A text]
    B: [Option B text]
    C: [Option C text]
    D: [Option D text]
    Correct Answer: [Single uppercase letter: A, B, C, or D]
    ```

**Output Structure (CRITICAL):**
*   The entire output MUST follow this structure precisely:
    1.  `Quiz Title: [Generated Title Here]` (on the first line)
    2.  An empty line.
    3.  `1.` (The number 1 followed by a period)
    4.  The first MCQ block, formatted exactly as specified above (starting with `Question:` and ending with `Correct Answer:`).
    5.  An empty line.
    6.  `2.` (The number 2 followed by a period)
    7.  The second MCQ block, formatted exactly as specified above.
    8.  An empty line.
    9.  `3.` (The number 3 followed by a period)
    10. The third MCQ block, formatted exactly as specified above.

*   **Strictly adhere to this structure.**
*   Do NOT include *any* extra text, introductions, explanations, summaries, or notes before the title, between the questions, or after the last question.
*   Ensure each numbered block (1, 2, 3) contains *only* the question text formatted according to the MCQ format rules.
"""



# --- FastAPI Application Code ---
app = FastAPI(title="AI Content Generation Service", version="0.1.0")

class ContentRequest(BaseModel):
    topic: str
    content_type: Literal["paragraph", "multiple_choice_question", "quiz"]
    context: Optional[str] = None

@app.get("/")
async def read_root():
     # Optionally log root access
     logger.info("Root endpoint '/' accessed.")
     return {"message": "Welcome to the AI Content Generation API!"}

@app.post("/generate")
async def generate_content_endpoint(request: ContentRequest):
    """Endpoint logic using logging."""
    # Log start of request processing
    logger.info(f"Received generation request - Topic: '{request.topic}', Type: '{request.content_type}', Context: '{request.context}'")

    prompt_template = None
    parsing_function = None # Store the correct parsing function

    # --- Select Prompt Template and Parser ---
    if request.content_type == "paragraph":
        logger.info("Routing to: Paragraph generation.") # logger.info
        prompt_template = PARAGRAPH_PROMPT_TEMPLATE
        # For paragraph, direct assignment is fine, but let's maintain pattern
        def parse_paragraph(raw_text): # Simple inline parser for paragraph
             logger.info("Parsing paragraph output.")
             content = raw_text.strip()
             if content:
                  logger.info("Successfully parsed paragraph.")
                  return {"type": "paragraph", "content": content}
             else:
                  logger.error("Paragraph Parsing Error: LLM returned empty text after stripping.")
                  return None
        parsing_function = parse_paragraph

    elif request.content_type == "multiple_choice_question":
        logger.info("Routing to: MCQ generation.") # logger.info
        prompt_template = MCQ_PROMPT_TEMPLATE
        parsing_function = parse_mcq_output # Use the dedicated function

    elif request.content_type == "quiz":
        logger.info("Routing to: Quiz generation.") # logger.info
        prompt_template = QUIZ_PROMPT_TEMPLATE
        parsing_function = parse_quiz_output # Use the dedicated function

    else:
        # Log invalid request info before raising exception
        logger.warning(f"Invalid content_type received: {request.content_type}")
        raise HTTPException(status_code=400, detail=f"Invalid content_type: '{request.content_type}'. Valid types are 'paragraph', 'multiple_choice_question', 'quiz'.")

    # --- Format the Final Prompt ---
    effective_context = request.context if request.context else "None provided."
    final_prompt = prompt_template.format(topic=request.topic, context=effective_context)
    # logger.debug(f"Formatted prompt:\n{final_prompt}") # DEBUG

    # --- Call the LLM ---
    raw_llm_output = await call_gemini_api(final_prompt)

    if raw_llm_output is None:
        # Error logged within call_gemini_api
        logger.error("LLM API call failed or returned no content.")
        raise HTTPException(status_code=503, detail="Failed to generate content using the LLM API. Check server logs.")

    # --- Parse and Format Output ---
    logger.info(f"Attempting to parse raw LLM output for type '{request.content_type}'...")
    parsed_data = parsing_function(raw_llm_output) # Call the selected parser

    if parsed_data:
        logger.info(f"Successfully processed request for '{request.content_type}'.")
        return parsed_data # Return the successfully parsed and structured data
    else:
        # Error logged within the specific parsing function
        logger.error(f"Parsing failed for content type '{request.content_type}'.")
        raise HTTPException(
            status_code=500,
            detail=f"Server failed to parse the LLM output for '{request.content_type}'. Check server logs."
        )