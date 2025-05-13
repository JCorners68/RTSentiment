#!/usr/bin/env python3
"""
TensorFlow Lite XNNPACK Delegate Fix for Dynamic Tensors

This module provides a solution to fix the common error:
"Attempting to use a delegate that only supports static-sized tensors 
with a graph that has dynamic-sized tensors"

The fix works by:
1. Configuring the TFLite interpreter to avoid using XNNPACK delegate when dynamic tensors are detected
2. Providing utility functions to safely load and run TFLite models
"""

import os
import logging
import numpy as np
from typing import Optional, List, Dict, Any, Union, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Try importing TensorFlow Lite - handle missing dependency gracefully
try:
    import tensorflow as tf
    TFLITE_AVAILABLE = True
except ImportError:
    logger.warning("TensorFlow not installed. TFLite functionality will not be available.")
    TFLITE_AVAILABLE = False

def has_dynamic_tensors(model_path: str) -> bool:
    """
    Check if a TFLite model contains any dynamic-sized tensors.
    
    Args:
        model_path: Path to the TFLite model file
        
    Returns:
        bool: True if the model has dynamic tensors, False otherwise
    """
    if not TFLITE_AVAILABLE:
        logger.error("Cannot check for dynamic tensors: TensorFlow not installed")
        return True  # Assume dynamic tensors to be safe
        
    try:
        # Load model without any delegates
        interpreter = tf.lite.Interpreter(model_path=model_path)
        interpreter.allocate_tensors()
        
        # Get input and output details
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()
        
        # Check if any input or output tensor has dynamic shape
        for tensor_details in input_details + output_details:
            # Check if any dimension is -1 (dynamic)
            if -1 in tensor_details['shape']:
                return True
                
        return False
    except Exception as e:
        logger.error(f"Error checking for dynamic tensors: {e}")
        return True  # Assume dynamic tensors to be safe

def create_tflite_interpreter(
    model_path: str, 
    use_xnnpack: Optional[bool] = None,
    num_threads: int = 4
) -> Any:
    """
    Create a TFLite interpreter with appropriate delegate settings.
    
    Args:
        model_path: Path to the TFLite model file
        use_xnnpack: Override XNNPACK usage:
                    - None (default): Auto-detect based on dynamic tensors
                    - True: Force enable XNNPACK
                    - False: Force disable XNNPACK
        num_threads: Number of threads to use for inference
        
    Returns:
        TFLite Interpreter object or None if creation fails
    """
    if not TFLITE_AVAILABLE:
        logger.error("Cannot create interpreter: TensorFlow not installed")
        return None
        
    try:
        # Check for dynamic tensors if auto-detection is enabled
        if use_xnnpack is None:
            has_dynamic = has_dynamic_tensors(model_path)
            use_xnnpack = not has_dynamic
            if has_dynamic:
                logger.info("Detected dynamic tensors in model, disabling XNNPACK delegate")
            else:
                logger.info("No dynamic tensors detected, enabling XNNPACK delegate")
        
        # Set up interpreter options
        options = tf.lite.Interpreter.get_options()
        options["num_threads"] = num_threads
        
        if use_xnnpack:
            # Create XNNPACK delegate options
            xnnpack_opts = tf.lite.XNNPackOptions()
            xnnpack_opts.num_threads = num_threads
            
            # Create interpreter with XNNPACK delegate
            interpreter = tf.lite.Interpreter(
                model_path=model_path,
                experimental_delegates=[tf.lite.load_delegate('libxnnpack.so', xnnpack_opts)],
                num_threads=num_threads
            )
            logger.info("Created TFLite interpreter with XNNPACK delegate")
        else:
            # Create interpreter without delegates
            interpreter = tf.lite.Interpreter(
                model_path=model_path,
                num_threads=num_threads
            )
            logger.info("Created TFLite interpreter without XNNPACK delegate")
            
        # Allocate tensors
        interpreter.allocate_tensors()
        return interpreter
        
    except Exception as e:
        logger.error(f"Error creating TFLite interpreter: {e}")
        return None

def run_tflite_inference(
    interpreter: Any, 
    input_data: Union[np.ndarray, List[np.ndarray]]
) -> List[np.ndarray]:
    """
    Run inference using a TFLite interpreter.
    
    Args:
        interpreter: A TFLite interpreter object
        input_data: Input data as numpy array or list of numpy arrays
                   (multiple inputs)
                   
    Returns:
        List of numpy arrays containing the inference results
    """
    if not TFLITE_AVAILABLE:
        logger.error("Cannot run inference: TensorFlow not installed")
        return []
        
    try:
        # Get input details
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()
        
        # Prepare inputs
        if not isinstance(input_data, list):
            input_data = [input_data]  # Convert single input to list
            
        # Set input tensor values
        for i, data in enumerate(input_data):
            if i < len(input_details):
                # Reshape input if needed
                required_shape = input_details[i]['shape']
                if data.shape != tuple(required_shape) and -1 not in required_shape:
                    # Only reshape if the shape is static and different
                    data = np.reshape(data, required_shape)
                
                interpreter.set_tensor(input_details[i]['index'], data)
            else:
                logger.warning(f"More input arrays provided than model inputs. Ignoring extra inputs.")
                break
                
        # Run inference
        interpreter.invoke()
        
        # Get outputs
        outputs = []
        for output_detail in output_details:
            tensor = interpreter.get_tensor(output_detail['index'])
            outputs.append(tensor)
            
        return outputs
        
    except Exception as e:
        logger.error(f"Error running TFLite inference: {e}")
        return []

def load_and_run_tflite_model(
    model_path: str,
    input_data: Union[np.ndarray, List[np.ndarray]],
    use_xnnpack: Optional[bool] = None,
    num_threads: int = 4
) -> List[np.ndarray]:
    """
    Convenience function to load a TFLite model and run inference in one step.
    
    Args:
        model_path: Path to the TFLite model file
        input_data: Input data as numpy array or list of numpy arrays
        use_xnnpack: Whether to use XNNPACK delegate
                    - None (default): Auto-detect based on dynamic tensors
                    - True: Force enable XNNPACK
                    - False: Force disable XNNPACK
        num_threads: Number of threads to use for inference
        
    Returns:
        List of numpy arrays containing the inference results
    """
    if not TFLITE_AVAILABLE:
        logger.error("Cannot load and run model: TensorFlow not installed")
        return []
        
    # Create interpreter
    interpreter = create_tflite_interpreter(
        model_path=model_path,
        use_xnnpack=use_xnnpack,
        num_threads=num_threads
    )
    
    if interpreter is None:
        return []
        
    # Run inference
    return run_tflite_inference(interpreter, input_data)

# Simple test function
def test_tflite_fix(model_path: str) -> bool:
    """
    Test the TFLite fix with a specified model.
    
    Args:
        model_path: Path to a TFLite model to test
        
    Returns:
        bool: True if test succeeds, False otherwise
    """
    if not TFLITE_AVAILABLE:
        logger.error("Cannot test TFLite fix: TensorFlow not installed")
        return False
        
    if not os.path.exists(model_path):
        logger.error(f"Model file not found: {model_path}")
        return False
        
    try:
        logger.info(f"Testing TFLite fix with model: {model_path}")
        
        # Check if model has dynamic tensors
        has_dynamic = has_dynamic_tensors(model_path)
        logger.info(f"Model has dynamic tensors: {has_dynamic}")
        
        # Create interpreter with auto-detection (should work with both dynamic and static models)
        interpreter = create_tflite_interpreter(model_path)
        
        if interpreter is None:
            logger.error("Failed to create interpreter")
            return False
            
        # Get model input details to create dummy input
        input_details = interpreter.get_input_details()
        
        for i, input_detail in enumerate(input_details):
            logger.info(f"Input {i}: shape={input_detail['shape']}, type={input_detail['dtype'].__name__}")
            
        # Create dummy input data matching the required shape
        dummy_inputs = []
        for input_detail in input_details:
            shape = input_detail['shape']
            # Replace dynamic dimensions with a reasonable size
            shape = [10 if dim == -1 else dim for dim in shape] 
            dtype = input_detail['dtype']
            
            # Create random data of the right shape and type
            if np.issubdtype(dtype, np.floating):
                dummy_input = np.random.rand(*shape).astype(dtype)
            else:
                dummy_input = np.random.randint(0, 10, size=shape).astype(dtype)
                
            dummy_inputs.append(dummy_input)
            
        # Run inference
        logger.info("Running inference with dummy input")
        if len(dummy_inputs) == 1:
            outputs = run_tflite_inference(interpreter, dummy_inputs[0])
        else:
            outputs = run_tflite_inference(interpreter, dummy_inputs)
            
        # Output results
        for i, output in enumerate(outputs):
            logger.info(f"Output {i}: shape={output.shape}, type={output.dtype}")
            
        logger.info("TFLite fix test successful")
        return True
            
    except Exception as e:
        logger.error(f"Error testing TFLite fix: {e}")
        return False
        
# Main execution    
if __name__ == "__main__":
    import sys
    
    # Check if TensorFlow is available
    if not TFLITE_AVAILABLE:
        print("TensorFlow is not installed. Please install TensorFlow:")
        print("pip install tensorflow")
        sys.exit(1)
        
    # Get model path from command line argument or use a default
    if len(sys.argv) > 1:
        test_model_path = sys.argv[1]
    else:
        # Try to find a model in the data directory
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "models")
        tflite_models = [f for f in os.listdir(data_dir) if f.endswith(".tflite")] if os.path.exists(data_dir) else []
        
        if tflite_models:
            test_model_path = os.path.join(data_dir, tflite_models[0])
            print(f"Using found model: {test_model_path}")
        else:
            print("No model path provided and no .tflite models found in data/models/")
            print("Usage: python tflite_fix.py [path_to_model.tflite]")
            sys.exit(1)
            
    # Run the test
    success = test_tflite_fix(test_model_path)
    sys.exit(0 if success else 1)