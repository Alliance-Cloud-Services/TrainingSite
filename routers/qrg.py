import os
from typing import Annotated
from fastapi import APIRouter, Cookie, HTTPException, Request, Response
from fastapi.responses import HTMLResponse

from fastapi.templating import Jinja2Templates
import motor.motor_asyncio

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/qrg/change_miner_fan", response_description="Changing Miner Fan QRG", response_class=HTMLResponse)
async def get_change_miner_fan_qrg(request: Request, response: Response):
    context = {"request": request}
    return templates.TemplateResponse("qrgs/changing_miner_fan.html", context)