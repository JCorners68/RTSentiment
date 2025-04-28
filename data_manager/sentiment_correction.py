#!/usr/bin/env python3
"""
GPU-accelerated sentiment recalculation for parquet files using FinBERT.

This script processes parquet files containing financial market data
and calculates sentiment scores using the FinBERT model with GPU acceleration.
"""

import os
import logging
import pandas as pd
import torch
import numpy as np
import argparse
from pathlib import Path
import glob
from tqdm import tqdm
import sys
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SentimentCalculator:
    """GPU-accelerated sentiment calculator for financial text data."""
    
    def __init__(self, use_gpu=None, batch_size=32):
        """
        Initialize the sentiment calculator.
        
        Args:
            use_gpu: Whether to use GPU (auto-detect if None)
            batch_size: Batch size for processing texts
        """
        self.batch_size = batch_size
        
        # Auto-detect GPU availability if not specified
        if use_gpu is None:
            use_gpu = torch.cuda.is_available()
        
        self.use_gpu = use_gpu and torch.cuda.is_available()
        
        if self.use_gpu:
            device_name = torch.cuda.get_device_name(0)
            logger.info(f"GPU acceleration enabled. Using device: {device_name}")
        else:
            logger.info("Using CPU for sentiment analysis")
        
        # Will be set during load_model
        self.model = None
        self.tokenizer = None
        self.device = None
    
    def load_model(self, model_dir=None):
        """
        Load the FinBERT model.
        
        Args:
            model_dir: Optional directory containing the model weights
        """
        try:
            # Import here to avoid making transformers a required dependency
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            
            logger.info("Loading FinBERT model...")
            start_time = time.time()
            
            # Default model to use
            model_name = "ProsusAI/finbert"
            
            # If model_dir is specified and exists, use it instead of downloading
            if model_dir and os.path.isdir(model_dir):
                if os.path.exists(os.path.join(model_dir, "model")):
                    logger.info(f"Loading model from local directory: {model_dir}/model")
                    self.model = AutoModelForSequenceClassification.from_pretrained(os.path.join(model_dir, "model"))
                    
                    logger.info(f"Loading tokenizer from local directory: {model_dir}/tokenizer")
                    self.tokenizer = AutoTokenizer.from_pretrained(os.path.join(model_dir, "tokenizer"))
                else:
                    logger.info(f"Loading model from local directory: {model_dir}")
                    self.model = AutoModelForSequenceClassification.from_pretrained(model_dir)
                    self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
            else:
                # Download from Hugging Face
                logger.info(f"Downloading model from Hugging Face: {model_name}")
                self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            # Set up device
            self.device = torch.device("cuda:0" if self.use_gpu else "cpu")
            self.model = self.model.to(self.device)
            
            # Set model to evaluation mode
            self.model.eval()
            
            # Get label mapping
            self.id2label = self.model.config.id2label
            
            load_time = time.time() - start_time
            logger.info(f"Model loaded successfully in {load_time:.2f} seconds")
            
            # Test the model with a sample
            self._test_model()
            
            return True
        
        except ImportError as e:
            logger.error(f"Required packages not installed. Error: {e}")
            logger.info("Please install transformers with: pip install transformers torch")
            return False
        
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _test_model(self):
        """Test the model with a sample text."""
        try:
            test_text = "The company reported quarterly earnings that exceeded analyst expectations."
            
            logger.info("Testing model with sample text...")
            result = self.get_sentiment(test_text)
            
            logger.info(f"Test successful! Prediction: {result['label']} ({result['score']:.4f})")
            return True
        
        except Exception as e:
            logger.error(f"Model test failed: {e}")
            return False
    
    def get_sentiment(self, text):
        """
        Get sentiment for a single text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with sentiment score and label
        """
        if not text or not isinstance(text, str):
            return {"score": 0.0, "label": "neutral"}
        
        # Tokenize text
        inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True).to(self.device)
        
        # Get prediction
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        # Get probabilities
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        prediction = torch.argmax(probs, dim=1).item()
        
        # Get label (FinBERT: 0=positive, 1=negative, 2=neutral)
        label = self.id2label[prediction]
        confidence = probs[0][prediction].item()
        
        # Calculate sentiment score (-1 to 1)
        if label == "positive":
            score = confidence
        elif label == "negative":
            score = -confidence
        else:
            score = 0.0
        
        return {
            "score": score,
            "label": label,
            "confidence": confidence
        }
    
    def process_batch(self, texts):
        """
        Process a batch of texts.
        
        Args:
            texts: List of texts to analyze
            
        Returns:
            List of sentiment dictionaries
        """
        if not texts:
            return []
        
        # Filter out None or non-string values
        valid_texts = [t for t in texts if t and isinstance(t, str)]
        
        if not valid_texts:
            return [{"score": 0.0, "label": "neutral", "confidence": 0.0} for _ in texts]
        
        # Tokenize all texts
        inputs = self.tokenizer(valid_texts, return_tensors="pt", padding=True, truncation=True).to(self.device)
        
        # Get predictions
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        # Get probabilities
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        predictions = torch.argmax(probs, dim=1).tolist()
        
        # Create results
        results = []
        for i, prediction in enumerate(predictions):
            label = self.id2label[prediction]
            confidence = probs[i][prediction].item()
            
            # Calculate sentiment score (-1 to 1)
            if label == "positive":
                score = confidence
            elif label == "negative":
                score = -confidence
            else:
                score = 0.0
            
            results.append({
                "score": score,
                "label": label,
                "confidence": confidence
            })
        
        return results
    
    def process_texts(self, texts):
        """
        Process multiple texts in batches.
        
        Args:
            texts: List of texts to analyze
            
        Returns:
            List of sentiment dictionaries
        """
        results = []
        
        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i:i+self.batch_size]
            batch_results = self.process_batch(batch_texts)
            results.extend(batch_results)
        
        return results

def process_parquet_file(file_path, output_path, calculator, text_column='article_title'):
    """
    Process a parquet file to calculate sentiment scores.
    
    Args:
        file_path: Path to the parquet file
        output_path: Path to save the updated file
        calculator: Initialized SentimentCalculator
        text_column: Column containing text for sentiment analysis
        
    Returns:
        Dictionary with processing statistics
    """
    try:
        logger.info(f"Processing file: {file_path}")
        
        # Read the parquet file
        df = pd.read_parquet(file_path)
        
        if df.empty:
            logger.warning(f"File is empty: {file_path}")
            return {"success": False, "rows_processed": 0, "error": "Empty file"}
        
        # Check if required columns exist
        if text_column not in df.columns:
            logger.error(f"Required column '{text_column}' not found in file: {file_path}")
            return {"success": False, "rows_processed": 0, "error": f"Missing column: {text_column}"}
        
        # Extract texts for sentiment analysis
        texts = df[text_column].tolist()
        logger.info(f"Analyzing sentiment for {len(texts)} texts...")
        
        # Process texts in batches
        results = calculator.process_texts(texts)
        
        # Extract sentiment scores and labels
        sentiment_scores = [r["score"] for r in results]
        sentiment_labels = [r["label"] for r in results]
        confidence_scores = [r["confidence"] for r in results]
        
        # Update DataFrame with new values
        df["sentiment"] = sentiment_scores
        df["sentiment_label"] = sentiment_labels
        df["confidence"] = confidence_scores
        
        # Calculate priority based on sentiment strength and confidence
        df["priority"] = df.apply(
            lambda row: calculate_priority(row["sentiment"], row["confidence"]),
            axis=1
        )
        
        # Calculate weighted priority (equal to priority for now)
        df["weighted_priority"] = df["priority"]
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save updated DataFrame
        df.to_parquet(output_path, index=False)
        
        logger.info(f"Processed {len(df)} rows, saved to: {output_path}")
        return {"success": True, "rows_processed": len(df)}
        
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "rows_processed": 0, "error": str(e)}

def calculate_priority(sentiment, confidence):
    """
    Calculate priority score based on sentiment strength and confidence.
    
    Args:
        sentiment: Sentiment score (-1 to 1)
        confidence: Model confidence (0 to 1)
        
    Returns:
        Priority score (0.1 to 10.0)
    """
    # Start with base priority of 1.0
    priority = 1.0
    
    # Adjust based on sentiment strength (absolute value)
    sentiment_strength = abs(sentiment)
    
    # Scale sentiment strength to a multiplier between 0.5 and 2.0
    sentiment_multiplier = 0.5 + (sentiment_strength * 1.5)
    
    # Apply confidence as a multiplier 
    confidence_multiplier = 0.5 + (confidence * 1.5)
    
    # Combine factors
    priority = priority * sentiment_multiplier * confidence_multiplier
    
    # Ensure within reasonable bounds (0.1 to 10.0)
    return max(0.1, min(10.0, priority))

def process_directory(input_dir, output_dir, calculator, text_column='article_title'):
    """
    Process all parquet files in a directory.
    
    Args:
        input_dir: Directory containing parquet files
        output_dir: Directory to save updated files
        calculator: Initialized SentimentCalculator
        text_column: Column containing text for sentiment analysis
        
    Returns:
        Dictionary with processing statistics
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")
    
    # Find all parquet files
    parquet_files = glob.glob(os.path.join(input_dir, "*.parquet"))
    if not parquet_files:
        logger.warning(f"No parquet files found in directory: {input_dir}")
        return {"files_processed": 0, "rows_processed": 0, "error": "No parquet files found"}
        
    logger.info(f"Found {len(parquet_files)} parquet files to process")
    
    # Process each file
    total_files = 0
    total_rows = 0
    failed_files = []
    
    for file_path in tqdm(parquet_files, desc="Processing files"):
        file_name = os.path.basename(file_path)
        output_path = os.path.join(output_dir, file_name)
        
        stats = process_parquet_file(file_path, output_path, calculator, text_column)
        
        if stats.get("success", False):
            total_files += 1
            total_rows += stats.get("rows_processed", 0)
        else:
            failed_files.append(file_path)
            
    # Return summary statistics
    return {
        "files_processed": total_files,
        "rows_processed": total_rows,
        "failed_files": len(failed_files),
        "failed_file_paths": failed_files
    }

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Calculate sentiment scores in parquet files using FinBERT with GPU acceleration")
    
    parser.add_argument("input_path", help="Path to parquet file or directory containing parquet files")
    parser.add_argument("--output_path", help="Output path for updated files")
    parser.add_argument("--text_column", default="article_title", 
                      help="Column containing text for sentiment analysis")
    parser.add_argument("--model_dir", help="Directory containing model weights (will download if not specified)")
    parser.add_argument("--batch_size", type=int, default=32, help="Batch size for processing texts")
    parser.add_argument("--cpu", action="store_true", help="Force CPU usage even if GPU is available")
    
    args = parser.parse_args()
    
    # Check if input path exists
    if not os.path.exists(args.input_path):
        logger.error(f"Input path does not exist: {args.input_path}")
        return 1
    
    # Initialize calculator
    calculator = SentimentCalculator(use_gpu=not args.cpu, batch_size=args.batch_size)
    
    # Load the model
    model_loaded = calculator.load_model(args.model_dir)
    if not model_loaded:
        logger.error("Failed to load sentiment model")
        return 1
    
    # Process input
    if os.path.isfile(args.input_path) and args.input_path.endswith('.parquet'):
        # Process single file
        output_path = args.output_path
        if not output_path:
            base, ext = os.path.splitext(args.input_path)
            output_path = f"{base}_sentiment{ext}"
        
        stats = process_parquet_file(args.input_path, output_path, calculator, args.text_column)
        
        if not stats.get("success", False):
            logger.error(f"Failed to process file: {args.input_path}")
            if "error" in stats:
                logger.error(f"Error: {stats['error']}")
            return 1
            
        logger.info(f"Successfully processed {stats['rows_processed']} rows in file")
        
    elif os.path.isdir(args.input_path):
        # Process directory
        output_dir = args.output_path
        if not output_dir:
            parent_dir = os.path.dirname(args.input_path.rstrip('/'))
            dir_name = os.path.basename(args.input_path.rstrip('/'))
            output_dir = os.path.join(parent_dir, f"{dir_name}_sentiment")
        
        stats = process_directory(args.input_path, output_dir, calculator, args.text_column)
        
        if "error" in stats and stats.get("files_processed", 0) == 0:
            logger.error(f"Error processing directory: {stats['error']}")
            return 1
            
        logger.info(f"Processed {stats['files_processed']} files with {stats['rows_processed']} total rows")
        
        if stats.get('failed_files', 0) > 0:
            logger.warning(f"Failed to process {stats['failed_files']} files")
            for file_path in stats.get('failed_file_paths', []):
                logger.warning(f"  - {file_path}")
    else:
        logger.error(f"Input path is not a valid parquet file or directory: {args.input_path}")
        return 1
        
    logger.info("Processing completed successfully")
    return 0

if __name__ == "__main__":
    exit(main())