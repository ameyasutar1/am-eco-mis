# ASRS Control System - Customer Operations Manual

## 1. Purpose
This system is a web-based control interface for an **Automated Storage and Retrieval System (ASRS)**.
It allows operators to:
- Log in securely
- View live tray/location status
- Run inward (store) and outward (issue) cycles
- Search inventory
- Monitor PLC connectivity
- View analytics and download PDF reports

This manual is written for end customers, operators, supervisors, and maintenance teams.

---

## 2. System Overview

### 2.1 Core Components
- **Web UI (Browser)**: operator dashboard and reports
- **Backend API (FastAPI)**: business logic, PLC cycle orchestration, reporting
- **Database (SQLite)**: users, storage status, and movement history
- **PLC Integration (Snap7)**: actual machine communication for inward/outward cycles

### 2.2 Main Modules
- `main.py`: application routes, APIs, operation workflow, reports APIs
- `db.py`: database schema and queries
- `test.py`: PLC communication and cycle logic
- `reports_pdf.py`: PDF generation engine
- `templates/`: HTML pages
- `static/`: JS/CSS assets

---

## 3. Supported Functionalities

### 3.1 Authentication
- Login
- Register user
- Reset password
- Logout

### 3.2 Storage Operations
- View all locations (LEFT/RIGHT rack sides)
- Select location and run:
  - **INWARD** (store item)
  - **OUTWARD** (issue item)
- Location occupancy protection:
  - Inward blocked for filled trays
  - Outward blocked for empty trays

### 3.3 Material Entry Modes (Inward)
Operator can run inward using either:
1. Manual `Item ID + Description`
2. Quick material buttons: `Type A`, `Type B`, `Type C`

When Type A/B/C is clicked, the UI auto-fills:
- Item ID: UUID
- Description: predefined type description

### 3.4 Live Behavior
- Grid auto-refresh
- Operation status polling
- PLC connectivity polling (`ONLINE/OFFLINE`)
- Buttons auto-disable when PLC is offline or operation is running

### 3.5 Reports and Analytics
Reports page includes:
- Summary KPI cards
- Charts (quick-glance analytics)
- PDF download for:
  1. Full inventory report
  2. Item-wise report
  3. Location-wise report
  4. User-wise report
  5. Storing history report
  6. Issuing report
  7. Tray status report

---

## 4. Prerequisites

## 4.1 Software
- Python 3.10+ (recommended 3.12+)
- Browser: Chrome recommended
- OS: Windows preferred for production operator station

### 4.2 Network/PLC
- PLC reachable from host machine
- Default PLC config in code:
  - IP: `192.168.2.50`
  - Port: `102`
  - Rack: `0`
  - Slot: `1`

### 4.3 Python Packages
From `req.txt`:
- fastapi
- uvicorn
- jinja2
- python-multipart
- itsdangerous

Install with:
```bash
pip install -r req.txt
```

---

## 5. Installation and First Run

1. Copy project folder to target machine.
2. Create and activate virtual environment.
3. Install dependencies.
4. Start backend:
```bash
python main.py
```
5. Open:
- `http://localhost:8000/`

Default seeded credentials:
- Username: `admin`
- Password: `admin`

Change credentials immediately after first login.

---

## 6. Windows Desktop Shortcut (Operator Friendly)

Create `start_asrs.bat` in project folder:

```bat
@echo off
cd /d "C:\Users\Admin\Desktop\Codes"
start "ASRS Backend" "C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\python.exe" "c:\Users\Admin\Desktop\Codes\main.py"
timeout /t 2 /nobreak >nul
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" "http://localhost:8000/"
```

Then create Desktop shortcut to this `.bat`.

---

## 7. Operator Workflow (Step-by-Step)

## 7.1 Login
1. Open system URL
2. Enter username/password
3. Open dashboard

### 7.2 Inward Cycle (Store)
1. Select an empty location in grid
2. Choose one input mode:
   - Manual item + description, or
   - Type A/B/C button
3. Click `RUN INWARD`
4. Observe operation status message
5. Wait for completion status
6. Verify tray turns occupied color

### 7.3 Outward Cycle (Issue)
1. Select a filled location
2. Click `RUN OUTWARD`
3. Wait for completion
4. Verify location becomes empty

### 7.4 Search
- Use search box with:
  - location number, or
  - item ID/description

### 7.5 Reports
1. Click `REPORTS` on dashboard
2. Check summary and charts
3. Download required PDF report
4. For item/location/user reports, enter filter and download

---

## 8. Color and Status Interpretation
- **Green tray**: empty/available
- **Red tray**: occupied
- **Yellow tray**: currently selected
- **PLC ONLINE**: PLC reachable
- **PLC OFFLINE**: PLC not reachable; operation buttons disabled

---

## 9. Report Definitions

1. **Full Inventory**: all locations with side/item/description
2. **Item-wise**: filtered current stock + related movement history
3. **Location-wise**: specific tray current state + movement history
4. **User-wise**: all actions by selected operator
5. **Storing History**: inward action history
6. **Issuing Report**: outward action history
7. **Tray Status**: empty vs filled summary and lists

---

## 10. Assumptions

- One ASRS machine is controlled by this instance.
- Operations are serialized (one cycle at a time).
- Station IDs for cycles are fixed in code (`1`) unless reconfigured.
- DB is local SQLite (`warehouse.db`) and machine has disk persistence.
- User sessions are browser-cookie based.
- Operators have basic knowledge of ASRS mechanical safety.

---

## 11. Cautions and Safety Notes

### 11.1 Operational Safety
- Do not run physical operations without confirming machine is in safe AUTO condition.
- Ensure no human/manual intervention is inside hazardous ASRS zones during automatic motion.
- If PLC reports faults/emergency conditions, stop operation and follow site SOP.

### 11.2 Data Integrity
- Never delete `warehouse.db` in production.
- Perform periodic backups of DB.
- Ensure time on host machine is correct; reports rely on timestamps.

### 11.3 Reliability
- If PLC is unreachable, UI disables operations and reports offline.
- Long network outages may cause failed cycles in logs.
- Review failed entries in user/location reports for diagnosis.

---

## 12. Troubleshooting Guide

### Issue: Cannot start app (Python not found)
- Use absolute Python executable path in `.bat`.

### Issue: "PLC OFFLINE"
- Verify PLC IP/port, network cable, firewall, switch, and rack/slot config.

### Issue: Inward rejected
- Location may already be occupied.
- Operation already running.
- Item/description missing and no type selected.

### Issue: Outward rejected
- Location already empty.
- Another cycle is running.

### Issue: Reports have no movement data
- No completed inward/outward operations logged yet.

### Issue: UI changes not visible
- Hard refresh browser (`Ctrl + F5` / `Cmd + Shift + R`).
- Restart backend process.

---

## 13. Maintenance Recommendations

- Daily DB backup (`warehouse.db`)
- Weekly log/report audit
- Monthly user access review
- PLC communication health check before shifts

---

## 15. Suggested Future Improvements

- Role-based authorization
- Password hashing + policy enforcement
- Signed audit trail export (CSV/PDF)
- Scheduled email report delivery
- Advanced charts (time range selector)
- Production WSGI/ASGI deployment and reverse proxy hardening

---

## 16. Support Handover Checklist

Before handover to end customer:
- [ ] Verify PLC connection from deployment machine
- [ ] Change default admin credentials
- [ ] Validate inward/outward cycle on test trays
- [ ] Validate all 7 report downloads
- [ ] Verify desktop launcher and browser startup
- [ ] Train operators on safety SOP
- [ ] Provide DB backup/restore SOP

---

## 17. Contact and Change Control
Maintain a change log for:
- PLC mapping changes
- Endpoint/DB schema updates
- Report format updates
- Operator SOP revisions

Store release notes per deployed version for traceability.
