import logging
import os
from enum import Enum
from typing import Dict, Any

# Import model implementations
try:
    from models.finbert import FinBertModel
    from models.fingpt import FinGPTModel
    from models.llama4_scout import Llama4ScoutModel
except ImportError:
    from sentiment_service.models.finbert import FinBertModel
    from sentiment_service.models.fingpt import FinGPTModel
    from sentiment_service.models.llama4_scout import Llama4ScoutModel

logger = logging.getLogger(__name__)

class ModelType(Enum):
    """Enum for model types."""
    FINBERT = "finbert"
    FINGPT = "fingpt"
    LLAMA4_SCOUT = "llama4_scout"

class ModelFactory:
    """Factory for creating sentiment models."""
    
    def __init__(self):
        """Initialize the model factory."""
        self.models = {}
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
            }
        elif model_type == ModelType.FINGPT:
            return {
                "latency": "Medium",
                "accuracy": "Very Good",
                "context_length": "Medium (4K tokens)",
                "recommended_for": "Premium sentiment analysis, financial reports, complex text",
                "subscription_tier": "Premium, Professional",
            }
        elif model_type == ModelType.LLAMA4_SCOUT:
            return {
                "latency": "High",
                "accuracy": "Excellent",
                "context_length": "Very Long (10M tokens)",
                "recommended_for": "Comprehensive financial document analysis, multimodal content",
                "subscription_tier": "Professional",
            }
        else:
            return {}