import sqlite3
import os

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
