import logging
import os
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel
import numpy as np

logger = logging.getLogger(__name__)

class FinGPTModel:
    """
    FinGPT model for financial sentiment analysis.
    Leverages Llama 2 with LoRA fine-tuning for financial text.
    """
    
    def __init__(
        self, 
        use_gpu=True, 
        quantize=True, 
        model_dir="./models/weights/fingpt",
        model_variant="FinGPT/fingpt-sentiment_llama2-7b_lora"
    ):
        """
        Initialize the FinGPT model.
        
        Args:
            use_gpu (bool): Whether to use GPU for inference
            quantize (bool): Whether to use quantization
            model_dir (str): Directory for model weights
            model_variant (str): Model variant/name
        """
        self.use_gpu = use_gpu and torch.cuda.is_available()
        self.quantize = quantize
        self.device = torch.device("cuda" if self.use_gpu else "cpu")
        self.model = None
        self.tokenizer = None
        self.is_loaded = False
        self.labels = ["negative", "neutral", "positive"]
        
        # Model paths
        self.model_dir = Path(model_dir)
        self.model_variant = model_variant
        self.base_model_name = "meta-llama/Llama-2-7b-hf"  # Default base model
        
        if "13b" in model_variant:
            self.base_model_name = "meta-llama/Llama-2-13b-hf"
        
        logger.info(f"Initializing FinGPT model (Variant: {model_variant}, GPU: {self.use_gpu}, Quantize: {self.quantize})")
    
    async def load(self):
        """Load the model and tokenizer."""
        try:
            # Check if already loaded
            if self.is_loaded:
                logger.info("FinGPT model already loaded")
                return
                
            # Set up quantization configuration if enabled
            if self.quantize:
                logger.info("Using 4-bit quantization for FinGPT")
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True
                )
            else:
                quantization_config = None
            
            # Load tokenizer
            logger.info(f"Loading FinGPT tokenizer from {self.model_variant}")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_variant,
                use_fast=True
            )
            
            # Load the base model with quantization
            logger.info(f"Loading FinGPT base model")
            
            # First check if we have a local copy
            local_base_path = self.model_dir / "base"
            if local_base_path.exists():
                logger.info(f"Loading base model from local path: {local_base_path}")
                base_model_path = str(local_base_path)
            else:
                logger.info(f"Loading base model from HuggingFace: {self.base_model_name}")
                base_model_path = self.base_model_name
            
            # Load the base model
            self.model = AutoModelForCausalLM.from_pretrained(
                base_model_path,
                quantization_config=quantization_config,
                device_map="auto" if self.use_gpu else None,
                torch_dtype=torch.float16 if self.use_gpu else torch.float32,
                trust_remote_code=True
            )
            
            # Now load the LoRA adapter
            logger.info(f"Loading FinGPT LoRA adapter from {self.model_variant}")
            
            # Check if we have a local copy of the adapter
            local_adapter_path = self.model_dir / "lora_adapter"
            if local_adapter_path.exists():
                logger.info(f"Loading LoRA adapter from local path: {local_adapter_path}")
                adapter_path = str(local_adapter_path)
            else:
                logger.info(f"Loading LoRA adapter from HuggingFace: {self.model_variant}")
                adapter_path = self.model_variant
            
            # Load the adapter
            self.model = PeftModel.from_pretrained(
                self.model,
                adapter_path,
                torch_dtype=torch.float16 if self.use_gpu else torch.float32
            )
            
            # Set to evaluation mode
            self.model.eval()
            
            # Set special tokens if not already set
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                
            self.is_loaded = True
            logger.info("FinGPT model loaded successfully")
        
        except Exception as e:
            logger.error(f"Failed to load FinGPT model: {str(e)}")
            raise
    
    async def predict(self, texts):
        """
        Predict sentiment for a list of texts.
        
        Args:
            texts (list): List of texts to analyze
            
        Returns:
            list: List of dictionaries with sentiment predictions
        """
        if not self.is_loaded:
            raise RuntimeError("Model is not loaded. Call load() first.")
        
        results = []
        
        # Process each text individually for sentiment analysis
        for text in texts:
            # Prepare the prompt for sentiment analysis
            prompt = f"""Analyze the sentiment of the following financial text and classify it as positive, neutral, or negative. After the classification, provide a sentiment score between -1 (most negative) and 1 (most positive).

Text: {text}

Sentiment:"""
            
            # Tokenize the prompt
            inputs = self.tokenizer(
                prompt, 
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            )
            
            # Move inputs to the correct device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate output
            with torch.no_grad():
                generation_output = self.model.generate(
                    **inputs,
                    max_new_tokens=50,
                    num_return_sequences=1,
                    temperature=0.1,
                    do_sample=False
                )
            
            # Decode the output
            output_text = self.tokenizer.decode(generation_output[0], skip_special_tokens=True)
            
            # Extract sentiment from output
            sentiment, score = self._extract_sentiment_from_output(output_text)
            
            # Store results
            results.append({
                "text": text,
                "sentiment_score": score,
                "sentiment_label": sentiment,
                "raw_output": output_text.replace(prompt, "").strip()
            })
        
        return results
    
    def _extract_sentiment_from_output(self, output_text):
        """
        Extract sentiment and score from model output.
        
        Args:
            output_text (str): Raw model output
            
        Returns:
            tuple: (sentiment_label, sentiment_score)
        """
        # Default values
        sentiment = "neutral"
        score = 0.0
        
        # Remove the prompt part
        response = output_text.lower()
        
        # Check for sentiment labels
        if "positive" in response:
            sentiment = "positive"
        elif "negative" in response:
            sentiment = "negative"
        elif "neutral" in response:
            sentiment = "neutral"
        
        # Try to extract score using various patterns
        try:
            # Look for the score in the format "score: X.XX" or "score of X.XX"
            score_patterns = [
                r"score:\s*([-+]?\d*\.\d+|\d+)",
                r"score of\s*([-+]?\d*\.\d+|\d+)",
                r"score is\s*([-+]?\d*\.\d+|\d+)",
                r"score\s*([-+]?\d*\.\d+|\d+)"
            ]
            
            import re
            for pattern in score_patterns:
                score_match = re.search(pattern, response)
                if score_match:
                    found_score = float(score_match.group(1))
                    # Ensure the score is between -1 and 1
                    if -1 <= found_score <= 1:
                        score = found_score
                        break
            
            # If score is still 0, but we have a sentiment, assign a default score
            if score == 0.0 and sentiment != "neutral":
                score = 0.7 if sentiment == "positive" else -0.7
        except Exception as e:
            logger.warning(f"Failed to extract score from output: {e}")
            
            # Use default scores based on sentiment
            if sentiment == "positive":
                score = 0.7
            elif sentiment == "negative":
                score = -0.7
        
        return sentiment, score

async def download_fingpt_model():
    """
    Download and prepare the FinGPT model for local use.
    This function can be called independently to set up the model.
    """
    import os
    from pathlib import Path
    from huggingface_hub import snapshot_download
    
    logger.info("Setting up FinGPT model...")
    
    # Set up paths
    model_dir = Path("./models/weights/fingpt")
    model_variant = os.getenv("FINGPT_MODEL_VARIANT", "FinGPT/fingpt-sentiment_llama2-7b_lora")
    
    # Check which base model to use
    base_model_name = "meta-llama/Llama-2-7b-hf"  # Default
    if "13b" in model_variant:
        base_model_name = "meta-llama/Llama-2-13b-hf"
    
    # Create directories
    os.makedirs(model_dir / "base", exist_ok=True)
    os.makedirs(model_dir / "lora_adapter", exist_ok=True)
    
    logger.info(f"Downloading FinGPT adapter from {model_variant}...")
    # Download the LoRA adapter
    adapter_path = snapshot_download(
        repo_id=model_variant,
        local_dir=str(model_dir / "lora_adapter"),
        ignore_patterns=["*.safetensors", "optimizer.pt"]
    )
    logger.info(f"FinGPT adapter downloaded to {adapter_path}")
    
    # Check if we need the base model locally
    # For production, you would also download the base model
    # but it's quite large so we use it from HF directly in this example
    
    logger.info("FinGPT model setup complete")

if __name__ == "__main__":
    # For testing and model download
    import asyncio
    
    async def test_model():
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        
        # Download model if needed
        await download_fingpt_model()
        
        # Initialize and load model
        model = FinGPTModel(use_gpu=True, quantize=True)
        await model.load()
        
        # Test a few examples
        test_texts = [
            "The company reported strong earnings, exceeding analyst expectations.",
            "The stock plummeted after the CEO announced their resignation.",
            "Quarterly results were in line with market consensus.",
        ]
        
        results = await model.predict(test_texts)
        for text, result in zip(test_texts, results):
            print(f"Text: {text}")
            print(f"Sentiment: {result['sentiment_label']} ({result['sentiment_score']:.2f})")
            print(f"Raw output: {result['raw_output']}")
            print("---")
    
    # Run the test
    asyncio.run(test_model())