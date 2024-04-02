from typing import List, Optional
from fastapi import APIRouter, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ConfigDict, BaseModel, Field
from pydantic.functional_validators import BeforeValidator
from typing_extensions import Annotated
from jinja2_ansible_filters.core_filters import regex_replace

from bson import ObjectId
import motor.motor_asyncio
from pymongo import ReturnDocument, errors

from quizzes import Quiz
from routers.vids import get_video_by_uuid
from datetime import datetime 

router = APIRouter()
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
    admin: bool
    content_assigned: Optional[List[str]] = None
    content_completed: Optional[List[str]] = None
    quiz_scores: Optional[List[str]] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

class UpdateUserModel(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    user_name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    content_assigned: Optional[List[str]] = None
    content_completed: Optional[List[str]] = None
    quiz_scores: Optional[List[str]] = None
    model_config = ConfigDict(arbitrary_types_allowed=True, json_encoders={ObjectId: str})


# Create a user.
@router.post("/users", response_description="Create a User", response_model=UserModel, status_code=status.HTTP_201_CREATED, response_model_by_alias=False)
async def create_user(request: Request, name: Annotated[str, Form()], role: Annotated[str, Form()], user_name:Annotated[str, Form()], email:Annotated[str, Form()], password:Annotated[str, Form()], admin:Annotated[str, Form()] = False):
    try:
        user: UserModel = {"name": name, "role": role, "email": email, "user_name": user_name, "email": email, "password": password, "admin": admin, "content_assigned": [], "content_completed": [], "quiz_scores": []}
        new_user = await user_collection.insert_one(user)

        created_user = await user_collection.find_one({"_id": new_user.inserted_id})
        return RedirectResponse(f"/v/administration", status_code=status.HTTP_303_SEE_OTHER)
    except errors.DuplicateKeyError:
        context = {"request": request, "error": "Username is already taken!"}
        return templates.TemplateResponse("add_user.html", context)

# Delete a user.
@router.get("/user/{id}/delete", response_description="Delete user", response_model=UserModel, response_model_by_alias=False)
async def delete_user(id: str):
    user = await user_collection.find_one(({"user_name": id}))
    if user is not None:
        delete_result = await user_collection.delete_one(({"user_name": id}))
        if delete_result.deleted_count == 1:
             return Response(status_code=status.HTTP_204_NO_CONTENT)
        else:
            raise HTTPException(status_code=500, detail=f"Unable to delete user.")
    else:
        raise HTTPException(status_code=404, detail=f"User {id} not found.")

@router.post("/login", response_description="Login as a user.", response_class=HTMLResponse)
async def login(request: Request, response: Response, user_name:Annotated[str, Form()] = None, password:Annotated[str, Form()] = None):
    if user_name is not None and password is not None:
        user = await user_collection.find_one({'user_name': user_name})
        context = {"request": request, 'user': user}
        # If the user exists check if the password matches.
        if user is not None:
            if user['password'] == password:
                response = templates.TemplateResponse("index.html", context)
                response.set_cookie(key="user", value=user['user_name'])
                # If the user is the admin set the admin cookie. #TODO
                if user['admin'] == True:
                    response.set_cookie(key="admin", value=True)
                    return response
                else:
                    return response
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

@router.get("/logout", response_description="Logout", response_class=RedirectResponse)
async def logout(request: Request, response: Response):

    context = {"request": request}
    response = RedirectResponse("/")
    response.delete_cookie("user")
    response.delete_cookie("admin")
    return response

# Assign content to a user.
@router.post("/user/{id}/ac/", response_description="Assign content to a user.", response_model=UserModel, response_model_by_alias=False)
async def update_user_content(id:str, vid:Annotated[str, Form()]):
    user = await user_collection.find_one(({"user_name": id}))
    if user is not None:
        # Check if user already has the file assigned to them.
        if vid in user["content_assigned"]:
            raise HTTPException(status_code=409, detail=f"User {id} is already assigned {vid}")
        # Check if user already completed the file assigned to them.
        if vid in user["content_completed"]:
            raise HTTPException(status_code=409, detail=f"User {id} has completed {vid}")
        else:
            update_result = await user_collection.find_one_and_update(
                {"user_name": id },
                {"$push": { "content_assigned": vid}}
            )
            if update_result is not None:
                return RedirectResponse(f"/", status_code=status.HTTP_302_FOUND)
    else:
        raise HTTPException(status_code=404, detail=f"User {id} not found.")

# Add content to a user's completed content and score the quiz. 
@router.post("/user/{id}/content/vids/{uuid}/{vid}/c", response_description="Add content to a user's completed content.", response_class=HTMLResponse)
async def update_user_content(id:str, vid:str, uuid: str, option1: Annotated[str, Form()] = None, option2: Annotated[str, Form()] = None, option3: Annotated[str, Form()] = None, option4: Annotated[str, Form()] = None, option5: Annotated[str, Form()] = None, option6: Annotated[str, Form()] = None, option7: Annotated[str, Form()] = None, option8: Annotated[str, Form()] = None, option9: Annotated[str, Form()] = None, option10: Annotated[str, Form()] = None, option11: Annotated[str, Form()] = None, option12: Annotated[str, Form()] = None, option13: Annotated[str, Form()] = None, option14: Annotated[str, Form()] = None):
    user = await user_collection.find_one(({"user_name": id}))
    # Video ID + Date
    if user is not None:
        # Check if the user already has the video completed.
        if vid in user["content_completed"]:
            raise HTTPException(status_code=409, detail=f"User has already completed {vid}")
        else:

            # Open the video's quiz file.
            options = []
            options.append(option1)
            options.append(option2)
            options.append(option3)
            options.append(option4)
            options.append(option5)
            options.append(option6)
            options.append(option7)
            options.append(option8)
            options.append(option9)
            options.append(option10)
            options.append(option11)
            options.append(option12)
            options.append(option13)
            options.append(option14)

            clean_options = []
            for option in options:
                if option is None:
                    continue
                else:
                    clean_options.append(option)
                    print(option)

            print(id)
            print(uuid),
            print(vid)
            
            video = await get_video_by_uuid(vid)
            video_quiz = Quiz()
            video_quiz.from_file(video.quiz)


            score = video_quiz.score_quiz(clean_options)
            date = datetime.now()

            update_result = await user_collection.find_one_and_update(
                {"user_name": id},
                {"$push": { "content_completed": f"{date.month}/{date.day}/{date.year}, {date.hour}:{date.minute}, {vid}:  {score}%"}, "$pull": { "content_assigned": vid}}
            )
            if update_result is not None:
                return RedirectResponse("/", status_code=status.HTTP_302_FOUND)
            else:
                raise HTTPException(status_code=500, detail=f"Unable to add content to {id}")
    else:
        raise HTTPException(status_code=404, detail=f"User: {id}, not found.")




