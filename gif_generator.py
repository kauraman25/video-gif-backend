import os
import moviepy.editor as mp
from PIL import Image, ImageFont, ImageDraw
import numpy as np

class GIF_Generator:
    def add_caption_to_frame(self, frame: np.ndarray, text: str) -> np.ndarray:
        img = Image.fromarray(frame).convert("RGBA")
        draw = ImageDraw.Draw(img)
    
        try:
            font = ImageFont.truetype("Arial.ttf", 80)  # Better readability
        except IOError:
            font = ImageFont.load_default()
    
        max_chars = 20
        lines = []
        words = text.split()
        current_line = ""
        for word in words:
            if len(current_line + " " + word) <= max_chars:
                current_line += " " + word if current_line else word
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        text = "\n".join(lines)
    
        width, height = img.size
        text_size = draw.multiline_textbbox((0, 0), text, font=font)
        text_width = text_size[2] - text_size[0]
        text_height = text_size[3] - text_size[1]
    
        x = (width - text_width) // 2
        y = height - text_height - 100
    
        
        draw = ImageDraw.Draw(img)
        draw.multiline_text((x, y), text, font=font, fill="yellow", align="center")
    
        return np.array(img.convert("RGB"))


    async def create_gif_with_captions(self, video_path: str, segment: dict, output_path: str, gif_index: int) -> str:
        start_time = max(0, segment["start"] - 0.5)
        video_duration = mp.VideoFileClip(video_path).duration
        end_time = min(segment["end"] + 0.5, video_duration)

        video = mp.VideoFileClip(video_path).subclip(start_time, end_time)
        captioned_clip = video.fl_image(lambda img: self.add_caption_to_frame(img, segment["text"]))

        gif_path = os.path.join(output_path, f"gif_{gif_index}.gif")
        captioned_clip.resize(width=540).write_gif(
            gif_path,
            fps=14,
            program='ffmpeg',
            opt='optimizeplus',
            fuzz=10
        )
        return gif_path