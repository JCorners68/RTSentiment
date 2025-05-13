import os
from PIL import Image, ImageDraw

# Create directory if it doesn't exist
os.makedirs('/home/jonat/real_senti/ui/website/assets/images/logos', exist_ok=True)

# Create a 32x32 image with a blue background
img = Image.new('RGBA', (32, 32), (46, 91, 255, 255))  # #2E5BFF

# Create a draw object
draw = ImageDraw.Draw(img)

# Draw rounded corners (approximate)
draw.rectangle([(0, 0), (3, 3)], fill=(0, 0, 0, 0))
draw.rectangle([(28, 0), (31, 3)], fill=(0, 0, 0, 0))
draw.rectangle([(0, 28), (3, 31)], fill=(0, 0, 0, 0))
draw.rectangle([(28, 28), (31, 31)], fill=(0, 0, 0, 0))

# Draw a stylized chart line (simplified from the SVG)
line_points = [(5, 17), (9, 13), (13, 21), (17, 9), (21, 15), (25, 7)]
for i in range(len(line_points) - 1):
    draw.line([line_points[i], line_points[i+1]], fill=(255, 255, 255), width=2)

# Save the image
img.save('/home/jonat/real_senti/ui/website/assets/images/logos/favicon.png')

print("Favicon created at: /home/jonat/real_senti/ui/website/assets/images/logos/favicon.png")