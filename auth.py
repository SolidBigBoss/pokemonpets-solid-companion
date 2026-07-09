# ============================================================
# PokemonPets Bot - Login automático + conexão com o Chrome (CDP)
# ============================================================
# Extraído de bot.py em 08/07, na organização em módulos.

import asyncio

from config import *
from logger import log


async def login_and_enter_game(page) -> bool:
    """Faz login no PokemonPets e navega até o gamepage.aspx.

    Fluxo: /Login -> preenche usuário/senha -> #btnLogin
           -> (se cair em WelcomePage.aspx) clica no link "Game Page"
           -> confirma que chegou no gamepage.aspx
    Retorna True se conseguiu chegar no mapa do jogo, False caso contrário.
    """
    if not POKEMONPETS_USERNAME or not POKEMONPETS_PASSWORD:
        log("Credenciais não encontradas no .env (POKEMONPETS_USERNAME / POKEMONPETS_PASSWORD).", "ERR")
        return False

    log("Navegando até a tela de login...", "ACTION")
    await page.goto(LOGIN_URL)
    await asyncio.sleep(1.0)

    try:
        await page.fill(SELECTORS["login_username"], POKEMONPETS_USERNAME, timeout=5000)
        await page.fill(SELECTORS["login_password"], POKEMONPETS_PASSWORD, timeout=5000)
        log("Credenciais preenchidas, efetuando login...", "ACTION")
        await page.click(SELECTORS["login_submit"], timeout=5000)
    except Exception as e:
        log(f"Falha ao preencher/enviar formulário de login: {e}", "ERR")
        return False

    await asyncio.sleep(2.0)

    if WELCOME_URL_FRAGMENT in page.url:
        log("Login OK, na página de boas-vindas. Indo para o mapa...", "OK")
        try:
            await page.click(SELECTORS["welcome_game_page_link"], timeout=5000)
            await asyncio.sleep(2.0)
        except Exception as e:
            log(f"Falha ao clicar em 'Game Page': {e}", "ERR")
            return False

    if "gamepage.aspx" in page.url:
        log("Chegou no mapa do jogo.", "OK")
        return True

    log(f"URL inesperada após tentativa de login: {page.url}", "WARN")
    return False


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
