#!/bin/bash
# Script to resize feature icons properly

set -e

# Create a virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
fi

# Activate the virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install required packages
echo "Installing dependencies..."
pip install pillow

# Create a Python script for resizing
cat > resize_script.py << 'EOF'
#!/usr/bin/env python3
"""
Resize feature icons to have proper dimensions while preserving aspect ratio.
"""

import os
from pathlib import Path
import sys
import shutil
import tempfile

# Directory containing feature icons
FEATURES_DIR = Path("/home/jonat/real_senti/ui/website/assets/images/features")
TARGET_SIZE = (240, 240)  # Target size for all feature icons

def resize_icons():
    """Resize all icons in the features directory to the target size."""
    # Import PIL
    from PIL import Image

    # Create a temporary directory for backup
    backup_dir = Path(tempfile.mkdtemp(prefix="feature_icons_backup_"))
    print(f"Backing up original icons to {backup_dir}")

    for icon_path in FEATURES_DIR.glob("*.png"):
        # Create backup
        backup_path = backup_dir / icon_path.name
        shutil.copy(str(icon_path), str(backup_path))
        
        # Open and resize the image
        try:
            img = Image.open(icon_path)
            original_size = img.size
            print(f"Processing {icon_path.name}: Original size {original_size}")
            
            # Create a new image with the target size and transparent background
            new_img = Image.new("RGBA", TARGET_SIZE, (0, 0, 0, 0))
            
            # Calculate the scaling factor to fit in the target size while preserving aspect ratio
            width_ratio = TARGET_SIZE[0] / original_size[0]
            height_ratio = TARGET_SIZE[1] / original_size[1]
            scale_factor = min(width_ratio, height_ratio)
            
            # Calculate the new size
            new_width = int(original_size[0] * scale_factor)
            new_height = int(original_size[1] * scale_factor)
            
            # Resize the image preserving aspect ratio
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Calculate position to paste the resized image (center it)
            paste_x = (TARGET_SIZE[0] - new_width) // 2
            paste_y = (TARGET_SIZE[1] - new_height) // 2
            
            # Paste the resized image onto the new image
            if resized_img.mode == "RGBA":
                new_img.paste(resized_img, (paste_x, paste_y), resized_img)
            else:
                new_img.paste(resized_img, (paste_x, paste_y))
            
            # Save the result
            new_img.save(icon_path, "PNG")
            print(f"Resized {icon_path.name} to {new_width}x{new_height} and padded to {TARGET_SIZE[0]}x{TARGET_SIZE[1]}")
            
        except Exception as e:
            print(f"Error processing {icon_path.name}: {e}")
            # Restore from backup if there was an error
            shutil.copy(str(backup_path), str(icon_path))
            print(f"Restored {icon_path.name} from backup")

def main():
    """Main function."""
    print("Starting feature icon resize process")
    
    # Resize icons
    resize_icons()
    
    print("Icon resize process complete")

if __name__ == "__main__":
    main()
EOF

# Run the Python script
echo "Running resize script..."
python resize_script.py

# Deactivate the virtual environment
echo "Deactivating virtual environment..."
deactivate

echo "Image fixing process complete!"