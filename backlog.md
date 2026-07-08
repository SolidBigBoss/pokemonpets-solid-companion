# Backlog — PokemonPets Bot

Roadmap de longo prazo do projeto, definido pelo Boss em 08/07/2026. Diferente do `fluxo-atual.md` (retrato do que já existe) e dos devlogs (histórico dia a dia), este arquivo é a visão de **futuro** — o que ainda vamos construir, em ordem de prioridade.

## Regra geral de desenvolvimento

Implementar **uma fase por vez**, em pequenos passos, sempre testando antes de avançar. Nunca implementar múltiplas fases simultaneamente. Perguntar antes de tomar decisões arquiteturais importantes. (Mesma regra de sempre: devagar, passo a passo, com confirmação.)

## Fase 1 — Concluída

Loop principal funcional com detecção de 7 estados: `MAP`, `NOT_CAPTURED_POPUP`, `POKEMON_SELECT`, `BATTLE`, `BATTLE_FINISHED`, `REWARDS_PAGE`, `ENCOUNTER`. Captura automática usando False Swipe + Poké Ball, fuga de pokémons já capturados. Login automático, Auto Hunting, persistência SQLite dos capturados, scrape da espécie (fonte 3). Detalhes completos em `fluxo-atual.md`.

## Fase 2 — Decisão por raridade e IV

Criar um scraper que, ao encontrar um pokémon, consulte tipo, catch rate, IVs e número de estrelas de raridade, e decida se vale capturar ou fugir com base nisso.

Exceções que sempre valem capturar mesmo já tendo a espécie:
- Shiny de qualquer espécie.
- Pokémons de linhas evolutivas de alto valor (ex: Larvitar → Tyranitar).

Lista de exceções configurável no `config.py`.

## Fase 3 — Troca de Pokémon no combate

Quando o pokémon ativo desmaiar, fazer scraper completo do time atual e escolher o substituto:
- Prioridade: pokémon que tenha False Swipe disponível.
- Fallback: escolher um com move efetivo contra o tipo do inimigo, sem risco de matar.
- Decisão baseada no tipo do pokémon inimigo.

## Fase 4 — Uso automático de itens

Detectar HP baixo e PP esgotado (durante e fora do combate). Usar automaticamente itens de recuperação de HP e PP, com thresholds configuráveis no `config.py`. Definir quais itens usar e em qual ordem de prioridade.

## Fase 5 — Movimentação própria e sistema decisório orientado a dados

- Substituir o Auto Hunting nativo por movimentação controlada pelo bot via setas direcionais.
- Sistema estatístico de captura: logar 1000+ encontros armazenando nome, tipo, catch rate, nível, HP% no arremesso, ball usada e resultado (capturou ou não). Usar esses dados pra decidir a melhor Poké Ball por faixa de HP e catch rate real.
- Em paralelo, logar dano causado por cada move em cada cenário (tipo do alvo, HP antes e depois), pra futuramente criar lógica de captura de Ghost types sem False Swipe — usando moves de dano calculado dentro de uma faixa segura (~15-25%) sem matar o alvo.

Estrutura de log sugerida por encontro (referência, formato pode virar tabela SQL em vez de JSON — ver seção "Ideias de persistência" abaixo):
```json
{
  "encounter_id": "uuid",
  "pokemon": { "name": "", "type": "", "level": 0, "catch_rate": 0 },
  "moves_used": [{ "move": "", "type": "", "damage": 0, "enemy_hp_before": 0, "enemy_hp_after": 0 }],
  "ball_attempts": [{ "ball": "", "hp_pct": 0, "success": false }],
  "result": "captured",
  "total_balls": 0
}
```

## Fase 6 — Sistema de saúde do time

Monitorar HP e PP dos 6 pokémon do time em tempo real. Thresholds configuráveis pra acionar recuperação via itens (Fase 4) antes de considerar navegação até o Pokémon Center.

## Fase 7 — Navegação autônoma entre mapas (alta complexidade, implementar por último)

O jogo tem 500+ mapas com conexões e saídas conhecidas. Construir um grafo desses mapas e implementar pathfinding (A*) pra navegar até o Pokémon Center mais próximo quando o time estiver fraco, curar e voltar ao mapa de caça. Considerar também NPCs diários espalhados pelos mapas com boas recompensas, visitáveis automaticamente na rota.

---

## Regra de jogo importante — uma ação por turno

Registrado em 08/07: em batalha, só é possível executar **uma ação por turno**. Se usar um move, precisa esperar o próximo turno pra usar item ou trocar de pokémon — a mesma restrição vale entre item e troca de pokémon (move, item e troca de pokémon são mutuamente exclusivos dentro de um turno). Isso é uma regra do próprio jogo, não uma limitação do bot, e precisa ser respeitada quando implementarmos:
- Fase 3 (troca de pokémon): não pode trocar no mesmo turno em que um move ou item já foi usado.
- Fase 4 (uso de itens): não pode usar item no mesmo turno em que um move já foi usado ou uma troca já aconteceu.

Isso reforça a necessidade de um controle de "ação já tomada nesse turno" na máquina de estado do combate, pra não tentar disparar duas ações no mesmo ciclo do loop.

## Ideia de persistência — tabelas novas (registrado em 08/07, ainda não implementado)

Duas tabelas novas propostas pelo Boss, pra viabilizar previsão de dano sofrido/causado em combate (alimenta a Fase 5):

1. **Log de combate** — um registro por turno/ação de batalha (não só por captura final como hoje). Guardaria algo como: encontro (referência), turno, ação tomada (move/item/troca), move usado (se aplicável), tipo do move, efetividade, dano causado, dano sofrido, HP do inimigo antes/depois, HP do pokémon ativo antes/depois.
2. **Pokémons do time / usados em batalha** — tabela separada dos "capturados" (`captured_pokemon` já existe pra isso). Essa nova guardaria os pokémons que o Boss **possui e já usou em combate**, com seus atributos (stats, moves, nature, etc.), pra poder relacionar esses atributos com os logs de combate acima e calcular/prever dano esperado em cenários futuros (esse pokémon vs. esse tipo de inimigo).

Ainda sem desenho de schema definido — avaliar com calma quando chegarmos na Fase 5 (é exatamente o que a fase já pede, só que com tabelas SQL em vez do JSON de exemplo).

---

*Guardado para implementação futura. Nenhuma dessas fases foi iniciada ainda — seguimos focados em estabilizar a Fase 1 (teste da correção de 05/07 ainda pendente) antes de avançar.*
