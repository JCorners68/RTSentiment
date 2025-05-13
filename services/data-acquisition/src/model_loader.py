#!/usr/bin/env python3
"""
Model Loader Module

This module provides safe loading of TensorFlow and TFLite models,
addressing common issues like the XNNPACK delegate dynamic tensor error.
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union, Tuple
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize module-level variables
tf = None
tflite_fix = None

# Try importing TensorFlow
try:
    import tensorflow as tf
    TENSORFLOW_AVAILABLE = True
    logger.debug("TensorFlow imported successfully")
    
    # Import our TFLite fix module
    try:
        from . import tflite_fix
    except ImportError:
        try:
            import tflite_fix
        except ImportError:
            logger.warning("TFLite fix module not found - XNNPACK delegate errors may occur")
except ImportError:
    TENSORFLOW_AVAILABLE = False
    logger.warning("TensorFlow not installed - model loading functionality will be limited")

def load_tflite_model(
    model_path: str,
    use_xnnpack: Optional[bool] = None,
    num_threads: int = 4
) -> Any:
    """
    Load a TensorFlow Lite model with appropriate handling for dynamic tensors.
    
    Args:
        model_path: Path to the TFLite model file
        use_xnnpack: Control XNNPACK delegate usage:
                    - None (default): Auto-detect based on model tensor shapes
                    - True: Force enable XNNPACK
                    - False: Force disable XNNPACK
        num_threads: Number of threads to use for inference
        
    Returns:
        TFLite Interpreter object or None if loading fails
    """
    if not TENSORFLOW_AVAILABLE:
        logger.error("Cannot load TFLite model: TensorFlow not installed")
        return None
        
    # Use tflite_fix if available
    if tflite_fix is not None:
        logger.info(f"Loading TFLite model with dynamic tensor fix: {model_path}")
        return tflite_fix.create_tflite_interpreter(
            model_path=model_path,
            use_xnnpack=use_xnnpack,
            num_threads=num_threads
        )
    
    # Fallback to standard loading logic with simple check for dynamic tensors
    try:
        logger.info(f"Loading TFLite model (standard method): {model_path}")
        
        # Try to determine if model has dynamic shapes
        if use_xnnpack is None:
            # Create a temp interpreter to check model properties
            temp_interpreter = tf.lite.Interpreter(model_path=model_path)
            temp_interpreter.allocate_tensors()
            
            # Check input shapes for dynamic dimensions
            has_dynamic = False
            for detail in temp_interpreter.get_input_details() + temp_interpreter.get_output_details():
                if -1 in detail['shape']:
                    has_dynamic = True
                    break
                    
            # Disable XNNPACK for dynamic tensor models
            if has_dynamic:
                use_xnnpack = False
                logger.warning("Detected dynamic tensors, disabling XNNPACK delegate")
            else:
                use_xnnpack = True
        
        # Create the actual interpreter
        if use_xnnpack:
            interpreter = tf.lite.Interpreter(
                model_path=model_path,
                num_threads=num_threads
            )
        else:
            # Create interpreter with explicit empty delegate list
            interpreter = tf.lite.Interpreter(
                model_path=model_path, 
                experimental_delegates=[],
                num_threads=num_threads
            )
            
        interpreter.allocate_tensors()
        return interpreter
        
    except Exception as e:
        logger.error(f"Error loading TFLite model: {str(e)}")
        return None

def load_tensorflow_model(model_path: str) -> Any:
    """
    Load a TensorFlow model (SavedModel or H5).
    
    Args:
        model_path: Path to the model directory (SavedModel) or file (H5)
        
    Returns:
        TensorFlow model object or None if loading fails
    """
    if not TENSORFLOW_AVAILABLE:
        logger.error("Cannot load TensorFlow model: TensorFlow not installed")
        return None
        
    try:
        logger.info(f"Loading TensorFlow model: {model_path}")
        
        # Handle different model types based on path
        if model_path.endswith('.h5') or model_path.endswith('.keras'):
            # Load Keras H5 model
            model = tf.keras.models.load_model(model_path)
            logger.info(f"Loaded Keras H5 model: {model_path}")
        else:
            # Assume SavedModel format
            model = tf.saved_model.load(model_path)
            logger.info(f"Loaded SavedModel: {model_path}")
            
        return model
        
    except Exception as e:
        logger.error(f"Error loading TensorFlow model: {str(e)}")
        return None

def load_model(model_path: str) -> Tuple[Any, str]:
    """
    Load a model of any supported type based on file extension.
    
    Args:
        model_path: Path to the model file or directory
        
    Returns:
        Tuple of (model_object, model_type) where:
            - model_object is the loaded model or None if loading failed
            - model_type is a string: 'tflite', 'tensorflow', or 'unknown'
    """
    if not os.path.exists(model_path):
        logger.error(f"Model path does not exist: {model_path}")
        return None, 'unknown'
        
    # Determine model type based on extension
    if model_path.endswith('.tflite'):
        model = load_tflite_model(model_path)
        return model, 'tflite'
    elif model_path.endswith('.h5') or model_path.endswith('.keras'):
        model = load_tensorflow_model(model_path)
        return model, 'tensorflow'
    elif os.path.isdir(model_path):
        # Check if it's a SavedModel directory
        if os.path.exists(os.path.join(model_path, 'saved_model.pb')):
            model = load_tensorflow_model(model_path)
            return model, 'tensorflow'
        else:
            logger.error(f"Unknown model format in directory: {model_path}")
            return None, 'unknown'
    else:
        logger.error(f"Unknown model format: {model_path}")
        return None, 'unknown'

def run_inference(
    model: Any,
    model_type: str,
    input_data: Union[np.ndarray, List[np.ndarray]]
) -> List[np.ndarray]:
    """
    Run inference on a model with the given input data.
    
    Args:
        model: The loaded model object
        model_type: The type of model ('tflite' or 'tensorflow')
        input_data: Input data as numpy array or list of numpy arrays
        
    Returns:
        List of numpy arrays containing the inference results
    """
    if not TENSORFLOW_AVAILABLE:
        logger.error("Cannot run inference: TensorFlow not installed")
        return []
        
    try:
        if model_type == 'tflite':
            # TFLite model
            if tflite_fix is not None:
                return tflite_fix.run_tflite_inference(model, input_data)
            else:
                # Handle TFLite inference manually
                input_details = model.get_input_details()
                output_details = model.get_output_details()
                
                # Convert single input to list
                if not isinstance(input_data, list):
                    input_data = [input_data]
                
                # Set input tensor values
                for i, data in enumerate(input_data):
                    if i < len(input_details):
                        model.set_tensor(input_details[i]['index'], data)
                
                # Run inference
                model.invoke()
                
                # Get outputs
                outputs = []
                for output_detail in output_details:
                    outputs.append(model.get_tensor(output_detail['index']))
                    
                return outputs
                
        elif model_type == 'tensorflow':
            # TensorFlow model
            if isinstance(input_data, list):
                # Multiple inputs
                result = model(input_data)
            else:
                # Single input
                result = model(input_data)
                
            # Convert result to list of numpy arrays
            if isinstance(result, dict):
                # Handle dictionary outputs
                return [result[key].numpy() for key in result]
            elif isinstance(result, list):
                # Handle list outputs
                return [r.numpy() for r in result]
            else:
                # Handle single tensor output
                return [result.numpy()]
        else:
            logger.error(f"Unknown model type for inference: {model_type}")
            return []
            
    except Exception as e:
        logger.error(f"Error running inference: {str(e)}")
        return []

# Test function
def test_model_loading(model_path: str) -> bool:
    """
    Test if a model can be loaded and used for a simple inference.
    
    Args:
        model_path: Path to the model file or directory
        
    Returns:
        bool: True if the model loads and runs successfully
    """
    # Load the model
    model, model_type = load_model(model_path)
    
    if model is None:
        logger.error(f"Failed to load model: {model_path}")
        return False
        
    logger.info(f"Successfully loaded model of type: {model_type}")
    
    try:
        # Create dummy input data
        if model_type == 'tflite':
            input_details = model.get_input_details()
            dummy_inputs = []
            
            for input_detail in input_details:
                shape = input_detail['shape']
                # Replace dynamic dimensions with a reasonable size
                shape = [10 if dim == -1 else dim for dim in shape]
                dtype = input_detail['dtype']
                
                # Create random data
                if np.issubdtype(dtype, np.floating):
                    dummy_input = np.random.rand(*shape).astype(dtype)
                else:
                    dummy_input = np.random.randint(0, 10, size=shape).astype(dtype)
                    
                dummy_inputs.append(dummy_input)
                
            # Run inference
            if len(dummy_inputs) == 1:
                outputs = run_inference(model, model_type, dummy_inputs[0])
            else:
                outputs = run_inference(model, model_type, dummy_inputs)
                
        else:  # tensorflow
            # Get model input shape - this is a simplification
            # In real usage, you'd need to know the model's input requirements
            dummy_input = np.random.rand(1, 224, 224, 3).astype(np.float32)
            outputs = run_inference(model, model_type, dummy_input)
            
        # Check outputs
        for i, output in enumerate(outputs):
            logger.info(f"Output {i}: shape={output.shape}, type={output.dtype}")
            
        logger.info("Model successfully loaded and tested")
        return True
        
    except Exception as e:
        logger.error(f"Error testing model: {str(e)}")
        return False

# Main execution
if __name__ == "__main__":
    import sys
    
    if not TENSORFLOW_AVAILABLE:
        print("TensorFlow is not installed. Please install TensorFlow:")
        print("pip install tensorflow")
        sys.exit(1)
        
    # Get model path from command line argument or use a default
    if len(sys.argv) > 1:
        test_model_path = sys.argv[1]
        
        # Test the model
        if test_model_loading(test_model_path):
            print(f"✅ Model successfully loaded and tested: {test_model_path}")
            sys.exit(0)
        else:
            print(f"❌ Failed to load or test model: {test_model_path}")
            sys.exit(1)
    else:
        print("No model path provided")
        print("Usage: python model_loader.py [path_to_model]")
        sys.exit(1)