import os
import shutil
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uuid
import uvicorn

from gif_generator import GIF_Generator
from transcription import VideoTranscriber, VideoDownloader

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Video to GIF Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(os.path.join("static", "uploads"), exist_ok=True)
os.makedirs(os.path.join("static", "gifs"), exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

gifgenerators = GIF_Generator()
videotranscriber = VideoTranscriber()
videodownloader = VideoDownloader()

class VideoURL(BaseModel):
    url: str
    prompt: str
    is_direct_mp4: bool 



@app.post("/youtube")
async def youtubeProcess(data: VideoURL):
    try:
        job_id = str(uuid.uuid4())

        if data.is_direct_mp4:
            video_path = await videodownloader.download_direct_mp4(data.url, job_id)
        else:
            video_path = await videodownloader.download_youtube(data.url, job_id)

        transcript = await videotranscriber.transcribe_video(video_path)
        key_segments = await videotranscriber.analyze_transcript(transcript, data.prompt)

        output_dir = os.path.join("static", "gifs", job_id)
        os.makedirs(output_dir, exist_ok=True)

        gif_paths = []
        for i, segment in enumerate(key_segments, start=1):  
            gif_path = await gifgenerators.create_gif_with_captions(video_path, segment, output_dir, i)
            relative_path = gif_path.replace("\\", "/")
            relative_path = "/" + relative_path.replace("static/", "static/")
            gif_paths.append(relative_path)

        return {"status": "success", "gifs": gif_paths, "job_id": job_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GIF is not generate: {str(e)}")

@app.post("/upload")
async def uploadProcess(prompt: str = Form(...), video: UploadFile = File(...)):
    try:
        if not video.content_type.startswith("video/"):
            raise HTTPException(status_code=400, detail="Uploaded file is not a video")

        job_id = str(uuid.uuid4())
        upload_dir = os.path.join("static", "uploads", job_id)
        os.makedirs(upload_dir, exist_ok=True)

        video_path = os.path.join(upload_dir, "input.mp4")
        with open(video_path, "wb") as buffer:
            shutil.copyfileobj(video.file, buffer)

        transcript = await videotranscriber.transcribe_video(video_path)
        key_segments = await videotranscriber.analyze_transcript(transcript, prompt)

        output_dir = os.path.join("static", "gifs", job_id)
        os.makedirs(output_dir, exist_ok=True)

        gif_paths = []
        for i, segment in enumerate(key_segments, start=1):  
            gif_path = await gifgenerators.create_gif_with_captions(video_path, segment, output_dir, i)
            relative_path = gif_path.replace("\\", "/")
            relative_path = "/" + relative_path.replace("static/", "static/")
            gif_paths.append(relative_path)

        return {"status": "success", "gifs": gif_paths, "job_id": job_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GIF is not generate: {str(e)}")

@app.get("/download/{job_id}/{gif_index}")
async def download_gif(job_id: str, gif_index: int):
    try:
        gif_path = os.path.join("static", "gifs", job_id, f"gif_{gif_index}.gif")
        if not os.path.exists(gif_path):
            raise HTTPException(status_code=404, detail="GIF not found")

        return FileResponse(
            path=gif_path,
            filename=f"gif_{gif_index}.gif",
            media_type="image/gif"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)