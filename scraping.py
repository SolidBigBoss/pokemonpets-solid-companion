# ============================================================
# PokemonPets Bot - Scrape da espécie (fonte 3, Pokédex)
# ============================================================
# Extraído de bot.py em 08/07, na organização em módulos. Só consultado
# durante a batalha — não persiste nada aqui (ver db.py e fluxo-atual.md).

from config import *
from logger import log


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
