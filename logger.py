# ============================================================
# PokemonPets Bot - Logging
# ============================================================
# Extraído de bot.py em 08/07, na organização em módulos. Isolado à parte
# porque todos os outros módulos (state, actions, scraping, auth, bot)
# precisam dessa função — mantê-la num módulo próprio evita import circular.

from datetime import datetime


def log(msg: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    icons = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "ERR": "❌", "ACTION": "🎮"}
    icon = icons.get(level, "•")
    print(f"[{timestamp}] {icon} {msg}")
