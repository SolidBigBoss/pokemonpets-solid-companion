# ============================================================
# PokemonPets Bot - Ações (cliques, teclas, ball, decisão de move)
# ============================================================
# Extraído de bot.py em 08/07, na organização em módulos.

import asyncio

from config import *
from logger import log


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


async def attack_move(page, state: dict):
    """Executa o ataque do turno: procura o move "False Swipe" pelo NOME (não
    por posição fixa — a posição/whichbutton depende de qual pokemon do time
    está batalhando). Se não achar, ou se ele não tiver efeito (0x) contra o
    inimigo atual, usa o melhor move alternativo disponível."""
    if not USE_FALSE_SWIPE_BEFORE_CAPTURE:
        return

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
