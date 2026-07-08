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
    """Cria a tabela de capturas se ainda não existir. Chamar uma vez no início do bot."""
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
