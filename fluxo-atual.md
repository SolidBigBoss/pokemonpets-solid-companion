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

Turno 1 (moves_used == 0):
    - Localiza o move "False Swipe" pelo NOME (campo `name` de moveButtons),
      não por posição fixa — a posição (whichbutton) varia conforme o
      pokemon do time em batalha, então não é confiável assumir slot fixo.
    - Se não achar nenhum move chamado "False Swipe": usa o melhor move
      disponível (choose_best_damaging_move, sem exclusão), com fallback
      fixo (FALLBACK_MOVE_POSITION) como último recurso.
    - Se achar: olha a efetividade dele (lida do div .effectiveXX ao lado
      do botão). Se 0x (sem efeito): usa o melhor move alternativo entre os
      demais (choose_best_damaging_move, excluindo a posição do False Swipe).
      Senão: usa o False Swipe.
    - Marca moves_used = 1 e para o turno (não joga ball ainda).

A partir do turno 2 em diante:
    - Se o arremesso anterior falhou por falta de seleção real da ball
      (campo `failMessage` do estado bate com "select a poké ball"), corrige
      a contagem de balls_used (não foi uma ball de verdade usada) antes de
      tentar de novo.
    - Sempre joga a pokéball (nunca mais usa move).
    - Ball escolhida por choose_pokeball(stars) — mas "stars" está fixo em 1
      (TODO no código: ainda não lemos a raridade real do pokémon).
    - select_pokeball() SEMPRE reabre o dropdown e clica na ball via clique
      real do Playwright (não mais JS sintético), e confirma a seleção lendo
      o título do dropdown depois do clique. Não pula mais a seleção mesmo se
      já parecer selecionada (ver nota abaixo).
```

**Nota sobre seleção de ball (bug corrigido em 08/07):** o rótulo do dropdown pode ficar "preso" mostrando a ball de um encontro anterior mesmo depois que o jogo já resetou a seleção real pro novo combate. O atalho antigo de "já selecionada, pulando" confiava só nesse rótulo visual e podia pular a seleção de verdade, causando o erro do jogo `"Please select a Poké Ball first before trying to catch a Pokémon!"` ao arremessar. Também trocamos o clique no `<li>` da lista — antes era `element.click()` disparado dentro de `page.evaluate` (nem sempre aciona o handler do plugin de dropdown do jogo), agora é um clique real do Playwright via `locator(...).click()`.

### Limitações conhecidas (a resolver nas próximas sessões)
- Não há leitura de **HP do pokémon inimigo** em uso real (existe o campo `enemyHpText` no estado, mas sem seletor confirmado nem lógica associada).
- Não há decisão dinâmica de "usar False Swipe de novo x jogar ball" baseada em HP — hoje é sempre: 1 move no turno 1, ball a partir do turno 2, sem reavaliar.
- Regra combinada de HP definida (mas não implementada): usar False Swipe até o pokémon ficar com ≤10% de HP; se ele se curar e passar de 30%, repetir o False Swipe antes de voltar a tentar a ball.
- `stars` fixo em 1 no `choose_pokeball` — raridade real do pokémon nunca é usada pra escolher a ball certa (mesmo já tendo a raridade disponível via `species_details["rarityClass"]`, ainda não conectada a essa decisão).
- "Classe" do popup Not Captured é raridade (Common/Rare/etc.), não tipo elemental — mas o tipo já é obtido separadamente pelo scrape da espécie (fonte 3).

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

## 7. Onde mexer em cada coisa
- Seletores, hotkeys, delays, credenciais: `config.py`
- Toda a lógica/handlers: `bot.py`
- Passo a passo de execução (comandos, debug): `notas-execute.md`
- Histórico dia a dia do que foi feito: `logs/devlog/AAAA-MM-DD.md`
- Roadmap de fases futuras (Fase 2 em diante): `backlog.md`

## 8. Regra de jogo — uma ação por turno

Em batalha, só dá pra executar **uma ação por turno**: usar um move, usar um item, ou trocar de pokémon são mutuamente exclusivos dentro do mesmo turno. Hoje isso não afeta a lógica atual (só usamos moves e ball, que já são turnos separados por natureza), mas será essencial nas Fases 3 e 4 do `backlog.md` (troca de pokémon e uso de itens) — precisa existir um controle de "ação já tomada nesse turno" pra não disparar duas ações no mesmo ciclo do loop.
