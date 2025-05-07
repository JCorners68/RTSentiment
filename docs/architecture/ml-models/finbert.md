here is sample code that works well for finbert

# src/sentiment_analyzer.py
import logging
from typing import Optional, Dict, Any
import torch
import httpx # Needed for calling HF endpoint async
# Ensure necessary components are imported from transformers
from transformers import (
    pipeline, # The easy-to-use pipeline abstraction
    AutoModelForSequenceClassification, # Generic model class for sequence classification
    AutoTokenizer, # Generic tokenizer class
    Pipeline, # The type hint for the pipeline object
    logging as transformers_logging # Control transformers' logging level
)

# Import Settings model for type hinting and accessing config
# NOTE: The example code in the Canvas used 'from .config import Settings'
# If config.py is in the root, this should be 'from config import settings' (importing the instance)
# Adjust the import below based on your final project structure and how config is imported elsewhere.
# Assuming config.py is in the root and defines an instance 'settings':
try:
    from config import settings as app_settings # Use alias to avoid potential name clash if needed
    # Define Settings type hint if needed for function signatures, requires importing the class
    # from config import Settings
    Settings = type(app_settings) # Dynamically get type from instance for hinting
except ImportError:
    logging.critical("Failed to import settings from root config.py")
    raise

# --- Setup ---
logger = logging.getLogger(__name__)
# Optional: Set transformers logging level (e.g., ERROR to reduce verbosity)
# Useful to hide download progress bars and routine messages in production logs
transformers_logging.set_verbosity_error()

# --- Model Configuration ---
# Define the model name as a constant for easy modification
MODEL_NAME = "ProsusAI/finbert"

# --- Global Pipeline Variable ---
# Use type hint for clarity. Initialize lazily (on first use or startup).
sentiment_pipeline: Optional[Pipeline] = None

# --- Model Loading ---
def load_sentiment_model():
    """
    Loads the sentiment analysis model and tokenizer locally, then creates the pipeline.
    Handles device selection (GPU/CPU). Should ideally be called at application startup.
    Sets the global `sentiment_pipeline` variable.
    """
    global sentiment_pipeline
    # Only load if it hasn't been loaded already
    if sentiment_pipeline is not None:
        logger.info("Local sentiment model already loaded.")
        return

    try:
        logger.info(f"Attempting to load local sentiment analysis model: {MODEL_NAME}...")
        # Determine device: Use CUDA (GPU) if available, otherwise CPU
        if torch.cuda.is_available():
            # Use the first available GPU (device 0)
            # For multi-GPU setups, device selection might need adjustment
            device_id = 0
            device_name = torch.cuda.get_device_name(device_id)
            logger.info(f"CUDA is available. Using GPU: {device_name} (ID: {device_id})")
        else:
            device_id = -1 # Special value for CPU in transformers pipeline
            logger.info("CUDA not available. Using CPU.")

        # Load the tokenizer and model from Hugging Face Hub (or cache)
        # These will be downloaded on first run if not cached
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)

        # Create the sentiment analysis pipeline from transformers library
        # Explicitly pass model, tokenizer, and device for clarity and control
        sentiment_pipeline = pipeline(
            "sentiment-analysis", # Task identifier
            model=model,
            tokenizer=tokenizer,
            device=device_id, # Pass device index (-1 for CPU, >=0 for GPU)
            # Truncate input text if it exceeds the model's maximum sequence length (e.g., 512 for BERT)
            truncation=True,
            # max_length=512 # Can be specified if needed, otherwise defaults to model config
            # return_all_scores=False # Default: Only return the score for the predicted label
        )
        logger.info(f"Local sentiment analysis model '{MODEL_NAME}' loaded successfully.")

    except Exception as e:
        # Log critical error if model loading fails
        logger.exception(f"CRITICAL: Failed to load local sentiment model '{MODEL_NAME}'. Local sentiment analysis will not be available.", exc_info=True)
        # Keep sentiment_pipeline as None. The get_sentiment function needs to handle this.
        # Depending on requirements, could raise error to stop app startup:
        # raise RuntimeError(f"Failed to load local sentiment model: {e}") from e

# --- Helper: Call HF Inference Endpoint ---
async def get_sentiment_from_endpoint(text: str, settings: Settings) -> float:
    """Gets sentiment by asynchronously calling the configured Hugging Face Inference Endpoint."""
    # Ensure necessary configuration is present
    # Assuming settings object has these attributes based on Canvas doc
    if not settings.huggingface_endpoint_url or not settings.huggingface_api_key:
        logger.error("Attempted to call HF Inference Endpoint, but URL or API Key is missing in settings.")
        # Raise specific error to be handled by the caller
        raise ValueError("Missing Hugging Face endpoint configuration for API call.")

    # Prepare headers and payload for the HF Inference API
    headers = {"Authorization": f"Bearer {settings.huggingface_api_key}"}
    # Standard payload format for text classification endpoints
    payload = {"inputs": text}

    # Reuse the initialized httpx client from the finnhub_client module
    # This avoids creating new clients repeatedly
    # Using absolute import assuming finnhub_client is also in src and root is in path
    try:
        from src import finnhub_client
    except ImportError:
         logger.critical("Failed to import src.finnhub_client for HTTP client.")
         raise # Re-raise import error

    http_client = await finnhub_client.get_client() # Assumes get_client is defined in finnhub_client

    try:
        logger.debug(f"Calling HF Inference Endpoint: {settings.huggingface_endpoint_url}")
        response = await http_client.post(
            settings.huggingface_endpoint_url,
            headers=headers,
            json=payload,
            # Increase timeout if needed for potentially slow model inference
            # timeout=httpx.Timeout(30.0, connect=5.0) # Use timeout from settings?
            )
        response.raise_for_status() # Raise HTTPStatusError for 4xx/5xx responses
        results = response.json()
        logger.debug(f"HF Endpoint response: {results}")

        # --- Parse the HF Endpoint Response ---
        # Adjusted based on example in Canvas doc (list of list of dict)
        if isinstance(results, list) and results and isinstance(results[0], list) and results[0] and isinstance(results[0][0], dict):
            result_dict = results[0][0]
            label = result_dict.get('label', '').lower() # Normalize label
            score = result_dict.get('score', 0.0)

            # Map label/score to the -1 to 1 range
            if label == 'positive': return float(score)
            if label == 'negative': return -float(score)
            if label == 'neutral': return 0.0
            # Handle unexpected labels
            logger.warning(f"Received unknown sentiment label '{label}' from HF Endpoint.")
            return 0.0 # Default to neutral
        else:
            # Log error if the response format is not as expected
            logger.error(f"Unexpected response format received from HF Inference Endpoint: {results}")
            return 0.0 # Default to neutral on unexpected format

    except httpx.HTTPStatusError as exc:
        # Log HTTP errors specifically
        status_code = exc.response.status_code
        logger.error(f"HF Endpoint request failed [{status_code}]: {exc.request.url} - Response: {exc.response.text[:200]}") # Log snippet
        # Return default score or re-raise specific exception
        return 0.0 # Default to neutral on HTTP error for now
    except httpx.RequestError as exc:
        # Log network errors
        logger.error(f"Network error calling HF Inference Endpoint: {exc.request.url} - {exc}")
        return 0.0 # Default to neutral on network error
    except Exception as e:
        # Log any other unexpected errors during the endpoint call
        logger.exception(f"An unexpected error occurred calling HF Inference Endpoint: {e}", exc_info=True)
        return 0.0 # Default to neutral on other errors

# --- Helper: Use Local Pipeline ---
def get_sentiment_from_local_pipeline(text: str) -> float:
    """Gets sentiment using the locally loaded Hugging Face pipeline."""
    global sentiment_pipeline
    # Check if the pipeline was successfully loaded
    if sentiment_pipeline is None:
        logger.error("Attempted to use local sentiment pipeline, but it's not loaded (check startup logs).")
        # Cannot proceed without the pipeline
        raise RuntimeError("Local sentiment analysis model is not available.")

    try:
        # Perform inference using the pipeline
        # Use torch.no_grad() for efficiency during inference (disables gradient calculation)
        with torch.no_grad():
             # Ensure text is passed correctly, pipeline expects str or list[str]
             results = sentiment_pipeline(text)

        # Process the result (pipeline typically returns a list with one dictionary)
        if not results or not isinstance(results, list) or not isinstance(results[0], dict):
             logger.error(f"Unexpected result format from local pipeline for text: '{text[:50]}...'. Result: {results}")
             return 0.0 # Default neutral on unexpected format

        result = results[0]
        label = result.get('label', '').lower() # Normalize label
        score = result.get('score', 0.0)

        # Map the label and score to the desired -1 to 1 range
        sentiment_score: float
        if label == 'positive': sentiment_score = float(score)
        elif label == 'negative': sentiment_score = -float(score)
        elif label == 'neutral': sentiment_score = 0.0
        else:
            # Handle unexpected labels defensively
            logger.warning(f"Received unknown sentiment label '{label}' from local model.")
            sentiment_score = 0.0

        # Ensure the final score is strictly within the [-1.0, 1.0] bounds
        final_score = max(-1.0, min(1.0, sentiment_score))
        logger.debug(f"Analyzed text: '{text[:50]}...' -> Label: {label}, Raw Score: {score:.4f}, Mapped Score: {final_score:.4f}")
        return final_score

    except Exception as e:
        # Log any exceptions during the local analysis process
        logger.exception(f"Error during local sentiment analysis for text '{text[:50]}...': {e}", exc_info=True)
        # Return a default neutral score in case of errors
        return 0.0

# --- Main Sentiment Function ---
# Note: Changed settings type hint to use the dynamically obtained type
async def get_sentiment(news_item: Dict[str, Any], settings: Settings) -> float:
    """
    Analyzes the sentiment of a given news item (provided as a dictionary).
    Chooses the analysis method (local vs. endpoint) based on application settings.

    Args:
        news_item: Dictionary representing the news item JSON (e.g., from Finnhub).
        settings: The application settings object containing configuration.

    Returns:
        A sentiment score between -1.0 (negative) and 1.0 (positive).
    """
    # --- Extract Text to Analyze ---
    # Prioritize using the 'headline'. Fallback to 'summary' if headline is missing/empty.
    text_to_analyze = news_item.get('headline')
    # Check if headline is valid text
    if not text_to_analyze or not isinstance(text_to_analyze, str) or not text_to_analyze.strip():
        logger.debug(f"Headline missing or invalid for item ID {news_item.get('id', 'N/A')}. Trying summary.")
        text_to_analyze = news_item.get('summary')
        # Check if summary is valid text
        if not text_to_analyze or not isinstance(text_to_analyze, str) or not text_to_analyze.strip():
            logger.warning(f"No valid headline or summary found for sentiment analysis in item ID {news_item.get('id', 'N/A')}. Returning neutral score.")
            return 0.0 # Return neutral if no suitable text found

    # Optional: Add basic text cleaning here if needed before analysis
    # text_to_analyze = clean_text(text_to_analyze)

    # --- Choose Analysis Method ---
    # Access settings attributes directly (assuming they exist based on config.py)
    hf_endpoint_url = getattr(settings, 'huggingface_endpoint_url', None)

    if hf_endpoint_url:
        # Use the configured Hugging Face Inference Endpoint (asynchronous call)
        logger.debug(f"Using configured HF Inference Endpoint for item ID {news_item.get('id', 'N/A')}")
        # Pass the settings object itself
        return await get_sentiment_from_endpoint(text_to_analyze, settings)
    else:
        # Use the locally loaded pipeline (synchronous call within this async function)
        logger.debug(f"Using local sentiment pipeline for item ID {news_item.get('id', 'N/A')}")
        # Ensure model is loaded before calling; load_sentiment_model should be called at startup
        if sentiment_pipeline is None:
             logger.error("Local sentiment model called but not loaded. Check application startup sequence.")
             # Attempt lazy loading (use with caution, might impact request time)
             # load_sentiment_model()
             # if sentiment_pipeline is None: # Check again after attempting load
             #      return 0.0 # Return neutral if still not loaded
             return 0.0 # Return neutral if model isn't ready

        # The local function will raise RuntimeError if the model isn't loaded and lazy load fails/isn't used
        try:
            # Pass only the text needed
            return get_sentiment_from_local_pipeline(text_to_analyze)
        except RuntimeError as e:
            logger.error(f"Local sentiment analysis failed for item ID {news_item.get('id', 'N/A')}: {e}")
            return 0.0 # Return neutral if local model fails at runtime

# Example of calling load_sentiment_model at module level (alternative to calling at app startup)
# load_sentiment_model()
# This ensures the model attempts to load when this module is imported.
# However, calling explicitly at FastAPI startup is generally preferred for control.

