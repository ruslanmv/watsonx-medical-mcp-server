# server.py

import os
import logging
from typing import Dict, List, Optional
from dotenv import load_dotenv

# MCP imports
from mcp.server.fastmcp import FastMCP

# IBM Watsonx.ai SDK
from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("WATSONX_APIKEY")
URL = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
PROJECT_ID = os.getenv("PROJECT_ID")
MODEL_ID = os.getenv("MODEL_ID", "meta-llama/llama-3-2-90b-vision-instruct")
SERVER_NAME = os.getenv("MCP_SERVER_NAME", "Watsonx Medical Assistant")
SERVER_VERSION = os.getenv("MCP_SERVER_VERSION", "1.0.0")

# Validate required environment variables
required_vars = {
    "WATSONX_APIKEY": API_KEY,
    "PROJECT_ID": PROJECT_ID
}

for var_name, var_value in required_vars.items():
    if not var_value:
        raise RuntimeError(
            f"{var_name} is not set. Please add it to your .env file."
        )

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize IBM watsonx.ai client
try:
    credentials = Credentials(url=URL, api_key=API_KEY)
    client = APIClient(credentials=credentials, project_id=PROJECT_ID)

    # Initialize the inference model
    model = ModelInference(
        model_id=MODEL_ID,
        credentials=credentials,
        project_id=PROJECT_ID
    )

    logger.info(
        f"Initialized watsonx.ai model '{MODEL_ID}' for project '{PROJECT_ID}'"
    )

except Exception as e:
    logger.error(f"Failed to initialize watsonx.ai client: {e}")
    raise

# Create MCP server instance
mcp = FastMCP(SERVER_NAME)

# Global conversation history for context
conversation_history: List[Dict[str, str]] = []


@mcp.tool()
def chat_with_watsonx(
    query: str, max_tokens: int = 200, temperature: float = 0.7
) -> str:
    """
    Generate a conversational response using IBM watsonx.ai

    Args:
        query: The user's input message or question
        max_tokens: Maximum number of tokens to generate (default: 200)
        temperature: Controls randomness in generation (0.0-1.0, default: 0.7)

    Returns:
        Generated response from watsonx.ai model
    """
    logger.info(f"Received chat query: {query[:100]}...")

    try:
        # Add user message to conversation history
        conversation_history.append({"role": "user", "content": query})

        # Build context from conversation history
        context = "\n".join([
            f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
            for msg in conversation_history[-10:]  # Keep last 10 messages
        ])

        # Define generation parameters
        params = {
            GenParams.DECODING_METHOD: "greedy" if temperature == 0.0 else "sample",
            GenParams.MAX_NEW_TOKENS: max_tokens,
            GenParams.TEMPERATURE: temperature,
            GenParams.TOP_P: 0.9,
            GenParams.TOP_K: 50,
        }

        # Generate response
        response = model.generate_text(
            prompt=f"Context:\n{context}\n\nPlease provide a helpful and accurate response:",
            params=params,
            raw_response=True
        )

        # Extract generated text
        generated_text = response["results"][0]["generated_text"].strip()

        # Add assistant response to conversation history
        conversation_history.append({"role": "assistant", "content": generated_text})

        logger.info(f"Generated response: {generated_text[:100]}...")
        return generated_text

    except Exception as e:
        error_msg = f"Error generating response: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


@mcp.tool()
def analyze_medical_symptoms(
    symptoms: str,
    patient_age: Optional[int] = None,
    patient_gender: Optional[str] = None
) -> str:
    """
    Analyze medical symptoms and provide preliminary assessment

    Args:
        symptoms: Description of patient symptoms
        patient_age: Patient's age (optional)
        patient_gender: Patient's gender (optional)

    Returns:
        Medical analysis and recommendations
    """
    logger.info(f"Analyzing symptoms: {symptoms[:50]}...")

    try:
        # Build patient context
        patient_context = ""
        if patient_age:
            patient_context += f"Patient age: {patient_age} years old. "
        if patient_gender:
            patient_context += f"Patient gender: {patient_gender}. "

        # Create medical analysis prompt
        medical_prompt = f"""
        {patient_context}

        Patient reports the following symptoms: {symptoms}

        As a medical assistant, please provide:
        1. Possible causes for these symptoms
        2. Recommended next steps
        3. When to seek immediate medical care
        4. General health advice

        Important: This is for informational purposes only and should not replace professional medical advice.
        """

        # Generate medical analysis
        params = {
            GenParams.DECODING_METHOD: "greedy",
            GenParams.MAX_NEW_TOKENS: 300,
            GenParams.TEMPERATURE: 0.3,  # Lower temperature for consistent advice
        }

        response = model.generate_text(
            prompt=medical_prompt,
            params=params,
            raw_response=True
        )

        analysis = response["results"][0]["generated_text"].strip()
        logger.info("Medical analysis completed successfully")
        return analysis

    except Exception as e:
        error_msg = f"Error analyzing symptoms: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


@mcp.tool()
def clear_conversation_history() -> str:
    """
    Clear the conversation history to start fresh

    Returns:
        Confirmation message
    """
    conversation_history.clear()
    logger.info("Conversation history cleared")
    return "Conversation history has been cleared. Starting fresh!"


@mcp.tool()
def get_conversation_summary() -> str:
    """
    Get a summary of the current conversation

    Returns:
        Summary of conversation history
    """
    if not conversation_history:
        return "No conversation history available."

    try:
        # Create summary prompt
        history_text = "\n".join([
            f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
            for msg in conversation_history
        ])

        summary_prompt = f"""
        Please provide a concise summary of the following conversation:

        {history_text}

        Summary should include:
        - Main topics discussed
        - Key questions asked
        - Important information shared
        """

        params = {
            GenParams.DECODING_METHOD: "greedy",
            GenParams.MAX_NEW_TOKENS: 150,
            GenParams.TEMPERATURE: 0.5,
        }

        response = model.generate_text(
            prompt=summary_prompt,
            params=params,
            raw_response=True
        )

        summary = response["results"][0]["generated_text"].strip()
        logger.info("Conversation summary generated")
        return summary

    except Exception as e:
        error_msg = f"Error generating summary: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


# Resources
@mcp.resource("greeting://patient/{name}")
def get_patient_greeting(name: str) -> str:
    """
    Generate a personalized greeting for a patient

    Args:
        name: Patient's name

    Returns:
        Personalized medical assistant greeting
    """
    return (
        f"Hello {name}, I'm your AI medical assistant powered by IBM watsonx. "
        f"How can I help you today? Please remember that I provide general "
        f"information and cannot replace professional medical advice."
    )


@mcp.resource("info://server")
def get_server_info() -> str:
    """
    Get information about the MCP server

    Returns:
        Server information and capabilities
    """
    return f"""
    {SERVER_NAME} v{SERVER_VERSION}

    Capabilities:
    - Conversational AI powered by IBM watsonx.ai
    - Medical symptom analysis
    - Conversation management
    - Patient greeting generation

    Model: {MODEL_ID}
    Project: {PROJECT_ID}

    Available Tools:
    - chat_with_watsonx: General conversation
    - analyze_medical_symptoms: Medical symptom analysis
    - clear_conversation_history: Reset conversation
    - get_conversation_summary: Summarize conversation

    Available Resources:
    - greeting://patient/{{name}}: Personalized patient greetings
    - info://server: Server information
    """


# Prompts
@mcp.prompt()
def medical_consultation_prompt(
    symptoms: str, duration: str = "", severity: str = ""
) -> str:
    """
    Generate a structured medical consultation prompt

    Args:
        symptoms: Patient's reported symptoms
        duration: How long symptoms have been present
        severity: Severity level of symptoms

    Returns:
        Structured prompt for medical consultation
    """
    base_prompt = f"""
    You are a qualified medical assistant AI. Please conduct a preliminary assessment based on the following information:

    Patient Symptoms: {symptoms}
    """

    if duration:
        base_prompt += f"\nDuration: {duration}"

    if severity:
        base_prompt += f"\nSeverity: {severity}"

    base_prompt += """

    Please provide:
    1. Possible differential diagnoses
    2. Recommended diagnostic tests or examinations
    3. Immediate care recommendations
    4. Red flag symptoms that require immediate medical attention
    5. Follow-up recommendations

    Important disclaimers:
    - This assessment is for informational purposes only
    - Always consult with a qualified healthcare provider
    - Seek immediate medical attention for emergency symptoms
    """

    return base_prompt


@mcp.prompt()
def health_education_prompt(topic: str) -> str:
    """
    Generate a health education prompt for a specific topic

    Args:
        topic: Health topic to educate about

    Returns:
        Educational prompt about the health topic
    """
    return f"""
    You are a health educator. Please provide comprehensive, accurate, and easy-to-understand information about: {topic}

    Please include:
    1. What is {topic}?
    2. Common causes and risk factors
    3. Signs and symptoms to watch for
    4. Prevention strategies
    5. Treatment options (general overview)
    6. When to seek medical care
    7. Lifestyle recommendations

    Ensure the information is:
    - Medically accurate
    - Easy to understand for general audiences
    - Includes appropriate medical disclaimers
    - Encourages professional medical consultation when appropriate
    """


# Server startup and main execution
if __name__ == "__main__":
    logger.info(f"Starting {SERVER_NAME} v{SERVER_VERSION}")
    logger.info(f"Using model: {MODEL_ID}")
    logger.info("MCP server ready for STDIO transport...")

    # Run the MCP server
    mcp.run()

# (blank line added above to satisfy W292)
