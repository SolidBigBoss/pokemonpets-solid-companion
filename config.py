# ============================================================
# PokemonPets Bot - Configurações
# ============================================================

import os
from dotenv import load_dotenv

load_dotenv()  # carrega variáveis do arquivo .env (não versionado)

# ============================================================
# CREDENCIAIS (login automático)
# ============================================================
# Lidas do .env — NUNCA colocar usuário/senha direto aqui.
POKEMONPETS_USERNAME = os.getenv("POKEMONPETS_USERNAME")
POKEMONPETS_PASSWORD = os.getenv("POKEMONPETS_PASSWORD")

# URL do jogo
GAME_URL = "https://www.pokemonpets.com/gamepage.aspx"
LOGIN_URL = "https://www.pokemonpets.com/Login"
CDP_URL = "http://localhost:9222"

# Fragmento de URL da página intermediária pós-login (antes de entrar no mapa)
WELCOME_URL_FRAGMENT = "WelcomePage.aspx"

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
    "auto_hunt_toggle": "#imgBtnEnableAutoHunt",

    # --- Detalhes do pokemon inimigo ---
    "btn_enemy_details": None,  # link com Wild=true

    # --- Login ---
    "login_username": "#ctl00_ContentPlaceHolder_txtUserName",
    "login_password": "#ctl00_ContentPlaceHolder_txtPassword",
    "login_submit": "#btnLogin",

    # --- Página de boas-vindas (pós-login) ---
    "welcome_game_page_link": 'a.myButtonGreen[href="gamepage.aspx"]',

    # --- Dropdown de Poké Ball ---
    "ball_dropdown_title": "#dropDownMonsterBoxes_title",
    "ball_dropdown_list": "#dropDownMonsterBoxes_child li",

    # --- Tela de recompensa (Obtained Rewards) ---
    # :visible é extensão do próprio Playwright — existem 2 elementos com esse
    # seletor na página (um oculto), então precisa filtrar pelo visível.
    "btn_return_adventure": 'a[href="gamepage.aspx"].buttonRed:visible',

    # --- Link do Pokédex do inimigo (dentro da tela de batalha) ---
    # A imagem do pokémon inimigo é um <a> que aponta pra página da espécie
    # no Pokédex (ex: /Trubbish-Pokemon-Pokedex-568).
    "enemy_pokedex_image": "#MonsterImageUser2",
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
# OBSOLETO: substituído pela checagem dinâmica de efetividade (0x) lida
# direto da tela de batalha em bot.py/handle_battle(). Mantido só de referência
# — mais confiável que uma lista fixa, já que o jogo tem fusões/fakemon.
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

# OBSOLETO: substituído pela busca dinâmica do move "False Swipe" pelo NOME
# (bot.py/handle_battle()), já que a posição (whichbutton) varia conforme o
# pokemon do time em batalha. Mantido só de referência histórica.
FALSE_SWIPE_POSITION = "4"

# ------------------------------------------------------------
# Decisão por HP do inimigo (fase attack x capture, definido em 08/07)
# ------------------------------------------------------------
# Quando o HP do inimigo cair pra esse valor (%) ou menos, o bot para de
# atacar e passa a jogar ball.
HP_THRESHOLD_CAPTURE = 10

# Se, depois de entrar em fase "capture", o HP do inimigo se recuperar (ex:
# habilidades como Regenerator/Natural Heal) e ficar acima desse valor (%),
# o bot volta a atacar com False Swipe antes de tentar a ball de novo.
HP_THRESHOLD_REENGAGE = 30

# ============================================================
# LOGGING
# ============================================================
# OBSOLETO: os registros de captura agora vão pro banco SQLite (db.py,
# arquivo pokemonpets_bot.db), não mais em JSON por dia. Mantido comentado
# só de referência histórica.
# LOG_DIR = "logs/captures"
