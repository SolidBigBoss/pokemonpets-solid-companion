# Notas de Execução — PokemonPets Bot

Guia rápido pra rodar, testar e atualizar o projeto sem precisar perguntar de novo. Atualizado sempre que um passo novo aparecer.

## 1. Pré-requisitos (só na primeira vez, ou em uma máquina nova)

Instalar as dependências do projeto:
```
pip install -r requirements.txt
```

Criar o arquivo `.env` na raiz do projeto (não é versionado, cada máquina precisa do seu):
```
POKEMONPETS_USERNAME=seu_usuario
POKEMONPETS_PASSWORD=sua_senha
```

## 2. Abrir o Chrome em modo debug

```
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome-debug-profile"
```

Pode deixar a janela em branco (sem navegar pro jogo) — desde a implementação do login automático, o bot abre a aba e loga sozinho.

## 3. Rodar o bot

**Opção A — Terminal:**
```
cd C:\pokemonpets-bot
python bot.py
```

**Opção B — Debug no VS Code (recomendado pra investigar problemas):**
1. Abre a aba "Run and Debug" (`Ctrl+Shift+D`).
2. Seleciona a configuração **"Python: bot.py (PokemonPets Bot)"** no menu superior.
3. Aperta `F5`.
4. Pode colocar breakpoints clicando à esquerda do número da linha, no `bot.py`, antes de rodar.

Pra parar: `Ctrl+C` no terminal, ou o botão quadrado (stop) na barra de debug.

## 4. Subir mudanças pro GitHub

```
git add .
git commit -m "descreva a mudança aqui"
git push
```

## 5. Onde encontrar as coisas

- Devlog do projeto (o que foi feito em cada dia): `logs/devlog/AAAA-MM-DD.md`
- Fluxo/arquitetura atual do bot (sempre atualizado): `fluxo-atual.md`
- Pokémons capturados (banco SQLite, gerado automaticamente): `pokemonpets_bot.db` — ver seção 6 abaixo pra acessar
- Configurações, seletores, hotkeys, delays: `config.py`
- Lógica principal do bot: `bot.py`
- Credenciais de login: `.env` (nunca commitar)

## 6. Acessar o banco de dados (SQLite) — ver pokémons capturados

O arquivo `pokemonpets_bot.db` fica na raiz do projeto (`C:\pokemonpets-bot\pokemonpets_bot.db`). Ele **só existe depois que o bot rodar pelo menos uma vez** (é criado automaticamente por `db.init_db()` no início do `main()`). Não é versionado no git.

**Opção A — DB Browser for SQLite (interface visual, recomendado):**
1. Abre o DB Browser for SQLite (já instalado, versão 3.13.1).
2. `Open Database` → navega até `C:\pokemonpets-bot\pokemonpets_bot.db` → abre.
3. Vai na aba `Browse Data`.
4. No dropdown de tabelas, seleciona `captured_pokemon`.
5. Cada linha é uma captura: nome, espécie, nível, raridade, tipo, catch rate, stats base, quantidade de balls usadas e data/hora da captura.

Pra rodar uma consulta customizada (ex: contar capturas por tipo), usa a aba `Execute SQL` e escreve o SQL diretamente, ex:
```sql
SELECT type, COUNT(*) as total FROM captured_pokemon GROUP BY type ORDER BY total DESC;
```

**Opção B — Linha de comando (sem instalar nada extra, usa o sqlite3 do Python):**
```
cd C:\pokemonpets-bot
python -c "import db; [print(dict(r)) for r in db.get_connection().execute('SELECT * FROM captured_pokemon').fetchall()]"
```

Se quiser só confirmar que a tabela existe e está vazia/populada, sem abrir nada:
```
python -c "import db; print(db.get_connection().execute('SELECT COUNT(*) FROM captured_pokemon').fetchone()[0])"
```

## 7. Se o Chrome não conectar (porta 9222)

O bot fica em loop esperando a porta abrir — não precisa reiniciar ele, só abrir o Chrome (passo 2) que a conexão acontece sozinha.

## 8. Pendências conhecidas (ver devlog para detalhes)

- Lógica de decisão de combate por HP (False Swipe até ≤10%, repetir se curar acima de 30%).
- Raridade real (`stars`) ainda fixa em 1 no `choose_pokeball` — não usa o scrape da espécie pra decidir a ball certa.
- Fonte 2 (popup "Show Pokémon's Details" com IV/EV/nature) ainda não implementada.
