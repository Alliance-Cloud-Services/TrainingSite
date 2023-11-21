# Import required modules.
# Create database models. 
# Create CRUD for each model.
# Create views which call the API, keep back-end and front-end seperate.

from datetime import datetime
import os
import aiofiles

from typing import Optional, List

from fastapi import FastAPI, Body, File, HTTPException, status, UploadFile
from fastapi.responses import Response, StreamingResponse, FileResponse
from pydantic import ConfigDict, BaseModel, Field, EmailStr
from pydantic.functional_validators import BeforeValidator


from typing_extensions import Annotated

from bson import ObjectId
import motor.motor_asyncio
from pymongo import ReturnDocument, errors



app = FastAPI(title="Training Module API", summary="The back-end for the training module allowing users to retrieve videos and admins to manage videos and users.")
client = motor.motor_asyncio.AsyncIOMotorClient("127.0.0.1:27017")

db = client.train
user_collection = db.get_collection('users')

# Represents an ObjectId field in the database.
# It will be represented as a `str` on the model so that it can be serialized to JSON.
PyObjectId = Annotated[str, BeforeValidator(str)]

class UserModel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    name: str = Field(...)
    user_name: str = Field(...)
    password: str = Field(...)
    content_assigned: Optional[List[str]] = None
    content_completed: Optional[List[str]] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

class UpdateUserModel(BaseModel):
    name: Optional[str] = None
    user_name: Optional[str] = None
    password: Optional[str] = None
    content_assigned: Optional[List[str]] = None
    content_completed: Optional[List[str]] = None
    model_config = ConfigDict(arbitrary_types_allowed=True, json_encoders={ObjectId: str})


# https://haacked.com/archive/2009/06/25/json-hijacking.aspx/
class UserCollection(BaseModel):
    users: List[UserModel]

# Individual CRUD User Endpoints

@app.post("/users", response_description="Create a User", response_model=UserModel, status_code=status.HTTP_201_CREATED, response_model_by_alias=False)
async def create_user(user: UserModel = Body(...)):
    try:
        new_user = await user_collection.insert_one(user.model_dump(by_alias=True, exclude=["id"]))

        created_user = await user_collection.find_one({"_id": new_user.inserted_id})
        return created_user
    except errors.DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Username is taken.")

    
@app.get("/user/{id}", response_description="List a single User.", response_model=UserModel, response_model_by_alias=False)
async def get_user(id: str):
     if (user := await user_collection.find_one({"_id": ObjectId(id)})) is not None:
        return user
     else:
        raise HTTPException(status_code=404, detail=f"User {id} not found")


# Put for updating Content completed or content assigned.
# Always Put the date completed, if available put the quiz score as well.
@app.put("/user/{id}", response_description="Update a user's assigned or completed content. This method can also be used to change user details.", response_model=UserModel, response_model_by_alias=False)
async def update_user(id: str):
    ...
@app.delete("/user/{id}", response_description="Delete user", response_model=UserModel, response_model_by_alias=False)
async def delete_user(id: str):
    ...

# Multiple Users 

@app.get("/users", response_description="List all Users", response_model=UserCollection, response_model_by_alias=False,)
async def get_users():
    return UserCollection(users = await user_collection.find().to_list(1000))



# Individual Video Endpoints

@app.post("/video", response_description="Upload a video file.")
async def upload_video(file: UploadFile=File(...), name = Body(...)):
    async with aiofiles.open(os.path.join("./", name), 'wb') as out_vid:
        content = await file.read()
        await out_vid.write(content)
    return { "filename": file.filename }


@app.get("/video/{id}", response_description="Get a specific video file.", response_class=FileResponse)
def stream_video(id: str):
  return os.path.join("./", id)

@app.put("/video/{id}", response_description="Change a video name.")
def update_video(id: str):
    ...

@app.delete("/video/{id}", response_description="Delete a video.")
def delete_video(id: str):
    ...


# Multiple Videos
@app.get("/videos", response_description="Get a list of all the videos.")
def get_videos():
    ...


