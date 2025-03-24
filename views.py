from fastapi import APIRouter, Depends, Request
from lnbits.core.models import User
from lnbits.decorators import check_user_exists
from lnbits.helpers import template_renderer
from starlette.responses import HTMLResponse

usermanager_generic_router = APIRouter()


def usermanager_renderer():
    return template_renderer(["usermanager/templates"])


@usermanager_generic_router.get("/", response_class=HTMLResponse)
async def index(req: Request, user: User = Depends(check_user_exists)):
    return usermanager_renderer().TemplateResponse(
        "usermanager/index.html", {"request": req, "user": user.json()}
    )
