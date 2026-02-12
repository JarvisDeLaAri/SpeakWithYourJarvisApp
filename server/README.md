# Server — Pipecat Voice Pipeline

See `../plans/SERVER_PLAN.md` for full architecture.

## Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env  # Edit with your values
python main.py
```

## Requirements
- Choose an available port for the server and set it in `.env` (`PORT=`)
- Open that port in your firewall (e.g. `ufw allow <port>`)
- Add the port to your service registry if you maintain one
