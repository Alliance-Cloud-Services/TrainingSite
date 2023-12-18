# Import required modules.
# Create database models.
# Create CRUD for each model.
# Create views which call the API, keep back-end and front-end separate.

# TODO: Restrict /v/user endpoint to admin and uploading video API endpoints.


import base64
from datetime import datetime
import os
import aiofiles

from typing import Optional, List

from fastapi import FastAPI, Body, File, HTTPException, Response, status, UploadFile, Request, Header, Form, Cookie
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
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
    email: str = Field(...)
    password: str = Field(...)
    content_assigned: Optional[List[str]] = None
    content_completed: Optional[List[str]] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

class UpdateUserModel(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    user_name: Optional[str] = None
    email: Optional[str] = None
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


# Get a specific user by user name.
@app.get("/user/{id}", response_description="List a single User.", response_model=UserModel, response_model_by_alias=False)
async def get_user(id: str):
     if (user := await user_collection.find_one({"user_name": id})) is not None:
        return user
     else:
        raise HTTPException(status_code=404, detail=f"User {id} not found.")


# Add content to the user's assigned content.

@app.post("/user/{id}/ac/", response_description="Assign content to a user.", response_model=UserModel, response_model_by_alias=False)
async def update_user_content(id:str, vid:Annotated[str, Form()]):
    user = await user_collection.find_one(({"user_name": id}))
    if user is not None:
        # Check if user already has the file assigned to them.
        if vid in user["content_assigned"]:
            raise HTTPException(status_code=409, detail=f"User is already assigned {vid}")
        else:
            update_result = await user_collection.find_one_and_update(
                {"user_name": id },
                {"$push": { "content_assigned": vid}}
            )
            if update_result is not None:
                return RedirectResponse(f"/", status_code=status.HTTP_302_FOUND)
    else:
        raise HTTPException(status_code=404, detail=f"User {id} not found.")
    # if(existing_user := await user_collection.find_one({"_id": id})) is not None:
    #     return existing_user
    # raise HTTPException(status_code=404, detail=f"User {id} not found.")


# Add content to a user's completed content and remove from assigned.

@app.post("/user/{id}/content/{vid}/c", response_description="Add content to a user's completed content.", response_class=HTMLResponse)
async def update_user_content(id:str, vid:str):
    user = await user_collection.find_one(({"user_name": id}))
    # Video ID + Date
    if user is not None:
        # Check if the user already has the video completed.
        if vid in user["content_completed"]:
            raise HTTPException(status_code=409, detail=f"User has already completed {vid}")
        else:
            update_result = await user_collection.find_one_and_update(
                {"user_name": id},
                {"$push": { "content_completed": vid}, "$pull": { "content_assigned": vid}}
            )
            if update_result is not None:
                return RedirectResponse("/", status_code=status.HTTP_302_FOUND)
            else:
                raise HTTPException(status_code=500, detail=f"Unable to add content to {id}")
    else:
        raise HTTPException(status_code=404, detail=f"User {id} not found.")
    # if(existing_user := await user_collection.find_one({"_id": id})) is not None:
    #     return existing_user
    # raise HTTPException(status_code=404, detail=f"User {id} not found.")

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









@app.post("/video", response_description="Upload a video file.")
async def upload_video(file: UploadFile=File(...), name:str = Body(...)):
    # Check for the admin cookie if it exists allow the file upload.


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
    return videos



# Login endpoint
@app.post("/login", response_description="Login as a user.", response_class=HTMLResponse)
async def login(request: Request, response: Response, user_name:Annotated[str, Form()] = None, password:Annotated[str, Form()] = None):
    if user_name is not None and password is not None:
        user = await user_collection.find_one({'user_name': user_name})
        context = {"request": request, 'user': user}
        # If the user exists check if the password matches.
        if user is not None:
            if user['password'] == password:
                response = templates.TemplateResponse("index.html", context)
                response.set_cookie(key="user", value=user['user_name'])
                return response
            # If the user is the admin set the admin cookie.
            if user['user_name'] == "admin":
                ...
            else:
                context = {"request": request, "error": "Username or password is incorrect"}
                response = templates.TemplateResponse("login.html", context)
                return response
        else:
            context = {"request": request, "error": "Username or password is incorrect"}
            response = templates.TemplateResponse("login.html", context)
            return response
    else:
        context = {"request": request, "error": "You must enter a username and password!"}
        response = templates.TemplateResponse("login.html", context)
        return response
# Logout endpoint
@app.get("/logout", response_description="Logout", response_class=RedirectResponse)
async def logout(request: Request, response: Response):

    context = {"request": request}
    response = RedirectResponse("/")
    response.delete_cookie("user")
    return response

# # View for a single user
# @app.get("/v/user/{id}", response_description="Get a single user.", response_class=HTMLResponse)
# async def user_view(request: Request, id: str):
#     # Check for the admin cookie if it exists view the user.
#     user = await user_collection.find_one({"user_name": id})
#     context = {"request": request, "user": user}
#     if user is not None:
#         return templates.TemplateResponse("user.html", context)
#     else:
#         raise HTTPException(status_code=404, detail=f"User {id} not found.")

# View for assigning content to a user.
@app.get("/v/user/{id}/ac", response_description="Assign content to a user.", response_class=HTMLResponse)
async def assign_content_view(request: Request, id:str):
    # Check for the admin cookie if it exists view the assigning content.
    user = await user_collection.find_one({"user_name": id})
    videos = await get_videos()
    context = {"request": request, "user": user, "vids": videos}
    if user is not None:
        return templates.TemplateResponse("assign_content.html", context)
    else:
        raise HTTPException(status_code=404, detail=f"User {id} not found.")

# View for list of users.
#@app.get("/v/users", response_description="Get a list of users", response_class=HTMLResponse)
#async def homepage(request: Request, hx_request: Optional[str] = Header(None)):
    # # Check for the admin cookie if it exists view the list of users.
    # users =  await user_collection.find().to_list(1000)
    # context = {"request": request, "users": users}
    # # If the button to reload is pressed don't reload the whole page, only the table.
    # if hx_request:
    #     return templates.TemplateResponse("users_table.html", context)
    # return templates.TemplateResponse("users.html", context)

# Homepage view

@ app.get("/", response_description="Get the homepage.", response_class=HTMLResponse)
async def index(request: Request, user: Annotated[str | None, Cookie()] = None):
    context = {"request": request}
    # Check if user is logged in, if not return log in page. (Cookies)
    # If user is logged in return homepage.
    if user is not None:
        user = await user_collection.find_one({"user_name": user})
        context = {"request": request, "user": user}
        return templates.TemplateResponse("index.html", context)
    else:
        return templates.TemplateResponse("login.html", context)

# Video view

@app.get("/v/vid/{id}", response_description="Get a video to view.", response_class=HTMLResponse)
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


# View all videos

# @app.get("/v/videos", response_description="Get all the content on the server.", response_class=HTMLResponse)
# async def get_videos_view(request: Request, user: Annotated[str | None, Cookie()] = None):
#     # Check for the admin cookie, if it exists provide the list.
#     videos = await get_videos()
#     context = {"request": request, "vids": videos}
#     return templates.TemplateResponse("videos.html", context)

@app.get("/v/administration", response_description="Get the admin view.", response_class=HTMLResponse)
async def get_admin_view(request: Request, user: Annotated[str | None, Cookie()] = None):
    videos = await get_videos()
    users =  await user_collection.find().to_list(1000)
    context = {"request": request, "users": users, "vids": videos}
    return templates.TemplateResponse("admin.html", context)
