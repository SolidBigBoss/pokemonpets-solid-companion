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
- Logs de captura do bot (gerados automaticamente): `logs/captures/AAAA-MM-DD.json`
- Configurações, seletores, hotkeys, delays: `config.py`
- Lógica principal do bot: `bot.py`
- Credenciais de login: `.env` (nunca commitar)

## 6. Se o Chrome não conectar (porta 9222)

O bot fica em loop esperando a porta abrir — não precisa reiniciar ele, só abrir o Chrome (passo 2) que a conexão acontece sozinha.

## 7. Pendências conhecidas (ver devlog para detalhes)

- Otimização da escolha de pokéball (evitar reabrir o dropdown se a ball já estiver selecionada).
- Lógica de decisão de combate por HP (False Swipe até ≤10%, repetir se curar acima de 30%).
