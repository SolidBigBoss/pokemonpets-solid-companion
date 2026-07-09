# Fluxo Atual do Bot — PokemonPets

Este arquivo descreve como o bot funciona **hoje**, sempre atualizado (diferente do devlog em `logs/devlog/`, que é o histórico do que foi feito em cada dia — aqui é só o retrato atual do fluxo).

## 1. Inicialização

```
1. Conecta no Chrome via CDP (wait_for_browser)
   - Fica em loop tentando até a porta 9222 responder (sem limite de tentativas).

2. Procura uma aba com "pokemonpets" na URL.
   - Não achou? Abre uma aba nova.

3. A aba está fora do domínio do jogo, ou na tela de login/welcome?
   (atualizado em 08/07 — antes só checava "gamepage.aspx not in url", o que
   derrubava batalhas em andamento ao reiniciar o bot com a aba em qualquer
   outra página válida do jogo, ex: BattleWildMonster.aspx)
   - Sim? Chama login_and_enter_game():
       /Login -> preenche usuário/senha (do .env) -> clica #btnLogin
       -> se cair em WelcomePage.aspx, clica no link "Game Page"
       -> confirma que chegou em gamepage.aspx
     Se o login falhar em qualquer etapa, o bot aborta com erro.
   - Não (já está em alguma página do jogo, seja mapa, batalha, etc.)? Pula o
     login e vai direto pro loop principal, que vai detectar o estado atual
     (inclusive uma batalha em andamento) normalmente.

4. Entra no loop principal (a cada ~1s: lê o estado do jogo e reage).
```

## 2. Estados detectados (`get_game_state`)

| Estado | Como é detectado | Handler | O que o handler faz |
|---|---|---|---|
| `REWARDS_PAGE` | Existe `a[href="gamepage.aspx"].buttonRed` + texto "obtained rewards" na página | `handle_rewards_page` | Clica no botão de voltar (usando seletor `:visible`, pois existem 2 elementos iguais na página). |
| `BATTLE_FINISHED` | Botão `#btnBattleFinish` visível | `handle_battle_finished` | Se a captura deu certo, salva log em `logs/captures/AAAA-MM-DD.json`. Sempre aperta `F` pra avançar. |
| `NOT_CAPTURED_POPUP` | Popup `.jconfirm-scrollpane` com texto "not captured" | `handle_not_captured_popup` | Lê nome/nível/classe(raridade) do popup, guarda na sessão, clica em "Battle". |
| `POKEMON_SELECT` | Existe `#btnSelectMonster[whichbutton]` na tela (e nenhum dos estados acima) | `handle_pokemon_select` | Aperta hotkey `1` pra selecionar o primeiro pokémon do time. |
| `BATTLE` | Existe `input[whichbutton='1']` visível, **e não** existe `#btnSelectMonster[whichbutton]` (ver nota abaixo) | `handle_battle` | Ver seção 3 (lógica de combate). |
| `ENCOUNTER` | Existe `#btnFightPokemon2` (pokémon já capturado antes) | `handle_encounter` | Clica em "Try Run" pra fugir. |
| `MAP` | Nenhum dos anteriores | `handle_map` | Confere `autoHuntEnabled`; se estiver desligado, clica no botão pra ligar. |

**Nota importante (atualizada em 05/07):** o id `#btnSelectMonster` é reaproveitado em dois contextos diferentes. Na tela de escolha de qual pokémon vai pra batalha, ele tem o atributo `whichbutton="1"`. **Dentro da batalha real**, o mesmo id é usado pelo botão "Switch Pokémon" (trocar de pokémon no meio do combate), mas **sem** o atributo `whichbutton`. Por isso a checagem exige `[whichbutton]` — sem isso, o bot confundia batalha real com tela de seleção (bug confirmado por log: o estado nunca virava `BATTLE`, sempre caía em `POKEMON_SELECT`).

## 3. Lógica de combate (`handle_battle`) — estado atual

```
Na primeira vez que entra em uma batalha (species_fetched == False):
    - Lê a URL do Pokédex do inimigo (link na imagem dele) e abre numa aba
      em segundo plano pra raspar tipo, catch rate e stats base (fonte 3).
    - Guarda esses dados na sessão (não persiste em cache, só usa nessa batalha
      e, se capturar, anexa ao registro salvo no final).

A cada turno, lê enemyHpPercent (HP % do inimigo, ver seção 3.1) e decide
entre atacar ou capturar por FASE (não mais por número fixo de turnos):

    Fase "attack" (padrão inicial):
        - Chama attack_move(): localiza o move "False Swipe" pelo NOME
          (campo `name` de moveButtons, não por posição fixa — o whichbutton
          varia conforme o pokemon do time em batalha). Se não achar, ou se
          tiver 0x de efetividade, usa o melhor move alternativo disponível
          (choose_best_damaging_move), com fallback fixo (FALLBACK_MOVE_POSITION)
          como último recurso.
        - Se enemy_hp <= HP_THRESHOLD_CAPTURE (10%): muda pra fase "capture"
          ANTES de decidir a ação deste turno (ou seja, se já caiu pra ≤10%
          logo depois do ataque anterior, esse turno já tenta a ball).

    Fase "capture":
        - Se o arremesso anterior falhou por falta de seleção real da ball
          (campo `failMessage` bate com "select a poké ball"), corrige a
          contagem de balls_used (não foi uma ball de verdade usada) antes
          de tentar de novo.
        - Joga a pokéball. Ball escolhida por choose_pokeball(stars) — mas
          "stars" está fixo em 1 (TODO: ainda não lemos a raridade real).
        - Se enemy_hp voltar a ficar acima de HP_THRESHOLD_REENGAGE (30%) —
          ex: habilidade Regenerator/Natural Heal curando o inimigo — volta
          pra fase "attack" no próximo turno.

    Fallback (enemy_hp não pôde ser lido, ex: seletor não bateu): mantém o
    comportamento antigo por segurança — ataca uma vez, depois só joga ball
    pro resto do encontro (sem reavaliar HP).

select_pokeball() SEMPRE reabre o dropdown e clica na ball via clique real do
Playwright (não mais JS sintético), e confirma a seleção lendo o título do
dropdown depois do clique. Não pula mais a seleção mesmo se já parecer
selecionada (ver nota abaixo).
```

**Nota sobre seleção de ball (bug corrigido em 08/07):** o rótulo do dropdown pode ficar "preso" mostrando a ball de um encontro anterior mesmo depois que o jogo já resetou a seleção real pro novo combate. O atalho antigo de "já selecionada, pulando" confiava só nesse rótulo visual e podia pular a seleção de verdade, causando o erro do jogo `"Please select a Poké Ball first before trying to catch a Pokémon!"` ao arremessar. Também trocamos o clique no `<li>` da lista — antes era `element.click()` disparado dentro de `page.evaluate` (nem sempre aciona o handler do plugin de dropdown do jogo), agora é um clique real do Playwright via `locator(...).click()`.

### 3.1 Leitura do HP do inimigo (implementado em 08/07)

`enemyHpPercent` é lido em `get_game_state()`: localiza a tabela que contém a imagem do inimigo (`#MonsterImageUser2`, mesma âncora usada pro link do Pokédex), acha a linha "HP:" dentro dela, e extrai o percentual do texto da `.StatBar` inteira via regex (o texto às vezes fica dentro do `<span class="HP">`, às vezes num `<span class="NotInRange">` irmão — pegar o texto todo cobre os dois casos sem depender de qual span exatamente).

Thresholds em `config.py`: `HP_THRESHOLD_CAPTURE = 10` (entra em fase capture) e `HP_THRESHOLD_REENGAGE = 30` (volta pra fase attack se curar acima disso). A histerese entre os dois valores evita ficar oscilando toda vez que o HP flutua na faixa intermediária (10-30%).

Motivação: existem ~207 habilidades no jogo (`https://www.pokemonpets.com/Abilities`), das quais 3 curam HP passivamente a cada turno (Natural Heal 5%, Regenerator 10%, Expert Regenerator 15%). Em vez de modelar cada habilidade, a decisão reage ao HP real observado a cada turno — funciona independente da causa da cura (habilidade, item, etc.).

### Limitações conhecidas (a resolver nas próximas sessões)
- `stars` fixo em 1 no `choose_pokeball` — raridade real do pokémon nunca é usada pra escolher a ball certa (mesmo já tendo a raridade disponível via `species_details["rarityClass"]`, ainda não conectada a essa decisão).
- "Classe" do popup Not Captured é raridade (Common/Rare/etc.), não tipo elemental — mas o tipo já é obtido separadamente pelo scrape da espécie (fonte 3).
- Fase attack/capture ainda não testada em jogo real (implementada em 08/07, pendente de validação).

## 4. Scrape de dados do pokémon (implementado)
- **Fonte 1 (dados ao vivo da batalha)**: lida direto do DOM em `get_game_state()` — HP, efetividade de cada move, etc. Muda a cada turno.
- **Fonte 2 (popup "Show Pokémon's Details")**: dados individuais (IV/EV/nature/moveset) — ainda **não implementado**, prioridade baixa.
- **Fonte 3 (Pokédex da espécie)**: `get_enemy_pokedex_url()` lê o link na imagem do inimigo; `scrape_species_details()` abre esse link numa aba em segundo plano, extrai tipo/raridade/catch rate/stats base, e fecha a aba. Só é consultada durante a batalha (não fica em cache) — se a captura for bem-sucedida, os valores lidos nesse momento são anexados ao registro salvo no banco.

## 5. Persistência (SQLite)
- Arquivo `pokemonpets_bot.db` (gerado automaticamente, fora do git), módulo `db.py`.
- `db.init_db()` roda uma vez no início do `main()`, cria a tabela `captured_pokemon` se não existir.
- `handle_battle_finished()` chama `db.save_captured_pokemon(...)` sempre que `captureSuccess` é true, salvando nome, nível, raridade, tipo, catch rate, stats base (tudo vindo da fonte 3 lida durante a batalha) e quantidade de balls usadas.
- Só os pokémons **capturados** são persistidos — dados gerais de espécie nunca viram uma tabela própria, só são consultados ao vivo.

## 6. Outros fluxos já automatizados
- **Login automático**: `login_and_enter_game()` — ver seção 1.
- **Auto Hunting**: detectado e ligado automaticamente pelo `handle_map()`.

## 7. Organização do código (reorganizado em módulos em 08/07)

`bot.py` estava com 619 linhas, misturando tudo. Dividido assim:

- `config.py` — seletores, hotkeys, delays, credenciais, thresholds.
- `logger.py` — só a função `log()`. Isolada porque todos os outros módulos precisam dela (evita import circular).
- `state.py` — `get_game_state()`, toda a detecção de estado via DOM.
- `actions.py` — `click`, `press_key`, `get_selected_pokeball`, `select_pokeball`, `throw_pokeball`, `choose_pokeball`, `choose_best_damaging_move`, `attack_move`.
- `scraping.py` — `get_enemy_pokedex_url`, `scrape_species_details` (fonte 3, Pokédex da espécie).
- `auth.py` — `login_and_enter_game`, `wait_for_browser`.
- `db.py` — persistência SQLite (sem mudança).
- `bot.py` — agora só os 7 `handle_*` e o `main()` (~265 linhas).

## 8. Onde mexer em cada coisa
- Seletores, hotkeys, delays, credenciais, thresholds: `config.py`
- Detecção de estado: `state.py`
- Ações de batalha (clique, tecla, ball, escolha de move): `actions.py`
- Scrape da espécie (Pokédex): `scraping.py`
- Login automático e conexão CDP: `auth.py`
- Handlers de estado e loop principal: `bot.py`
- Persistência: `db.py`
- Passo a passo de execução (comandos, debug): `notas-execute.md`
- Histórico dia a dia do que foi feito: `logs/devlog/AAAA-MM-DD.md`
- Roadmap de fases futuras (Fase 2 em diante): `backlog.md`

## 9. Regra de jogo — uma ação por turno

Em batalha, só dá pra executar **uma ação por turno**: usar um move, usar um item, ou trocar de pokémon são mutuamente exclusivos dentro do mesmo turno. Hoje isso não afeta a lógica atual (só usamos moves e ball, que já são turnos separados por natureza), mas será essencial nas Fases 3 e 4 do `backlog.md` (troca de pokémon e uso de itens) — precisa existir um controle de "ação já tomada nesse turno" pra não disparar duas ações no mesmo ciclo do loop.
