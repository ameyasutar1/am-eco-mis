from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import threading
from datetime import datetime

from db import *
from test import inward_cycle, outward_cycle, probe_plc_connection
from reports_pdf import build_text_pdf

# ---------------- APP ----------------

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key="asrs-super-secret-key"
)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

init_db()

op_lock = threading.Lock()
operation_state = {
    "running": False,
    "type": None,
    "loc": None,
    "user": None,
    "status": "idle",
    "msg": "",
    "started_at": None,
    "finished_at": None,
}


def _utc_now():
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _start_operation(op_type: str, loc: int, user: str):
    with op_lock:
        if operation_state["running"]:
            return False
        operation_state.update({
            "running": True,
            "type": op_type,
            "loc": loc,
            "user": user,
            "status": "running",
            "msg": f"{op_type.upper()} started for location {loc} by {user}",
            "started_at": _utc_now(),
            "finished_at": None,
        })
        return True


def _finish_operation(success: bool, msg: str):
    with op_lock:
        operation_state.update({
            "running": False,
            "status": "completed" if success else "failed",
            "msg": msg,
            "finished_at": _utc_now(),
        })


def _run_inward(loc: int, item: str, desc: str, material_type: str | None, user: str):
    try:
        inward_cycle(1, loc)
        update_store(loc, item, desc)
        log_movement(
            action="INWARD",
            location_id=loc,
            item_id=item,
            description=desc,
            material_type=material_type,
            username=user,
            status="SUCCESS"
        )
        _finish_operation(True, f"INWARD completed for location {loc}")
    except Exception as e:
        log_movement(
            action="INWARD",
            location_id=loc,
            item_id=item,
            description=desc,
            material_type=material_type,
            username=user,
            status="FAILED",
            error_msg=str(e)
        )
        _finish_operation(False, f"INWARD failed for location {loc}: {e}")


def _run_outward(loc: int, item: str | None, desc: str | None, user: str):
    try:
        outward_cycle(loc, 1)
        outward(loc)
        log_movement(
            action="OUTWARD",
            location_id=loc,
            item_id=item,
            description=desc,
            material_type=None,
            username=user,
            status="SUCCESS"
        )
        _finish_operation(True, f"OUTWARD completed for location {loc}")
    except Exception as e:
        log_movement(
            action="OUTWARD",
            location_id=loc,
            item_id=item,
            description=desc,
            material_type=None,
            username=user,
            status="FAILED",
            error_msg=str(e)
        )
        _finish_operation(False, f"OUTWARD failed for location {loc}: {e}")


def _pdf_download(filename: str, title: str, lines: list[str]) -> Response:
    pdf_bytes = build_text_pdf(title, lines)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


def _fit_col(text: str, width: int) -> str:
    v = str(text or "-")
    return v[:width-1] + "…" if len(v) > width else v.ljust(width)


def _table(headers: list[str], rows: list[list], widths: list[int]) -> list[str]:
    out = []
    header_line = " | ".join(_fit_col(h, w) for h, w in zip(headers, widths))
    sep_line = "-+-".join("-" * w for w in widths)
    out.append(header_line)
    out.append(sep_line)
    if not rows:
        out.append("No data")
        return out
    for row in rows:
        out.append(" | ".join(_fit_col(v, w) for v, w in zip(row, widths)))
    return out

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


@app.get("/reports")
def reports_page(req: Request):
    if not req.session.get("user"):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("reports.html", {"request": req})


# =========================================================
# API
# =========================================================

@app.get("/api/locations")
def locations():
    return all_locations()


# ---------------- INWARD ----------------

@app.post("/api/inward")
def inward_api(
    req: Request,
    loc: int = Form(...),
    item: str | None = Form(None),
    desc: str | None = Form(None),
    material_type: str | None = Form(None)
):
    try:
        with op_lock:
            if operation_state["running"]:
                return {"status": "error", "msg": "Another cycle is already running"}

        current = find_loc(loc)
        if not current:
            return {"status": "error", "msg": f"Location {loc} not found"}

        if current[2] is not None:
            return {"status": "error", "msg": f"Location {loc} is already occupied"}

        clean_item = (item or "").strip()
        clean_desc = (desc or "").strip()
        clean_type = (material_type or "").strip().upper()
        allowed_types = {"TYPE_A", "TYPE_B", "TYPE_C"}

        if clean_type and clean_type not in allowed_types:
            return {"status": "error", "msg": "Invalid material type"}

        # Operator can provide either:
        # 1) Item ID + Description, or
        # 2) A material type shortcut (TYPE_A / TYPE_B / TYPE_C).
        if not clean_type and (not clean_item or not clean_desc):
            return {
                "status": "error",
                "msg": "Provide Item ID + Description, or select material type",
            }

        if clean_type:
            if not clean_item:
                clean_item = clean_type
            if not clean_desc:
                clean_desc = clean_type.replace("_", " ")

        user = req.session.get("user", "unknown")

        if not _start_operation("inward", loc, user):
            return {"status": "error", "msg": "Another cycle is already running"}

        t = threading.Thread(
            target=_run_inward,
            args=(loc, clean_item, clean_desc, clean_type or None, user),
            daemon=True
        )
        t.start()

        return {"status": "accepted", "msg": f"INWARD started for location {loc}"}

    except Exception as e:

        return {"status": "error", "msg": str(e)}


# ---------------- OUTWARD ----------------

@app.post("/api/outward")
def outward_api(req: Request, loc: int = Form(...)):

    try:
        with op_lock:
            if operation_state["running"]:
                return {"status": "error", "msg": "Another cycle is already running"}

        current = find_loc(loc)
        if not current:
            return {"status": "error", "msg": f"Location {loc} not found"}

        if current[2] is None:
            return {"status": "error", "msg": f"Location {loc} is already empty"}

        user = req.session.get("user", "unknown")

        if not _start_operation("outward", loc, user):
            return {"status": "error", "msg": "Another cycle is already running"}

        t = threading.Thread(
            target=_run_outward,
            args=(loc, current[2], current[3], user),
            daemon=True
        )
        t.start()

        return {"status": "accepted", "msg": f"OUTWARD started for location {loc}"}

    except Exception as e:

        return {"status": "error", "msg": str(e)}


@app.get("/api/op-status")
def op_status():
    with op_lock:
        return dict(operation_state)


@app.get("/api/plc-status")
def plc_status():
    ok, msg = probe_plc_connection()
    return {
        "connected": ok,
        "msg": msg,
        "checked_at": _utc_now(),
    }


@app.get("/api/reports/summary")
def reports_summary():
    return report_summary()


@app.get("/api/reports/charts")
def reports_charts():
    return get_reports_chart_data()


@app.get("/api/reports/full-inventory.pdf")
def report_full_inventory():
    rows = get_full_inventory()
    lines = ["Section: Current Inventory", ""]
    lines += _table(
        ["Location", "Side", "Item ID", "Description"],
        [[r[0], r[1], r[2] or "-", r[3] or "-"] for r in rows],
        [8, 8, 36, 34]
    )
    return _pdf_download(
        "full_inventory_report.pdf",
        "Full Inventory Data Report",
        lines
    )


@app.get("/api/reports/item-wise.pdf")
def report_item_wise(q: str):
    current, history = get_item_wise(q)
    lines = [f"Filter: {q}", "", "Section: Current Inventory Matches", ""]
    lines += _table(
        ["Location", "Side", "Item ID", "Description"],
        [[r[0], r[1], r[2] or "-", r[3] or "-"] for r in current],
        [8, 8, 36, 34]
    )
    lines += ["", "Section: Movement History", ""]
    lines += _table(
        ["Timestamp", "Action", "Loc", "User", "Status"],
        [[h[7], h[0], h[1], h[5] or "-", h[6]] for h in history],
        [20, 9, 5, 20, 8]
    )
    return _pdf_download("item_wise_report.pdf", "Item Wise Data Report", lines)


@app.get("/api/reports/location-wise.pdf")
def report_location_wise(loc: int):
    current, history = get_location_wise(loc)
    lines = [f"Location: {loc}", "", "Section: Current Tray Status", ""]
    if current:
        lines += _table(
            ["Location", "Side", "Item ID", "Description"],
            [[current[0], current[1], current[2] or "-", current[3] or "-"]],
            [8, 8, 36, 34]
        )
    else:
        lines.append("Location not found")
    lines += ["", "Section: Movement History", ""]
    lines += _table(
        ["Timestamp", "Action", "Item ID", "User", "Status"],
        [[h[7], h[0], h[2] or "-", h[5] or "-", h[6]] for h in history],
        [20, 9, 32, 20, 8]
    )
    return _pdf_download("location_wise_report.pdf", "Location Wise Data Report", lines)


@app.get("/api/reports/user-wise.pdf")
def report_user_wise(user: str):
    rows = get_user_wise(user)
    lines = [f"User: {user}", "", "Section: User Movement History", ""]
    lines += _table(
        ["Timestamp", "Action", "Loc", "Item ID", "Status"],
        [[r[6], r[0], r[1], r[2] or "-", r[5]] for r in rows],
        [20, 9, 5, 38, 8]
    )
    return _pdf_download("user_wise_report.pdf", "User Wise Data Report", lines)


@app.get("/api/reports/storing-history.pdf")
def report_storing_history():
    rows = get_storing_history()
    lines = ["Section: Inward Storing History", ""]
    lines += _table(
        ["Timestamp", "Loc", "Item ID", "Type", "User", "Status"],
        [[r[6], r[0], r[1] or "-", r[3] or "-", r[4] or "-", r[5]] for r in rows],
        [20, 5, 28, 12, 18, 8]
    )
    return _pdf_download("storing_history_report.pdf", "Storing History Report", lines)


@app.get("/api/reports/issuing-report.pdf")
def report_issuing():
    rows = get_issuing_history()
    lines = ["Section: Outward Issuing History", ""]
    lines += _table(
        ["Timestamp", "Loc", "Item ID", "User", "Status"],
        [[r[6], r[0], r[1] or "-", r[4] or "-", r[5]] for r in rows],
        [20, 5, 38, 20, 8]
    )
    return _pdf_download("issuing_report.pdf", "Issuing Report", lines)


@app.get("/api/reports/tray-status.pdf")
def report_tray_status():
    empty, filled = get_tray_status()
    lines = [
        "Section: Summary",
        "",
        f"Total Trays : {len(empty) + len(filled)}",
        f"Empty Trays : {len(empty)}",
        f"Filled Trays: {len(filled)}",
        "",
        "Section: Filled Tray List",
        ""
    ]
    lines += _table(
        ["Location", "Side", "Item ID", "Description"],
        [[r[0], r[1], r[2] or "-", r[3] or "-"] for r in filled],
        [8, 8, 36, 34]
    )

    lines += ["", "Section: Empty Tray List", ""]
    lines += _table(
        ["Location", "Side"],
        [[r[0], r[1]] for r in empty],
        [8, 8]
    )
    return _pdf_download("tray_status_report.pdf", "Tray Status Report", lines)


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
