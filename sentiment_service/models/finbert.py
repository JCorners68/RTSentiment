import logging
import os
import asyncio
import math
from datetime import datetime, timedelta
from pathlib import Path
import json
from typing import List, Dict, Any, Optional, Union, Tuple

# Mock imports for testing without real dependencies
try:
    import torch
    import numpy as np
    import pandas as pd
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
            
    class pd:
        DataFrame = dict

logger = logging.getLogger(__name__)

class FinBertModel:
    """
    FinBERT model for financial sentiment analysis.
    Supports both PyTorch and ONNX runtime inference.
    """
    
    def __init__(self, use_onnx=True, use_gpu=True, model_dir=None):
        """
        Initialize the FinBERT model.
        
        Args:
            use_onnx (bool): Whether to use ONNX runtime for inference.
            use_gpu (bool): Whether to use GPU for inference.
            model_dir (str, optional): Directory containing model weights.
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
        if model_dir:
            self.model_dir = Path(model_dir)
        else:
            self.model_dir = Path(os.getenv("MODEL_DIR", "./models/weights"))
        
        self.model_name = "finbert-sentiment"
        self.pytorch_path = self.model_dir / "pytorch"
        self.onnx_path = self.model_dir / "onnx" / "finbert-sentiment.onnx"
        
        # Source credibility configuration
        self.source_credibility = {
            "NewsScraper": 0.9,
            "RedditScraper": 0.7,
            "TwitterScraper": 0.6,
            "default": 0.8
        }
        
        # Time decay parameters
        self.time_decay_half_life_days = 5.0  # Half-life in days
        self.time_decay_factor = math.log(2) / (self.time_decay_half_life_days * 24 * 60 * 60)  # Convert to seconds
        
        # Batch processing settings
        self.batch_size = int(os.getenv("FINBERT_BATCH_SIZE", "16"))
        
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
    
    async def predict_batch(self, texts: List[str], batch_size: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Predict sentiment for a large batch of texts.
        
        Args:
            texts (List[str]): List of texts to analyze
            batch_size (Optional[int]): Size of batches to process. If None, uses self.batch_size
            
        Returns:
            List[Dict[str, Any]]: List of dictionaries with sentiment predictions
        """
        if not batch_size:
            batch_size = self.batch_size
            
        results = []
        
        # Process in batches to avoid OOM errors
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_results = await self.predict(batch_texts)
            results.extend(batch_results)
            
            # Add a small delay to prevent resource exhaustion
            await asyncio.sleep(0.01)
        
        return results
    
    async def process_parquet_data(self, 
                                   parquet_path: Union[str, Path],
                                   text_column: str = "article_title",
                                   timestamp_column: str = "timestamp",
                                   source_column: str = "source",
                                   confidence_column: str = "confidence",
                                   ticker_column: str = "ticker") -> pd.DataFrame:
        """
        Process sentiment from a Parquet file.
        
        Args:
            parquet_path (Union[str, Path]): Path to Parquet file
            text_column (str): Column containing text to analyze
            timestamp_column (str): Column containing timestamps
            source_column (str): Column containing source information
            confidence_column (str): Column containing confidence scores
            ticker_column (str): Column containing ticker symbols
            
        Returns:
            pd.DataFrame: DataFrame with sentiment scores
        """
        try:
            # Read Parquet file
            df = pd.read_parquet(parquet_path)
            
            if df.empty:
                logger.warning(f"Parquet file is empty: {parquet_path}")
                return df
                
            # Check required columns
            for col in [text_column, timestamp_column]:
                if col not in df.columns:
                    logger.error(f"Required column '{col}' not found in Parquet file: {parquet_path}")
                    return df
            
            # Extract texts for sentiment analysis
            texts = df[text_column].tolist()
            
            # Analyze sentiment
            sentiment_results = await self.predict_batch(texts)
            
            # Extract sentiment scores
            sentiment_scores = [result["sentiment_score"] for result in sentiment_results]
            sentiment_labels = [result["sentiment_label"] for result in sentiment_results]
            
            # Add to DataFrame
            df["sentiment_raw"] = sentiment_scores
            df["sentiment_label"] = sentiment_labels
            
            # Apply time decay and source credibility if available
            if timestamp_column in df.columns:
                df["timestamp_dt"] = pd.to_datetime(df[timestamp_column])
                
                # Calculate time decay factors
                now = datetime.now()
                df["time_decay"] = df["timestamp_dt"].apply(
                    lambda x: self._calculate_time_decay(x, now)
                )
            else:
                df["time_decay"] = 1.0
            
            # Apply source credibility if available
            if source_column in df.columns:
                df["source_credibility"] = df[source_column].apply(
                    lambda x: self.source_credibility.get(x, self.source_credibility["default"])
                )
            else:
                df["source_credibility"] = self.source_credibility["default"]
            
            # Apply confidence weighting if available
            if confidence_column not in df.columns:
                df[confidence_column] = 0.8  # Default confidence
            
            # Calculate final weighted sentiment score
            df["sentiment"] = df.apply(
                lambda row: self._calculate_weighted_sentiment(
                    row["sentiment_raw"],
                    row["source_credibility"],
                    row[confidence_column],
                    row["time_decay"]
                ),
                axis=1
            )
            
            return df
            
        except Exception as e:
            logger.error(f"Error processing Parquet file: {str(e)}")
            return pd.DataFrame()
    
    async def analyze_ticker_sentiment(self, 
                                       parquet_path: Union[str, Path], 
                                       ticker: str,
                                       start_date: Optional[str] = None,
                                       end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze sentiment for a specific ticker.
        
        Args:
            parquet_path (Union[str, Path]): Path to Parquet file or directory
            ticker (str): Ticker symbol to analyze
            start_date (Optional[str]): Start date for filtering (ISO format)
            end_date (Optional[str]): End date for filtering (ISO format)
            
        Returns:
            Dict[str, Any]: Dictionary with sentiment analysis results
        """
        try:
            # Determine if path is a file or directory
            path = Path(parquet_path)
            
            if path.is_file():
                # Single file
                df = await self.process_parquet_data(path)
            elif path.is_dir():
                # Directory - look for ticker-specific file
                ticker_file = path / f"{ticker.lower()}_sentiment.parquet"
                if ticker_file.exists():
                    df = await self.process_parquet_data(ticker_file)
                else:
                    # Check multi_ticker file
                    multi_ticker_file = path / "multi_ticker_sentiment.parquet"
                    if multi_ticker_file.exists():
                        df = await self.process_parquet_data(multi_ticker_file)
                    else:
                        logger.error(f"No sentiment data found for ticker {ticker}")
                        return {"error": f"No sentiment data found for ticker {ticker}"}
            else:
                logger.error(f"Invalid path: {parquet_path}")
                return {"error": f"Invalid path: {parquet_path}"}
            
            # Filter for the specific ticker
            df = df[df["ticker"] == ticker.upper()]
            
            # Apply date filters
            if start_date or end_date:
                df["timestamp_dt"] = pd.to_datetime(df["timestamp"])
                
                if start_date:
                    start_dt = pd.to_datetime(start_date)
                    df = df[df["timestamp_dt"] >= start_dt]
                
                if end_date:
                    end_dt = pd.to_datetime(end_date)
                    df = df[df["timestamp_dt"] <= end_dt]
            
            # Calculate average sentiment
            if df.empty:
                return {
                    "ticker": ticker,
                    "average_sentiment": 0.0,
                    "count": 0,
                    "sentiment_distribution": {"positive": 0, "neutral": 0, "negative": 0},
                    "time_period": {"start": start_date, "end": end_date}
                }
            
            # Weight by confidence
            weighted_sentiment = (df["sentiment"] * df["confidence"]).sum() / df["confidence"].sum()
            
            # Count sentiment categories
            sentiment_counts = df["sentiment_label"].value_counts().to_dict()
            for label in ["positive", "neutral", "negative"]:
                if label not in sentiment_counts:
                    sentiment_counts[label] = 0
            
            return {
                "ticker": ticker,
                "average_sentiment": float(weighted_sentiment),
                "count": len(df),
                "sentiment_distribution": sentiment_counts,
                "time_period": {"start": start_date, "end": end_date}
            }
            
        except Exception as e:
            logger.error(f"Error analyzing ticker sentiment: {str(e)}")
            return {"error": str(e)}
    
    def _calculate_time_decay(self, timestamp: datetime, current_time: datetime) -> float:
        """
        Calculate time decay factor based on elapsed time.
        
        Args:
            timestamp (datetime): Timestamp of the event
            current_time (datetime): Current time
            
        Returns:
            float: Time decay factor (0-1)
        """
        # Calculate time difference in seconds
        time_diff = (current_time - timestamp).total_seconds()
        
        # Apply exponential decay
        if time_diff < 0:  # Future events get full weight
            return 1.0
            
        decay = math.exp(-self.time_decay_factor * time_diff)
        return max(0.1, decay)  # Minimum decay factor of 0.1
    
    def _calculate_weighted_sentiment(self, 
                                     raw_sentiment: float, 
                                     source_credibility: float,
                                     confidence: float,
                                     time_decay: float) -> float:
        """
        Calculate weighted sentiment score.
        
        Args:
            raw_sentiment (float): Raw sentiment score (-1 to 1)
            source_credibility (float): Source credibility factor (0-1)
            confidence (float): Model confidence (0-1)
            time_decay (float): Time decay factor (0-1)
            
        Returns:
            float: Weighted sentiment score
        """
        # Combine factors - each factor scales the sentiment
        weight = source_credibility * confidence * time_decay
        
        # Apply weight to raw sentiment
        return raw_sentiment * weight
            
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