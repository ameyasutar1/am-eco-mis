# ASRS System - Customer User Manual

This document is for customer teams who will **use, supervise, and maintain** the ASRS software.
It explains the system in simple terms and gives clear operating steps.

## 1. What This System Does
This ASRS software is used to:
- Store material in trays (**Inward**) 
- Issue material from trays (**Outward**)
- Show tray status live on screen
- Track operation history
- Generate management reports (PDF)

In short: this is the digital control panel for your ASRS machine.

---

## 2. Main Screens

### 2.1 Login Screen
- User enters username and password
- Options: Register, Forgot Password

### 2.2 Dashboard Screen
Main operator screen with:
- Left and Right storage grids (tray locations)
- Search box (location/item)
- PLC connection status (ONLINE/OFFLINE)
- Inward/Outward operation panel
- Quick material buttons: Type A, Type B, Type C
- Reports button

### 2.3 Reports Screen
Used by supervisor/admin for:
- KPI summary cards
- Charts (quick data view)
- Downloading PDF reports

---

## 3. Color Meaning on Dashboard
- **Green tray** = Empty tray
- **Red tray** = Filled tray
- **Yellow tray** = Selected tray
- **PLC ONLINE** = machine communication available
- **PLC OFFLINE** = machine not reachable, operations blocked for safety

---

## 4. Daily Operation Steps

## 4.1 Login
1. Open system URL: `http://localhost:8000/`
2. Enter credentials
3. Go to dashboard

### 4.2 Inward (Store Material)
1. Click an **empty** tray location
2. Choose one method:
   - Enter `Item ID + Description` manually, or
   - Click Type A / Type B / Type C (auto-fills fields)
3. Click `RUN INWARD`
4. Wait for completion message
5. Confirm tray changes to red (filled)

### 4.3 Outward (Issue Material)
1. Click a **filled** tray location
2. Click `RUN OUTWARD`
3. Wait for completion message
4. Confirm tray changes to green (empty)

### 4.4 Search
- Enter location number or item keyword in search box
- System jumps to matching location

---

## 5. Smart Safety Checks in Software
The system automatically prevents wrong operations:
- Inward is blocked on already filled location
- Outward is blocked on empty location
- If one cycle is running, second cycle is blocked
- If PLC is offline, operation buttons are disabled

---

## 6. Reports Available (PDF)
1. Full Inventory Report
2. Item-wise Report
3. Location-wise Report
4. User-wise Report
5. Storing History Report
6. Issuing Report
7. Tray Status Report (empty vs filled)

How to use:
1. Open Reports page
2. Fill filter field if required (item/location/user)
3. Click Download PDF

---

## 7. Charts/Analytics on Reports Page
Reports page gives quick visual understanding:
- Tray fill ratio
- Side-wise utilization (LEFT/RIGHT)
- Material type distribution
- 7-day inward/outward trend

Use this screen for shift reviews and management checks.

---

## 8. Customer Assumptions
This system assumes:
- ASRS PLC network is configured correctly
- Only one cycle should run at a time
- Operators are trained for machine safety
- System is used from authorized PCs
- Database file is not manually edited/deleted

---

## 9. Caution and Safety Notes

### 9.1 Machine Safety
- Never run cycle if any person is inside ASRS hazard zone
- Follow your plant emergency and lockout procedures
- If PLC fault/emergency appears, stop and call maintenance

### 9.2 Data Safety
- Take regular backup of `warehouse.db`
- Do not delete database file
- Keep system clock correct (reports use timestamp)

### 9.3 Access Safety
- Change default admin password after deployment
- Do not share operator credentials
- Use restricted network where possible

---

## 10. Common Problems and Quick Fix

### Problem: App does not start
- Check Python path in startup `.bat`
- Confirm project folder path is correct

### Problem: PLC OFFLINE shown
- Check PLC power/network cable
- Check IP, rack, slot, and port config
- Check firewall/network rules

### Problem: Inward/Outward button not working
- Operation may already be running
- PLC may be offline
- Wrong tray state selected (filled/empty mismatch)

### Problem: UI not updating
- Hard refresh browser (`Ctrl+F5`)
- Restart backend process

### Problem: Report is empty
- No matching data in filter
- No movement history for selected criteria

---

## 11. Deployment and Start (Windows Shortcut)
Use a desktop shortcut for easy operator launch.

Example `start_asrs.bat`:

```bat
@echo off
cd /d "C:\Users\Admin\Desktop\Codes"
start "ASRS Backend" "C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\python.exe" "c:\Users\Admin\Desktop\Codes\main.py"
timeout /t 2 /nobreak >nul
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" "http://localhost:8000/"
```

Then create desktop shortcut of this `.bat`.

---

## 12. Recommended Customer SOP (Daily)
1. Start system
2. Check PLC status = ONLINE
3. Run production inward/outward operations
4. Supervisor checks reports at shift end
5. Backup database daily

---

## 13. Known Limitations (Current Version)
- Password storage is basic (not enterprise IAM)
- Local SQLite database (single machine file)
- Reports are generated as text-style PDFs

---

## 14. Support Handover Checklist
Before final customer handover, confirm:
- [ ] Login works
- [ ] Inward/Outward cycle tested
- [ ] PLC online/offline indication tested
- [ ] All report downloads tested
- [ ] Desktop launcher tested
- [ ] Customer team trained on operation + safety

---

## 15. Contact / Support Process
If issue occurs:
1. Capture screenshot
2. Note time and operator username
3. Note tray location and action attempted
4. Share with support/maintenance team

This helps fast root-cause analysis.
