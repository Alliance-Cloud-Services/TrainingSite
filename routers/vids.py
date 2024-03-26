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
import glob
from pox.shutils import find

from quizzes import *

router = APIRouter()
templates = Jinja2Templates(directory="templates")

client = motor.motor_asyncio.AsyncIOMotorClient("127.0.0.1:27017")
db = client.train

user_collection = db.get_collection("users")





class Video:
    def __init__(self, uuid:str = None, quiz:str = None, mp4:str = None):
        self.uuid = uuid
        self.quiz = quiz
        self.mp4 = mp4



       
async def get_video_by_uuid(video_name: str):
    vids = glob.glob("./vids/**/*.mp4", recursive=True)
    video = Video()


    for vid in vids:
        video_pattern = re.search(video_name, vid)
        # For each video file find the parent directory of the file.
        if video_pattern:
           video_path = re.sub(video_name, " ", video_pattern.string).rstrip()
           quizzes = glob.glob(f"{video_path}*.txt", recursive=True)
           for quiz in quizzes:
            if len(quizzes) == 1:
                video.quiz = quiz
           video.mp4=video_pattern.string
        else:
            continue

    return video
    

@router.get("/videos")
async def get_vids():
    x = await get_video_by_uuid("uuid")
    return {"vids": x.mp4}

async def get_videos():
    mp4_files = glob.iglob("./vids/**/*.mp4", recursive=True)
    return mp4_files




@router.post("/upload_qv", response_description="Upload quiz and video file.", status_code=status.HTTP_202_ACCEPTED)
async def upload_vid_and_quiz(quiz: UploadFile, video: UploadFile):
    if quiz and video:
        if quiz.content_type == "text/plain" and video.content_type == "video/mp4":

            id = str(uuid.uuid4())
            path = Path(f"./vids/{id}")
            path.mkdir(parents=True, exist_ok=True)

            files = [quiz, video]

            for file in files:
                if file.content_type == "video/mp4":
                    file_content = await file.read()
                    video_file = open(f"{path}/{file.filename}", "w+b")
                    video_file.write(file_content)

                if file.content_type == "text/plain":
                    file_content = await file.read()
                    quiz_file = open(f"{path}/{file.filename}", "w")
                    quiz_file.write(file_content.decode("utf-8"))

            return RedirectResponse(f"/v/administration", status_code = status.HTTP_303_SEE_OTHER)
        else:
            print("Quiz must be .txt and video must be .mp4")
    else:
        print("You must upload both a quiz and video file!")


@router.get("/v/video/{id}", response_description="View a video by UUID")
async def show_video(request: Request, id:str, user: Annotated[str | None, Cookie()] = None):
     context = {"request": request, "id": id}
     # Find the video folder and return the .mp4 name.
     video = await get_video_by_uuid(id)
     video_quiz = Quiz()
     video_quiz.from_file(video.quiz)

     for question in video_quiz.questions:
         print(question.text)
         print(question.options)

     user = await user_collection.find_one({"user_name": user})
     context = {"request": request, "id": video.mp4, 'user': user, 'quiz': video_quiz}
     return templates.TemplateResponse("video.html", context)
     

@router.get("/video/vids/{id}/{file}", response_description="Get a specific video file.", response_class=FileResponse)
async def stream_video(id: str):
    video = await get_video_by_uuid(id)
    return video.mp4