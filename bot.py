# ============================================================
# PokemonPets Bot - Loop Principal MVP
# ============================================================

import asyncio
import json
import os
from datetime import datetime
from playwright.async_api import async_playwright
from config import *


# ============================================================
# LOGGING
# ============================================================
def log(msg: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    icons = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "ERR": "❌", "ACTION": "🎮"}
    icon = icons.get(level, "•")
    print(f"[{timestamp}] {icon} {msg}")


def save_capture_log(data: dict):
    """Salva histórico de capturas em JSON, separado por dia (logs/captures/AAAA-MM-DD.json)."""
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, f"{datetime.now().strftime('%Y-%m-%d')}.json")
    logs = []
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            logs = json.load(f)
    logs.append({**data, "timestamp": datetime.now().isoformat()})
    with open(log_file, "w") as f:
        json.dump(logs, f, indent=2)


# ============================================================
# DETECÇÃO DE ESTADO
# ============================================================
async def get_game_state(page) -> dict:
    """Lê o DOM e retorna o estado atual do jogo."""
    return await page.evaluate("""
    () => {
        const exists = (sel) => !!document.querySelector(sel);
        const visible = (sel) => {
            const el = document.querySelector(sel);
            return el && el.offsetParent !== null;
        };

        // 1. Tela de recompensa pós-batalha (Obtained Rewards)
        const rewardsPage = !!document.querySelector('a[href="gamepage.aspx"].buttonRed') &&
            /obtained rewards/i.test(document.body.innerText);

        // 2. Botão "Battle Finished"
        const battleFinished = visible('#btnBattleFinish');

        // 3. Popup Not Captured
        const notCapturedPopup = !!document.querySelector('.jconfirm-scrollpane') &&
            /not captured/i.test(document.querySelector('.jconfirm-scrollpane')?.innerText || '');

        // 4. Tela de batalha
        const inBattle = !!document.querySelector("input[whichbutton='1']") &&
            document.querySelector("input[whichbutton='1']")?.offsetParent !== null;

        // 5. Tela de seleção de pokemon
        const inPokemonSelect = exists('#btnSelectMonster') &&
            !inBattle &&
            !notCapturedPopup &&
            !battleFinished &&
            !rewardsPage;

        // 6. Frame de pokemon já capturado
        const encounterButtons = !!document.querySelector('#btnFightPokemon2') && !notCapturedPopup;

        // Info do popup Not Captured
        const popupText = document.querySelector('.jconfirm-scrollpane')?.innerText || '';
        const nameMatch = popupText.match(/^([^\n]+)/);
        const levelMatch = popupText.match(/Level:\s*(\d+)/i);
        const classMatch = popupText.match(/Class:\s*(\S+)/i);

        // Moves na batalha
        const moveButtons = Array.from(document.querySelectorAll("input[whichbutton]"))
            .map(el => ({
                position: el.getAttribute('whichbutton'),
                name: el.value,
                visible: el.offsetParent !== null
            }));

        // HP do inimigo
        const enemyHpEl = document.querySelector('.EnemyHP, [id*="EnemyHP"], [class*="EnemyHP"]');
        const enemyHpText = enemyHpEl?.innerText?.trim() || '';

        // Detecta mensagem de captura bem sucedida
        const captureSuccess = /successfully captured/i.test(document.body.innerText);

        // Determina estado atual
        let currentState = 'MAP';
        if (rewardsPage)           currentState = 'REWARDS_PAGE';
        else if (battleFinished)   currentState = 'BATTLE_FINISHED';
        else if (notCapturedPopup) currentState = 'NOT_CAPTURED_POPUP';
        else if (inBattle)         currentState = 'BATTLE';
        else if (inPokemonSelect)  currentState = 'POKEMON_SELECT';
        else if (encounterButtons) currentState = 'ENCOUNTER';

        return {
            currentState,
            captureSuccess,
            popupPokemonName: nameMatch?.[1]?.trim() || '',
            popupPokemonLevel: levelMatch?.[1] || '',
            popupPokemonClass: classMatch?.[1] || '',
            moveButtons,
            enemyHpText,
        };
    }
    """)


# ============================================================
# AÇÕES
# ============================================================
async def click(page, selector: str, description: str = ""):
    try:
        await page.click(selector, timeout=3000)
        log(f"Clicou: {description or selector}", "ACTION")
        await asyncio.sleep(DELAYS["after_click"])
        return True
    except Exception as e:
        log(f"Falha ao clicar em {description or selector}: {e}", "WARN")
        return False


async def press_key(page, key: str, description: str = ""):
    try:
        await page.keyboard.press(key)
        log(f"Tecla: {key} ({description})", "ACTION")
        await asyncio.sleep(DELAYS["after_keypress"])
        return True
    except Exception as e:
        log(f"Falha ao pressionar {key}: {e}", "WARN")
        return False


async def select_pokeball(page, ball_name: str):
    try:
        await page.click("#dropDownMonsterBoxes_title", timeout=3000)
        await asyncio.sleep(0.3)
        result = await page.evaluate(f"""
        () => {{
            const items = Array.from(document.querySelectorAll('li'));
            const target = items.find(el => el.innerText?.includes('{ball_name}'));
            if (target) {{ target.click(); return true; }}
            return false;
        }}
        """)
        if result:
            log(f"Poké Ball selecionada: {ball_name}", "OK")
        else:
            log(f"Ball '{ball_name}' não encontrada, usando padrão", "WARN")
        return result
    except Exception as e:
        log(f"Erro ao selecionar ball: {e}", "WARN")
        return False


async def throw_pokeball(page, ball_name: str):
    await select_pokeball(page, ball_name)
    await asyncio.sleep(0.3)
    await click(page, SELECTORS["btn_throw_ball"], "Throw Poké Ball")
    await asyncio.sleep(DELAYS["after_ball"])


def choose_pokeball(stars: int) -> str:
    balls = POKEBALL_BY_STARS.get(stars, [DEFAULT_POKEBALL])
    return balls[0]


# ============================================================
# HANDLERS DE ESTADO
# ============================================================
async def handle_not_captured_popup(page, state: dict, session: dict):
    name = state["popupPokemonName"]
    level = state["popupPokemonLevel"]
    cls = state["popupPokemonClass"]
    log(f"Encontrou: {name} | Lv.{level} | Classe: {cls}", "OK")

    session["current_pokemon"] = {
        "name": name,
        "level": level,
        "class": cls,
        "balls_used": 0,
        "moves_used": 0,
    }

    log("Iniciando batalha...", "ACTION")
    await click(page, SELECTORS["btn_battle"], "Battle")
    await asyncio.sleep(DELAYS["after_click"])


async def handle_pokemon_select(page, state: dict):
    log("Selecionando Pokemon 1...", "ACTION")
    await press_key(page, HOTKEYS["select_pokemon_1"], "Selecionar Pokemon 1")
    await asyncio.sleep(1.0)


async def handle_battle(page, state: dict, session: dict):
    pokemon = session.get("current_pokemon", {})
    moves_used = pokemon.get("moves_used", 0)

    if moves_used == 0:
        if USE_FALSE_SWIPE_BEFORE_CAPTURE:
            log("Usando False Swipe...", "ACTION")
            await press_key(page, FALSE_SWIPE_POSITION, "False Swipe")
            await asyncio.sleep(DELAYS["after_move"])
            pokemon["moves_used"] = 1
            session["current_pokemon"] = pokemon
            return

    stars = 1  # TODO: pegar do scraper futuramente
    ball = choose_pokeball(stars)
    log(f"Jogando {ball}...", "ACTION")
    await throw_pokeball(page, ball)
    pokemon["balls_used"] = pokemon.get("balls_used", 0) + 1
    session["current_pokemon"] = pokemon


async def handle_battle_finished(page, state: dict, session: dict):
    """Clica em 'Battle Finished' após captura ou batalha encerrada."""
    pokemon = session.get("current_pokemon", {})

    if state.get("captureSuccess"):
        log(f"✨ Capturado: {pokemon.get('name', '?')} com {pokemon.get('balls_used', '?')} ball(s)!", "OK")
        save_capture_log({
            "pokemon": pokemon.get("name"),
            "level": pokemon.get("level"),
            "class": pokemon.get("class"),
            "balls_used": pokemon.get("balls_used", 0),
            "result": "captured"
        })

    log("Avançando batalha (tecla F)...", "ACTION")
    await press_key(page, "f", "Battle Finished")
    await asyncio.sleep(DELAYS["after_battle_end"])


async def handle_rewards_page(page, state: dict):
    """Fecha tela de recompensas e volta ao mapa."""
    log("Fechando tela de recompensas...", "ACTION")
    await click(page, 'a[href="gamepage.aspx"].buttonRed', "Return to Adventure")
    await asyncio.sleep(DELAYS["after_battle_end"])


async def handle_encounter(page, state: dict):
    """Pokemon já capturado — foge."""
    log("Pokemon já capturado. Fugindo...", "INFO")
    await click(page, SELECTORS["btn_run"], "Try Run")
    await asyncio.sleep(DELAYS["after_battle_end"])


# ============================================================
# CONEXÃO COM O CHROME (CDP)
# ============================================================
async def wait_for_browser(p, url: str):
    """Fica tentando conectar ao Chrome via CDP até a porta ficar disponível.

    Loop infinito por enquanto (Ctrl+C cancela). Sem timeout/limite de
    tentativas — se o CDP_URL estiver errado, o bot vai ficar esperando
    para sempre, então confira o config.py se demorar demais.
    """
    attempt = 0
    while True:
        attempt += 1
        try:
            browser = await p.chromium.connect_over_cdp(url)
            log(f"Conectado ao Chrome via CDP ({url})", "OK")
            return browser
        except Exception:
            if attempt == 1 or attempt % CDP_RETRY_LOG_EVERY == 0:
                log(f"Chrome não disponível em {url} ainda (tentativa {attempt}). Aguardando...", "WARN")
            await asyncio.sleep(DELAYS["cdp_retry_interval"])


# ============================================================
# LOOP PRINCIPAL
# ============================================================
async def main():
    async with async_playwright() as p:
        browser = await wait_for_browser(p, CDP_URL)
        context = browser.contexts[0]

        page = None
        for pg in context.pages:
            if "pokemonpets" in pg.url:
                page = pg
                break

        if not page:
            log("Aba do PokemonPets não encontrada!", "ERR")
            return

        log(f"Conectado: {page.url}", "OK")
        log("Bot iniciado! Ative o Auto Hunting no jogo.", "INFO")
        log("Pressione Ctrl+C para parar.\n", "INFO")

        session = {"current_pokemon": {}}
        last_state = None
        captures = 0
        runs = 0

        while True:
            try:
                state = await get_game_state(page)
                current = state["currentState"]

                if current != last_state:
                    log(f"Estado: {last_state} → {current}")
                    last_state = current

                if current == "NOT_CAPTURED_POPUP":
                    await handle_not_captured_popup(page, state, session)

                elif current == "POKEMON_SELECT":
                    await handle_pokemon_select(page, state)

                elif current == "BATTLE":
                    await handle_battle(page, state, session)

                elif current == "BATTLE_FINISHED":
                    await handle_battle_finished(page, state, session)
                    if state.get("captureSuccess"):
                        captures += 1

                elif current == "REWARDS_PAGE":
                    await handle_rewards_page(page, state)

                elif current == "ENCOUNTER":
                    await handle_encounter(page, state)
                    runs += 1

                elif current == "MAP":
                    pass

            except KeyboardInterrupt:
                log("Bot encerrado pelo usuário.", "WARN")
                log(f"Capturas: {captures} | Fugas: {runs}", "INFO")
                break
            except Exception as e:
                log(f"Erro no loop: {e}", "ERR")

            await asyncio.sleep(DELAYS["poll_interval"])


if __name__ == "__main__":
    asyncio.run(main())