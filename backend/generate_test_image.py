from PIL import Image, ImageDraw, ImageFont
import random

# Create a white/grayish "paper" background
width, height = 800, 1000
img = Image.new('RGB', (width, height), color=(240, 240, 235))
draw = ImageDraw.Draw(img)

# The text with ALJI triggers (Mumbai, Maharashtra, 5 months deposit)
contract_text = """
GOVERNMENT OF MAHARASHTRA
STAMP DUTY PAID: Rs. 500

LEAVE AND LICENSE AGREEMENT

This Agreement is made at Mumbai, Maharashtra 
on this 24th of March, 2026.

BETWEEN: 
Mr. Ramesh (Landlord) 
AND 
Mr. Suresh (Tenant)

TERMS:
1. The Tenant shall pay a monthly rent of Rs. 20,000.
2. The Tenant agrees to pay a security deposit of 
   Rs. 1,00,000 (which is equal to 5 months rent).
3. The Landlord can evict the tenant with 15 days notice.
4. Jurisdiction: Courts of Mumbai.
"""

# Try to load a default font, otherwise use PIL's basic font
try:
    # Windows default font path
    font = ImageFont.truetype("arial.ttf", 24)
except IOError:
    font = ImageFont.load_default()

# Draw the text onto the image
draw.text((50, 50), contract_text, fill=(30, 30, 30), font=font)

# Add some "scanner noise" (random dark pixels) to make it look like a real scan
for _ in range(5000):
    x = random.randint(0, width - 1)
    y = random.randint(0, height - 1)
    draw.point((x, y), fill=(100, 100, 100))

# Apply a slight rotation to simulate a poorly scanned photo
img = img.rotate(1.5, fillcolor=(255, 255, 255))

# Save the final image
img.save("test_scan_maharashtra.jpg", "JPEG", quality=85)
print("✅ Created test_scan_maharashtra.jpg!")