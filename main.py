from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from db import *
from test import inward_cycle, outward_cycle

# ---------------- APP ----------------

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key="asrs-super-secret-key"
)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

init_db()

# ---------------- LOGIN ----------------

@app.get("/")
def login_page(req: Request):
    return templates.TemplateResponse("login.html", {"request": req})


@app.post("/login")
def do_login(req: Request, user: str = Form(...), pwd: str = Form(...)):

    if login(user, pwd):
        req.session["user"] = user
        return RedirectResponse("/dashboard", status_code=302)

    return RedirectResponse("/", status_code=302)


# ---------------- LOGOUT ----------------

@app.get("/logout")
def logout(req: Request):
    req.session.clear()
    return RedirectResponse("/", status_code=302)


# ---------------- REGISTER ----------------

@app.get("/register")
def reg(req: Request):
    return templates.TemplateResponse("register.html", {"request": req})


@app.post("/register")
def do_reg(user: str = Form(...), pwd: str = Form(...)):
    create_user(user, pwd)
    return RedirectResponse("/", status_code=302)


# ---------------- FORGOT ----------------

@app.get("/forgot")
def forgot(req: Request):
    return templates.TemplateResponse("forgot.html", {"request": req})


@app.post("/forgot")
def do_forgot(user: str = Form(...), pwd: str = Form(...)):
    reset_password(user, pwd)
    return RedirectResponse("/", status_code=302)


# ---------------- DASHBOARD ----------------

@app.get("/dashboard")
def dash(req: Request):

    if not req.session.get("user"):
        return RedirectResponse("/", status_code=302)

    return templates.TemplateResponse("dashboard.html", {"request": req})


# =========================================================
# API
# =========================================================

@app.get("/api/locations")
def locations():
    return all_locations()


# ---------------- INWARD ----------------

@app.post("/api/inward")
def inward_api(
    loc: int = Form(...),
    item: str = Form(...),
    desc: str = Form(...)
):
    try:

        # Run PLC cycle
        inward_cycle(1, loc)

        # Update DB
        update_store(loc, item, desc)

        return {"status": "ok"}

    except Exception as e:

        return {"status": "error", "msg": str(e)}


# ---------------- OUTWARD ----------------

@app.post("/api/outward")
def outward_api(loc: int = Form(...)):

    try:

        # Run PLC cycle
        outward_cycle(loc, 1)

        # Clear DB
        outward(loc)

        return {"status": "ok"}

    except Exception as e:

        return {"status": "error", "msg": str(e)}


# ---------------- SEARCH ----------------

@app.get("/api/search/{q}")
def search_api(q: str):

    if q.isdigit():
        return find_loc(int(q))

    return search(q)


# ---------------- RUN SERVER ----------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)