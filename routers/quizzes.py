from typing import Annotated, Optional, List
from bson import ObjectId
from fastapi import APIRouter, Form, Request, status
from fastapi.templating import Jinja2Templates
import motor.motor_asyncio
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field
from pymongo import ReturnDocument, errors

router = APIRouter()
templates = Jinja2Templates(directory="templates")

client = motor.motor_asyncio.AsyncIOMotorClient("127.0.0.1:27017")
db = client.train

user_collection = db.get_collection("users")
quizzes_collection = db.get_collection("quizzes")
vid_collection = db.get_collection("vids")
# Represents an ObjectId field in the database.
# It will be represented as a `str` on the model so that it can be serialized to JSON.


class QuizScore:
    quiz_id: str
    score: str

class QuizQuestion:
    question: str
    correct_answer: str
    answers: []

PyObjectId = Annotated[str, BeforeValidator(str)]

class QuizModel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    vid: str
    quiz_questions: List[str] = None
    quiz_answers: List[str] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

@router.post("/quizzes", response_description="Add a quiz to the database.", status_code=status.HTTP_201_CREATED, response_model_by_alias=False)
async def add_quiz(request: Request, quiz: QuizModel):
    new_quiz = await quizzes_collection.insert_one(quiz.model_dump())