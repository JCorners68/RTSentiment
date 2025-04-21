#!/bin/bash
set -e

# Path to models
PYTORCH_MODEL_DIR="/app/models/weights/pytorch"
ONNX_MODEL_DIR="/app/models/weights/onnx"

# Check if PyTorch model exists
if [ ! -f "$PYTORCH_MODEL_DIR/config.json" ]; then
    echo "PyTorch model not found, downloading..."
    
    # Create directories if they don't exist
    mkdir -p $PYTORCH_MODEL_DIR
    mkdir -p $ONNX_MODEL_DIR
    
    # Download FinBERT model
    python3 -c "
from transformers import AutoModelForSequenceClassification, AutoTokenizer

print('Downloading FinBERT model...')
model_name = 'ProsusAI/finbert'
model = AutoModelForSequenceClassification.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

print('Saving model to $PYTORCH_MODEL_DIR...')
model.save_pretrained('$PYTORCH_MODEL_DIR')
tokenizer.save_pretrained('$PYTORCH_MODEL_DIR')
print('Model downloaded successfully')
"
    # Create ONNX model if PyTorch model exists and ONNX model doesn't
    if [ -f "$PYTORCH_MODEL_DIR/config.json" ] && [ ! -f "$ONNX_MODEL_DIR/finbert-sentiment.onnx" ]; then
        echo "Creating ONNX model..."
        python3 -c "
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# Load model and tokenizer
model = AutoModelForSequenceClassification.from_pretrained('$PYTORCH_MODEL_DIR')
tokenizer = AutoTokenizer.from_pretrained('$PYTORCH_MODEL_DIR')

# Create dummy input
dummy_input = tokenizer(
    'This is a test sentence for ONNX export',
    return_tensors='pt'
)

# Export to ONNX
with torch.no_grad():
    torch.onnx.export(
        model,
        (dummy_input['input_ids'], dummy_input['attention_mask']),
        '$ONNX_MODEL_DIR/finbert-sentiment.onnx',
        opset_version=13,
        input_names=['input_ids', 'attention_mask'],
        output_names=['logits'],
        dynamic_axes={
            'input_ids': {0: 'batch_size', 1: 'sequence_length'},
            'attention_mask': {0: 'batch_size', 1: 'sequence_length'},
            'logits': {0: 'batch_size'}
        }
    )
print('ONNX model created successfully')
"
    fi
else
    echo "Models already exist, skipping download"
fi

echo "Model setup complete"