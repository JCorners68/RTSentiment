#!/usr/bin/env python3
"""
Test Script for TensorFlow Lite XNNPACK Fix

This script verifies that our fix for the XNNPACK delegate with dynamic tensors works correctly.
It attempts to load and run inference on a TensorFlow Lite model both with and without our fix.
"""

import os
import sys
import time
import argparse
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Add the src directory to path
current_dir = Path(__file__).resolve().parent
src_dir = current_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Try importing our fixes
try:
    from src import tflite_fix
    from src import model_loader
    fixes_available = True
except ImportError:
    logger.warning("Could not import fix modules. Make sure they're in the src directory.")
    fixes_available = False

# Try importing TensorFlow
try:
    import tensorflow as tf
    import numpy as np
    tf_available = True
except ImportError:
    logger.warning("TensorFlow not installed. Please install with: pip install tensorflow")
    tf_available = False

def find_tflite_models(search_dir=None):
    """Find TFLite model files in the project."""
    if search_dir is None:
        # Look in standard locations
        search_paths = [
            Path(current_dir) / "data" / "models",
            Path(current_dir).parent / "data" / "models",
            Path.home() / "real_senti" / "data" / "models"
        ]
    else:
        search_paths = [Path(search_dir)]
    
    models = []
    for path in search_paths:
        if path.exists() and path.is_dir():
            for file in path.glob("**/*.tflite"):
                models.append(str(file))
    
    return models

def test_standard_loading(model_path):
    """
    Test loading a TFLite model with standard TensorFlow Lite API.
    This might fail with dynamic tensor models when XNNPACK is used.
    """
    if not tf_available:
        return False, "TensorFlow not available"
    
    try:
        logger.info(f"Testing standard loading for: {model_path}")
        
        # Standard loading - might trigger the XNNPACK delegate error with dynamic tensors
        start_time = time.time()
        interpreter = tf.lite.Interpreter(model_path=model_path)
        interpreter.allocate_tensors()
        load_time = time.time() - start_time
        
        # Get model details
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()
        
        # Create dummy input
        input_shape = input_details[0]['shape']
        input_dtype = input_details[0]['dtype']
        
        # Replace any dynamic dimensions (-1) with a fixed size
        input_shape = [10 if dim == -1 else dim for dim in input_shape]
        
        # Create appropriate random data
        if input_dtype == np.float32:
            dummy_input = np.random.rand(*input_shape).astype(input_dtype)
        else:
            dummy_input = np.random.randint(0, 10, size=input_shape).astype(input_dtype)
        
        # Run inference
        start_time = time.time()
        interpreter.set_tensor(input_details[0]['index'], dummy_input)
        interpreter.invoke()
        output = interpreter.get_tensor(output_details[0]['index'])
        inference_time = time.time() - start_time
        
        return True, {
            "load_time": load_time,
            "inference_time": inference_time, 
            "input_shape": input_shape,
            "output_shape": output.shape
        }
    
    except Exception as e:
        return False, str(e)

def test_fix_loading(model_path):
    """Test loading a TFLite model with our fix that handles dynamic tensors properly."""
    if not fixes_available:
        return False, "Fix modules not available"
    
    try:
        logger.info(f"Testing fixed loading for: {model_path}")
        
        # Test if model has dynamic tensors
        has_dynamic = tflite_fix.has_dynamic_tensors(model_path)
        
        # Load with our fixed loader
        start_time = time.time()
        model, model_type = model_loader.load_model(model_path)
        if model is None:
            return False, "Failed to load model"
        load_time = time.time() - start_time
        
        # Create input data
        if model_type == 'tflite':
            input_details = model.get_input_details()
            input_shape = input_details[0]['shape']
            input_dtype = input_details[0]['dtype']
            
            # Replace any dynamic dimensions (-1) with a fixed size
            input_shape = [10 if dim == -1 else dim for dim in input_shape]
            
            # Create appropriate random data
            if np.issubdtype(input_dtype, np.floating):
                dummy_input = np.random.rand(*input_shape).astype(input_dtype)
            else:
                dummy_input = np.random.randint(0, 10, size=input_shape).astype(input_dtype)
        else:
            return False, f"Unexpected model type: {model_type}"
        
        # Run inference
        start_time = time.time()
        outputs = model_loader.run_inference(model, model_type, dummy_input)
        inference_time = time.time() - start_time
        
        if not outputs:
            return False, "No outputs returned from inference"
            
        return True, {
            "has_dynamic_tensors": has_dynamic,
            "load_time": load_time,
            "inference_time": inference_time,
            "input_shape": input_shape,
            "output_shape": outputs[0].shape
        }
        
    except Exception as e:
        return False, str(e)

def test_full_model(model_path):
    """Run both standard and fixed loading tests and compare results."""
    print(f"\n{'=' * 60}")
    print(f"Testing model: {os.path.basename(model_path)}")
    print(f"{'=' * 60}")
    
    # Run standard loading test
    print("\nStandard TFLite loading test:")
    standard_success, standard_result = test_standard_loading(model_path)
    if standard_success:
        print(f"✅ Standard loading SUCCESSFUL")
        print(f"   Load time: {standard_result['load_time']:.4f}s")
        print(f"   Inference time: {standard_result['inference_time']:.4f}s")
        print(f"   Input shape: {standard_result['input_shape']}")
        print(f"   Output shape: {standard_result['output_shape']}")
    else:
        print(f"❌ Standard loading FAILED: {standard_result}")
    
    # Run fixed loading test
    print("\nFixed TFLite loading test:")
    fixed_success, fixed_result = test_fix_loading(model_path)
    if fixed_success:
        print(f"✅ Fixed loading SUCCESSFUL")
        print(f"   Has dynamic tensors: {fixed_result['has_dynamic_tensors']}")
        print(f"   Load time: {fixed_result['load_time']:.4f}s")
        print(f"   Inference time: {fixed_result['inference_time']:.4f}s")
        print(f"   Input shape: {fixed_result['input_shape']}")
        print(f"   Output shape: {fixed_result['output_shape']}")
    else:
        print(f"❌ Fixed loading FAILED: {fixed_result}")
    
    # Compare results
    print("\nResults comparison:")
    if standard_success and fixed_success:
        print("✅ Both loading methods successful")
        
        # Compare output shapes
        std_shape = standard_result['output_shape'] 
        fix_shape = fixed_result['output_shape']
        shapes_match = (std_shape == fix_shape)
        print(f"   Output shapes match: {shapes_match}")
        
        # Compare performance
        std_time = standard_result['inference_time']
        fix_time = fixed_result['inference_time']
        speedup = (std_time / fix_time) if fix_time > 0 else 0
        print(f"   Standard inference time: {std_time:.4f}s")
        print(f"   Fixed inference time: {fix_time:.4f}s")
        print(f"   Speedup factor: {speedup:.2f}x")
    elif not standard_success and fixed_success:
        print("✅ Fixed loading succeeded where standard loading failed")
        print("   This indicates our fix is working correctly for models with dynamic tensors")
    elif standard_success and not fixed_success:
        print("❓ Standard loading succeeded but fixed loading failed")
        print("   This is unexpected and indicates a problem with our fix")
    else:
        print("❌ Both loading methods failed")
        print("   This indicates a fundamental problem with the model")
    
    return fixed_success

def main():
    parser = argparse.ArgumentParser(description="Test TensorFlow Lite XNNPACK delegate fix")
    parser.add_argument("--model", type=str, help="Path to a specific TFLite model file")
    parser.add_argument("--dir", type=str, help="Directory to search for TFLite models")
    parser.add_argument("--all", action="store_true", help="Test all found models")
    args = parser.parse_args()
    
    if not tf_available:
        print("TensorFlow is not installed. Please install with: pip install tensorflow")
        return 1
    
    if not fixes_available:
        print("Fix modules not found. Make sure tflite_fix.py and model_loader.py are in the src directory.")
        return 1
    
    # Find models to test
    if args.model:
        # Test specific model
        models = [args.model]
    else:
        # Find models
        models = find_tflite_models(args.dir)
        if not models:
            print("No TFLite models found.")
            print("Please provide a model path with --model or a search directory with --dir")
            return 1
    
    # Test models
    success_count = 0
    print(f"Found {len(models)} TFLite model(s) to test")
    
    if args.all:
        # Test all models
        for model in models:
            if test_full_model(model):
                success_count += 1
    else:
        # Test only the first model
        if models:
            if test_full_model(models[0]):
                success_count += 1
    
    # Print summary
    print(f"\n{'=' * 60}")
    print(f"Summary: {success_count}/{len(models) if args.all else 1} tests passed")
    print(f"{'=' * 60}")
    
    # Return success if all tested models work with our fix
    return 0 if success_count == (len(models) if args.all else 1) else 1

if __name__ == "__main__":
    sys.exit(main())