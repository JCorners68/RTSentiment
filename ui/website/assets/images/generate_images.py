#!/usr/bin/env python3
"""
Image Generation Script for Sentimark Website

This script reads the image requirements from the JSON file and uses OpenAI's DALL-E
to generate and save the images according to the specifications.

Usage:
    python generate_images.py --api-key YOUR_API_KEY [--image-id ID] [--all]

    --api-key: Your OpenAI API key (required)
    --image-id: ID of specific image to generate (optional)
    --all: Generate all images (optional, default is False)

Example:
    python generate_images.py --api-key sk-xxxx --image-id hero_dashboard
    python generate_images.py --api-key sk-xxxx --all
"""

import os
import json
import argparse
import time
import requests
from io import BytesIO
from PIL import Image
import logging
from pathlib import Path
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("image_generation.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Constants
REQUIREMENTS_FILE = "image_requirements.json"
OPENAI_API_URL = "https://api.openai.com/v1/images/generations"
DALLE_MODEL = "dall-e-3"  # Use dall-e-3 for highest quality images

def setup_argparse():
    """Set up command line argument parsing."""
    parser = argparse.ArgumentParser(description="Generate images for Sentimark website using DALL-E")
    parser.add_argument("--api-key", required=True, help="Your OpenAI API key")
    parser.add_argument("--image-id", help="ID of specific image to generate")
    parser.add_argument("--all", action="store_true", help="Generate all images")
    return parser.parse_args()

def load_image_requirements():
    """Load image requirements from JSON file."""
    try:
        with open(REQUIREMENTS_FILE, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error loading requirements file: {e}")
        sys.exit(1)

def create_output_directory(path):
    """Create output directory if it doesn't exist."""
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created directory: {directory}")

def generate_image_with_dalle(prompt, api_key, width, height):
    """Generate image using DALL-E API."""
    # Determine the best aspect ratio for DALL-E 3
    # DALL-E 3 supports square (1:1), portrait (2:3), or landscape (3:2)
    aspect_ratio = width / height
    
    if 0.8 <= aspect_ratio <= 1.2:  # Close to square
        size = "1024x1024"
    elif aspect_ratio < 0.8:  # Portrait
        size = "1024x1792"
    else:  # Landscape
        size = "1792x1024"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = {
        "model": DALLE_MODEL,
        "prompt": prompt,
        "size": size,
        "quality": "hd",
        "n": 1,
    }
    
    logger.info(f"Requesting image generation for size {size}")
    
    try:
        response = requests.post(OPENAI_API_URL, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        image_url = result['data'][0]['url']
        
        # Download the generated image
        image_response = requests.get(image_url)
        image_response.raise_for_status()
        
        # Return the image data
        return BytesIO(image_response.content)
    
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response: {e.response.text}")
        return None

def resize_and_save_image(image_data, output_path, target_width, target_height):
    """Resize the generated image to the target dimensions and save it."""
    try:
        img = Image.open(image_data)
        
        # Resize while maintaining aspect ratio
        img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        # Create directory if it doesn't exist
        create_output_directory(output_path)
        
        # Save the image
        if output_path.lower().endswith('.png'):
            img.save(output_path, 'PNG', optimize=True)
        elif output_path.lower().endswith('.jpg') or output_path.lower().endswith('.jpeg'):
            img.save(output_path, 'JPEG', quality=90, optimize=True)
        elif output_path.lower().endswith('.webp'):
            img.save(output_path, 'WEBP', quality=90)
        else:
            # Default to PNG
            output_path = f"{os.path.splitext(output_path)[0]}.png"
            img.save(output_path, 'PNG', optimize=True)
        
        logger.info(f"Image saved to {output_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        return False

def generate_single_image(image_spec, base_path, api_key):
    """Generate a single image based on its specification."""
    image_id = image_spec["id"]
    logger.info(f"Generating image: {image_id}")
    
    # Skip SVG logo generation as DALL-E cannot generate vector graphics
    if image_spec["format"] == "SVG":
        logger.info(f"Skipping SVG generation for {image_id} - DALL-E cannot generate vector graphics")
        return False
    
    # Get image properties
    prompt = image_spec["dalle_prompt"]
    width = image_spec["dimensions"]["width"]
    height = image_spec["dimensions"]["height"]
    
    # Determine the output path
    rel_path = image_spec["replacement_path"].lstrip('/')
    output_path = os.path.join(base_path, rel_path)
    
    # Generate the image
    logger.info(f"Requesting DALL-E to generate: {image_id}")
    image_data = generate_image_with_dalle(prompt, api_key, width, height)
    
    if image_data:
        # Resize and save the image
        success = resize_and_save_image(image_data, output_path, width, height)
        
        if success:
            logger.info(f"Successfully generated {image_id} at {output_path}")
            return True
    
    logger.error(f"Failed to generate {image_id}")
    return False

def main():
    """Main function to generate images based on command line arguments."""
    args = setup_argparse()
    api_key = args.api_key
    
    # Validate API key format
    if not api_key.startswith("sk-"):
        logger.error("Invalid API key format. OpenAI API keys typically start with 'sk-'")
        sys.exit(1)
    
    # Load image requirements
    requirements = load_image_requirements()
    image_specs = requirements["website_images"]
    
    # Determine the base path (script directory)
    base_path = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.dirname(base_path)  # Go up one level to assets
    base_path = os.path.dirname(base_path)  # Go up one level to website
    
    # Track success and failure
    successes = 0
    failures = 0
    
    if args.image_id:
        # Generate specific image
        image_spec = next((img for img in image_specs if img["id"] == args.image_id), None)
        
        if not image_spec:
            logger.error(f"Image ID '{args.image_id}' not found in requirements")
            sys.exit(1)
        
        if generate_single_image(image_spec, base_path, api_key):
            successes += 1
        else:
            failures += 1
    
    elif args.all:
        # Generate all images
        for image_spec in image_specs:
            # Add a delay between API calls to avoid rate limiting
            if successes + failures > 0:
                logger.info("Waiting 2 seconds before next request...")
                time.sleep(2)
                
            if generate_single_image(image_spec, base_path, api_key):
                successes += 1
            else:
                failures += 1
    
    else:
        logger.error("Please specify either --image-id or --all")
        sys.exit(1)
    
    # Report results
    logger.info(f"Image generation complete. Successes: {successes}, Failures: {failures}")

if __name__ == "__main__":
    main()