from typing import Annotated
from fastapi import Cookie, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import Template
from pydantic import BeforeValidator
import motor.motor_asyncio

from routers import users, vids, admin, qrg

templates = Jinja2Templates(directory="templates")


client = motor.motor_asyncio.AsyncIOMotorClient("127.0.0.1:27017")
db = client.train
user_collection = db.get_collection('users')
vid_collection = db.get_collection("vids")
# Represents an ObjectId field in the database.
# It will be represented as a `str` on the model so that it can be serialized to JSON.
PyObjectId = Annotated[str, BeforeValidator(str)]

app = FastAPI();
app.mount("/public", StaticFiles(directory="public"), name="public")
app.include_router(admin.router)
app.include_router(users.router)
app.include_router(vids.router)
app.include_router(qrg.router)


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