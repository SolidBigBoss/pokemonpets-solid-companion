# ============================================================
# PokemonPets Bot - Loop Principal MVP
# ============================================================

import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from config import *
import db


# ============================================================
# LOGGING
# ============================================================
def log(msg: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    icons = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "ERR": "❌", "ACTION": "🎮"}
    icon = icons.get(level, "•")
    print(f"[{timestamp}] {icon} {msg}")


# ============================================================
# DETECÇÃO DE ESTADO
# ============================================================
async def get_game_state(page) -> dict:
    """Lê o DOM e retorna o estado atual do jogo."""
    return await page.evaluate(r"""
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

        // 5. Tela de seleção de pokemon
        // OBS: o id #btnSelectMonster é reaproveitado em DOIS contextos diferentes:
        //   - Tela de escolha de qual pokemon vai pra batalha: tem o atributo whichbutton="1".
        //   - Dentro da batalha real, como botão "Switch Pokémon" (trocar de pokemon
        //     no meio do combate): mesmo id, mas SEM o atributo whichbutton.
        // Por isso exigimos o atributo whichbutton pra considerar que é de fato
        // a tela de seleção — só checar exists('#btnSelectMonster') (sem o atributo)
        // fazia o bot confundir batalha real com tela de seleção (bug confirmado
        // em 05/07: estado nunca virava BATTLE, sempre POKEMON_SELECT).
        const hasSelectMonsterBtn = !!document.querySelector('#btnSelectMonster[whichbutton]');
        const inPokemonSelect = hasSelectMonsterBtn &&
            !notCapturedPopup &&
            !battleFinished &&
            !rewardsPage;

        // 4. Tela de batalha
        const inBattle = !hasSelectMonsterBtn &&
            !!document.querySelector("input[whichbutton='1']") &&
            document.querySelector("input[whichbutton='1']")?.offsetParent !== null;

        // 6. Frame de pokemon já capturado
        const encounterButtons = !!document.querySelector('#btnFightPokemon2') && !notCapturedPopup;

        // Info do popup Not Captured
        const popupText = document.querySelector('.jconfirm-scrollpane')?.innerText || '';
        const nameMatch = popupText.match(/^([^\n]+)/);
        const levelMatch = popupText.match(/Level:\s*(\d+)/i);
        const classMatch = popupText.match(/Class:\s*(\S+)/i);

        // Moves na batalha (com efetividade contra o pokemon inimigo, ex: 0x, 0.5x, 1x)
        // O div .effectiveXX fica como irmão do botão, dentro do mesmo container.
        const moveButtons = Array.from(document.querySelectorAll("input[whichbutton]"))
            .map(el => {
                const effEl = el.parentElement?.querySelector('[class^="effective"]');
                const effText = effEl?.innerText?.trim() || '';
                const effMatch = effText.match(/([\d.]+)x/i);
                return {
                    position: el.getAttribute('whichbutton'),
                    name: el.value,
                    visible: el.offsetParent !== null,
                    effectiveness: effMatch ? parseFloat(effMatch[1]) : null,
                };
            });

        // HP do inimigo
        const enemyHpEl = document.querySelector('.EnemyHP, [id*="EnemyHP"], [class*="EnemyHP"]');
        const enemyHpText = enemyHpEl?.innerText?.trim() || '';

        // Detecta mensagem de captura bem sucedida
        const captureSuccess = /successfully captured/i.test(document.body.innerText);

        // Mensagem de falha do jogo (ex: "Please select a Poké Ball first
        // before trying to catch a Pokémon!", quando o arremesso é feito sem
        // a ball estar de fato selecionada do lado do servidor).
        const failEl = document.querySelector('.FailMessage');
        const failMessage = failEl?.innerText?.trim() || '';

        // Estado do Auto Hunting (mesmo botão, muda o ícone conforme liga/desliga)
        const autoHuntImg = document.querySelector('#imgBtnEnableAutoHunt');
        const autoHuntEnabled = autoHuntImg ? /auto_hunt_enabled_icon/i.test(autoHuntImg.src) : null;

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
            autoHuntEnabled,
            failMessage,
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


async def get_selected_pokeball(page) -> str:
    """Lê o nome da ball atualmente selecionada no título do dropdown
    (removendo o prefixo numérico, ex: '1820-Poke Ball' -> 'Poke Ball').
    Retorna string vazia/placeholder se nenhuma ball estiver selecionada."""
    return await page.evaluate(r"""
    () => {
        const label = document.querySelector('#dropDownMonsterBoxes_title .ddlabel')?.innerText || '';
        return label.replace(/^\d+-/, '').trim();
    }
    """)


async def select_pokeball(page, ball_name: str) -> bool:
    """Abre o dropdown e seleciona a ball pelo nome.

    Duas mudanças importantes feitas em 08/07 (bug: dropdown abria mas a ball
    não era de fato selecionada, resultando no erro do jogo "Please select a
    Poké Ball first..."):
    1. Removido o atalho de "já selecionada, pulando seleção" — o rótulo do
       dropdown pode ficar com o valor de um encontro anterior mesmo que a
       seleção real (do lado do jogo) já tenha sido resetada.
    2. O clique agora é um clique REAL do Playwright no <li> (via locator),
       em vez de `element.click()` disparado dentro de um `page.evaluate` —
       o clique sintético nem sempre aciona o handler do plugin de dropdown
       do jogo.
    """
    try:
        await page.click(SELECTORS["ball_dropdown_title"], timeout=3000)
        await asyncio.sleep(0.3)

        index = await page.evaluate(f"""
        () => {{
            const items = Array.from(document.querySelectorAll('{SELECTORS["ball_dropdown_list"]}'));
            return items.findIndex(el => {{
                const label = el.querySelector('.ddlabel')?.innerText || '';
                return label.replace(/^\\d+-/, '').trim() === '{ball_name}';
            }});
        }}
        """)

        if index is None or index < 0:
            log(f"Ball '{ball_name}' não encontrada no dropdown.", "WARN")
            return False

        await page.locator(SELECTORS["ball_dropdown_list"]).nth(index).click(timeout=3000)
        await asyncio.sleep(0.3)

        confirmed = await get_selected_pokeball(page)
        if confirmed == ball_name:
            log(f"Poké Ball selecionada: {ball_name}", "OK")
            return True

        log(f"Cliquei em '{ball_name}', mas o dropdown mostra '{confirmed}'. Seleção pode não ter sido aplicada.", "WARN")
        return False
    except Exception as e:
        log(f"Erro ao selecionar ball: {e}", "WARN")
        return False


async def throw_pokeball(page, ball_name: str) -> bool:
    """Seleciona a ball e arremessa. Retorna se a seleção foi confirmada antes
    do arremesso (não garante que o arremesso em si teve sucesso — isso é
    checado depois via o campo `failMessage` do estado, no próximo ciclo)."""
    selected = await select_pokeball(page, ball_name)
    if not selected:
        log("Seleção da ball não confirmada. Tentando arremessar mesmo assim...", "WARN")
    await asyncio.sleep(0.3)
    await click(page, SELECTORS["btn_throw_ball"], "Throw Poké Ball")
    await asyncio.sleep(DELAYS["after_ball"])
    return selected


def choose_pokeball(stars: int) -> str:
    balls = POKEBALL_BY_STARS.get(stars, [DEFAULT_POKEBALL])
    return balls[0]


def choose_best_damaging_move(move_buttons: list, exclude_position: str):
    """Escolhe, entre os moves visíveis (exceto `exclude_position`), o de maior
    efetividade não-zero contra o pokémon atual. Retorna None se nenhum servir."""
    candidates = [
        m for m in move_buttons
        if m.get("position") != exclude_position
        and m.get("visible")
        and m.get("effectiveness") not in (None, 0)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda m: m["effectiveness"])


# ============================================================
# SCRAPE - DADOS GERAIS DA ESPÉCIE (fonte 3, só consultado, nunca salvo em cache)
# ============================================================
async def get_enemy_pokedex_url(page) -> str:
    """Lê a URL da página do Pokédex do pokémon inimigo, a partir do link
    na imagem dele na tela de batalha."""
    return await page.evaluate(f"""
    () => {{
        const img = document.querySelector('{SELECTORS["enemy_pokedex_image"]}');
        const link = img?.closest('a');
        return link?.href || '';
    }}
    """)


async def scrape_species_details(context, pokedex_url: str) -> dict:
    """Abre a página do Pokédex da espécie numa aba nova, extrai tipo, raridade,
    catch rate e stats base, e fecha a aba. Não persiste nada aqui — só retorna
    os dados pra uso imediato na decisão do turno e, se capturar, no registro final."""
    if not pokedex_url:
        return {}

    details = {}
    tab = await context.new_page()
    try:
        await tab.goto(pokedex_url, timeout=15000)
        details = await tab.evaluate(r"""
        () => {
            const findCell = (label) => Array.from(document.querySelectorAll('td'))
                .find(td => td.textContent.trim().startsWith(label));

            const rarityCell = findCell('Class:');
            const rarityClass = rarityCell
                ? rarityCell.textContent.replace('Class:', '').trim().split('\n')[0].trim()
                : null;

            const typeCell = findCell('Type:');
            const type = typeCell?.querySelector('.InlineBlock')?.textContent?.trim() || null;

            const catchRateCell = findCell('Catch Rate:');
            const catchRateMatch = catchRateCell?.textContent.match(/Catch Rate:\s*(\d+)/);
            const catchRate = catchRateMatch ? parseInt(catchRateMatch[1]) : null;

            const idCell = findCell('Pokemon Id:');
            const speciesIdMatch = idCell?.textContent.match(/Pokemon Id:\s*(\d+)/);
            const speciesId = speciesIdMatch ? parseInt(speciesIdMatch[1]) : null;

            const getStat = (label) => {
                const cell = findCell(label + ':');
                const match = cell?.textContent.match(new RegExp(label + ':\\s*(\\d+)'));
                return match ? parseInt(match[1]) : null;
            };

            return {
                rarityClass,
                type,
                catchRate,
                speciesId,
                baseHp: getStat('HP'),
                baseAttack: getStat('Attack'),
                baseDefense: getStat('Defense'),
                baseSpAttack: getStat('SpAttack'),
                baseSpDefense: getStat('SpDefense'),
                baseSpeed: getStat('Speed'),
                baseTotal: getStat('Total'),
            };
        }
        """)
    except Exception as e:
        log(f"Erro ao raspar detalhes da espécie ({pokedex_url}): {e}", "WARN")
    finally:
        await tab.close()

    return details


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

    if moves_used == 0:
        if USE_FALSE_SWIPE_BEFORE_CAPTURE:
            # Busca o move "False Swipe" pelo NOME, não por posição fixa — a posição
            # (whichbutton) depende de qual pokemon do time está batalhando, então
            # não é confiável assumir que está sempre no mesmo slot.
            false_swipe = next(
                (m for m in state.get("moveButtons", [])
                 if m.get("name", "").strip().lower() == "false swipe"),
                None,
            )

            if false_swipe is None:
                log("Move 'False Swipe' não encontrado no time atual. Usando o melhor move disponível.", "WARN")
                fallback = choose_best_damaging_move(state.get("moveButtons", []), exclude_position=None)
                if fallback:
                    await press_key(page, fallback["position"], f"Move alternativo: {fallback['name']}")
                else:
                    log("Nenhum move com efeito encontrado. Usando fallback fixo.", "WARN")
                    await press_key(page, FALLBACK_MOVE_POSITION, "Move alternativo (fallback fixo)")
            else:
                effectiveness = false_swipe.get("effectiveness")
                if effectiveness == 0:
                    fallback = choose_best_damaging_move(state.get("moveButtons", []), false_swipe["position"])
                    if fallback:
                        log(f"False Swipe sem efeito (0x). Usando '{fallback['name']}' ({fallback['effectiveness']}x)...", "INFO")
                        await press_key(page, fallback["position"], f"Move alternativo: {fallback['name']}")
                    else:
                        log("False Swipe sem efeito e nenhum move alternativo com efeito encontrado. Usando fallback fixo.", "WARN")
                        await press_key(page, FALLBACK_MOVE_POSITION, "Move alternativo (fallback fixo)")
                else:
                    log("Usando False Swipe...", "ACTION")
                    await press_key(page, false_swipe["position"], "False Swipe")

            await asyncio.sleep(DELAYS["after_move"])
            pokemon["moves_used"] = 1
            session["current_pokemon"] = pokemon
            return

    # Se o arremesso anterior falhou por falta de seleção real da ball
    # (mensagem do próprio jogo), corrige a contagem (não foi uma ball de
    # verdade usada) antes de tentar de novo.
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
# LOGIN
# ============================================================
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