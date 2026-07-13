import os
import json
import uuid
import hashlib
from datetime import datetime

DATA_DIR = os.path.join(os.getcwd(), "data")
DB_FILE = os.path.join(DATA_DIR, "db.json")

# Ensure data directory exists
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)

INITIAL_DB = {
    "users": [],
    "sessions": [],
    "profiles": [],
    "documents": [],
    "applications": [],
    "tasks": [],
    "roadmaps": [],
    "chats": []
}

_memory_db = None

def load_db():
    global _memory_db
    if _memory_db is not None:
        return _memory_db
    
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r", encoding="utf-8") as f:
                _memory_db = json.load(f)
                return _memory_db
    except Exception as e:
        print(f"Failed to load db.json, resetting... Error: {e}")
        
    _memory_db = json.loads(json.dumps(INITIAL_DB))
    save_db(_memory_db)
    return _memory_db

def save_db(data):
    global _memory_db
    _memory_db = data
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Warning: Failed to write to db.json: {e}")

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

# --- AUTHENTICATION ---

def signup(email: str, password_string: str, full_name: str):
    data = load_db()
    clean_email = email.strip().lower()
    
    # Check if user already exists
    if any(u["email"] == clean_email for u in data["users"]):
        return {"error": "An account with this email already exists."}
    
    user_id = str(uuid.uuid4())
    new_user = {
        "id": user_id,
        "email": clean_email,
        "passwordHash": hash_password(password_string),
        "full_name": full_name.strip()
    }
    
    data["users"].append(new_user)
    
    # Auto-create profile
    new_profile = {
        "id": user_id,
        "full_name": full_name.strip(),
        "email": clean_email,
        "college": "",
        "target_role": "Full Stack Developer",
        "current_level": "Beginner",
        "daily_hours": 4,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    data["profiles"].append(new_profile)
    
    save_db(data)
    return {"user": new_user}

def login(email: str, password_string: str):
    data = load_db()
    clean_email = email.strip().lower()
    
    user = next((u for u in data["users"] if u["email"] == clean_email), None)
    if not user or user["passwordHash"] != hash_password(password_string):
        return {"error": "Invalid email or password."}
        
    # Python Streamlit handles sessions in session_state, so we don't necessarily 
    # need session tables, but keeping it database-compliant just in case.
    token = hashlib.sha256(os.urandom(32)).hexdigest()
    expires_at = datetime.utcnow().isoformat() + "Z" # we can set expiry, but Streamlit is stateful
    
    data["sessions"].append({
        "token": token,
        "userId": user["id"],
        "expiresAt": expires_at
    })
    save_db(data)
    
    return {"token": token, "user": user}

# --- PROFILES ---

def get_profile(user_id: str):
    data = load_db()
    return next((p for p in data["profiles"] if p["id"] == user_id), None)

def update_profile(user_id: str, updates: dict):
    data = load_db()
    profile = next((p for p in data["profiles"] if p["id"] == user_id), None)
    
    if not profile:
        profile = {
            "id": user_id,
            "full_name": updates.get("full_name", "New User"),
            "email": updates.get("email", ""),
            "college": updates.get("college", ""),
            "target_role": updates.get("target_role", "Full Stack Developer"),
            "current_level": updates.get("current_level", "Beginner"),
            "daily_hours": int(updates.get("daily_hours", 4)),
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        data["profiles"].append(profile)
    else:
        for k, v in updates.items():
            if k != "id":
                profile[k] = v
                
    save_db(data)
    return profile

# --- APPLICATIONS ---

def get_applications(user_id: str):
    data = load_db()
    return [a for a in data["applications"] if a["user_id"] == user_id]

def create_application(user_id: str, app_data: dict):
    data = load_db()
    new_app = {
        **app_data,
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    data["applications"].append(new_app)
    save_db(data)
    return new_app

def update_application(user_id: str, app_id: str, updates: dict):
    data = load_db()
    app = next((a for a in data["applications"] if a["id"] == app_id and a["user_id"] == user_id), None)
    if not app:
        return None
        
    for k, v in updates.items():
        if k not in ["id", "user_id"]:
            app[k] = v
            
    save_db(data)
    return app

def delete_application(user_id: str, app_id: str):
    data = load_db()
    initial_len = len(data["applications"])
    data["applications"] = [a for a in data["applications"] if not (a["id"] == app_id and a["user_id"] == user_id)]
    deleted = len(data["applications"]) < initial_len
    if deleted:
        save_db(data)
    return deleted

# --- TASKS ---

def get_tasks(user_id: str):
    data = load_db()
    return [t for t in data["tasks"] if t["user_id"] == user_id]

def create_task(user_id: str, task_data: dict):
    data = load_db()
    new_task = {
        **task_data,
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    data["tasks"].append(new_task)
    save_db(data)
    return new_task

def update_task(user_id: str, task_id: str, updates: dict):
    data = load_db()
    task = next((t for t in data["tasks"] if t["id"] == task_id and t["user_id"] == user_id), None)
    if not task:
        return None
        
    for k, v in updates.items():
        if k not in ["id", "user_id"]:
            task[k] = v
            
    save_db(data)
    return task

def delete_task(user_id: str, task_id: str):
    data = load_db()
    initial_len = len(data["tasks"])
    data["tasks"] = [t for t in data["tasks"] if not (t["id"] == task_id and t["user_id"] == user_id)]
    deleted = len(data["tasks"]) < initial_len
    if deleted:
        save_db(data)
    return deleted

# --- DOCUMENTS ---

def get_documents(user_id: str):
    data = load_db()
    return [d for d in data["documents"] if d["user_id"] == user_id]

def create_document(user_id: str, doc_data: dict):
    data = load_db()
    new_doc = {
        **doc_data,
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "uploaded_at": datetime.utcnow().isoformat() + "Z"
    }
    data["documents"].append(new_doc)
    save_db(data)
    return new_doc

def delete_document(user_id: str, doc_id: str):
    data = load_db()
    initial_len = len(data["documents"])
    data["documents"] = [d for d in data["documents"] if not (d["id"] == doc_id and d["user_id"] == user_id)]
    deleted = len(data["documents"]) < initial_len
    if deleted:
        save_db(data)
    return deleted

# --- ROADMAPS ---

def get_roadmaps(user_id: str):
    data = load_db()
    return [r for r in data["roadmaps"] if r["user_id"] == user_id]

def save_roadmap(user_id: str, roadmap_data: dict):
    data = load_db()
    # Delete previous roadmaps to maintain focus
    data["roadmaps"] = [r for r in data["roadmaps"] if r["user_id"] != user_id]
    
    new_roadmap = {
        **roadmap_data,
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    data["roadmaps"].append(new_roadmap)
    save_db(data)
    return new_roadmap

def update_roadmap_progress(user_id: str, roadmap_id: str, progress: int):
    data = load_db()
    roadmap = next((r for r in data["roadmaps"] if r["id"] == roadmap_id and r["user_id"] == user_id), None)
    if not roadmap:
        return None
        
    roadmap["progress"] = progress
    save_db(data)
    return roadmap

def delete_roadmap(user_id: str, roadmap_id: str):
    data = load_db()
    initial_len = len(data["roadmaps"])
    data["roadmaps"] = [r for r in data["roadmaps"] if not (r["id"] == roadmap_id and r["user_id"] == user_id)]
    deleted = len(data["roadmaps"]) < initial_len
    if deleted:
        save_db(data)
    return deleted

# --- COPILOT CHATS ---

def get_chat_history(user_id: str):
    data = load_db()
    chats = data.get("chats", [])
    user_chat = next((c for c in chats if c["user_id"] == user_id), None)
    return user_chat["messages"] if user_chat else []

def add_chat_message(user_id: str, role: str, content: str):
    data = load_db()
    if "chats" not in data:
        data["chats"] = []
        
    chats = data["chats"]
    user_chat = next((c for c in chats if c["user_id"] == user_id), None)
    if not user_chat:
        user_chat = {"user_id": user_id, "messages": []}
        chats.append(user_chat)
        
    new_message = {
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    user_chat["messages"].append(new_message)
    save_db(data)
    return user_chat["messages"]

def clear_chat_history(user_id: str):
    data = load_db()
    chats = data.get("chats", [])
    user_chat = next((c for c in chats if c["user_id"] == user_id), None)
    if user_chat:
        user_chat["messages"] = []
        save_db(data)
