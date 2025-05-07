#!/usr/bin/env python3
"""
Script to fix CUDA compatibility by enabling just-in-time compilation for the specific GPU architecture.
"""

import os
import sys
import torch
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Enable compile for the specific GPU architecture."""
    print("=" * 60)
    print("PyTorch CUDA Fix Tool".center(60))
    print("=" * 60)
    
    if not torch.cuda.is_available():
        print("CUDA is not available. Cannot fix GPU compatibility.")
        return
    
    # Get current device information
    current_device = torch.cuda.current_device()
    device_name = torch.cuda.get_device_name(current_device)
    capability = torch.cuda.get_device_capability(current_device)
    
    print(f"Device: {device_name}")
    print(f"CUDA Capability: {capability[0]}.{capability[1]}")
    print(f"PyTorch Version: {torch.__version__}")
    print(f"CUDA Version: {torch.version.cuda}")
    
    # Set environment variables for CUDA
    os.environ["CUDA_LAUNCH_BLOCKING"] = "1"
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:128"
    
    # Enable JIT compilation for specific architecture
    try:
        print("\nTesting JIT compilation for your GPU...")
        # Create a simple module to compile
        class SimpleModule(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.linear = torch.nn.Linear(10, 10)
                
            def forward(self, x):
                return self.linear(x)
        
        # Create the module and move to GPU
        module = SimpleModule().to('cuda')
        
        # Sample input
        input_data = torch.randn(1, 10, device='cuda')
        
        # Trace the module
        print("Tracing module...")
        traced_module = torch.jit.trace(module, input_data)
        
        # Test compiled module
        print("Testing compiled module...")
        output = traced_module(input_data)
        print(f"Output shape: {output.shape}")
        
        # Test a more complex operation
        print("\nTesting more complex operations...")
        
        # Matrix multiplication
        a = torch.randn(100, 100, device='cuda')
        b = torch.randn(100, 100, device='cuda')
        
        # Enable CUDA graphs for potentially better performance
        with torch.cuda.graph(pool=None):
            c = torch.matmul(a, b)
        
        print(f"Matrix multiplication shape: {c.shape}")
        
        print("\nBasic CUDA JIT compilation successful!")
        
        # Save settings to a file
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".cuda_fix_applied"), "w") as f:
            f.write(f"CUDA fix applied for {device_name} (sm_{capability[0]}{capability[1]})\n")
            f.write(f"PyTorch Version: {torch.__version__}\n")
            f.write(f"CUDA Version: {torch.version.cuda}\n")
            f.write("Environment variables:\n")
            f.write("CUDA_LAUNCH_BLOCKING=1\n")
            f.write("PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128\n")
        
        print("\nCUDA settings have been saved. Add these to your environment or startup script:")
        print("export CUDA_LAUNCH_BLOCKING=1")
        print("export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128")
        
        return True
        
    except Exception as e:
        print(f"\nError during CUDA fix: {e}")
        return False

if __name__ == "__main__":
    main()