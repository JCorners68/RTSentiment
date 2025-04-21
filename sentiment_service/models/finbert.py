import logging
import os
import asyncio
from pathlib import Path
import json
from typing import List, Dict, Any

# Mock imports for testing without real dependencies
try:
    import torch
    import numpy as np
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    import onnxruntime as ort
    HAVE_DEPS = True
except ImportError:
    # Create dummy classes/functions for testing
    HAVE_DEPS = False
    
    class torch:
        @staticmethod
        def device(device_str):
            return device_str
            
        class no_grad:
            def __enter__(self): pass
            def __exit__(self, *args): pass
            
        class cuda:
            @staticmethod
            def is_available():
                return False
    
    class np:
        @staticmethod
        def argmax(arr):
            return 0 if arr[0] > arr[2] else 2 if arr[2] > arr[0] else 1
            
        @staticmethod
        def exp(x):
            return x
            
        @staticmethod
        def sum(x, **kwargs):
            return 1.0

logger = logging.getLogger(__name__)

class FinBertModel:
    """
    FinBERT model for financial sentiment analysis.
    Supports both PyTorch and ONNX runtime inference.
    """
    
    def __init__(self, use_onnx=True, use_gpu=True):
        """
        Initialize the FinBERT model.
        
        Args:
            use_onnx (bool): Whether to use ONNX runtime for inference.
            use_gpu (bool): Whether to use GPU for inference.
        """
        self.use_onnx = use_onnx
        self.use_gpu = use_gpu and torch.cuda.is_available()
        self.device = torch.device("cuda" if self.use_gpu else "cpu")
        self.model = None
        self.tokenizer = None
        self.ort_session = None
        self.is_loaded = False
        self.labels = ["negative", "neutral", "positive"]
        
        # Model paths
        self.model_dir = Path(os.getenv("MODEL_DIR", "./models/weights"))
        self.model_name = "finbert-sentiment"
        self.pytorch_path = self.model_dir / "pytorch"
        self.onnx_path = self.model_dir / "onnx" / "finbert-sentiment.onnx"
        
        logger.info(f"Initializing FinBERT model (ONNX: {use_onnx}, GPU: {self.use_gpu})")
    
    async def load(self):
        """Load the model and tokenizer."""
        try:
            # For testing, we might not have the actual dependencies
            if not HAVE_DEPS:
                logger.info("Using mock FinBERT model for testing")
                self.tokenizer = "mock_tokenizer"
                self.model = "mock_model"
                self.is_loaded = True
                return
                
            # Always load the tokenizer
            logger.info(f"Loading tokenizer from {self.pytorch_path}")
            self.tokenizer = await self._load_tokenizer()
            
            if self.use_onnx:
                logger.info(f"Loading ONNX model from {self.onnx_path}")
                await self._load_onnx_model()
            else:
                logger.info(f"Loading PyTorch model from {self.pytorch_path}")
                await self._load_pytorch_model()
            
            self.is_loaded = True
            logger.info("FinBERT model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load FinBERT model: {str(e)}")
            if not HAVE_DEPS:
                # If we're in testing mode with no dependencies, just mock the model
                logger.info("Falling back to mock FinBERT model for testing")
                self.tokenizer = "mock_tokenizer"
                self.model = "mock_model"
                self.is_loaded = True
            else:
                raise
    
    async def _load_tokenizer(self):
        """Load the tokenizer."""
        return AutoTokenizer.from_pretrained(
            str(self.pytorch_path), 
            local_files_only=True
        )
    
    async def _load_pytorch_model(self):
        """Load the PyTorch model."""
        self.model = AutoModelForSequenceClassification.from_pretrained(
            str(self.pytorch_path), 
            local_files_only=True
        )
        self.model.to(self.device)
        self.model.eval()
    
    async def _load_onnx_model(self):
        """Load the ONNX model."""
        # Set up ONNX runtime session
        if self.use_gpu:
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        else:
            providers = ["CPUExecutionProvider"]
        
        # Create ONNX Runtime session
        self.ort_session = ort.InferenceSession(
            str(self.onnx_path), 
            providers=providers
        )
    
    async def predict(self, texts):
        """
        Predict sentiment for a list of texts.
        
        Args:
            texts (list): List of texts to analyze.
            
        Returns:
            list: List of dictionaries with sentiment predictions.
        """
        if not self.is_loaded:
            raise RuntimeError("Model is not loaded. Call load() first.")
        
        # For testing without dependencies
        if not HAVE_DEPS:
            # Mock implementation for testing
            return self._predict_mock(texts)
            
        # Tokenize inputs
        inputs = self.tokenizer(
            texts, 
            padding=True, 
            truncation=True, 
            return_tensors="pt",
            max_length=512
        )
        
        if self.use_onnx:
            return await self._predict_onnx(inputs, texts)
        else:
            return await self._predict_pytorch(inputs, texts)
            
    def _predict_mock(self, texts):
        """Mock prediction for testing."""
        results = []
        
        for text in texts:
            # Very basic keyword-based mock sentiment analysis
            positive_keywords = ["growth", "profit", "increase", "up", "positive", "bullish", "exceed", "beat"]
            negative_keywords = ["loss", "decline", "decrease", "down", "negative", "bearish", "miss", "below"]
            
            positive_count = sum(1 for keyword in positive_keywords if keyword in text.lower())
            negative_count = sum(1 for keyword in negative_keywords if keyword in text.lower())
            
            if positive_count > negative_count:
                sentiment_label = "positive"
                sentiment_score = 0.7
                probs = [0.15, 0.15, 0.7]
            elif negative_count > positive_count:
                sentiment_label = "negative"
                sentiment_score = -0.7
                probs = [0.7, 0.15, 0.15]
            else:
                sentiment_label = "neutral"
                sentiment_score = 0.0
                probs = [0.15, 0.7, 0.15]
            
            results.append({
                "text": text,
                "sentiment_score": sentiment_score,
                "sentiment_label": sentiment_label,
                "probabilities": {
                    "negative": probs[0],
                    "neutral": probs[1],
                    "positive": probs[2],
                }
            })
            
        return results
    
    async def _predict_pytorch(self, inputs, texts):
        """Run inference using PyTorch."""
        # Move inputs to device
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Run inference
        with torch.no_grad():
            outputs = self.model(**inputs)
            probabilities = torch.nn.functional.softmax(outputs.logits, dim=1)
        
        # Process results
        return self._process_results(probabilities.cpu().numpy(), texts)
    
    async def _predict_onnx(self, inputs, texts):
        """Run inference using ONNX runtime."""
        # Prepare inputs for ONNX runtime
        ort_inputs = {
            "input_ids": inputs["input_ids"].numpy(),
            "attention_mask": inputs["attention_mask"].numpy(),
        }
        if "token_type_ids" in inputs:
            ort_inputs["token_type_ids"] = inputs["token_type_ids"].numpy()
        
        # Run inference
        logits = self.ort_session.run(None, ort_inputs)[0]
        probabilities = self._softmax(logits)
        
        # Process results
        return self._process_results(probabilities, texts)
    
    def _softmax(self, x):
        """Compute softmax for ONNX outputs."""
        return np.exp(x) / np.sum(np.exp(x), axis=1, keepdims=True)
    
    def _process_results(self, probabilities, texts):
        """Process model outputs into sentiment predictions."""
        results = []
        
        for i, (probs, text) in enumerate(zip(probabilities, texts)):
            # Get sentiment score (-1 to +1)
            # Negative: -1, Neutral: 0, Positive: +1
            sentiment_score = probs[2] - probs[0]  # positive - negative
            
            # Get predicted label
            label_idx = np.argmax(probs)
            sentiment_label = self.labels[label_idx]
            
            results.append({
                "text": text,
                "sentiment_score": float(sentiment_score),
                "sentiment_label": sentiment_label,
                "probabilities": {
                    "negative": float(probs[0]),
                    "neutral": float(probs[1]),
                    "positive": float(probs[2]),
                }
            })
        
        return results

async def create_optimized_model():
    """Create an optimized ONNX model from a PyTorch model."""
    import os
    from pathlib import Path
    
    # Set up paths
    model_dir = Path("./models/weights")
    pytorch_path = model_dir / "pytorch"
    onnx_path = model_dir / "onnx"
    onnx_path.mkdir(parents=True, exist_ok=True)
    onnx_model_path = onnx_path / "finbert-sentiment.onnx"
    
    # Load PyTorch model and tokenizer
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    
    if not pytorch_path.exists():
        # Download model if not available
        model_name = "ProsusAI/finbert"
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        # Save model locally
        model.save_pretrained(pytorch_path)
        tokenizer.save_pretrained(pytorch_path)
    else:
        model = AutoModelForSequenceClassification.from_pretrained(str(pytorch_path))
        tokenizer = AutoTokenizer.from_pretrained(str(pytorch_path))
    
    # Export to ONNX
    import torch
    
    # Create dummy input
    dummy_input = tokenizer(
        "This is a test sentence for ONNX export",
        return_tensors="pt"
    )
    
    # Export the model
    with torch.no_grad():
        torch.onnx.export(
            model,
            (dummy_input["input_ids"], dummy_input["attention_mask"]),
            onnx_model_path,
            opset_version=13,
            input_names=["input_ids", "attention_mask"],
            output_names=["logits"],
            dynamic_axes={
                "input_ids": {0: "batch_size", 1: "sequence_length"},
                "attention_mask": {0: "batch_size", 1: "sequence_length"},
                "logits": {0: "batch_size"}
            }
        )
    
    print(f"ONNX model saved to {onnx_model_path}")
    
    # Optimize ONNX model
    import onnxruntime as ort
    from onnxruntime.quantization import quantize_dynamic, QuantType
    
    # Quantize the model
    quantized_model_path = onnx_path / "finbert-sentiment-quantized.onnx"
    quantize_dynamic(
        str(onnx_model_path),
        str(quantized_model_path),
        weight_type=QuantType.QUInt8
    )
    
    print(f"Quantized ONNX model saved to {quantized_model_path}")

if __name__ == "__main__":
    # For local testing and model export
    import asyncio
    
    async def test_model():
        model = FinBertModel(use_onnx=True, use_gpu=True)
        await model.load()
        
        test_texts = [
            "The company reported strong earnings, exceeding analyst expectations.",
            "The stock plummeted after the CEO announced their resignation.",
            "Quarterly results were in line with market consensus.",
        ]
        
        results = await model.predict(test_texts)
        for text, result in zip(test_texts, results):
            print(f"Text: {text}")
            print(f"Sentiment: {result['sentiment_label']} ({result['sentiment_score']:.2f})")
            print("---")
    
    # To create an optimized model
    # asyncio.run(create_optimized_model())
    
    # To test model inference
    asyncio.run(test_model())