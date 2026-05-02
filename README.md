# ChatApp — Web-Based Real-Time Chat Application

> **SRS Project** | Software Construction & Development  
> Student: Huzaifa Kamran
> Stack: Python · Django 4.x · Django Channels · WebSockets · MySQL

---

## Features

| Feature | Status |
|---------|--------|
| User Registration & Login | ✅ |
| Secure Password Hashing | ✅ |
| Real-Time Messaging (WebSockets) | ✅ |
| Persistent Chat History | ✅ |
| Unread Message Badges | ✅ |
| User Search | ✅ |
| Logout & Session Management | ✅ |
| Admin Panel | ✅ |
| Responsive Dark UI | ✅ |

---

## Project Structure

```
chatapp/
├── chatapp/              ← Django project config
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py           ← WebSocket entry point
│   └── wsgi.py
├── chat/                 ← Chat app (messages, WebSocket consumer)
│   ├── models.py         ← Message model
│   ├── consumers.py      ← WebSocket consumer (real-time logic)
│   ├── views.py          ← Home, room, search views
│   ├── routing.py        ← WebSocket URL routing
│   ├── urls.py
│   ├── admin.py
│   └── templates/chat/
│       ├── home.html     ← Conversation list
│       ├── room.html     ← Chat window
│       └── search.html   ← User search
├── users/                ← Authentication app
│   ├── models.py         ← CustomUser model
│   ├── forms.py          ← Register / Login forms
│   ├── views.py
│   ├── urls.py
│   └── templates/users/
│       ├── login.html
│       ├── register.html
│       ├── profile.html
│       └── logout_confirm.html
├── templates/
│   └── base.html         ← Shared base template
├── .vscode/
│   ├── launch.json       ← Debug configurations
│   ├── settings.json     ← VS Code settings
│   └── extensions.json   ← Recommended extensions
├── manage.py
├── requirements.txt
└── README.md
```

---

## Setup Instructions (Windows — VS Code)

### 1. Open the Project
```
File → Open Folder → select the chatapp/ folder
```

### 2. Create a Virtual Environment
Open the VS Code terminal (`Ctrl + `` ` ``) and run:
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Apply Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create a Superuser (optional, for admin panel)
```bash
python manage.py createsuperuser
```

### 6. Run the Server

**Option A — VS Code Debugger (recommended)**  
Press `F5` and select **"Run Daphne (WebSocket Support)"**

**Option B — Terminal**
```bash
daphne -b 127.0.0.1 -p 8000 chatapp.asgi:application
```

### 7. Open in Browser
```
http://127.0.0.1:8000
```

---

## How to Use

1. Open two different browsers (e.g. Chrome + Firefox)
2. Register two separate accounts
3. Click on a user's name to open a chat room
4. Type a message and press **Enter** or the send button
5. Messages appear instantly in both windows — real-time via WebSockets!

---

## Architecture (MVC/MVT)

| MVC Layer | Django Equivalent | File |
|-----------|-------------------|------|
| Model     | models.py         | `users/models.py`, `chat/models.py` |
| View      | templates/        | All `*.html` files |
| Controller| views.py + consumers.py | `chat/views.py`, `chat/consumers.py` |

---

## Admin Panel
```
http://127.0.0.1:8000/admin/
```
Log in with your superuser credentials to view and manage all users and messages.

---

## Tech Stack

- **Python 3.10+**
- **Django 4.x** — MVT framework
- **Django Channels 4.x** — WebSocket support (ASGI)
- **Daphne** — ASGI server
- **SQLite** — Default database (swap for PostgreSQL in production)
- **In-Memory Channel Layer** — No Redis required for local development
