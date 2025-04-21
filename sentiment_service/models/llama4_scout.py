import logging
import os
from pathlib import Path
import torch
from transformers import AutoProcessor, Llama4ForConditionalGeneration, AutoTokenizer, BitsAndBytesConfig
import numpy as np

logger = logging.getLogger(__name__)

class Llama4ScoutModel:
    """
    Llama 4 Scout model for advanced financial sentiment analysis.
    Leverages mixture of experts (MoE) architecture for high-quality analysis.
    """
    
    def __init__(
        self, 
        use_gpu=True, 
        quantize=True, 
        model_dir="./models/weights/llama4",
        model_variant="meta-llama/Llama-4-Scout-17B-16E-Instruct"
    ):
        """
        Initialize the Llama 4 Scout model.
        
        Args:
            use_gpu (bool): Whether to use GPU for inference
            quantize (bool): Whether to use quantization
            model_dir (str): Directory for model weights
            model_variant (str): Model variant/name
        """
        self.use_gpu = use_gpu and torch.cuda.is_available()
        self.model = None
        self.processor = None
        self.tokenizer = None
        self.is_loaded = False
        self.multimodal = True  # Llama 4 Scout is multimodal
        
        # Model paths
        self.model_dir = Path(model_dir)
        self.model_variant = model_variant
        self.quantize = quantize
        
        logger.info(f"Initializing Llama 4 Scout (GPU: {self.use_gpu}, Quantize: {quantize})")
    
    async def load(self):
        """Load the model and tokenizer."""
        try:
            # Set up quantization configuration
            if self.quantize:
                logger.info("Using 4-bit quantization for Llama 4 Scout")
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True
                )
            else:
                quantization_config = None
            
            # Load processor and model
            logger.info(f"Loading Llama 4 Scout processor from {self.model_variant}")
            self.processor = AutoProcessor.from_pretrained(
                self.model_variant,
                use_auth_token=os.getenv("HF_TOKEN", None),
                trust_remote_code=True
            )
            
            # Load the tokenizer as well for text-only inputs
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_variant,
                use_auth_token=os.getenv("HF_TOKEN", None),
                trust_remote_code=True
            )
            
            logger.info(f"Loading Llama 4 Scout model from {self.model_variant}")
            self.model = Llama4ForConditionalGeneration.from_pretrained(
                self.model_variant,
                quantization_config=quantization_config,
                device_map="auto" if self.use_gpu else None,
                torch_dtype=torch.bfloat16 if self.use_gpu else torch.float32,
                low_cpu_mem_usage=True,
                use_auth_token=os.getenv("HF_TOKEN", None),
                trust_remote_code=True
            )
            
            self.is_loaded = True
            logger.info("Llama 4 Scout model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Llama 4 Scout model: {str(e)}")
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
        
        # Process each text separately for detailed analysis
        for text in texts:
            # Prepare the prompt for sentiment analysis
            prompt = f"""<|begin_of_text|><|user|>
You are a financial sentiment analysis expert. Please analyze the following financial text and determine whether the sentiment is positive, negative, or neutral. After your analysis, assign a sentiment score between -1 (most negative) and 1 (most positive). Give a detailed explanation of your reasoning.

Text to analyze: {text}<|end_of_turn|>
<|assistant|>"""
            
            # Encode the prompt
            inputs = self.tokenizer(
                prompt, 
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=4096  # Llama 4 can handle much longer, but we limit for efficiency
            )
            
            # Move inputs to device
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
            
            # Generate response
            with torch.no_grad():
                generation_output = self.model.generate(
                    **inputs,
                    max_new_tokens=512,
                    temperature=0.1,
                    do_sample=False
                )
            
            # Decode the response
            generated_text = self.tokenizer.decode(generation_output[0], skip_special_tokens=True)
            
            # Extract sentiment and score from the response
            sentiment, score, explanation = self._extract_sentiment_from_output(generated_text)
            
            # Store results
            results.append({
                "text": text,
                "sentiment_score": score,
                "sentiment_label": sentiment,
                "explanation": explanation,
                "model": "Llama 4 Scout"
            })
        
        return results
    
    def _extract_sentiment_from_output(self, output_text):
        """
        Extract sentiment and score from model output.
        
        Args:
            output_text (str): Raw model output
            
        Returns:
            tuple: (sentiment_label, sentiment_score, explanation)
        """
        # Strip any prefixes and get just the assistant's response
        response = output_text.strip()
        
        try:
            # Try to find response after the prompt
            if "<|assistant|>" in response:
                response = response.split("<|assistant|>", 1)[1].strip()
        except:
            pass
        
        # Default values
        sentiment = "neutral"
        score = 0.0
        explanation = response  # Keep original explanation
        
        # Identify sentiment label
        response_lower = response.lower()
        if "positive" in response_lower:
            sentiment = "positive"
        elif "negative" in response_lower:
            sentiment = "negative"
        elif "neutral" in response_lower:
            sentiment = "neutral"
        
        # Try to extract score
        import re
        
        # Look for the score in various formats
        score_patterns = [
            r"sentiment score:?\s*([-+]?\d+(\.\d+)?)",
            r"score:?\s*([-+]?\d+(\.\d+)?)",
            r"score of\s*([-+]?\d+(\.\d+)?)",
            r"score is\s*([-+]?\d+(\.\d+)?)",
            r"rating of\s*([-+]?\d+(\.\d+)?)",
            r"[-+]?\d+(\.\d+)?\s*out of\s*1",
            r"[-+]?\d+(\.\d+)?"  # Try to find any number as last resort
        ]
        
        for pattern in score_patterns:
            matches = re.findall(pattern, response_lower)
            if matches:
                # Extract the first group from the first match
                try:
                    score_str = matches[0]
                    if isinstance(score_str, tuple):
                        score_str = score_str[0]
                    score_val = float(score_str)
                    
                    # Ensure score is within -1 to 1 range
                    if -1 <= score_val <= 1:
                        score = score_val
                        break
                except:
                    continue
        
        # If we still couldn't find a valid score, assign based on sentiment
        if sentiment == "positive" and score == 0:
            score = 0.7
        elif sentiment == "negative" and score == 0:
            score = -0.7
        
        # Try to extract a concise explanation
        explanation_patterns = [
            r"explanation:(.*?)(?=sentiment score:|score:|$)",
            r"reasoning:(.*?)(?=sentiment score:|score:|$)",
            r"analysis:(.*?)(?=sentiment score:|score:|$)"
        ]
        
        for pattern in explanation_patterns:
            matches = re.search(pattern, response_lower, re.DOTALL)
            if matches:
                explanation = matches.group(1).strip()
                break
        
        # If explanation is too long, trim it
        if len(explanation) > 500:
            explanation = explanation[:497] + "..."
            
        return sentiment, score, explanation
    
    async def analyze_document(self, document):
        """
        Analyze a financial document for sentiment.
        Leverages the large context window of Llama 4 Scout.
        
        Args:
            document (str): Full document text
            
        Returns:
            dict: Analysis results
        """
        if not self.is_loaded:
            raise RuntimeError("Model is not loaded. Call load() first.")
        
        # Prepare the prompt for document analysis
        prompt = f"""<|begin_of_text|><|user|>
You are a financial expert. Analyze this financial document and extract the key information:
1. Overall sentiment (positive, negative, or neutral)
2. Key financial metrics mentioned
3. Important highlights or changes
4. Any potential risks or concerns
5. Future outlook or guidance

Document:
{document}<|end_of_turn|>
<|assistant|>"""
        
        # For very long documents, we might need to chunk
        max_tokens = 128000  # Llama 4 Scout can handle up to 10M tokens, but we use a smaller value for efficiency
        
        # Tokenize the prompt
        tokens = self.tokenizer.encode(prompt)
        if len(tokens) > max_tokens:
            logger.warning(f"Document too long ({len(tokens)} tokens). Truncating to {max_tokens} tokens.")
            tokens = tokens[:max_tokens]
            prompt = self.tokenizer.decode(tokens)
        
        # Encode the prompt
        inputs = self.tokenizer(
            prompt, 
            return_tensors="pt",
            truncation=True,
            max_length=max_tokens
        )
        
        # Move inputs to device
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        
        # Generate response
        with torch.no_grad():
            generation_output = self.model.generate(
                **inputs,
                max_new_tokens=1024,
                temperature=0.2,
                do_sample=True
            )
        
        # Decode the response
        generated_text = self.tokenizer.decode(generation_output[0], skip_special_tokens=True)
        
        # Extract the assistant's response
        response = generated_text
        try:
            if "<|assistant|>" in response:
                response = response.split("<|assistant|>", 1)[1].strip()
        except:
            pass
        
        # Extract sentiment
        sentiment = "neutral"
        sentiment_score = 0.0
        
        response_lower = response.lower()
        if "positive" in response_lower:
            sentiment = "positive"
            sentiment_score = 0.7
        elif "negative" in response_lower:
            sentiment = "negative"
            sentiment_score = -0.7
        
        # Try to extract a more precise sentiment score if available
        import re
        score_match = re.search(r"sentiment score:?\s*([-+]?\d+(\.\d+)?)", response_lower)
        if score_match:
            try:
                sentiment_score = float(score_match.group(1))
            except:
                pass
        
        return {
            "sentiment": sentiment,
            "sentiment_score": sentiment_score,
            "analysis": response,
            "model": "Llama 4 Scout"
        }
    
    async def analyze_image_with_text(self, image_path, text):
        """
        Analyze an image with accompanying text.
        Leverages Llama 4 Scout's multimodal capabilities.
        
        Args:
            image_path (str): Path to the image file
            text (str): Accompanying text
            
        Returns:
            dict: Analysis results
        """
        if not self.is_loaded:
            raise RuntimeError("Model is not loaded. Call load() first.")
        
        try:
            # Load image
            from PIL import Image
            image = Image.open(image_path)
            
            # Prepare prompt
            prompt = f"""<|begin_of_text|><|user|>
Analyze this financial chart or image along with the provided text. 
Explain what the image shows and its sentiment implications.

Text: {text}<|end_of_turn|>
<|assistant|>"""
            
            # Process inputs
            inputs = self.processor(
                text=prompt,
                images=image,
                return_tensors="pt"
            )
            
            # Move inputs to device
            inputs = {k: v.to(self.model.device) if hasattr(v, "to") else v for k, v in inputs.items()}
            
            # Generate response
            with torch.no_grad():
                generation_output = self.model.generate(
                    **inputs,
                    max_new_tokens=512,
                    temperature=0.2,
                    do_sample=True
                )
            
            # Decode the response
            generated_text = self.processor.decode(generation_output[0], skip_special_tokens=True)
            
            # Extract the assistant's response
            response = generated_text
            try:
                if "<|assistant|>" in response:
                    response = response.split("<|assistant|>", 1)[1].strip()
            except:
                pass
            
            # Extract sentiment
            sentiment = "neutral"
            sentiment_score = 0.0
            
            response_lower = response.lower()
            if "positive" in response_lower:
                sentiment = "positive"
                sentiment_score = 0.7
            elif "negative" in response_lower:
                sentiment = "negative"
                sentiment_score = -0.7
            
            return {
                "sentiment": sentiment,
                "sentiment_score": sentiment_score,
                "analysis": response,
                "model": "Llama 4 Scout Multimodal"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing image with text: {str(e)}")
            raise

async def download_llama4_model():
    """
    This function prepares the environment for Llama 4 Scout.
    Note: The actual model will be downloaded when first used due to its size.
    """
    logger.info("Setting up Llama 4 Scout environment...")
    
    # Create model directory
    model_dir = Path("./models/weights/llama4")
    os.makedirs(model_dir, exist_ok=True)
    
    # Check for HuggingFace token
    if not os.getenv("HF_TOKEN"):
        logger.warning("HF_TOKEN environment variable not set. You may need to set this to download Llama 4 Scout.")
        logger.warning("Visit https://huggingface.co/settings/tokens to create a token.")
        logger.warning("Then set it with: export HF_TOKEN=your_token_here")
    
    logger.info("Llama 4 Scout environment prepared.")
    logger.info("The model will be downloaded when first used.")

if __name__ == "__main__":
    # For testing
    import asyncio
    
    async def test_model():
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        
        # Download model (prepares environment)
        await download_llama4_model()
        
        # Check for HF_TOKEN
        if not os.getenv("HF_TOKEN"):
            print("WARNING: HF_TOKEN not set. This is required to download Llama 4 Scout.")
            print("Please set the HF_TOKEN environment variable and try again.")
            return
        
        # Initialize and load model
        model = Llama4ScoutModel(use_gpu=True, quantize=True)
        await model.load()
        
        # Test sentiment analysis
        test_texts = [
            "Quarterly earnings exceeded analyst expectations, with revenue growth of 15% year-over-year.",
            "The company announced a significant restructuring plan, including layoffs affecting 10% of its workforce.",
            "The market showed mixed reactions to the Federal Reserve's decision to maintain current interest rates."
        ]
        
        results = await model.predict(test_texts)
        for text, result in zip(test_texts, results):
            print(f"Text: {text}")
            print(f"Sentiment: {result['sentiment_label']} ({result['sentiment_score']:.2f})")
            print(f"Explanation: {result['explanation'][:100]}...")
            print("---")
    
    # Run the test
    asyncio.run(test_model())

        