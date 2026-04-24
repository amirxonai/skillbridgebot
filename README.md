# 🌉 SkillBridge Bot

> A Telegram bot for **skill exchange** — teach what you know, learn what you don't.

Built with **Python + aiogram v3**, clean modular architecture, and ready to scale to PostgreSQL.

---

## 🚀 Quick Start

### 1. Clone / Download the project

```bash
git clone https://github.com/your-org/skillbridge-bot.git
cd skillbridge-bot
```

### 2. Create a virtual environment (recommended)

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set your Bot Token

Get a token from [@BotFather](https://t.me/BotFather) on Telegram.

**Option A — Environment variable (recommended):**

```bash
# Windows CMD
set BOT_TOKEN=123456:ABC-DEF...

# Windows PowerShell
$env:BOT_TOKEN="123456:ABC-DEF..."

# macOS / Linux
export BOT_TOKEN=123456:ABC-DEF...
```

**Option B — Edit `skillbridge_bot/config.py` directly:**

```python
BOT_TOKEN: str = "123456:ABC-DEF..."
```

> ⚠️ Never commit your token to version control.

### 5. Run the bot

```bash
python bot.py
```

You should see:
```
2026-03-16 15:00:00 | INFO     | __main__: 🚀  SkillBridge Bot is starting…
```

---

## 🎮 Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Register → teach skill → learn skill |
| `/profile` | View your profile card |
| `/find <skill>` | List users who teach that skill |
| `/rate` | Rate your matched partner (1–5 ⭐) |
| `/invite` | Get the bot link to share |
| `/help` | Show all commands |

---

## 📁 Project Structure

```
bot2/
├── bot.py                          ← Top-level runner (shortcut)
├── requirements.txt
├── README.md
└── skillbridge_bot/
    ├── __init__.py
    ├── bot.py                      ← Main entry point
    ├── config.py                   ← Token & app settings
    │
    ├── data/
    │   ├── __init__.py
    │   └── storage.py              ← In-memory data store + helpers
    │
    ├── handlers/
    │   ├── __init__.py
    │   ├── start.py                ← /start, /help, registration FSM
    │   ├── profile.py              ← /profile
    │   ├── search.py               ← /find
    │   └── rating.py               ← /rate, /invite
    │
    ├── keyboards/
    │   ├── __init__.py
    │   └── menu.py                 ← Keyboard builders
    │
    └── services/
        ├── __init__.py
        └── matcher.py              ← Matching algorithm
```

---

## 🧠 How the Matching Works

SkillBridge uses a **bidirectional skill swap** algorithm:

```
User A.learn_skill == User B.teach_skill
    AND
User B.learn_skill == User A.teach_skill
```

When a new user registers:
1. The system immediately checks the waiting queue for a perfect match.
2. If found → both users are notified instantly.
3. If not → the user is placed in the queue and notified when a future match arrives.

---

## 📈 Upgrade Path → PostgreSQL

The data layer is deliberately isolated in `data/storage.py`.
To add PostgreSQL:
1. Keep all function signatures identical.
2. Replace dictionary lookups with `async` SQLAlchemy queries.
3. No changes required in handlers or services.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| Bot Framework | aiogram 3.x |
| HTTP Client | aiohttp |
| State Machine | aiogram FSM (MemoryStorage) |
| Database (MVP) | In-memory Python dicts |
| Database (prod) | PostgreSQL + SQLAlchemy (planned) |

---

## 📝 License

MIT — free for personal and commercial use.
