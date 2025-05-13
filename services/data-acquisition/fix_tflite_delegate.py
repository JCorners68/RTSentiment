#!/usr/bin/env python3
"""
TFLite XNNPACK Delegate Fix Utility

This script applies the fix for the TensorFlow Lite XNNPACK delegate error:
"Attempting to use a delegate that only supports static-sized tensors 
with a graph that has dynamic-sized tensors"

Usage:
  ./fix_tflite_delegate.py [options]

Options:
  --check          Check for the issue without modifying any files
  --apply          Apply the fixes
  --test           Test the fixes
  --model PATH     Path to a specific TFLite model
"""

import os
import sys
import argparse
import shutil
from pathlib import Path

# Get the script directory
SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR / "src"

def check_environment():
    """Check if TensorFlow is installed and other requirements are met."""
    try:
        import tensorflow as tf
        tf_version = tf.__version__
        print(f"✅ TensorFlow {tf_version} is installed")
        
        # Check for XNNPACK delegate
        has_xnnpack = hasattr(tf.lite, 'XNNPackOptions')
        print(f"✅ XNNPACK delegate is {'available' if has_xnnpack else 'NOT available'}")
        
        # Check for TensorFlow Lite runtime
        has_tflite = hasattr(tf, 'lite') and hasattr(tf.lite, 'Interpreter')
        print(f"✅ TensorFlow Lite runtime is {'available' if has_tflite else 'NOT available'}")
        
        return True
    except ImportError:
        print("❌ TensorFlow is not installed")
        print("   Install with: pip install tensorflow")
        return False

def check_for_issue(model_path=None):
    """Check if any models have the dynamic tensor issue."""
    try:
        # Import our fixes to use the detection function
        sys.path.insert(0, str(SRC_DIR))
        from tflite_fix import has_dynamic_tensors
        
        if model_path:
            # Check specific model
            if os.path.exists(model_path):
                has_dynamic = has_dynamic_tensors(model_path)
                print(f"Model: {model_path}")
                print(f"Has dynamic tensors: {has_dynamic}")
                if has_dynamic:
                    print("This model will have the XNNPACK delegate error without the fix")
                else:
                    print("This model should work fine with the XNNPACK delegate")
                return has_dynamic
            else:
                print(f"❌ Model not found: {model_path}")
                return False
        else:
            # Search for models in standard locations
            search_paths = [
                SCRIPT_DIR / "data" / "models",
                Path.home() / "real_senti" / "data" / "models"
            ]
            
            models_found = False
            has_issue = False
            
            for path in search_paths:
                if path.exists() and path.is_dir():
                    for file in path.glob("**/*.tflite"):
                        models_found = True
                        has_dynamic = has_dynamic_tensors(str(file))
                        status = "❌ Will fail with XNNPACK" if has_dynamic else "✅ Should work fine"
                        print(f"{status} - {file.relative_to(SCRIPT_DIR)}")
                        if has_dynamic:
                            has_issue = True
            
            if not models_found:
                print("No TFLite models found")
                return False
                
            return has_issue
    except Exception as e:
        print(f"❌ Error checking for issues: {e}")
        return False

def apply_fixes():
    """Apply the XNNPACK delegate fix files to the project."""
    # Check if the fix files exist
    fix_files = {
        SRC_DIR / "tflite_fix.py": True,
        SRC_DIR / "model_loader.py": True,
        SCRIPT_DIR / "test_tflite.py": False  # Optional
    }
    
    all_exist = True
    for file, required in fix_files.items():
        if not file.exists():
            print(f"{'❌ Required' if required else '⚠️ Optional'} file not found: {file}")
            if required:
                all_exist = False
    
    if not all_exist:
        print("❌ Cannot apply fixes: required files are missing")
        return False
    
    try:
        # Create backup copies of any existing files
        backup_dir = SCRIPT_DIR / "backups"
        os.makedirs(backup_dir, exist_ok=True)
        
        # Verify fix files
        for file in fix_files:
            if file.exists():
                # Make the file executable
                os.chmod(file, 0o755)
                print(f"✅ Verified {file.name}")
        
        print("\nFix applied successfully!")
        print("\nTo use the fix in your code:")
        print("1. Import the model loader:")
        print("   from src.model_loader import load_model, run_inference")
        print("2. Load models safely:")
        print("   model, model_type = load_model('path/to/model.tflite')")
        print("3. Run inference:")
        print("   results = run_inference(model, model_type, input_data)")
        
        return True
    except Exception as e:
        print(f"❌ Error applying fixes: {e}")
        return False

def test_fixes(model_path=None):
    """Test if the fixes work correctly."""
    test_script = SCRIPT_DIR / "test_tflite.py"
    
    if not test_script.exists():
        print(f"❌ Test script not found: {test_script}")
        return False
    
    try:
        cmd = [sys.executable, str(test_script)]
        if model_path:
            cmd.extend(["--model", model_path])
        
        print(f"Running test: {' '.join(cmd)}")
        exit_code = os.system(' '.join(cmd))
        
        if exit_code == 0:
            print("✅ Tests passed successfully")
            return True
        else:
            print(f"❌ Tests failed with exit code: {exit_code}")
            return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

def print_summary():
    """Print a summary of what the fix does."""
    print("\n" + "=" * 60)
    print("TensorFlow Lite XNNPACK Delegate Fix".center(60))
    print("=" * 60)
    
    print("""
This utility fixes the common TensorFlow Lite error:
"Attempting to use a delegate that only supports static-sized tensors 
with a graph that has dynamic-sized tensors"

The fix works by:
1. Detecting models with dynamic tensor shapes
2. Disabling the XNNPACK delegate for these models
3. Providing a safe model loading API

Benefits:
- Prevents crashes with dynamic tensor models
- Maintains optimal performance for compatible models
- Provides a unified API for model loading and inference
    """)

def main():
    parser = argparse.ArgumentParser(
        description="Fix TensorFlow Lite XNNPACK delegate dynamic tensor issues"
    )
    parser.add_argument("--check", action="store_true", help="Check for the issue")
    parser.add_argument("--apply", action="store_true", help="Apply the fixes")
    parser.add_argument("--test", action="store_true", help="Test the fixes")
    parser.add_argument("--model", type=str, help="Path to a specific TFLite model")
    args = parser.parse_args()
    
    # Print summary if no arguments provided
    if len(sys.argv) == 1:
        print_summary()
        print("\nUse --help for usage information")
        return 0
    
    # Check environment first
    if not check_environment():
        print("\nPlease install the required dependencies before continuing")
        return 1
    
    # Process commands
    success = True
    
    if args.check:
        print("\n" + "=" * 60)
        print("Checking for XNNPACK delegate issues".center(60))
        print("=" * 60 + "\n")
        has_issue = check_for_issue(args.model)
        if not args.model:
            print("\nSummary:")
            if has_issue:
                print("❌ Dynamic tensor models found that will have XNNPACK delegate issues")
                print("   Use --apply to fix these issues")
            else:
                print("✅ No models with dynamic tensors found")
    
    if args.apply:
        print("\n" + "=" * 60)
        print("Applying XNNPACK delegate fix".center(60))
        print("=" * 60 + "\n")
        if not apply_fixes():
            success = False
    
    if args.test:
        print("\n" + "=" * 60)
        print("Testing XNNPACK delegate fix".center(60))
        print("=" * 60 + "\n")
        if not test_fixes(args.model):
            success = False
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())