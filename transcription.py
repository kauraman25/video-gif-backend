import os
import requests
import moviepy.editor as mp
from faster_whisper import WhisperModel
from typing import List, Dict, Any
import yt_dlp


class VideoDownloader:
    async def download_youtube(self, url: str, job_id: str) -> str:
        

        upload_dir = os.path.join("static", "uploads", job_id)
        os.makedirs(upload_dir, exist_ok=True)
        video_path = os.path.join(upload_dir, "input.mp4")

        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': video_path,
            'quiet': True,
            'no_warnings': True,
            'restrictfilenames': True,
            'noplaylist': True,
            'ignoreerrors': False,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if not os.path.exists(video_path) or os.path.getsize(video_path) == 0:
            raise Exception("Downloaded file is missing or empty")
        return video_path

    async def download_direct_mp4(self, url: str, job_id: str) -> str:
        upload_dir = os.path.join("static", "uploads", job_id)
        os.makedirs(upload_dir, exist_ok=True)
        video_path = os.path.join(upload_dir, "input.mp4")

        with requests.get(url, stream=True) as response:
            response.raise_for_status()
            with open(video_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

        if not os.path.exists(video_path) or os.path.getsize(video_path) == 0:
            raise Exception("Downloaded file is missing or empty")
        return video_path

class VideoTranscriber:
    def __init__(self):
        self.model = WhisperModel("base.en", device="cpu", compute_type="int8")

    async def transcribe_video(self, video_path: str) -> List[Dict[str, Any]]:
        video = mp.VideoFileClip(video_path)
        if video.audio is None:
            duration = video.duration
            segment_length = min(5.0, duration / 3)
            result = []
            current_time = 0
            segment_index = 1
            while current_time < duration:
                end_time = min(current_time + segment_length, duration)
                result.append({
                    "text": f"Segment {segment_index} (No audio)",
                    "start": current_time,
                    "end": end_time,
                    "words": []
                })
                current_time = end_time
                segment_index += 1
            return result

        audio_path = video_path.replace(".mp4", ".wav")
        video.audio.write_audiofile(audio_path, codec='pcm_s16le')

        segments, _ = self.model.transcribe(audio_path, word_timestamps=True)

        os.remove(audio_path)

        return [{
            "text": seg.text,
            "start": seg.start,
            "end": seg.end,
            "words": [{"word": w.word, "start": w.start, "end": w.end} for w in seg.words]
        } for seg in segments]

    async def analyze_transcript(self, transcript: List[Dict[str, Any]], prompt: str) -> List[Dict[str, Any]]:
        prompt_keywords = prompt.lower().split()
        scored_segments = []

        for segment in transcript:
            score = 0
            text = segment["text"].lower()
            for keyword in prompt_keywords:
                if keyword in text:
                    score += 5
            duration = segment["end"] - segment["start"]
            if 2 <= duration <= 7:
                score += 3
            if score > 0:
                scored_segments.append({"segment": segment, "score": score})

        scored_segments.sort(key=lambda x: x["score"], reverse=True)
        top_segments = [item["segment"] for item in scored_segments[:3]]

        if not top_segments and transcript:
            transcript.sort(key=lambda x: x["end"] - x["start"], reverse=True)
            top_segments = transcript[:min(3, len(transcript))]

        return top_segments
