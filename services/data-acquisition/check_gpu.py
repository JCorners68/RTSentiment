#!/usr/bin/env python3
"""
Check GPU usage for FinBERT
"""

import os
import sys
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import sentiment_analyzer
from src.sentiment_analyzer import initialize_model, check_cuda_compatibility

def main():
    print("\n=== GPU/CUDA Status ===")
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        print(f"CUDA version: {torch.version.cuda}")
        print(f"Device count: {torch.cuda.device_count()}")
        
        for i in range(torch.cuda.device_count()):
            print(f"Device {i}: {torch.cuda.get_device_name(i)}")
            print(f"  Capability: {torch.cuda.get_device_capability(i)}")
    
    print("\n=== FinBERT Compatibility Check ===")
    compatible, reason = check_cuda_compatibility()
    print(f"GPU compatible: {compatible}")
    print(f"Reason: {reason}")
    
    print("\n=== Current Environment Setting ===")
    use_cuda = os.environ.get("USE_CUDA", "auto").lower()
    print(f"USE_CUDA setting: {use_cuda}")
    
    print("\nTo force CPU usage: export USE_CUDA=no")
    print("To force GPU usage: export USE_CUDA=yes")
    print("For automatic selection: export USE_CUDA=auto (default)")

if __name__ == "__main__":
    main()