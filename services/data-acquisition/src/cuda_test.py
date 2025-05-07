#!/usr/bin/env python3
"""
CUDA/GPU test script to diagnose issues with the PyTorch CUDA setup.
This script runs basic CUDA operations to identify compatibility issues.
"""

import os
import sys
import logging
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FinBERT model parameters
MODEL_NAME = "ProsusAI/finbert"
MODEL_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "models")

def test_basic_cuda_operations():
    """Test basic CUDA tensor operations to verify PyTorch CUDA works."""
    logger.info("Testing basic CUDA tensor operations")
    
    if not torch.cuda.is_available():
        logger.error("CUDA is not available")
        return False
    
    try:
        # Print CUDA device information
        device_count = torch.cuda.device_count()
        logger.info(f"CUDA device count: {device_count}")
        
        for i in range(device_count):
            logger.info(f"CUDA Device {i}: {torch.cuda.get_device_name(i)}")
            logger.info(f"CUDA Device {i} Capability: {torch.cuda.get_device_capability(i)}")
        
        # Create a CUDA tensor
        logger.info("Creating CUDA tensor")
        x = torch.tensor([1.0, 2.0, 3.0, 4.0], device='cuda')
        logger.info(f"CUDA tensor created: {x}")
        
        # Perform some operations
        logger.info("Performing tensor operations")
        y = x * 2
        logger.info(f"Multiplication result: {y}")
        
        # Create a larger tensor and perform matrix operations
        logger.info("Testing matrix operations")
        a = torch.randn(1000, 1000, device='cuda')
        b = torch.randn(1000, 1000, device='cuda')
        logger.info("Computing matrix multiplication")
        c = torch.matmul(a, b)
        logger.info(f"Matrix multiplication result shape: {c.shape}")
        
        logger.info("Basic CUDA operations successful")
        return True
    
    except Exception as e:
        logger.error(f"Error in basic CUDA operations: {e}")
        return False

def test_finbert_model_loading():
    """Test loading the FinBERT model with explicit CUDA options."""
    logger.info(f"Testing FinBERT model loading from {MODEL_NAME}")
    
    try:
        # Ensure cache directory exists
        os.makedirs(MODEL_CACHE_DIR, exist_ok=True)
        
        # Check CUDA capabilities and versions
        if torch.cuda.is_available():
            cuda_version = torch.version.cuda
            device_count = torch.cuda.device_count()
            current_device = torch.cuda.current_device()
            device_name = torch.cuda.get_device_name(current_device)
            capability = torch.cuda.get_device_capability(current_device)
            
            logger.info(f"CUDA Version: {cuda_version}")
            logger.info(f"Device Count: {device_count}")
            logger.info(f"Current Device: {current_device}")
            logger.info(f"Device Name: {device_name}")
            logger.info(f"Device Capability: {capability[0]}.{capability[1]}")
        else:
            logger.error("CUDA not available for model loading test")
            return False
        
        # Set environment variables that might help with CUDA issues
        os.environ["CUDA_LAUNCH_BLOCKING"] = "1"  # Get better error messages
        
        # Try to load the tokenizer
        logger.info("Loading tokenizer")
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, cache_dir=MODEL_CACHE_DIR)
        logger.info("Tokenizer loaded successfully")
        
        # Try to load the model
        logger.info("Loading model")
        model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, cache_dir=MODEL_CACHE_DIR)
        logger.info("Model loaded successfully")
        
        # Try device placement with error handling
        try:
            logger.info("Moving model to CUDA device")
            model.to('cuda')
            logger.info("Model successfully moved to CUDA")
        except Exception as e:
            logger.error(f"Error moving model to CUDA: {e}")
            return False
        
        # Test tokenization and inference with a sample text
        try:
            logger.info("Testing model inference with sample text")
            sample_text = "The company reported strong earnings growth this quarter."
            inputs = tokenizer(sample_text, return_tensors="pt")
            
            # Move inputs to GPU
            inputs = {key: val.to('cuda') for key, val in inputs.items()}
            
            logger.info("Running model prediction")
            with torch.no_grad():
                outputs = model(**inputs)
            
            logger.info(f"Model outputs shape: {outputs.logits.shape}")
            logger.info("Model inference successful")
            
            # Try creating a pipeline
            logger.info("Creating sentiment pipeline")
            sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model=model,
                tokenizer=tokenizer,
                device=0  # Explicitly use CUDA device 0
            )
            
            # Run pipeline inference
            logger.info("Running pipeline inference")
            result = sentiment_pipeline(sample_text)
            logger.info(f"Pipeline result: {result}")
            logger.info("Pipeline test successful")
            
            return True
        except Exception as e:
            logger.error(f"Error during model inference: {e}")
            return False
        
    except Exception as e:
        logger.error(f"Error loading FinBERT model: {e}")
        return False

def main():
    """Run all CUDA tests."""
    print("=" * 60)
    print("CUDA/GPU Test Diagnostics".center(60))
    print("=" * 60)
    
    # Check if CUDA is available
    print(f"\nCUDA Available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA Version: {torch.version.cuda}")
        print(f"PyTorch CUDA Version: {torch.backends.cudnn.version()}")
        print(f"Device Count: {torch.cuda.device_count()}")
        
        # Get current device information
        current_device = torch.cuda.current_device()
        print(f"Current Device: {current_device}")
        print(f"Device Name: {torch.cuda.get_device_name(current_device)}")
        
        # Test basic CUDA operations
        print("\n" + "-" * 60)
        print("Testing Basic CUDA Operations".center(60))
        print("-" * 60)
        basic_ops_success = test_basic_cuda_operations()
        print(f"Basic CUDA Operations Test: {'PASSED' if basic_ops_success else 'FAILED'}")
        
        # Test FinBERT model loading
        print("\n" + "-" * 60)
        print("Testing FinBERT Model Loading".center(60))
        print("-" * 60)
        model_loading_success = test_finbert_model_loading()
        print(f"FinBERT Model Loading Test: {'PASSED' if model_loading_success else 'FAILED'}")
        
        # Overall assessment
        print("\n" + "=" * 60)
        print("CUDA Diagnostics Summary".center(60))
        print("=" * 60)
        
        if basic_ops_success and model_loading_success:
            print("\nAll CUDA tests PASSED. Your GPU setup is working properly.")
        elif basic_ops_success and not model_loading_success:
            print("\nBasic CUDA operations work, but there are issues with the FinBERT model.")
            print("This suggests a compatibility issue between the model and your CUDA setup.")
            print("\nPossible solutions:")
            print("1. Check if your PyTorch version is compatible with CUDA 12.6")
            print("2. Try installing a different PyTorch version with: pip install torch==<version> --force-reinstall")
            print("3. Check if the transformers library needs updating")
        elif not basic_ops_success:
            print("\nBasic CUDA operations failed. There are fundamental issues with your CUDA setup.")
            print("\nPossible solutions:")
            print("1. Reinstall PyTorch with the correct CUDA version: https://pytorch.org/get-started/locally/")
            print("2. Make sure your NVIDIA drivers are up to date")
            print("3. Check for compatibility between PyTorch, CUDA, and your GPU")
    else:
        print("\nCUDA is not available. Cannot run GPU tests.")
        print("Make sure you have NVIDIA drivers and CUDA toolkit installed correctly.")

if __name__ == "__main__":
    main()