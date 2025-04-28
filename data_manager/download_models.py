#!/usr/bin/env python3
"""
Script to download sentiment analysis model weights for local usage.
This ensures that model weights are cached locally before runtime.
"""

import os
import logging
import argparse
import torch
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def download_finbert_model(output_dir=None, use_gpu=None):
    """
    Downloads the FinBERT model weights from Hugging Face.
    
    Args:
        output_dir: Optional directory to save model to (defaults to HF cache)
        use_gpu: Whether to use GPU for testing the model (auto-detects if None)
    """
    try:
        # Import here to avoid making transformers a required dependency
        # for users who just want to run other scripts
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        
        # Default model to use
        model_name = "ProsusAI/finbert"
        
        logger.info(f"Started downloading model: {model_name}")
        
        # Check GPU availability if not explicitly set
        if use_gpu is None:
            use_gpu = torch.cuda.is_available()
        
        if use_gpu:
            device_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NONE"
            logger.info(f"GPU acceleration enabled. Available device: {device_name}")
        else:
            logger.info("Using CPU for model loading (will be slower for inference)")
        
        # Download and save tokenizer
        logger.info("Downloading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        # Download and save model
        logger.info("Downloading model weights...")
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        
        # If output directory is specified, save the model there
        if output_dir:
            output_path = Path(output_dir)
            os.makedirs(output_path, exist_ok=True)
            
            logger.info(f"Saving model to custom directory: {output_path}")
            model.save_pretrained(output_path / "model")
            tokenizer.save_pretrained(output_path / "tokenizer")
            
            logger.info(f"Model and tokenizer saved to: {output_path}")
        else:
            # Just downloading to cache is enough
            logger.info(f"Model and tokenizer downloaded to Hugging Face cache")
        
        # Test the model
        logger.info("Testing model with a sample sentence...")
        device = torch.device("cuda:0" if use_gpu and torch.cuda.is_available() else "cpu")
        model = model.to(device)
        
        # Sample text for testing
        test_text = "The company reported strong earnings this quarter, exceeding expectations."
        
        # Tokenize and prepare input
        inputs = tokenizer(test_text, return_tensors="pt", padding=True, truncation=True).to(device)
        
        # Run inference
        with torch.no_grad():
            outputs = model(**inputs)
            
        # Get predictions
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        prediction = torch.argmax(probs, dim=1).item()
        
        # Map prediction to label (FinBERT usually has positive=0, negative=1, neutral=2)
        labels = ["positive", "negative", "neutral"]
        label = labels[prediction]
        confidence = probs[0][prediction].item()
        
        logger.info(f"Test successful! Prediction: {label.upper()} with confidence: {confidence:.4f}")
        logger.info(f"Model download and testing completed successfully!")
        
        return True
        
    except ImportError as e:
        logger.error(f"Required packages not installed. Error: {e}")
        logger.info("Please install the required packages with: pip install transformers torch")
        return False
    except Exception as e:
        logger.error(f"Error downloading model: {e}")
        import traceback
        traceback.print_exc()
        return False

def download_finbert_onnx(output_dir=None):
    """
    Converts the FinBERT model to ONNX format for faster inference.
    
    Args:
        output_dir: Directory to save ONNX model to (required)
    """
    try:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        
        if not output_dir:
            logger.error("Output directory is required for ONNX conversion")
            return False
            
        # Default model to use
        model_name = "ProsusAI/finbert"
        output_path = Path(output_dir) / "onnx"
        os.makedirs(output_path, exist_ok=True)
        
        logger.info(f"Converting {model_name} to ONNX format...")
        
        # Load model and tokenizer
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        
        # Create dummy input
        dummy_text = "This is a sample text for ONNX conversion."
        dummy_input = tokenizer(dummy_text, return_tensors="pt")
        
        # Export to ONNX
        input_names = ["input_ids", "attention_mask"]
        output_names = ["logits"]
        
        # Only export the relevant inputs present in dummy_input
        dynamic_axes = {
            'input_ids': {0: 'batch_size', 1: 'sequence_length'},
            'attention_mask': {0: 'batch_size', 1: 'sequence_length'},
            'logits': {0: 'batch_size'}
        }
        
        # Export the model to ONNX
        onnx_path = output_path / "model.onnx"
        logger.info(f"Exporting model to {onnx_path}...")
        
        torch.onnx.export(
            model,                                         # Model to export
            (dummy_input['input_ids'], dummy_input['attention_mask']),  # Model inputs
            onnx_path,                                     # Output file
            export_params=True,                            # Store trained parameters
            opset_version=13,                              # ONNX version
            input_names=input_names,                       # Model's input names
            output_names=output_names,                     # Model's output names
            dynamic_axes=dynamic_axes                      # Dynamic axes
        )
        
        # Save tokenizer alongside ONNX model
        tokenizer.save_pretrained(output_path)
        
        logger.info(f"ONNX model and tokenizer saved to: {output_path}")
        logger.info("Conversion to ONNX format completed successfully!")
        
        return True
        
    except ImportError as e:
        logger.error(f"Required packages not installed. Error: {e}")
        logger.info("Please install the required packages with: pip install transformers torch onnx")
        return False
    except Exception as e:
        logger.error(f"Error converting model to ONNX: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Download FinBERT model weights")
    parser.add_argument("--output_dir", help="Directory to save model weights (default: HF cache)")
    parser.add_argument("--onnx", action="store_true", help="Convert model to ONNX format for faster inference")
    parser.add_argument("--gpu", action="store_true", help="Use GPU for testing the model")
    parser.add_argument("--cpu", action="store_true", help="Force CPU usage even if GPU is available")
    
    args = parser.parse_args()
    
    # Determine GPU usage
    use_gpu = None
    if args.gpu:
        use_gpu = True
    elif args.cpu:
        use_gpu = False
    
    # Create default output directory in the same directory as the script
    if not args.output_dir:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        args.output_dir = os.path.join(parent_dir, "sentiment_service/models/weights/finbert")
    
    # Download the model
    success = download_finbert_model(args.output_dir, use_gpu)
    
    # Optionally convert to ONNX
    if success and args.onnx:
        download_finbert_onnx(args.output_dir)
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())