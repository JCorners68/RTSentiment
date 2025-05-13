import os
from PIL import Image, ImageDraw

# Activate virtual environment if needed
venv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'venv')
if os.path.exists(venv_path):
    # We're already in a venv, so we don't need to activate it
    pass

# Create directory if it doesn't exist
os.makedirs('/home/jonat/real_senti/ui/website/assets/images/logos', exist_ok=True)

# Create a 180x180 image with a blue background (standard size for apple-touch-icon)
img = Image.new('RGBA', (180, 180), (46, 91, 255, 255))  # #2E5BFF

# Create a draw object
draw = ImageDraw.Draw(img)

# Draw stylized chart lines (scaled up from favicon)
line_start_x = 30
line_start_y = 90
scale_factor = 5.5

line_points = [
    (line_start_x, line_start_y), 
    (line_start_x + int(4 * scale_factor), line_start_y - int(4 * scale_factor)), 
    (line_start_x + int(8 * scale_factor), line_start_y + int(4 * scale_factor)), 
    (line_start_x + int(12 * scale_factor), line_start_y - int(8 * scale_factor)), 
    (line_start_x + int(16 * scale_factor), line_start_y - int(2 * scale_factor)), 
    (line_start_x + int(20 * scale_factor), line_start_y - int(10 * scale_factor))
]

# Draw the main line
line_width = 8
for i in range(len(line_points) - 1):
    draw.line([line_points[i], line_points[i+1]], fill=(255, 255, 255), width=line_width)

# Draw dots at key points
dot_color = (140, 84, 255, 255)  # #8C54FF
dot_size = 10
for x, y in [line_points[1], line_points[3], line_points[5]]:
    draw.ellipse([(x-dot_size, y-dot_size), (x+dot_size, y+dot_size)], fill=dot_color)

# Draw arrow at the end
arrow_color = (0, 209, 178, 255)  # #00D1B2
arrow_size = 12
x, y = line_points[5]
draw.line([(x, y), (x+arrow_size, y-arrow_size)], fill=arrow_color, width=line_width)
draw.line([(x, y), (x+arrow_size, y+arrow_size)], fill=arrow_color, width=line_width)

# Save the image
img.save('/home/jonat/real_senti/ui/website/assets/images/logos/apple-touch-icon.png')

print("Apple touch icon created at: /home/jonat/real_senti/ui/website/assets/images/logos/apple-touch-icon.png")