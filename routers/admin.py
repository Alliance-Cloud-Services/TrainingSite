import os
from typing import Annotated
from fastapi import APIRouter, Cookie, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import motor.motor_asyncio

from .vids import get_videos


router = APIRouter()
templates = Jinja2Templates(directory="templates")

client = motor.motor_asyncio.AsyncIOMotorClient("127.0.0.1:27017")
db = client.train

user_collection = db.get_collection("users")
vid_collection = db.get_collection("vids")


# Admin Dashboard
@router.get("/v/administration", response_description="Get the admin view.", response_class=HTMLResponse)
async def get_admin_view(request: Request, user: Annotated[str | None, Cookie()] = None):
    content = await get_videos()
    videos = []
    for vid in content:
        videos.append(os.path.basename(vid))
    users =  await user_collection.find().to_list(1000)
    context = {"request": request, "users": users, "vids": videos}
    return templates.TemplateResponse("admin.html", context)


# User Management

@router.get("/v/create_user", response_description="View for creating a user.", response_class=HTMLResponse)
async def create_user_view(request: Request):
    context = {"request": request}
    return templates.TemplateResponse("add_user.html", context)

@router.get("/v/user/{id}", response_description="Get a single user.", response_class=HTMLResponse)
async def user_view(request: Request, id: str):
    # Check for the admin cookie if it exists view the user.
    user = await user_collection.find_one({"user_name": id})
    context = {"request": request, "user": user}
    if user is not None:
        return templates.TemplateResponse("user.html", context)
    else:
        raise HTTPException(status_code=404, detail=f"User {id} not found.")

@router.get("/v/user/{id}/ac", response_description="Assign content to a user.", response_class=HTMLResponse)
async def assign_content_view(request: Request, id:str):
    # Check for the admin cookie if it exists view the assigning content.
    user = await user_collection.find_one({"user_name": id})
    content = await get_videos()
    videos = []
    for vid in content:
        videos.append(os.path.basename(vid))
    
    context = {"request": request, "user": user, "vids": videos}
    if user is not None:
        return templates.TemplateResponse("assign_content.html", context)
    else:
        raise HTTPException(status_code=404, detail=f"User {id} not found.")

# Video Management
@router.get("/v/upload_video", response_description="Upload video view", response_class=HTMLResponse)
async def upload_video_view(request: Request):
    context = {"request": request}
    return templates.TemplateResponse("upload_video.html", context)

# Logging
@router.get("/v/logs", response_description="Get the logs of completed content", response_class=HTMLResponse)
async def get_logs_view(request: Request):
    users = await user_collection.find().to_list(1000)
    context = {"request": request, "users": users}
    return templates.TemplateResponse("logs.html", context)