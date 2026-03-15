# ASRS System - Customer Operations & Feature Guide

This guide is written for production operators, supervisors, and plant support teams.
It explains:
1. How to run the system day-to-day
2. What each screen does
3. How the software is built and how features work

## 1. System Purpose

The ASRS software is the control interface for storage and issuing operations.

It helps your team to:
- Store material into tray locations (`Inward`)
- Issue material from tray locations (`Outward`)
- Manually add/remove inventory records when needed (`Manual Entry`)
- View live location status
- Track operator-wise activity history
- Download PDF reports for operations and management

## 2. Quick Start

1. Open `http://localhost:8000/`
2. Login with your user credentials
3. Use one of the main pages:
- `Dashboard` for machine cycles
- `Manual Entry` for non-cycle data updates
- `Reports` for analytics and PDF downloads

## 3. Main Screens

### 3.1 Login
- User authentication
- Register / password reset support

### 3.2 Dashboard
Main cycle operation page:
- Left/Right tray grid view
- Search by location, item ID, or description
- PLC status (Online/Offline)
- Inward and Outward action panel
- Quick material shortcuts (`Type A`, `Type B`, `Type C`)
- Navigation to Reports and Manual Entry

### 3.3 Manual Entry
Used when inventory data must be updated without running a PLC cycle:
- Select location from tray grid
- Add data manually (`Item ID`, `Description`)
- Remove data manually
- Real-time cycle status check
- Action blocking if a cycle is running at the same location
- All manual actions are logged with username and timestamp

### 3.4 Reports
Supervisor and management page:
- KPI summary cards
- Operational charts
- Report downloads in PDF format

## 4. Tray & Status Meaning

- `Green tray` = Empty location
- `Red tray` = Occupied location
- `Yellow tray` = Selected location
- `PLC ONLINE` = Communication available for cycle commands
- `PLC OFFLINE` = Cycle commands are disabled for safety
- `CYCLE RUNNING LOC X` (Manual page) = manual changes blocked for that location

## 5. Operator Workflows

### 5.1 Inward (Store Material via PLC)
1. Open `Dashboard`
2. Select an empty location
3. Enter `Item ID` and `Description`, or choose `Type A/B/C`
4. Click `RUN INWARD`
5. Wait for completion message
6. Verify tray turns red

### 5.2 Outward (Issue Material via PLC)
1. Open `Dashboard`
2. Select a filled location
3. Click `RUN OUTWARD`
4. Wait for completion message
5. Verify tray turns green

### 5.3 Manual Add (No PLC cycle)
1. Open `Manual Entry`
2. Select an empty location
3. Enter `Item ID` and `Description`
4. Click `MANUALLY ADD`
5. Confirm success message and updated tray state

### 5.4 Manual Remove (No PLC cycle)
1. Open `Manual Entry`
2. Select a filled location
3. Click `MANUALLY REMOVE`
4. Confirm success message and updated tray state

### 5.5 Search
- Enter location number, item ID, or description in search
- System jumps to matching location

## 6. Built-In Operational Controls

The software enforces safe and consistent operation logic:
- Inward blocked on occupied locations
- Outward blocked on empty locations
- Single cycle at a time
- Dashboard cycle actions blocked when PLC is offline
- Manual add/remove blocked if a cycle is running at that same location
- Every operation is logged with user, status, and timestamp

## 7. Reports Available (PDF)

1. Full Inventory Report
2. Item-wise Report
3. Location-wise Report
4. User-wise Report
5. Storing History Report (`Inward + Manual Add`)
6. Issuing Report (`Outward + Manual Remove`)
7. Tray Status Report
8. Manual Activity Report (`who manually added/removed data`)

How to use:
1. Open `Reports`
2. Enter filter values where needed (item/location/user)
3. Click `Download PDF`

## 8. Charts on Reports Page

- Tray fill ratio
- Side-wise utilization (`LEFT` / `RIGHT`)
- Material distribution
- 7-day movement trend

This gives fast shift-level and daily visibility.

## 9. Software Feature Architecture (Code Overview)

This section explains how the code is organized so customer IT/support teams can understand behavior quickly.

### 9.1 `main.py` (Application + Routes)
`main.py` is the FastAPI entry point.

It handles:
- Authentication routes (`/`, `/login`, `/register`, `/forgot`, `/logout`)
- UI page routes (`/dashboard`, `/manual-entry`, `/reports`)
- API routes for operations and reporting
- Operation state tracking (running/idle, location, status message)
- Background thread execution for Inward/Outward cycles

Key idea:
- Cycle operations are started from API and run in background threads.
- UI polls operation status to show live progress.

### 9.2 `test.py` (PLC Communication Layer)
`test.py` contains PLC-level logic using `snap7`.

It provides:
- PLC connectivity check
- Read/write bit and DINT helpers
- `inward_cycle(...)` implementation
- `outward_cycle(...)` implementation
- Handshake, pulse, and completion waiting logic

### 9.3 `db.py` (Database + Reporting Queries)
`db.py` manages SQLite data and report data preparation.

It includes:
- User table operations
- Storage table operations (location/item/description)
- Movement logging
- Summary and history queries used by reports

Core tables:
- `users`
- `storage`
- `movement_logs`

### 9.4 `templates/` (HTML Pages)
- `dashboard.html` for cycle operations
- `manual_entry.html` for manual add/remove
- `reports.html` for analytics and report downloads
- auth pages for login/register/forgot

### 9.5 `static/` (Frontend Logic + Styling)
- `app.js` for dashboard behavior
- `manual.js` for manual entry behavior
- `reports.js` for charts/report downloads
- `style.css` for UI styling

### 9.6 `reports_pdf.py` (PDF Generator)
Creates downloadable text-style PDF reports from prepared rows and sections.

## 10. Feature Data Flow

### 10.1 Inward/Outward Flow
1. Operator clicks action on Dashboard
2. API validates selected location and operation state
3. PLC cycle runs (background thread)
4. On success, storage table updates
5. Movement log entry is created
6. UI refresh shows latest tray state

### 10.2 Manual Add/Remove Flow
1. Operator selects location on Manual Entry page
2. API validates location and cycle status
3. Storage table updates directly (no PLC cycle)
4. `MANUAL_ADD` or `MANUAL_REMOVE` is logged with user
5. Report history reflects the action immediately

## 11. Startup (Windows Shortcut Example)

Use a launcher file for easy operator start.

```bat
@echo off
cd /d "C:\Users\Admin\Desktop\Codes"
start "ASRS Backend" "C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\python.exe" "C:\Users\Admin\Desktop\Codes\main.py"
timeout /t 2 /nobreak >nul
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" "http://localhost:8000/"
```

## 12. Daily Operations Checklist

1. Start backend and open UI
2. Confirm PLC status
3. Perform Inward/Outward operations on Dashboard
4. Use Manual Entry where non-cycle updates are required
5. Review Reports at shift end
6. Take regular `warehouse.db` backup

## 13. Support Handover Checklist

- [ ] Login and user access verified
- [ ] Inward cycle tested
- [ ] Outward cycle tested
- [ ] Manual add/remove tested
- [ ] Report downloads tested
- [ ] Supervisor team trained on workflow

## 14. Incident Information to Capture

For fast support response, share:
1. Screenshot
2. Time of issue
3. Username
4. Location number
5. Action attempted

This helps support and maintenance teams diagnose quickly.
