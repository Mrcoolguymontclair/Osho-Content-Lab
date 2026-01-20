#!/usr/bin/env python3
"""
AI-POWERED THUMBNAIL GENERATOR
Creates eye-catching thumbnails with text overlays optimized for YouTube Shorts.
Uses PIL for text rendering and FFmpeg for video frame extraction.
"""

import os
import subprocess
import tempfile
from typing import Dict, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter


def extract_best_frame(video_path: str, output_path: str, timestamp: float = 2.0) -> bool:
    """
    Extract a high-quality frame from video at specified timestamp.

    Args:
        video_path: Input video file
        output_path: Where to save extracted frame
        timestamp: Time in seconds to extract frame (default 2.0 for after intro)

    Returns: True if successful
    """
    try:
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(timestamp),
            '-i', video_path,
            '-vframes', '1',
            '-vf', 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920',
            '-q:v', '2',  # High quality
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=10)
        return result.returncode == 0 and os.path.exists(output_path)

    except Exception as e:
        print(f"Frame extraction error: {e}")
        return False


def create_text_overlay_shorts(
    base_image_path: str,
    title: str,
    output_path: str,
    rank_number: Optional[int] = None
) -> bool:
    """
    Create YouTube Shorts thumbnail with bold text overlay.
    Optimized for 1080x1920 vertical format.

    Args:
        base_image_path: Background image (video frame)
        title: Video title text
        output_path: Where to save thumbnail
        rank_number: If ranking video, show rank number

    Returns: True if successful
    """
    try:
        # Open base image
        img = Image.open(base_image_path)

        # Ensure correct size
        img = img.resize((1080, 1920), Image.Resampling.LANCZOS)

        # Enhance image
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.2)  # Increase contrast by 20%

        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.3)  # Boost saturation by 30%

        # Apply slight blur to background (makes text pop)
        img = img.filter(ImageFilter.GaussianBlur(radius=1))

        # Create drawing context
        draw = ImageDraw.Draw(img)

        # Add dark gradient overlay for text readability
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)

        # Top gradient (for title)
        for i in range(600):
            alpha = int(180 * (600 - i) / 600)
            overlay_draw.rectangle([(0, i), (1080, i+1)], fill=(0, 0, 0, alpha))

        # Bottom gradient (for rank number if present)
        if rank_number:
            for i in range(400):
                y = 1920 - 400 + i
                alpha = int(180 * i / 400)
                overlay_draw.rectangle([(0, y), (1080, y+1)], fill=(0, 0, 0, alpha))

        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
        draw = ImageDraw.Draw(img)

        # Load fonts (try different locations)
        try:
            # Try system fonts
            title_font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 90)
            subtitle_font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 60)
            number_font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 200)
        except:
            try:
                title_font = ImageFont.truetype('/Library/Fonts/Arial Bold.ttf', 90)
                subtitle_font = ImageFont.truetype('/Library/Fonts/Arial Bold.ttf', 60)
                number_font = ImageFont.truetype('/Library/Fonts/Arial Bold.ttf', 200)
            except:
                # Fallback to default
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
                number_font = ImageFont.load_default()

        # Prepare title text (wrap if too long)
        title = title.upper()  # All caps for impact

        # Remove common prefixes for cleaner thumbnail
        for prefix in ['TOP 10 ', 'TOP 5 ', 'RANKING ', 'MOST ']:
            if title.startswith(prefix):
                title = title[len(prefix):]
                break

        # Wrap text to fit width
        words = title.split()
        lines = []
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=title_font)
            if bbox[2] - bbox[0] < 950:  # Max width 950px
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]

        if current_line:
            lines.append(' '.join(current_line))

        # Limit to 3 lines max
        if len(lines) > 3:
            lines = lines[:2]
            lines.append('...')

        # Draw title text with outline
        y_offset = 100
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=title_font)
            text_width = bbox[2] - bbox[0]
            x = (1080 - text_width) // 2  # Center

            # Draw outline (black stroke)
            for offset_x in [-3, -2, -1, 0, 1, 2, 3]:
                for offset_y in [-3, -2, -1, 0, 1, 2, 3]:
                    if offset_x != 0 or offset_y != 0:
                        draw.text((x + offset_x, y_offset + offset_y), line, font=title_font, fill=(0, 0, 0))

            # Draw main text (white or yellow)
            draw.text((x, y_offset), line, font=title_font, fill=(255, 255, 0))  # Yellow for high visibility

            y_offset += 100

        # Draw rank number if ranking video
        if rank_number:
            rank_text = f"#{rank_number}"
            bbox = draw.textbbox((0, 0), rank_text, font=number_font)
            text_width = bbox[2] - bbox[0]
            x = (1080 - text_width) // 2
            y = 1920 - 450

            # Outline
            for offset_x in [-5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5]:
                for offset_y in [-5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5]:
                    if offset_x != 0 or offset_y != 0:
                        draw.text((x + offset_x, y + offset_y), rank_text, font=number_font, fill=(0, 0, 0))

            # Main text (red for urgency)
            draw.text((x, y), rank_text, font=number_font, fill=(255, 50, 50))

        # Save
        img.save(output_path, 'JPEG', quality=95)
        return True

    except Exception as e:
        print(f"Thumbnail creation error: {e}")
        return False


def generate_ai_thumbnail(
    video_path: str,
    title: str,
    output_path: str,
    rank_number: Optional[int] = None,
    timestamp: float = 2.0
) -> Tuple[bool, str]:
    """
    Main function: Generate AI-optimized thumbnail from video.

    Args:
        video_path: Input video file
        title: Video title (will be overlaid)
        output_path: Where to save thumbnail
        rank_number: If ranking video, which rank to show
        timestamp: Which second of video to extract frame from

    Returns: (success, error_message)
    """
    try:
        # Create temp file for extracted frame
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            temp_frame = tmp.name

        # Step 1: Extract best frame
        if not extract_best_frame(video_path, temp_frame, timestamp):
            return False, "Failed to extract frame from video"

        # Step 2: Add text overlay
        if not create_text_overlay_shorts(temp_frame, title, output_path, rank_number):
            os.unlink(temp_frame)
            return False, "Failed to create text overlay"

        # Cleanup
        os.unlink(temp_frame)

        return True, ""

    except Exception as e:
        return False, f"Thumbnail generation failed: {str(e)}"


# Example usage and testing
if __name__ == "__main__":
    print("AI Thumbnail Generator - Test Mode\n")

    # Test with a sample video (if exists)
    test_video = "output/test_video.mp4"
    test_title = "Most Amazing Natural Wonders on Earth"
    test_output = "output/test_thumbnail.jpg"

    if os.path.exists(test_video):
        print(f"Generating thumbnail for: {test_title}")
        success, error = generate_ai_thumbnail(
            video_path=test_video,
            title=test_title,
            output_path=test_output,
            rank_number=1,
            timestamp=2.0
        )

        if success:
            print(f"[OK] Thumbnail generated: {test_output}")
        else:
            print(f"[ERROR] Error: {error}")
    else:
        print(f"[WARNING] Test video not found: {test_video}")
        print("\nTo test, provide a video file path:")
        print("python3 thumbnail_ai.py")
