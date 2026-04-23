from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pydantic import ValidationError
import subprocess
import psutil
import time
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

class RequestedProfile(BaseModel):
    resolution: str = "854:480"
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    ffmpeg_preset: str = "medium"
    crf: int = 23
    video_bitrate: str = "1000k"

default_profile = RequestedProfile(
    resolution="854:480",
    video_codec="libx264",
    audio_codec="aac",
    ffmpeg_preset="medium",
    crf=23,
    video_bitrate="1000k"
)

def transcode_video(
    input_path: str, 
    output_path: str,
    video_codec: str, 
    audio_codec: str, 
    ffmpeg_preset: str, 
    scale: str, 
    crf: int, 
    video_bitrate: str | None
) -> bool:
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel", "error",
            "-i", input_path,
            "-c:v", video_codec,
            "-c:a", audio_codec,
            "-preset", ffmpeg_preset,
            "-vf", f"scale={scale}",
            "-crf", str(crf),
        ]

        if video_bitrate:
            cmd.extend(["-b:v", video_bitrate])
        cmd.append(output_path)

        process = subprocess.Popen(cmd)
        ffmpeg_process = psutil.Process(process.pid)
        cpu_samples: list[float] = []
        memory_samples_mb: list[float] = []
        started_at = time.perf_counter()

        while process.poll() is None:
            cpu_samples.append(ffmpeg_process.cpu_percent(interval=0.2))
            try:
                memory_samples_mb.append(ffmpeg_process.memory_info().rss / (1024 * 1024))
            except psutil.Error:
                pass

        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, cmd)

        duration_s = time.perf_counter() - started_at
        avg_cpu = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0.0
        peak_cpu = max(cpu_samples) if cpu_samples else 0.0
        avg_mem = sum(memory_samples_mb) / len(memory_samples_mb) if memory_samples_mb else 0.0
        peak_mem = max(memory_samples_mb) if memory_samples_mb else 0.0

        print(
            "Transcode utilization - "
            f"duration={duration_s:.2f}s, "
            f"avg_cpu={avg_cpu:.1f}%, peak_cpu={peak_cpu:.1f}%, "
            f"avg_mem={avg_mem:.1f}MB, peak_mem={peak_mem:.1f}MB"
        )
        return True
    except subprocess.CalledProcessError:
        print(f"Error occurred while transcoding video: {input_path}")
        return False
    

@app.post("/transcode")
def transcode(
    file: UploadFile = File(...),
    request: str = Form(default_profile.model_dump_json())
):
    try:
        request_profile = RequestedProfile.model_validate_json(request)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    input_path = f"/tmp/{file.filename}"
    output_path = f"/tmp/transcoded_{file.filename}"
    with open(input_path, "wb") as f:
        f.write(file.file.read())
    success = transcode_video(
        input_path=input_path,
        output_path=output_path,
        video_codec=request_profile.video_codec,
        audio_codec=request_profile.audio_codec,
        ffmpeg_preset=request_profile.ffmpeg_preset,
        scale=request_profile.resolution,
        crf=request_profile.crf,
        video_bitrate=request_profile.video_bitrate
    )
    if success:
        return FileResponse(output_path, media_type="video/mp4", filename=f"transcoded_{file.filename}")
    else:
        return {"message": "Failed to transcode video"}, 500


@app.get("/trasncode/{filename}")
def get_transcoded_video(filename: str):
    output_path = f"/tmp/transcoded_{filename}"
    return FileResponse(output_path, media_type="video/mp4", filename=f"transcoded_{filename}")
