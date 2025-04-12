#!/usr/bin/env python3
"""
Script to create sample corrupt images for documentation purposes.
"""

from PIL import Image
import numpy as np
import os
import random

# Directory to save sample images
SAMPLES_DIR = "docs/samples"
os.makedirs(SAMPLES_DIR, exist_ok=True)

# Image size for samples
WIDTH, HEIGHT = 600, 400

def create_blank_image(width, height, color=(255, 255, 255)):
    """Create a blank image with the given color."""
    return Image.new('RGB', (width, height), color)

def save_image(img, filename, quality=95):
    """Save an image with the given filename."""
    filepath = os.path.join(SAMPLES_DIR, filename)
    img.save(filepath, quality=quality)
    print(f"Created {filepath}")
    return filepath

# 1. Create a sample image with a large gray block (simulating corruption)
def create_gray_block_corruption():
    img = create_blank_image(WIDTH, HEIGHT)
    # Draw a mountain landscape
    draw_array = np.array(img)
    
    # Sky gradient (blue to light blue)
    for y in range(HEIGHT):
        blue_val = int(180 + (75 * y / HEIGHT))
        draw_array[y, :] = [135, 206, blue_val]
    
    # Mountains
    mountain_height = HEIGHT * 0.6
    for x in range(WIDTH):
        mountain_y = int(mountain_height + np.sin(x/50) * 40)
        draw_array[mountain_y:, x] = [100, 120, 80]  # Green mountains
    
    # Now add corruption - a large gray block
    corrupt_height = int(HEIGHT * 0.4)
    corrupt_width = int(WIDTH * 0.7)
    start_x = int((WIDTH - corrupt_width) / 2)
    start_y = int((HEIGHT - corrupt_height) / 2)
    
    draw_array[start_y:start_y+corrupt_height, start_x:start_x+corrupt_width] = [120, 120, 120]
    
    img = Image.fromarray(draw_array.astype('uint8'))
    return save_image(img, "gray_block_corruption.jpg")

# 2. Create a sample image with black block corruption
def create_black_block_corruption():
    img = create_blank_image(WIDTH, HEIGHT)
    # Draw a beach scene
    draw_array = np.array(img)
    
    # Sky
    draw_array[:int(HEIGHT*0.5), :] = [135, 206, 235]  # Sky blue
    
    # Sea
    draw_array[int(HEIGHT*0.5):int(HEIGHT*0.7), :] = [65, 105, 225]  # Royal blue
    
    # Beach
    draw_array[int(HEIGHT*0.7):, :] = [238, 214, 175]  # Sandy color
    
    # Now add corruption - a large black block on the right side
    corrupt_height = HEIGHT
    corrupt_width = int(WIDTH * 0.4)
    start_x = WIDTH - corrupt_width
    
    draw_array[:, start_x:] = [0, 0, 0]  # Black block
    
    img = Image.fromarray(draw_array.astype('uint8'))
    return save_image(img, "black_block_corruption.jpg")

# 3. Create a sample image with partial corruption (bottom third missing)
def create_partial_corruption():
    img = create_blank_image(WIDTH, HEIGHT)
    draw_array = np.array(img)
    
    # Draw a simple garden
    # Sky
    draw_array[:int(HEIGHT*0.6), :] = [135, 206, 235]  # Sky blue
    
    # Grass
    draw_array[int(HEIGHT*0.6):, :] = [34, 139, 34]  # Forest green
    
    # Sun
    sun_center = (100, 100)
    sun_radius = 50
    for y in range(max(0, sun_center[1]-sun_radius), min(HEIGHT, sun_center[1]+sun_radius)):
        for x in range(max(0, sun_center[0]-sun_radius), min(WIDTH, sun_center[0]+sun_radius)):
            if ((x - sun_center[0])**2 + (y - sun_center[1])**2) <= sun_radius**2:
                draw_array[y, x] = [255, 255, 0]  # Yellow
    
    # Corrupt the bottom third
    corrupt_height = int(HEIGHT * 0.33)
    draw_array[HEIGHT-corrupt_height:, :] = [120, 120, 120]  # Gray block
    
    img = Image.fromarray(draw_array.astype('uint8'))
    return save_image(img, "partial_corruption.jpg")

# 4. Create a sample image with random noise corruption
def create_noise_corruption():
    img = create_blank_image(WIDTH, HEIGHT)
    draw_array = np.array(img)
    
    # Draw a simple landscape
    # Sky
    draw_array[:int(HEIGHT*0.5), :] = [100, 150, 255]  # Light blue
    
    # Hills
    draw_array[int(HEIGHT*0.5):, :] = [50, 120, 50]  # Green
    
    # Add noise to the right side
    for y in range(HEIGHT):
        for x in range(int(WIDTH * 0.6), WIDTH):
            if random.random() < 0.5:  # 50% chance for each pixel
                # Random color noise
                draw_array[y, x] = [
                    random.randint(0, 255),
                    random.randint(0, 255),
                    random.randint(0, 255)
                ]
    
    img = Image.fromarray(draw_array.astype('uint8'))
    return save_image(img, "noise_corruption.jpg")

# 5. Create a sample image with a random band of corruption
def create_band_corruption():
    img = create_blank_image(WIDTH, HEIGHT)
    draw_array = np.array(img)
    
    # Draw a simple mountain lake
    # Sky
    draw_array[:int(HEIGHT*0.3), :] = [135, 206, 235]  # Sky blue
    
    # Mountains
    for x in range(WIDTH):
        mountain_height = int(HEIGHT * 0.3 + np.sin(x/40) * 20 + np.sin(x/20) * 10)
        draw_array[int(HEIGHT*0.3):mountain_height, x] = [100, 100, 100]  # Gray mountains
    
    # Lake
    draw_array[int(HEIGHT*0.5):, :] = [65, 105, 225]  # Royal blue
    
    # Add a horizontal band of corruption
    band_height = 30
    band_start = int(HEIGHT * 0.4)
    
    for y in range(band_start, band_start + band_height):
        for x in range(WIDTH):
            if x % 4 == 0:  # Create a pattern
                draw_array[y, x] = [255, 0, 0]  # Red
            elif x % 4 == 1:
                draw_array[y, x] = [0, 255, 0]  # Green
            elif x % 4 == 2:
                draw_array[y, x] = [0, 0, 255]  # Blue
            else:
                draw_array[y, x] = [0, 0, 0]  # Black
    
    img = Image.fromarray(draw_array.astype('uint8'))
    return save_image(img, "band_corruption.jpg")

# 6. Create a perfect, uncorrupted image
def create_perfect_image():
    img = create_blank_image(WIDTH, HEIGHT)
    draw_array = np.array(img)
    
    # Draw a nice sunset scene
    # Sky gradient (blue to orange)
    for y in range(HEIGHT):
        if y < HEIGHT * 0.6:
            # Calculate gradient from blue to orange
            ratio = y / (HEIGHT * 0.6)
            r = int(135 * (1 - ratio) + 255 * ratio)
            g = int(206 * (1 - ratio) + 165 * ratio)
            b = int(235 * (1 - ratio) + 0 * ratio)
            draw_array[y, :] = [r, g, b]
        else:
            # Ocean
            draw_array[y, :] = [65, 105, 225]  # Royal blue
    
    # Sun
    sun_center = (WIDTH // 2, int(HEIGHT * 0.4))
    sun_radius = 50
    for y in range(max(0, sun_center[1]-sun_radius), min(HEIGHT, sun_center[1]+sun_radius)):
        for x in range(max(0, sun_center[0]-sun_radius), min(WIDTH, sun_center[0]+sun_radius)):
            if ((x - sun_center[0])**2 + (y - sun_center[1])**2) <= sun_radius**2:
                draw_array[y, x] = [255, 255, 200]  # Bright sun
    
    img = Image.fromarray(draw_array.astype('uint8'))
    return save_image(img, "perfect_image.jpg")

# Create all sample images
create_gray_block_corruption()
create_black_block_corruption() 
create_partial_corruption()
create_noise_corruption()
create_band_corruption()
create_perfect_image()

print("All sample images created successfully!")