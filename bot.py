# ============================================================
# PokemonPets Bot - Loop Principal
# ============================================================
# Reorganizado em módulos em 08/07 (bot.py estava com 619 linhas, misturando
# detecção de estado, ações, scrape e login). Agora só tem os handlers de
# estado e o loop principal — ver logger.py, state.py, actions.py,
# scraping.py e auth.py pro resto. Detalhes em fluxo-atual.md.

import asyncio
import threading
from playwright.async_api import async_playwright

from config import *
import db
from logger import log
from state import get_game_state
from actions import (
    click,
    press_key,
    choose_pokeball,
    throw_pokeball,
    attack_move,
)
from scraping import get_enemy_pokedex_url, scrape_species_details
from auth import login_and_enter_game, wait_for_browser


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

    # Na primeira vez que entramos nessa batalha, busca os dados gerais da
    # espécie (fonte 3: tipo, catch rate, stats base). Só uma vez por encontro.
    if not pokemon.get("species_fetched"):
        pokedex_url = await get_enemy_pokedex_url(page)
        details = await scrape_species_details(page.context, pokedex_url)
        pokemon["species_details"] = details
        pokemon["species_fetched"] = True
        session["current_pokemon"] = pokemon
        if details.get("type"):
            log(f"Espécie: {details.get('type')} | Catch Rate: {details.get('catchRate')}", "INFO")

    enemy_hp = state.get("enemyHpPercent")
    moves_used = pokemon.get("moves_used", 0)

    if enemy_hp is None:
        # Sem leitura confiável de HP: mantém o comportamento antigo como
        # fallback de segurança — ataca uma vez, depois só joga ball.
        if moves_used == 0:
            log("HP do inimigo não pôde ser lido. Usando fallback: 1 ataque, depois só ball.", "WARN")
            await attack_move(page, state)
            pokemon["moves_used"] = 1
            session["current_pokemon"] = pokemon
            return
    else:
        # Decisão por fase (attack/capture) com histerese, baseada no HP real
        # do inimigo (definido em 08/07). Fica em "attack" até o HP cair pra
        # HP_THRESHOLD_CAPTURE (%) ou menos; muda pra "capture" e só volta a
        # atacar se o HP se recuperar acima de HP_THRESHOLD_REENGAGE (%) —
        # cobre habilidades passivas de cura (Regenerator, Natural Heal, etc.)
        # sem precisar saber qual habilidade é: reage ao HP observado.
        phase = pokemon.get("phase", "attack")
        if phase == "attack" and enemy_hp <= HP_THRESHOLD_CAPTURE:
            phase = "capture"
        elif phase == "capture" and enemy_hp > HP_THRESHOLD_REENGAGE:
            phase = "attack"
        pokemon["phase"] = phase
        session["current_pokemon"] = pokemon

        if phase == "attack":
            log(f"HP do inimigo: {enemy_hp}% (fase: atacar)", "INFO")
            await attack_move(page, state)
            pokemon["moves_used"] = moves_used + 1
            session["current_pokemon"] = pokemon
            return

        log(f"HP do inimigo: {enemy_hp}% (fase: capturar)", "INFO")

    # Fase capture (ou fallback sem leitura de HP, após o primeiro ataque):
    # joga a pokéball.
    fail_message = state.get("failMessage", "")
    if fail_message and "select a poké ball" in fail_message.lower():
        log(f"Arremesso anterior falhou (\"{fail_message}\"). Corrigindo contagem e tentando de novo...", "WARN")
        pokemon["balls_used"] = max(0, pokemon.get("balls_used", 0) - 1)

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
        details = pokemon.get("species_details") or {}
        db.save_captured_pokemon({
            "pokemon_name": pokemon.get("name"),
            "pokemon_species_id": details.get("speciesId"),
            "level": pokemon.get("level"),
            "rarity_class": details.get("rarityClass") or pokemon.get("class"),
            "type": details.get("type"),
            "catch_rate": details.get("catchRate"),
            "base_hp": details.get("baseHp"),
            "base_attack": details.get("baseAttack"),
            "base_defense": details.get("baseDefense"),
            "base_spattack": details.get("baseSpAttack"),
            "base_spdefense": details.get("baseSpDefense"),
            "base_speed": details.get("baseSpeed"),
            "base_total": details.get("baseTotal"),
            "balls_used": pokemon.get("balls_used", 0),
        })

    log("Avançando batalha (tecla F)...", "ACTION")
    await press_key(page, "f", "Battle Finished")
    await asyncio.sleep(DELAYS["after_battle_end"])


async def handle_rewards_page(page, state: dict):
    """Fecha tela de recompensas e volta ao mapa."""
    log("Fechando tela de recompensas...", "ACTION")
    await click(page, SELECTORS["btn_return_adventure"], "Return to Adventure")
    await asyncio.sleep(DELAYS["after_battle_end"])


async def handle_encounter(page, state: dict):
    """Pokemon já capturado — foge."""
    log("Pokemon já capturado. Fugindo...", "INFO")
    await click(page, SELECTORS["btn_run"], "Try Run")
    await asyncio.sleep(DELAYS["after_battle_end"])


async def handle_map(page, state: dict):
    """No mapa: garante que o Auto Hunting está ativado."""
    if state.get("autoHuntEnabled") is False:
        log("Auto Hunting desativado. Ativando...", "ACTION")
        await click(page, SELECTORS["auto_hunt_toggle"], "Ativar Auto Hunting")
        await asyncio.sleep(DELAYS["after_click"])


# ============================================================
# LOOP PRINCIPAL
# ============================================================
async def main(stop_event: threading.Event = None):
    """stop_event é opcional — só usado quando o bot é iniciado pela HUD
    (hud.py), rodando em background thread. Rodando direto via
    `python bot.py`, ninguém passa esse parâmetro e o comportamento é o
    mesmo de sempre (só Ctrl+C pra parar)."""
    db.init_db()

    async with async_playwright() as p:
        browser = await wait_for_browser(p, CDP_URL)
        context = browser.contexts[0]

        page = None
        for pg in context.pages:
            if "pokemonpets" in pg.url:
                page = pg
                break

        if not page:
            log("Aba do PokemonPets não encontrada. Abrindo uma nova aba...", "INFO")
            page = await context.new_page()

        # Só dispara o login se a aba NÃO estiver no domínio do jogo, ou estiver
        # especificamente na tela de login/welcome. Antes checávamos apenas
        # "gamepage.aspx not in url", o que derrubava batalhas em andamento: se
        # o bot reiniciasse com a aba em BattleWildMonster.aspx (ou qualquer
        # outra página válida do jogo), ele achava que não estava logado e
        # navegava pra /Login, perdendo o estado da batalha. Corrigido em 08/07
        # após o Boss reiniciar o bot no meio de um combate.
        login_url_path = LOGIN_URL.rsplit("/", 1)[-1].lower()
        on_pokemonpets_domain = "pokemonpets" in page.url.lower()
        on_login_or_welcome = (login_url_path in page.url.lower()) or (WELCOME_URL_FRAGMENT in page.url)
        needs_login = (not on_pokemonpets_domain) or on_login_or_welcome

        if needs_login:
            log("Login necessário (aba fora do jogo ou na tela de login/welcome)...", "INFO")
            logged_in = await login_and_enter_game(page)
            if not logged_in:
                log("Não foi possível logar/entrar no jogo. Abortando.", "ERR")
                return
        else:
            log(f"Já em uma página do jogo ({page.url}). Pulando login.", "INFO")

        log(f"Conectado: {page.url}", "OK")
        log("Bot iniciado! Ative o Auto Hunting no jogo.", "INFO")
        log("Pressione Ctrl+C para parar.\n", "INFO")

        session = {"current_pokemon": {}}
        last_state = None
        captures = 0
        runs = 0

        while True:
            if stop_event and stop_event.is_set():
                log("Bot interrompido (stop_event).", "WARN")
                log(f"Capturas: {captures} | Fugas: {runs}", "INFO")
                break

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
                    await handle_map(page, state)

            except KeyboardInterrupt:
                log("Bot encerrado pelo usuário.", "WARN")
                log(f"Capturas: {captures} | Fugas: {runs}", "INFO")
                break
            except Exception as e:
                log(f"Erro no loop: {e}", "ERR")

            await asyncio.sleep(DELAYS["poll_interval"])


if __name__ == "__main__":
    asyncio.run(main())
