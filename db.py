# ============================================================
# PokemonPets Bot - Persistência (SQLite)
# ============================================================
# Banco de dados local, arquivo único, sem servidor. Guarda os detalhes
# dos pokémons CAPTURADOS. Dados gerais de espécie (fonte 3) não são
# cacheados aqui — são só consultados durante a batalha e anexados
# ao registro de captura, se a captura acontecer.

import sqlite3
from datetime import datetime

DB_FILE = "pokemonpets_bot.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Cria as tabelas se ainda não existirem. Chamar uma vez no início do bot."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS captured_pokemon (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pokemon_name TEXT,
            pokemon_species_id INTEGER,
            level INTEGER,
            rarity_class TEXT,
            type TEXT,
            catch_rate INTEGER,
            base_hp INTEGER,
            base_attack INTEGER,
            base_defense INTEGER,
            base_spattack INTEGER,
            base_spdefense INTEGER,
            base_speed INTEGER,
            base_total INTEGER,
            balls_used INTEGER,
            captured_at TEXT
        )
    """)

    # Roster do time (pokémons possuídos/ativos), dados detalhados (fonte 2:
    # natureza, IVs, EVs, habilidades, moveset com PP). Diferente de
    # captured_pokemon (histórico de capturas na natureza) — essa tabela é
    # uma "foto" atual do time, atualizada sempre que sync_team() rodar
    # (upsert por identity_no, não acumula histórico).
    conn.execute("""
        CREATE TABLE IF NOT EXISTS team_pokemon (
            identity_no INTEGER PRIMARY KEY,
            pokemon_name TEXT,
            pokemon_species_id INTEGER,
            level INTEGER,
            exp INTEGER,
            gender TEXT,
            won_battles INTEGER,
            lost_battles INTEGER,
            happiness INTEGER,
            held_item TEXT,
            captured_pokeball TEXT,
            nature TEXT,
            hidden_power_value INTEGER,
            hidden_power_type TEXT,
            stat_hp INTEGER,
            stat_attack INTEGER,
            stat_defense INTEGER,
            stat_spattack INTEGER,
            stat_spdefense INTEGER,
            stat_speed INTEGER,
            ev_hp INTEGER,
            ev_attack INTEGER,
            ev_defense INTEGER,
            ev_spattack INTEGER,
            ev_spdefense INTEGER,
            ev_speed INTEGER,
            ev_total INTEGER,
            iv_hp INTEGER,
            iv_attack INTEGER,
            iv_defense INTEGER,
            iv_spattack INTEGER,
            iv_spdefense INTEGER,
            iv_speed INTEGER,
            iv_total INTEGER,
            move_1 TEXT,
            pp_1 INTEGER,
            move_2 TEXT,
            pp_2 INTEGER,
            move_3 TEXT,
            pp_3 INTEGER,
            move_4 TEXT,
            pp_4 INTEGER,
            ability_1 TEXT,
            ability_2 TEXT,
            ability_3 TEXT,
            physical_trait TEXT,
            personality TEXT,
            quirk TEXT,
            scraped_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_captured_pokemon(data: dict):
    """Insere um registro de captura. `data` pode ter campos faltando (None é aceitável)."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO captured_pokemon (
            pokemon_name, pokemon_species_id, level, rarity_class, type,
            catch_rate, base_hp, base_attack, base_defense, base_spattack,
            base_spdefense, base_speed, base_total, balls_used, captured_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("pokemon_name"),
        data.get("pokemon_species_id"),
        data.get("level"),
        data.get("rarity_class"),
        data.get("type"),
        data.get("catch_rate"),
        data.get("base_hp"),
        data.get("base_attack"),
        data.get("base_defense"),
        data.get("base_spattack"),
        data.get("base_spdefense"),
        data.get("base_speed"),
        data.get("base_total"),
        data.get("balls_used"),
        datetime.now().isoformat(),
    ))
    conn.commit()
    conn.close()


def count_captures_by_species(pokemon_species_id: int) -> int:
    """Quantas vezes já capturamos essa espécie (útil pra decisões futuras)."""
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) as total FROM captured_pokemon WHERE pokemon_species_id = ?",
        (pokemon_species_id,),
    ).fetchone()
    conn.close()
    return row["total"] if row else 0


def save_team_pokemon(data: dict):
    """Insere ou atualiza (upsert por identity_no) um pokémon do time. Chamar
    uma vez por pokémon a cada sync_team() — não acumula histórico, só
    mantém a foto mais recente de cada um."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO team_pokemon (
            identity_no, pokemon_name, pokemon_species_id, level, exp, gender,
            won_battles, lost_battles, happiness, held_item, captured_pokeball,
            nature, hidden_power_value, hidden_power_type,
            stat_hp, stat_attack, stat_defense, stat_spattack, stat_spdefense, stat_speed,
            ev_hp, ev_attack, ev_defense, ev_spattack, ev_spdefense, ev_speed, ev_total,
            iv_hp, iv_attack, iv_defense, iv_spattack, iv_spdefense, iv_speed, iv_total,
            move_1, pp_1, move_2, pp_2, move_3, pp_3, move_4, pp_4,
            ability_1, ability_2, ability_3,
            physical_trait, personality, quirk, scraped_at
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        ON CONFLICT(identity_no) DO UPDATE SET
            pokemon_name=excluded.pokemon_name,
            pokemon_species_id=excluded.pokemon_species_id,
            level=excluded.level,
            exp=excluded.exp,
            gender=excluded.gender,
            won_battles=excluded.won_battles,
            lost_battles=excluded.lost_battles,
            happiness=excluded.happiness,
            held_item=excluded.held_item,
            captured_pokeball=excluded.captured_pokeball,
            nature=excluded.nature,
            hidden_power_value=excluded.hidden_power_value,
            hidden_power_type=excluded.hidden_power_type,
            stat_hp=excluded.stat_hp,
            stat_attack=excluded.stat_attack,
            stat_defense=excluded.stat_defense,
            stat_spattack=excluded.stat_spattack,
            stat_spdefense=excluded.stat_spdefense,
            stat_speed=excluded.stat_speed,
            ev_hp=excluded.ev_hp,
            ev_attack=excluded.ev_attack,
            ev_defense=excluded.ev_defense,
            ev_spattack=excluded.ev_spattack,
            ev_spdefense=excluded.ev_spdefense,
            ev_speed=excluded.ev_speed,
            ev_total=excluded.ev_total,
            iv_hp=excluded.iv_hp,
            iv_attack=excluded.iv_attack,
            iv_defense=excluded.iv_defense,
            iv_spattack=excluded.iv_spattack,
            iv_spdefense=excluded.iv_spdefense,
            iv_speed=excluded.iv_speed,
            iv_total=excluded.iv_total,
            move_1=excluded.move_1, pp_1=excluded.pp_1,
            move_2=excluded.move_2, pp_2=excluded.pp_2,
            move_3=excluded.move_3, pp_3=excluded.pp_3,
            move_4=excluded.move_4, pp_4=excluded.pp_4,
            ability_1=excluded.ability_1,
            ability_2=excluded.ability_2,
            ability_3=excluded.ability_3,
            physical_trait=excluded.physical_trait,
            personality=excluded.personality,
            quirk=excluded.quirk,
            scraped_at=excluded.scraped_at
    """, (
        data.get("identity_no"),
        data.get("pokemon_name"),
        data.get("pokemon_species_id"),
        data.get("level"),
        data.get("exp"),
        data.get("gender"),
        data.get("won_battles"),
        data.get("lost_battles"),
        data.get("happiness"),
        data.get("held_item"),
        data.get("captured_pokeball"),
        data.get("nature"),
        data.get("hidden_power_value"),
        data.get("hidden_power_type"),
        data.get("stat_hp"),
        data.get("stat_attack"),
        data.get("stat_defense"),
        data.get("stat_spattack"),
        data.get("stat_spdefense"),
        data.get("stat_speed"),
        data.get("ev_hp"),
        data.get("ev_attack"),
        data.get("ev_defense"),
        data.get("ev_spattack"),
        data.get("ev_spdefense"),
        data.get("ev_speed"),
        data.get("ev_total"),
        data.get("iv_hp"),
        data.get("iv_attack"),
        data.get("iv_defense"),
        data.get("iv_spattack"),
        data.get("iv_spdefense"),
        data.get("iv_speed"),
        data.get("iv_total"),
        data.get("move_1"), data.get("pp_1"),
        data.get("move_2"), data.get("pp_2"),
        data.get("move_3"), data.get("pp_3"),
        data.get("move_4"), data.get("pp_4"),
        data.get("ability_1"),
        data.get("ability_2"),
        data.get("ability_3"),
        data.get("physical_trait"),
        data.get("personality"),
        data.get("quirk"),
        datetime.now().isoformat(),
    ))
    conn.commit()
    conn.close()


def get_team_pokemon() -> list:
    """Retorna o roster atual do time (todas as linhas de team_pokemon)."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM team_pokemon").fetchall()
    conn.close()
    return [dict(r) for r in rows]
