#!/usr/bin/env python3
"""
Case Study Image Generation Script for Sentimark Website

This script generates PNG case study images for the Sentimark website.
"""

import os
import json
import argparse
import requests
from PIL import Image
from io import BytesIO
import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("case_study_generation.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Constants
REQUIREMENTS_FILE = "case_studies_requirements.json"
OPENAI_API_URL = "https://api.openai.com/v1/images/generations"
DALLE_MODEL = "dall-e-3"  # Use dall-e-3 for highest quality images
OUTPUT_DIR = "case-studies"

def setup_argparse():
    """Set up command line argument parsing."""
    parser = argparse.ArgumentParser(description="Generate case study images for Sentimark website using DALL-E")
    parser.add_argument("--api-key", required=True, help="Your OpenAI API key")
    parser.add_argument("--image-id", help="ID of specific image to generate")
    parser.add_argument("--all", action="store_true", help="Generate all images")
    parser.add_argument("--status", choices=['todo', 'done'], help="Filter by status")
    return parser.parse_args()

def load_image_requirements():
    """Load image requirements from JSON file."""
    try:
        with open(REQUIREMENTS_FILE, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error loading requirements file: {e}")
        sys.exit(1)

def create_output_directory():
    """Create output directory if it doesn't exist."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        logger.info(f"Created directory: {OUTPUT_DIR}")

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

def resize_and_save_image(image_data, output_filename, target_width, target_height):
    """Resize the generated image to the target dimensions and save it."""
    try:
        img = Image.open(image_data)
        
        # Resize while maintaining aspect ratio
        img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        # Save the image
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        img.save(output_path, 'PNG', optimize=True)
        
        logger.info(f"Image saved to {output_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        return False

def update_image_status(image_id, new_status='done'):
    """Update the status of an image in the requirements file."""
    try:
        with open(REQUIREMENTS_FILE, 'r') as file:
            data = json.load(file)

        # Find and update the status of the specified image
        for image in data["case_study_images"]:
            if image["id"] == image_id:
                image["status"] = new_status
                logger.info(f"Updated status of {image_id} to '{new_status}'")
                break

        # Write the updated data back to the file
        with open(REQUIREMENTS_FILE, 'w') as file:
            json.dump(data, file, indent=2)

    except Exception as e:
        logger.error(f"Error updating image status: {e}")

def generate_single_image(image_spec, api_key):
    """Generate a single image based on its specification."""
    image_id = image_spec["id"]
    logger.info(f"Generating image: {image_id}")

    # Get image properties
    prompt = image_spec["dalle_prompt"]
    width = image_spec["dimensions"]["width"]
    height = image_spec["dimensions"]["height"]

    # Generate the image
    logger.info(f"Requesting DALL-E to generate: {image_id}")
    image_data = generate_image_with_dalle(prompt, api_key, width, height)

    if image_data:
        # Resize and save the image
        success = resize_and_save_image(image_data, f"{image_id}.png", width, height)

        if success:
            logger.info(f"Successfully generated {image_id}")
            # Update the status in the requirements file
            update_image_status(image_id, 'done')
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
    image_specs = requirements["case_study_images"]
    
    # Create output directory
    create_output_directory()
    
    # Track success and failure
    successes = 0
    failures = 0

    # Filter the images based on arguments
    filtered_specs = []

    if args.image_id:
        # Filter by image ID
        filtered_specs = [img for img in image_specs if img["id"] == args.image_id]
        if not filtered_specs:
            logger.error(f"Image ID '{args.image_id}' not found in requirements")
            sys.exit(1)
    elif args.status:
        # Filter by status
        filtered_specs = [img for img in image_specs if img.get("status") == args.status]
        if not filtered_specs:
            logger.info(f"No images with status '{args.status}' found")
            sys.exit(0)
    elif args.all:
        # Generate all images
        filtered_specs = image_specs
    else:
        logger.error("Please specify either --image-id, --status, or --all")
        sys.exit(1)

    # Generate the filtered images
    for i, image_spec in enumerate(filtered_specs):
        # Add a delay between API calls to avoid rate limiting
        if i > 0:
            logger.info("Waiting 2 seconds before next request...")
            import time
            time.sleep(2)

        if generate_single_image(image_spec, api_key):
            successes += 1
        else:
            failures += 1
    
    # Report results
    logger.info(f"Image generation complete. Successes: {successes}, Failures: {failures}")

if __name__ == "__main__":
    main()