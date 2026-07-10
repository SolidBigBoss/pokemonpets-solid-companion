# ============================================================
# PokemonPets Bot - Logging
# ============================================================
# Extraído de bot.py em 08/07, na organização em módulos. Isolado à parte
# porque todos os outros módulos (state, actions, scraping, auth, bot)
# precisam dessa função — mantê-la num módulo próprio evita import circular.

from datetime import datetime

# Assinantes registrados via subscribe() — chamados a cada log(), além do
# print() normal. Usado pela HUD (hud.py) pra espelhar o log no widget de
# texto, sem que este módulo precise saber nada de tkinter/threading.
_subscribers = []


def subscribe(fn):
    """Registra uma função a ser chamada a cada log(). fn recebe
    (mensagem_formatada: str, level: str). Quem se inscreve é responsável
    por qualquer marshaling entre threads (ex: usar uma queue.Queue)."""
    _subscribers.append(fn)


def log(msg: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    icons = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "ERR": "❌", "ACTION": "🎮"}
    icon = icons.get(level, "•")
    formatted = f"[{timestamp}] {icon} {msg}"
    print(formatted)
    for fn in _subscribers:
        fn(formatted, level)
