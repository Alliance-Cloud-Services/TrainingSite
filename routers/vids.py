import os
from typing import List, Optional
from fastapi import APIRouter, Cookie, HTTPException, Request, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ConfigDict, BaseModel, Field
from pydantic.functional_validators import BeforeValidator
from typing_extensions import Annotated

from bson import ObjectId
import motor.motor_asyncio
from pymongo import ReturnDocument, errors

router = APIRouter()
templates = Jinja2Templates(directory="templates")

client = motor.motor_asyncio.AsyncIOMotorClient("127.0.0.1:27017")
db = client.train

user_collection = db.get_collection("users")
vid_collection = db.get_collection("vids")
# Represents an ObjectId field in the database.
# It will be represented as a `str` on the model so that it can be serialized to JSON.
PyObjectId = Annotated[str, BeforeValidator(str)]

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