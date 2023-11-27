# Import required modules.
# Create database models.
# Create CRUD for each model.
# Create views which call the API, keep back-end and front-end separate.

from datetime import datetime
import os
import aiofiles

from typing import Optional, List

from fastapi import FastAPI, Body, File, HTTPException, status, UploadFile, Request, Header
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pydantic import ConfigDict, BaseModel, Field
from pydantic.functional_validators import BeforeValidator


from typing_extensions import Annotated

from bson import ObjectId
import motor.motor_asyncio
from pymongo import ReturnDocument, errors



app = FastAPI(title="Training Module API", summary="The back-end for the training module allowing users to retrieve videos and admins to manage videos and users.")
templates = Jinja2Templates(directory="templates")


client = motor.motor_asyncio.AsyncIOMotorClient("127.0.0.1:27017")
db = client.train
user_collection = db.get_collection('users')

vid_collection = db.get_collection("vids")
# Represents an ObjectId field in the database.
# It will be represented as a `str` on the model so that it can be serialized to JSON.
PyObjectId = Annotated[str, BeforeValidator(str)]

class UserModel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    name: str = Field(...)
    role: str = Field(...)
    user_name: str = Field(...)
    password: str = Field(...)
    content_assigned: Optional[List[str]] = None
    content_completed: Optional[List[str]] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

class UpdateUserModel(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    user_name: Optional[str] = None
    password: Optional[str] = None
    content_assigned: Optional[List[str]] = None
    content_completed: Optional[List[str]] = None
    model_config = ConfigDict(arbitrary_types_allowed=True, json_encoders={ObjectId: str})


# https://haacked.com/archive/2009/06/25/json-hijacking.aspx/
class UserCollection(BaseModel):
    users: List[UserModel]



# Individual CRUD User Endpoints

# Create a user.
@app.post("/users", response_description="Create a User", response_model=UserModel, status_code=status.HTTP_201_CREATED, response_model_by_alias=False)
async def create_user(user: UserModel = Body(...)):
    try:
        new_user = await user_collection.insert_one(user.model_dump(by_alias=True, exclude=["id"]))

        created_user = await user_collection.find_one({"_id": new_user.inserted_id})
        return created_user
    except errors.DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Username is taken.")


# Get a specific user.
@app.get("/user/{id}", response_description="List a single User.", response_model=UserModel, response_model_by_alias=False)
async def get_user(id: str):
     if (user := await user_collection.find_one({"_id": ObjectId(id)})) is not None:
        return user
     else:
        raise HTTPException(status_code=404, detail=f"User {id} not found.")


# Add content to the user's assigned content.

@app.put("/user/{id}/content/{vid}", response_description="Assign content to a user.", response_model=UserModel, response_model_by_alias=False)
async def update_user_content(id:str, vid:str, user:UpdateUserModel = Body(...)):
    user = {k: v for k, v in user.model_dump(by_alias=True).items() if v is not None}
    if(len(user) > 1):
        update_result = await user_collection.find_one_and_update(
            {"_id": ObjectId(id)},
            {"$push": { "content_assigned":vid }}
        )
    if update_result is not None:
        return update_result
    else:
        raise HTTPException(status_code=404, detail=f"User {id} not found.")
    if(existing_user := await user_collection.find_one({"_id": id})) is not None:
        return existing_user
    raise HTTPException(status_code=404, detail=f"User {id} not found.")


# Add content to a user's completed content.

@app.put("/user/{id}/content/{vid}/c", response_description="Add content to a user's completed content.", response_model=UserModel, response_model_by_alias=False)
async def update_user_content(id:str, vid:str, user:UpdateUserModel = Body(...)):
    user = {k: v for k, v in user.model_dump(by_alias=True).items() if v is not None}

    # Video ID + Date
    if(len(user) > 1):
        update_result = await user_collection.find_one_and_update(
            {"_id": ObjectId(id)},
            {"$push": { "content_completed":f"{datetime.now()}"+vid }}
        )
    if update_result is not None:
        return update_result
    else:
        raise HTTPException(status_code=404, detail=f"User {id} not found.")
    if(existing_user := await user_collection.find_one({"_id": id})) is not None:
        return existing_user
    raise HTTPException(status_code=404, detail=f"User {id} not found.")

# Change a user's name.
@app.put("/user/{id}/cn/{name}", response_description="Change a user's user name.", response_model=UserModel, response_model_by_alias=False)
async def update_user_content(id:str, name:str, user:UpdateUserModel = Body(...)):
    user = {k: v for k, v in user.model_dump(by_alias=True).items() if v is not None}

    # Video ID + Date
    if(len(user) > 1):
        update_result = await user_collection.find_one_and_update(
            {"_id": ObjectId(id)},
            {"$set": {"name":name}}
        )
    if update_result is not None:
        return update_result
    else:
        raise HTTPException(status_code=404, detail=f"User {id} not found.")
    if(existing_user := await user_collection.find_one({"_id": id})) is not None:
        return existing_user
    raise HTTPException(status_code=404, detail=f"User {id} not found.")
# Change a user's user name.

@app.put("/user/{id}/cu/{user_name}", response_description="Change a user's user name.", response_model=UserModel, response_model_by_alias=False)
async def update_user_content(id:str, user_name:str, user:UpdateUserModel = Body(...)):
    user = {k: v for k, v in user.model_dump(by_alias=True).items() if v is not None}

    # Video ID + Date
    if(len(user) > 1):
        update_result = await user_collection.find_one_and_update(
            {"_id": ObjectId(id)},
            {"$set": {"user_name":user_name}}
        )
    if update_result is not None:
        return update_result
    else:
        raise HTTPException(status_code=404, detail=f"User {id} not found.")
    if(existing_user := await user_collection.find_one({"_id": id})) is not None:
        return existing_user
    raise HTTPException(status_code=404, detail=f"User {id} not found.")

# Change a user's password.

@app.put("/user/{id}/pc/{password}", response_description="Change a user's password.", response_model=UserModel, response_model_by_alias=False)
async def update_user_content(id:str, password:str, user:UpdateUserModel = Body(...)):
    user = {k: v for k, v in user.model_dump(by_alias=True).items() if v is not None}

    # Video ID + Date
    if(len(user) > 1):
        update_result = await user_collection.find_one_and_update(
            {"_id": ObjectId(id)},
            {"$set": {"password":password}}
        )
    if update_result is not None:
        return update_result
    else:
        raise HTTPException(status_code=404, detail=f"User {id} not found.")
    if(existing_user := await user_collection.find_one({"_id": id})) is not None:
        return existing_user
    raise HTTPException(status_code=404, detail=f"User {id} not found.")

# Change a user's role
@app.put("/user/{id}/cr/{role}", response_description="Change a user's role.", response_model=UserModel, response_model_by_alias=False)
async def update_user_content(id:str, role:str, user:UpdateUserModel = Body(...)):
    user = {k: v for k, v in user.model_dump(by_alias=True).items() if v is not None}

    # Video ID + Date
    if(len(user) > 1):
        update_result = await user_collection.find_one_and_update(
            {"_id": ObjectId(id)},
            {"$set": {"role":role}}
        )
    if update_result is not None:
        return update_result
    else:
        raise HTTPException(status_code=404, detail=f"User {id} not found.")
    if(existing_user := await user_collection.find_one({"_id": id})) is not None:
        return existing_user
    raise HTTPException(status_code=404, detail=f"User {id} not found.")

@app.delete("/user/{id}", response_description="Delete user", response_model=UserModel, response_model_by_alias=False)
async def delete_user(id: str):
    ...

# Multiple Users

@app.get("/users", response_description="List all Users", response_model=UserCollection, response_model_by_alias=False,)
async def get_users():
    users = await user_collection.find().to_list(1000)
    return users




class VidModel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    name: str = Field(...)
    file_name: str = Field(...)

# Individual Video Endpoints






# Create a user.
@app.post("/users", response_description="Create a User", response_model=UserModel, status_code=status.HTTP_201_CREATED, response_model_by_alias=False)
async def create_user(user: UserModel = Body(...)):
    try:
        new_user = await user_collection.insert_one(user.model_dump(by_alias=True, exclude=["id"]))

        created_user = await user_collection.find_one({"_id": new_user.inserted_id})
        return created_user
    except errors.DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Username is taken.")



@app.post("/video", response_description="Upload a video file.")
async def upload_video(file: UploadFile=File(...), name:str = Body(...)):

    # Write the file to disk.
    async with aiofiles.open(os.path.join("./vids", name), 'wb') as out_vid:
        content = await file.read()
        await out_vid.write(content)
    return {"filename": file.filename}

    # # Add the video name to the database.
    # try:
    #     new_video = await vid_collection.insert_one(vid.model_dump(by_alias=True, exclude=["id"]))

    #     created_vid = await vid_collection.find_one({"_id": created_vid.inserted_id})
    #     return created_vid
    # except errors.DuplicateKeyError:
    #     raise HTTPException(status_code=409, detail="Video with name already exists!")


# Return a single video file.
@app.get("/video/{id}", response_description="Get a specific video file.", response_class=FileResponse)
def stream_video(id: str):
  return os.path.join("./vids/", id)

#  Return a list of all videos on the server.
@app.get("/videos", response_description="Get a list of all the videos.")
async def get_videos():
    videos = []
    vid_dir = os.path.join("./", "vids")
    for vid in os.scandir(vid_dir):
       if vid.is_file():
        videos.append(vid.name)
    return {"vids": videos}

# View for list of users.
@app.get("/v/users", response_description="Get a list of users", response_class=HTMLResponse)
async def homepage(request: Request, hx_request: Optional[str] = Header(None)):
    users =  await user_collection.find().to_list(1000)
    context = {"request": request, "users": users}
    # If the button to reload is pressed don't reload the whole page, only the table.
    if hx_request:
        return templates.TemplateResponse("table.html", context)
    return templates.TemplateResponse("users.html", context)

# Index

@ app.get("/", response_description="Get the homepage.", response_class=HTMLResponse)
async def index(request: Request):
    context = {"request": request}
    return templates.TemplateResponse("index.html", context)

@ app.get("/v/vid/{id}", response_description="Get a video to view.", response_class=HTMLResponse)
async def get_video(request: Request, id: str):
    context = {"request": request, "id": id}
    return templates.TemplateResponse("video.html", context)