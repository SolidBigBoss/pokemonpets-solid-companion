# ============================================================
# PokemonPets Bot - Scrape do time (fonte 2: dados detalhados dos
# pokémons possuídos/ativos)
# ============================================================
# Diferente de scraping.py (fonte 3, dados genéricos de espécie do inimigo
# em batalha), este módulo lê os dados INDIVIDUAIS dos pokémons do próprio
# time: natureza, IVs, EVs, habilidades, moveset com PP, etc. Usado pelo
# botão "Sincronizar Time" do HUD — não roda dentro do loop de caça.

from logger import log
import db

MANAGE_TEAM_URL = "https://www.pokemonpets.com/ManageTeam.aspx"
DETAILS_URL_TEMPLATE = "https://www.pokemonpets.com/SeeUserPokemonDetails.aspx?ID={id}"


async def get_team_identity_ids(page) -> list:
    """Navega até ManageTeam.aspx e extrai o 'Identity No' de cada pokémon do
    time (até 6). Esses números são os mesmos IDs usados na URL de detalhes."""
    await page.goto(MANAGE_TEAM_URL, timeout=15000)
    ids = await page.evaluate(r"""
    () => {
        const text = document.body.innerText;
        const matches = [...text.matchAll(/Identity No\s*:\s*([\d,]+)/g)];
        return matches.map(m => parseInt(m[1].replace(/,/g, '')));
    }
    """)
    return ids


async def scrape_pokemon_details(context, identity_id: int) -> dict:
    """Abre SeeUserPokemonDetails.aspx?ID=X numa aba nova e extrai os dados
    detalhados desse pokemon (nature, IVs, EVs, habilidades, moveset+PP,
    stats). Usa comparacao normalizada (sem acento/pontuacao) pra achar cada
    campo pelo rotulo, evitando depender do caractere exato de aspas/acento
    usado pelo jogo. Validado em 09/07 contra o HTML real da tela de
    detalhes (Lapras) via teste com jsdom antes de rodar contra o jogo."""
    details = {"identity_no": identity_id}
    tab = await context.new_page()
    try:
        await tab.goto(DETAILS_URL_TEMPLATE.format(id=identity_id), timeout=15000)
        scraped = await tab.evaluate(r"""
        () => {
            const norm = (s) => (s || '')
                .normalize('NFD').replace(new RegExp('[\\u0300-\\u036f]', 'g'), '')
                .toLowerCase()
                .replace(/[^a-z0-9]/g, '');

            const cells = Array.from(document.querySelectorAll('td'));

            const findCell = (label) => {
                const target = norm(label);
                return cells.find(td => norm(td.textContent).includes(target));
            };
            const findAllCells = (label) => {
                const target = norm(label);
                return cells.filter(td => norm(td.textContent).includes(target));
            };
            const cleanText = (el) => (el?.textContent || '').replace(/\s+/g, ' ').trim();
            const cellValue = (label) => {
                const cell = findCell(label);
                return cell ? cleanText(cell.nextElementSibling) : null;
            };
            const cellValueInt = (label) => {
                const v = cellValue(label);
                if (!v) return null;
                const m = v.match(/-?[\d,]+/);
                return m ? parseInt(m[0].replace(/,/g, '')) : null;
            };

            const name = cleanText(document.querySelector('#pokemon_isim'));
            const moveCells = findAllCells('Move');
            const ppCells = findAllCells('Power Points');
            const moves = [0, 1, 2, 3].map(i => ({
                name: moveCells[i] ? cleanText(moveCells[i].nextElementSibling) : null,
                pp: ppCells[i] ? parseInt((cleanText(ppCells[i].nextElementSibling).match(/\d+/) || [])[0]) || null : null,
            }));

            let abilities = [null, null, null];
            let flavor = [null, null, null];
            const abilitiesHeader = cells.find(td => norm(td.textContent) === norm('Abilities'));
            if (abilitiesHeader) {
                const table = abilitiesHeader.closest('table');
                const rows = Array.from(table.querySelectorAll('tr')).slice(1);
                rows.forEach((tr, i) => {
                    const tds = tr.querySelectorAll('td');
                    if (i < 3) {
                        flavor[i] = tds[1] ? cleanText(tds[1]) : null;
                        abilities[i] = tds[2] ? cleanText(tds[2]) : null;
                    }
                });
            }

            return {
                pokemon_name: name || null,
                pokemon_species_id: cellValueInt('Pokemon Id'),
                level: cellValueInt('Level'),
                exp: cellValueInt('EXP'),
                won_battles: cellValueInt('Won Battles'),
                lost_battles: cellValueInt('Lost Battles'),
                happiness: cellValueInt('Happiness'),
                held_item: cellValue('Held Item'),
                captured_pokeball: cellValue('Captured Poke Ball'),
                gender: document.querySelector('#dropDownGender')?.value || cellValue('Gender'),
                nature: cellValue('Nature'),
                hidden_power_value: cellValueInt('Hidden Power'),
                hidden_power_type: cellValue('Hidden Power Type'),
                stat_hp: cellValueInt('HP'),
                stat_attack: cellValueInt('Attack'),
                stat_defense: cellValueInt('Defense'),
                stat_spattack: cellValueInt('SpAttack'),
                stat_spdefense: cellValueInt('SpDefense'),
                stat_speed: cellValueInt('Speed'),
                ev_hp: cellValueInt('EV HP'),
                ev_attack: cellValueInt('EV Attack'),
                ev_defense: cellValueInt('EV Defense'),
                ev_spattack: cellValueInt('EV SpAttack'),
                ev_spdefense: cellValueInt('EV SpDefense'),
                ev_speed: cellValueInt('EV Speed'),
                iv_hp: cellValueInt('IV HP'),
                iv_attack: cellValueInt('IV Attack'),
                iv_defense: cellValueInt('IV Defense'),
                iv_spattack: cellValueInt('IV SpAttack'),
                iv_spdefense: cellValueInt('IV SpDefense'),
                iv_speed: cellValueInt('IV Speed'),
                move_1: moves[0].name, pp_1: moves[0].pp,
                move_2: moves[1].name, pp_2: moves[1].pp,
                move_3: moves[2].name, pp_3: moves[2].pp,
                move_4: moves[3].name, pp_4: moves[3].pp,
                ability_1: abilities[0],
                ability_2: abilities[1],
                ability_3: abilities[2],
                physical_trait: flavor[0],
                personality: flavor[1],
                quirk: flavor[2],
            };
        }
        """)
        details.update(scraped)

        ev_parts = [details.get(k) for k in ("ev_hp", "ev_attack", "ev_defense", "ev_spattack", "ev_spdefense", "ev_speed")]
        iv_parts = [details.get(k) for k in ("iv_hp", "iv_attack", "iv_defense", "iv_spattack", "iv_spdefense", "iv_speed")]
        details["ev_total"] = sum(v for v in ev_parts if v is not None) if any(v is not None for v in ev_parts) else None
        details["iv_total"] = sum(v for v in iv_parts if v is not None) if any(v is not None for v in iv_parts) else None
    except Exception as e:
        log(f"Erro ao raspar detalhes do pokemon (ID {identity_id}): {e}", "WARN")
    finally:
        await tab.close()

    return details


async def sync_team(page) -> int:
    """Sincroniza o time inteiro: lista os IDs em ManageTeam.aspx, raspa os
    detalhes de cada um e salva/atualiza no banco (team_pokemon). Retorna
    quantos pokemons foram sincronizados com sucesso."""
    log("Sincronizando time: lendo lista de pokemons...", "ACTION")
    ids = await get_team_identity_ids(page)

    if not ids:
        log("Nenhum pokemon encontrado em ManageTeam.aspx.", "WARN")
        return 0

    log(f"Encontrados {len(ids)} pokemons no time. Coletando detalhes...", "INFO")
    synced = 0
    for identity_id in ids:
        details = await scrape_pokemon_details(page.context, identity_id)
        if details.get("pokemon_name"):
            db.save_team_pokemon(details)
            log(f"Sincronizado: {details['pokemon_name']} (ID {identity_id})", "OK")
            synced += 1
        else:
            log(f"Falha ao ler detalhes do pokemon ID {identity_id} - pulando.", "WARN")

    log(f"Sincronizacao concluida: {synced}/{len(ids)} pokemons salvos.", "OK")
    return synced
