import os
from typing import List, Optional
from fastapi import APIRouter, Cookie, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ConfigDict, BaseModel, Field
from pydantic.functional_validators import BeforeValidator
from typing_extensions import Annotated

from bson import ObjectId
import motor.motor_asyncio
from pymongo import ReturnDocument, errors
from pathlib import Path
import uuid

router = APIRouter()
templates = Jinja2Templates(directory="templates")

client = motor.motor_asyncio.AsyncIOMotorClient("127.0.0.1:27017")
db = client.train

user_collection = db.get_collection("users")


async def get_videos():
    videos = []
    vid_dir = os.path.join("./", "vids")
    for vid in os.scandir(vid_dir):
       if vid.is_file():
        videos.append(vid.name)
    return videos

@router.get("/video/{id}", response_description="Get a specific video file.", response_class=FileResponse)
def stream_video(id: str):
  return os.path.join("./vids/", id)

@router.get("/v/vid/{id}", response_description="Get a video to view.", response_class=HTMLResponse)
async def get_video(request: Request, id: str, user: Annotated[str | None, Cookie()] = None):
    context = {"request": request, "id": id}
    user = await user_collection.find_one({"user_name": user})
    if user is not None:
        if id in user["content_assigned"]:
            context = {"request": request, "id": id, 'user': user}
            return templates.TemplateResponse("video.html", context)
        else:
            raise HTTPException(403, "Not assigned content.")
    else:
        raise HTTPException(403, "Not allowed to view resource.")

@router.post("/upload_quiz", response_description="Upload a quiz file.", status_code=status.HTTP_202_ACCEPTED)
async def upload_quiz(quiz: UploadFile):
    file_content = await quiz.read()

    quiz_file = open(f"{quiz.filename}", "w")
    quiz_file.write(file_content.decode("utf-8"))

    return {"filename": quiz.filename, "contents": file_content}

@router.post("/upload_video", response_description="Upload a video", status_code=status.HTTP_202_ACCEPTED)
async def upload_video(video: UploadFile):
    file_content = await video.read()

    print(video.file)
    video_file = open(f"{video.filename}", "w+b")
    video_file.write(file_content)

    return {"filename": video.filename, "contents": file_content}

@router.post("/upload_qv", response_description="Upload quiz and video file.", status_code=status.HTTP_202_ACCEPTED)
async def upload_video_and_quiz(files: list[UploadFile]):
    if len(files) == 2:
        id = str(uuid.uuid4())
        path = Path(f"./vids/{id}")
        path.mkdir(parents=True, exist_ok=True)
        for file in files:
            if ".mp4" in file.filename:
                file_content = await file.read()
                video_file = open(f"{path}/{file.filename}", "w+b")
                video_file.write(file_content)
            elif ".txt" in file.filename:
                file_content = await file.read()
                quiz_file = open(f"{path}/{file.filename}", "w")
                quiz_file.write(file_content.decode("utf-8"))
            else:
                return {"message": "Must be .txt and .mp4!"}
    else:
        return {"message": "Must upload one .mp4 and one .txt!"}
    return {"filenames": [file.filename for file in files]}