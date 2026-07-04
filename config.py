# ============================================================
# PokemonPets Bot - Configurações
# ============================================================

# URL do jogo
GAME_URL = "https://www.pokemonpets.com/gamepage.aspx"
CDP_URL = "http://localhost:9222"

# ============================================================
# SELETORES DO DOM
# ============================================================
SELECTORS = {
    # --- Popup Not Captured ---
    "not_captured_popup": ".jconfirm-scrollpane",
    "btn_battle": "#btnFightPokemon2",
    "btn_run": "#btnRunFromPokemon2",

    # --- Tela de seleção de pokemon ---
    # Usamos hotkey 1-6 (teclado)

    # --- Tela de batalha ---
    "btn_move_1": "input[whichbutton='1']",
    "btn_move_2": "input[whichbutton='2']",
    "btn_move_3": "input[whichbutton='3']",
    "btn_move_4": "input[whichbutton='4']",
    "btn_throw_ball": "#btnThrowMonsterBox",
    "btn_switch_pokemon": "#btnSelectMonster",
    "btn_surrender": None,  # mapear depois

    # HP do inimigo (mapear depois via scraper)
    "enemy_hp_text": None,

    # --- Auto Hunting ---
    "auto_hunt_div": ".AutoHunt.NiceText",

    # --- Detalhes do pokemon inimigo ---
    "btn_enemy_details": None,  # link com Wild=true
}

# ============================================================
# HOTKEYS DO JOGO
# ============================================================
HOTKEYS = {
    "enter_battle": "e",
    "run_from_battle": "f",
    "move_1": "1",
    "move_2": "2",
    "move_3": "3",
    "move_4": "4",
    "select_pokemon_1": "1",
}

# ============================================================
# POKÉBALLS
# ============================================================
# Ordem de preferência por raridade (estrelas)
# O bot vai tentar na ordem da lista até capturar
POKEBALL_BY_STARS = {
    1: ["Poke Ball", "Great Ball"],
    2: ["Great Ball", "Mega Ball"],
    3: ["Mega Ball", "Super Ball"],
    4: ["Super Ball", "Ultra Ball"],
    5: ["Ultra Ball", "Extreme Ball"],
    6: ["Master Ball"],
}

# Ball padrão se não souber a raridade
DEFAULT_POKEBALL = "Poke Ball"

# ============================================================
# TIPOS QUE NÃO SÃO AFETADOS POR FALSE SWIPE
# ============================================================
GHOST_IMMUNE_TO_FALSE_SWIPE = ["Ghost"]

# Move fallback para Ghost types (posição do botão)
FALLBACK_MOVE_POSITION = "3"  # Headbutt por enquanto

# ============================================================
# DELAYS (em segundos)
# ============================================================
DELAYS = {
    "after_click": 0.5,       # após clicar em qualquer botão
    "after_move": 2.0,        # aguarda animação do move
    "after_ball": 2.5,        # aguarda animação da ball
    "after_battle_end": 1.5,  # após fim de batalha
    "poll_interval": 1.0,     # intervalo do loop principal
    "after_keypress": 0.8,    # após pressionar hotkey
    "cdp_retry_interval": 2.0,  # intervalo entre tentativas de conectar ao Chrome (CDP)
}

# A cada quantas tentativas o bot avisa no log que ainda está esperando o Chrome
CDP_RETRY_LOG_EVERY = 5

# ============================================================
# COMPORTAMENTO
# ============================================================
# Se True, captura TODOS os pokemon não capturados
# Se False, aplica filtro de raridade mínima
CAPTURE_ALL_NOT_CAPTURED = True

# Raridade mínima pra capturar (em estrelas) — usado se acima for False
MIN_STARS_TO_CAPTURE = 2

# Sempre usar False Swipe antes de jogar a ball?
USE_FALSE_SWIPE_BEFORE_CAPTURE = True

# Posição do False Swipe no time atual
FALSE_SWIPE_POSITION = "4"

# ============================================================
# LOGGING
# ============================================================
# Pasta onde os logs de captura são salvos, um arquivo JSON por dia
# (ex: logs/captures/2026-07-04.json), gerado automaticamente pelo bot.py.
LOG_DIR = "logs/captures"
