import logging
import os
from enum import Enum
from typing import Dict, Any, Optional, Union, List
from pathlib import Path

# Import model implementations
try:
    from models.finbert import FinBertModel
    from models.fingpt import FinGPTModel
    from models.llama4_scout import Llama4ScoutModel
except ImportError:
    from sentiment_service.models.finbert import FinBertModel
    from sentiment_service.models.fingpt import FinGPTModel
    from sentiment_service.models.llama4_scout import Llama4ScoutModel

# Import utils for Parquet support
try:
    from utils.parquet_reader import ParquetReader
except ImportError:
    try:
        from sentiment_service.utils.parquet_reader import ParquetReader
    except ImportError:
        ParquetReader = None

logger = logging.getLogger(__name__)

class ModelType(Enum):
    """Enum for model types."""
    FINBERT = "finbert"
    FINGPT = "fingpt"
    LLAMA4_SCOUT = "llama4_scout"

class DataSourceType(Enum):
    """Enum for data source types."""
    KAFKA = "kafka"
    PARQUET = "parquet"
    TEXT = "text"

class ModelFactory:
    """Factory for creating sentiment models."""
    
    def __init__(self):
        """Initialize the model factory."""
        self.models = {}
        self.parquet_reader = None
        self.model_configs = {
            ModelType.FINBERT: {
                "use_onnx": os.getenv("FINBERT_USE_ONNX", "true").lower() == "true",
                "use_gpu": os.getenv("FINBERT_USE_GPU", "true").lower() == "true",
                "model_dir": os.getenv("FINBERT_MODEL_DIR", "./models/weights/finbert"),
            },
            ModelType.FINGPT: {
                "use_gpu": os.getenv("FINGPT_USE_GPU", "true").lower() == "true",
                "quantize": os.getenv("FINGPT_QUANTIZE", "true").lower() == "true",
                "model_dir": os.getenv("FINGPT_MODEL_DIR", "./models/weights/fingpt"),
                "model_variant": os.getenv("FINGPT_MODEL_VARIANT", "FinGPT/fingpt-sentiment_llama2-7b_lora"),
            },
            ModelType.LLAMA4_SCOUT: {
                "use_gpu": os.getenv("LLAMA4_USE_GPU", "true").lower() == "true",
                "quantize": os.getenv("LLAMA4_QUANTIZE", "true").lower() == "true",
                "model_dir": os.getenv("LLAMA4_MODEL_DIR", "./models/weights/llama4"),
                "model_variant": os.getenv("LLAMA4_MODEL_VARIANT", "meta-llama/Llama-4-Scout-17B-16E-Instruct"),
            }
        }
        
        # Parquet configuration
        self.parquet_configs = {
            "data_dir": os.getenv("PARQUET_DATA_DIR", "./data/output"),
            "cache_size": int(os.getenv("PARQUET_CACHE_SIZE", "128")),
        }
    
    async def get_model(self, model_type: ModelType):
        """
        Get a model instance, creating it if it doesn't exist.
        
        Args:
            model_type (ModelType): Type of model to get
            
        Returns:
            Model instance
        """
        if model_type not in self.models:
            await self._create_model(model_type)
        
        return self.models[model_type]
    
    async def _create_model(self, model_type: ModelType):
        """
        Create a model instance.
        
        Args:
            model_type (ModelType): Type of model to create
        """
        logger.info(f"Creating model: {model_type.name}")
        
        config = self.model_configs.get(model_type, {})
        
        if model_type == ModelType.FINBERT:
            model = FinBertModel(
                use_onnx=config.get("use_onnx", True),
                use_gpu=config.get("use_gpu", True),
                model_dir=config.get("model_dir", "./models/weights/finbert"),
            )
        elif model_type == ModelType.FINGPT:
            model = FinGPTModel(
                use_gpu=config.get("use_gpu", True),
                quantize=config.get("quantize", True),
                model_dir=config.get("model_dir", "./models/weights/fingpt"),
                model_variant=config.get("model_variant", "FinGPT/fingpt-sentiment_llama2-7b_lora"),
            )
        elif model_type == ModelType.LLAMA4_SCOUT:
            model = Llama4ScoutModel(
                use_gpu=config.get("use_gpu", True),
                quantize=config.get("quantize", True),
                model_dir=config.get("model_dir", "./models/weights/llama4"),
                model_variant=config.get("model_variant", "meta-llama/Llama-4-Scout-17B-16E-Instruct"),
            )
        else:
            raise ValueError(f"Unknown model type: {model_type}")
        
        # Load the model
        await model.load()
        
        # Store the model instance
        self.models[model_type] = model
        
        logger.info(f"Model {model_type.name} created and loaded")
    
    async def get_parquet_reader(self):
        """
        Get a ParquetReader instance, creating it if it doesn't exist.
        
        Returns:
            ParquetReader instance
        """
        if self.parquet_reader is None:
            if ParquetReader is None:
                raise ImportError("ParquetReader is not available. Please ensure utils.parquet_reader is installed.")
            
            # Create ParquetReader
            self.parquet_reader = ParquetReader(
                data_dir=self.parquet_configs.get("data_dir"),
                cache_size=self.parquet_configs.get("cache_size")
            )
            logger.info(f"ParquetReader created with data_dir: {self.parquet_configs.get('data_dir')}")
        
        return self.parquet_reader
    
    async def process_from_source(self, 
                                  source_type: DataSourceType, 
                                  model_type: ModelType = ModelType.FINBERT, 
                                  data: Any = None, 
                                  **kwargs) -> Dict[str, Any]:
        """
        Process data from a specified source using the appropriate model.
        
        Args:
            source_type (DataSourceType): Type of data source
            model_type (ModelType): Type of model to use
            data (Any): Data to process (format depends on source_type)
            **kwargs: Additional arguments specific to source type
            
        Returns:
            Dict[str, Any]: Processing results
        """
        # Get the model
        model = await self.get_model(model_type)
        
        # Process based on source type
        if source_type == DataSourceType.TEXT:
            # Direct text analysis
            if isinstance(data, str):
                data = [data]
            return await model.predict(data)
            
        elif source_type == DataSourceType.KAFKA:
            # Process Kafka event
            # This is handled by the event consumers directly
            # Just a placeholder for completeness
            logger.info("Kafka data processing should be handled by event consumers")
            return {"error": "Kafka processing should be handled by event consumers"}
            
        elif source_type == DataSourceType.PARQUET:
            # Process data from Parquet file
            parquet_path = kwargs.get("parquet_path") or data
            
            if not parquet_path:
                raise ValueError("parquet_path is required for Parquet data source")
                
            if hasattr(model, "process_parquet_data"):
                # Use model's built-in Parquet processing if available
                return await model.process_parquet_data(
                    parquet_path=parquet_path,
                    text_column=kwargs.get("text_column", "article_title"),
                    timestamp_column=kwargs.get("timestamp_column", "timestamp"),
                    source_column=kwargs.get("source_column", "source"),
                    confidence_column=kwargs.get("confidence_column", "confidence"),
                    ticker_column=kwargs.get("ticker_column", "ticker")
                )
            else:
                # Fall back to manual processing for models without Parquet support
                reader = await self.get_parquet_reader()
                df = reader.read_ticker_data(kwargs.get("ticker", ""))
                
                if df.empty:
                    return {"error": "No data found in Parquet file"}
                
                text_column = kwargs.get("text_column", "article_title")
                texts = df[text_column].tolist()
                results = await model.predict(texts)
                
                # Combine results with DataFrame
                for i, result in enumerate(results):
                    df.loc[i, "sentiment_score"] = result["sentiment_score"]
                    df.loc[i, "sentiment_label"] = result["sentiment_label"]
                
                return df.to_dict(orient="records")
        else:
            raise ValueError(f"Unknown source type: {source_type}")
    
    async def analyze_ticker_sentiment(self, 
                                       ticker: str, 
                                       model_type: ModelType = ModelType.FINBERT,
                                       start_date: Optional[str] = None,
                                       end_date: Optional[str] = None,
                                       data_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        """
        Analyze sentiment for a specific ticker using Parquet data.
        
        Args:
            ticker (str): Ticker symbol to analyze
            model_type (ModelType): Type of model to use
            start_date (Optional[str]): Start date for filtering (ISO format)
            end_date (Optional[str]): End date for filtering (ISO format)
            data_dir (Optional[Union[str, Path]]): Directory containing Parquet files
            
        Returns:
            Dict[str, Any]: Sentiment analysis results
        """
        # Get the model
        model = await self.get_model(model_type)
        
        # Check if model has built-in ticker analysis
        if hasattr(model, "analyze_ticker_sentiment"):
            # Use model's built-in ticker analysis
            return await model.analyze_ticker_sentiment(
                parquet_path=data_dir or self.parquet_configs.get("data_dir"),
                ticker=ticker,
                start_date=start_date,
                end_date=end_date
            )
        else:
            # Fall back to manual analysis using ParquetReader
            reader = await self.get_parquet_reader()
            
            # Build query parameters
            params = {
                "tickers": [ticker],
                "start_date": start_date,
                "end_date": end_date
            }
            
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}
            
            # Query data
            df = reader.query(**params)
            
            if df.empty:
                return {
                    "ticker": ticker,
                    "average_sentiment": 0.0,
                    "count": 0,
                    "sentiment_distribution": {"positive": 0, "neutral": 0, "negative": 0},
                    "time_period": {"start": start_date, "end": end_date}
                }
            
            # Process texts if sentiment not already present
            if "sentiment" not in df.columns:
                text_column = "article_title"
                texts = df[text_column].tolist()
                results = await model.predict(texts)
                
                # Add sentiment scores and labels
                sentiment_scores = [result["sentiment_score"] for result in results]
                sentiment_labels = [result["sentiment_label"] for result in results]
                
                df["sentiment"] = sentiment_scores
                df["sentiment_label"] = sentiment_labels
            
            # Calculate average sentiment
            avg_sentiment = df["sentiment"].mean()
            
            # Count sentiment categories
            if "sentiment_label" in df.columns:
                sentiment_counts = df["sentiment_label"].value_counts().to_dict()
                for label in ["positive", "neutral", "negative"]:
                    if label not in sentiment_counts:
                        sentiment_counts[label] = 0
            else:
                # Categorize based on sentiment score
                sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
                for score in df["sentiment"]:
                    if score > 0.3:
                        sentiment_counts["positive"] += 1
                    elif score < -0.3:
                        sentiment_counts["negative"] += 1
                    else:
                        sentiment_counts["neutral"] += 1
            
            return {
                "ticker": ticker,
                "average_sentiment": float(avg_sentiment),
                "count": len(df),
                "sentiment_distribution": sentiment_counts,
                "time_period": {"start": start_date, "end": end_date}
            }
    
    async def get_available_models(self):
        """
        Get information about available models.
        
        Returns:
            Dict[str, Dict[str, Any]]: Information about available models
        """
        result = {}
        
        for model_type in ModelType:
            config = self.model_configs.get(model_type, {})
            loaded = model_type in self.models
            
            result[model_type.name] = {
                "loaded": loaded,
                "config": config,
                "suitable_for": self._get_model_suitability(model_type),
            }
        
        return result
    
    def _get_model_suitability(self, model_type: ModelType) -> Dict[str, Any]:
        """
        Get information about model suitability for different tasks.
        
        Args:
            model_type (ModelType): Type of model
            
        Returns:
            Dict[str, Any]: Suitability information
        """
        if model_type == ModelType.FINBERT:
            return {
                "latency": "Very Low",
                "accuracy": "Good",
                "context_length": "Short (512 tokens)",
                "recommended_for": "High-volume real-time sentiment analysis",
                "subscription_tier": "All tiers",
                "source_types": ["Kafka", "Parquet", "Text"],
            }
        elif model_type == ModelType.FINGPT:
            return {
                "latency": "Medium",
                "accuracy": "Very Good",
                "context_length": "Medium (4K tokens)",
                "recommended_for": "Premium sentiment analysis, financial reports, complex text",
                "subscription_tier": "Premium, Professional",
                "source_types": ["Kafka", "Text"],
            }
        elif model_type == ModelType.LLAMA4_SCOUT:
            return {
                "latency": "High",
                "accuracy": "Excellent",
                "context_length": "Very Long (10M tokens)",
                "recommended_for": "Comprehensive financial document analysis, multimodal content",
                "subscription_tier": "Professional",
                "source_types": ["Kafka", "Text"],
            }
        else:
            return {}