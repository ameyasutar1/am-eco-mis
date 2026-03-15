import sqlite3
import os
from datetime import datetime

# Absolute path (prevents new DB creation issue)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "warehouse.db")


def conn():
    return sqlite3.connect(DB, check_same_thread=False)


def init_db():
    c = conn()
    cur = c.cursor()

    # USERS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    # STORAGE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS storage(
        location_id INTEGER PRIMARY KEY,
        side TEXT,
        item_id TEXT,
        description TEXT
    )
    """)

    # MOVEMENT LOGS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS movement_logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT,
        location_id INTEGER,
        item_id TEXT,
        description TEXT,
        material_type TEXT,
        username TEXT,
        status TEXT,
        error_msg TEXT,
        created_at TEXT
    )
    """)

    # Default admin
    cur.execute("""
    INSERT OR IGNORE INTO users(username,password)
    VALUES('admin','admin')
    """)

    # Seed locations
    for i in range(1,298):
        side = "RIGHT" if i <= 149 else "LEFT"
        cur.execute("""
        INSERT OR IGNORE INTO storage
        VALUES(?,?,NULL,NULL)
        """,(i,side))

    c.commit()
    c.close()


def utc_now():
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


# ---------- AUTH ----------
def login(u,p):
    c=conn()
    cur=c.cursor()
    cur.execute("""
    SELECT * FROM users
    WHERE username=? AND password=?
    """,(u,p))
    r=cur.fetchone()
    c.close()
    return r


def create_user(u,p):
    c=conn()
    cur=c.cursor()
    cur.execute("""
    INSERT INTO users(username,password)
    VALUES(?,?)
    """,(u,p))
    c.commit()
    c.close()


def reset_password(u,p):
    c=conn()
    cur=c.cursor()
    cur.execute("""
    UPDATE users SET password=?
    WHERE username=?
    """,(p,u))
    c.commit()
    c.close()


# ---------- STORAGE ----------
def all_locations():
    c=conn()
    cur=c.cursor()
    cur.execute("""
    SELECT * FROM storage
    ORDER BY location_id
    """)
    r=cur.fetchall()
    c.close()
    return r


def update_store(loc,item,desc):
    c=conn()
    cur=c.cursor()
    cur.execute("""
    UPDATE storage
    SET item_id=?, description=?
    WHERE location_id=?
    """,(item,desc,loc))
    c.commit()
    c.close()


def outward(loc):
    c=conn()
    cur=c.cursor()
    cur.execute("""
    UPDATE storage
    SET item_id=NULL, description=NULL
    WHERE location_id=?
    """,(loc,))
    c.commit()
    c.close()


def find_loc(loc):
    c=conn()
    cur=c.cursor()
    cur.execute("""
    SELECT * FROM storage
    WHERE location_id=?
    """,(loc,))
    r=cur.fetchone()
    c.close()
    return r


def search(q):
    q=f"%{q}%"
    c=conn()
    cur=c.cursor()
    cur.execute("""
    SELECT * FROM storage
    WHERE item_id LIKE ? OR description LIKE ?
    """,(q,q))
    r=cur.fetchone()
    c.close()
    return r


# ---------- LOGS / REPORTS ----------
def log_movement(action, location_id, item_id, description, material_type, username, status, error_msg=None):
    c=conn()
    cur=c.cursor()
    cur.execute("""
    INSERT INTO movement_logs(
        action, location_id, item_id, description, material_type,
        username, status, error_msg, created_at
    )
    VALUES(?,?,?,?,?,?,?,?,?)
    """,(
        action,
        location_id,
        item_id,
        description,
        material_type,
        username,
        status,
        error_msg,
        utc_now()
    ))
    c.commit()
    c.close()


def report_summary():
    c=conn()
    cur=c.cursor()

    cur.execute("SELECT COUNT(*) FROM storage")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM storage WHERE item_id IS NOT NULL")
    filled = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]

    cur.execute("""
    SELECT COUNT(*) FROM movement_logs
    WHERE action IN ('INWARD', 'MANUAL_ADD') AND status='SUCCESS'
    """)
    inward_ok = cur.fetchone()[0]

    cur.execute("""
    SELECT COUNT(*) FROM movement_logs
    WHERE action IN ('OUTWARD', 'MANUAL_REMOVE') AND status='SUCCESS'
    """)
    outward_ok = cur.fetchone()[0]

    c.close()
    return {
        "total_locations": total,
        "filled_trays": filled,
        "empty_trays": total - filled,
        "total_users": users,
        "stored_count": inward_ok,
        "issued_count": outward_ok
    }


def get_full_inventory():
    c=conn()
    cur=c.cursor()
    cur.execute("""
    SELECT location_id, side, item_id, description
    FROM storage
    ORDER BY location_id
    """)
    rows=cur.fetchall()
    c.close()
    return rows


def get_item_wise(item_query):
    q=f"%{item_query}%"
    c=conn()
    cur=c.cursor()
    cur.execute("""
    SELECT location_id, side, item_id, description
    FROM storage
    WHERE item_id LIKE ? OR description LIKE ?
    ORDER BY location_id
    """,(q,q))
    current=cur.fetchall()

    cur.execute("""
    SELECT action, location_id, item_id, description, material_type, username, status, created_at
    FROM movement_logs
    WHERE item_id LIKE ? OR description LIKE ?
    ORDER BY id DESC
    """,(q,q))
    history=cur.fetchall()
    c.close()
    return current, history


def get_location_wise(loc):
    c=conn()
    cur=c.cursor()
    cur.execute("""
    SELECT location_id, side, item_id, description
    FROM storage
    WHERE location_id=?
    """,(loc,))
    current=cur.fetchone()

    cur.execute("""
    SELECT action, location_id, item_id, description, material_type, username, status, created_at
    FROM movement_logs
    WHERE location_id=?
    ORDER BY id DESC
    """,(loc,))
    history=cur.fetchall()
    c.close()
    return current, history


def get_user_wise(username):
    c=conn()
    cur=c.cursor()
    cur.execute("""
    SELECT action, location_id, item_id, description, material_type, status, created_at
    FROM movement_logs
    WHERE username=?
    ORDER BY id DESC
    """,(username,))
    rows=cur.fetchall()
    c.close()
    return rows


def get_storing_history():
    c=conn()
    cur=c.cursor()
    cur.execute("""
    SELECT action, location_id, item_id, description, material_type, username, status, created_at
    FROM movement_logs
    WHERE action IN ('INWARD', 'MANUAL_ADD')
    ORDER BY id DESC
    """)
    rows=cur.fetchall()
    c.close()
    return rows


def get_issuing_history():
    c=conn()
    cur=c.cursor()
    cur.execute("""
    SELECT action, location_id, item_id, description, material_type, username, status, created_at
    FROM movement_logs
    WHERE action IN ('OUTWARD', 'MANUAL_REMOVE')
    ORDER BY id DESC
    """)
    rows=cur.fetchall()
    c.close()
    return rows


def get_manual_history():
    c=conn()
    cur=c.cursor()
    cur.execute("""
    SELECT action, location_id, item_id, description, username, status, created_at
    FROM movement_logs
    WHERE action IN ('MANUAL_ADD', 'MANUAL_REMOVE')
    ORDER BY id DESC
    """)
    rows=cur.fetchall()
    c.close()
    return rows


def get_tray_status():
    c=conn()
    cur=c.cursor()
    cur.execute("""
    SELECT location_id, side, item_id, description
    FROM storage
    WHERE item_id IS NULL
    ORDER BY location_id
    """)
    empty=cur.fetchall()

    cur.execute("""
    SELECT location_id, side, item_id, description
    FROM storage
    WHERE item_id IS NOT NULL
    ORDER BY location_id
    """)
    filled=cur.fetchall()
    c.close()
    return empty, filled


def get_reports_chart_data():
    c=conn()
    cur=c.cursor()

    cur.execute("SELECT COUNT(*) FROM storage")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM storage WHERE item_id IS NOT NULL")
    filled = cur.fetchone()[0]
    empty = total - filled

    cur.execute("""
    SELECT side,
           SUM(CASE WHEN item_id IS NOT NULL THEN 1 ELSE 0 END) as filled_count,
           SUM(CASE WHEN item_id IS NULL THEN 1 ELSE 0 END) as empty_count
    FROM storage
    GROUP BY side
    ORDER BY side
    """)
    side_rows = cur.fetchall()

    cur.execute("""
    SELECT COALESCE(material_type, 'UNKNOWN') as material_type, COUNT(*) as cnt
    FROM movement_logs
    WHERE action IN ('INWARD', 'MANUAL_ADD') AND status='SUCCESS'
    GROUP BY COALESCE(material_type, 'UNKNOWN')
    ORDER BY cnt DESC
    """)
    material_rows = cur.fetchall()

    cur.execute("""
    SELECT substr(created_at,1,10) as d,
           SUM(CASE WHEN action IN ('INWARD', 'MANUAL_ADD') AND status='SUCCESS' THEN 1 ELSE 0 END) as inward_cnt,
           SUM(CASE WHEN action IN ('OUTWARD', 'MANUAL_REMOVE') AND status='SUCCESS' THEN 1 ELSE 0 END) as outward_cnt
    FROM movement_logs
    GROUP BY substr(created_at,1,10)
    ORDER BY d DESC
    LIMIT 7
    """)
    trend_rows = cur.fetchall()

    c.close()
    trend_rows.reverse()
    return {
        "tray_ratio": {"filled": filled, "empty": empty, "total": total},
        "side_utilization": [
            {"side": r[0], "filled": r[1], "empty": r[2]} for r in side_rows
        ],
        "material_distribution": [
            {"material_type": r[0], "count": r[1]} for r in material_rows
        ],
        "movement_trend": [
            {"date": r[0], "inward": r[1], "outward": r[2]} for r in trend_rows
        ]
    }
