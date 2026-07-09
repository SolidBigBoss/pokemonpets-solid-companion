# ============================================================
# PokemonPets Bot - Detecção de Estado
# ============================================================
# Extraído de bot.py em 08/07, na organização em módulos. Função autocontida
# (só depende do Playwright `page`), sem imports do projeto.


async def get_game_state(page) -> dict:
    """Lê o DOM e retorna o estado atual do jogo."""
    return await page.evaluate(r"""
    () => {
        const exists = (sel) => !!document.querySelector(sel);
        const visible = (sel) => {
            const el = document.querySelector(sel);
            return el && el.offsetParent !== null;
        };

        // 1. Tela de recompensa pós-batalha (Obtained Rewards)
        const rewardsPage = !!document.querySelector('a[href="gamepage.aspx"].buttonRed') &&
            /obtained rewards/i.test(document.body.innerText);

        // 2. Botão "Battle Finished"
        const battleFinished = visible('#btnBattleFinish');

        // 3. Popup Not Captured
        const notCapturedPopup = !!document.querySelector('.jconfirm-scrollpane') &&
            /not captured/i.test(document.querySelector('.jconfirm-scrollpane')?.innerText || '');

        // 5. Tela de seleção de pokemon
        // OBS: o id #btnSelectMonster é reaproveitado em DOIS contextos diferentes:
        //   - Tela de escolha de qual pokemon vai pra batalha: tem o atributo whichbutton="1".
        //   - Dentro da batalha real, como botão "Switch Pokémon" (trocar de pokemon
        //     no meio do combate): mesmo id, mas SEM o atributo whichbutton.
        // Por isso exigimos o atributo whichbutton pra considerar que é de fato
        // a tela de seleção — só checar exists('#btnSelectMonster') (sem o atributo)
        // fazia o bot confundir batalha real com tela de seleção (bug confirmado
        // em 05/07: estado nunca virava BATTLE, sempre POKEMON_SELECT).
        const hasSelectMonsterBtn = !!document.querySelector('#btnSelectMonster[whichbutton]');
        const inPokemonSelect = hasSelectMonsterBtn &&
            !notCapturedPopup &&
            !battleFinished &&
            !rewardsPage;

        // 4. Tela de batalha
        const inBattle = !hasSelectMonsterBtn &&
            !!document.querySelector("input[whichbutton='1']") &&
            document.querySelector("input[whichbutton='1']")?.offsetParent !== null;

        // 6. Frame de pokemon já capturado
        const encounterButtons = !!document.querySelector('#btnFightPokemon2') && !notCapturedPopup;

        // Info do popup Not Captured
        const popupText = document.querySelector('.jconfirm-scrollpane')?.innerText || '';
        const nameMatch = popupText.match(/^([^\n]+)/);
        const levelMatch = popupText.match(/Level:\s*(\d+)/i);
        const classMatch = popupText.match(/Class:\s*(\S+)/i);

        // Moves na batalha (com efetividade contra o pokemon inimigo, ex: 0x, 0.5x, 1x)
        // O div .effectiveXX fica como irmão do botão, dentro do mesmo container.
        const moveButtons = Array.from(document.querySelectorAll("input[whichbutton]"))
            .map(el => {
                const effEl = el.parentElement?.querySelector('[class^="effective"]');
                const effText = effEl?.innerText?.trim() || '';
                const effMatch = effText.match(/([\d.]+)x/i);
                return {
                    position: el.getAttribute('whichbutton'),
                    name: el.value,
                    visible: el.offsetParent !== null,
                    effectiveness: effMatch ? parseFloat(effMatch[1]) : null,
                };
            });

        // HP do inimigo (percentual). Âncora: a tabela que contém a imagem do
        // inimigo (#MonsterImageUser2, mesma usada pro link do Pokédex), dentro
        // dela procura a linha "HP:" e lê o percentual da .StatBar. O texto do
        // percentual às vezes fica dentro do <span class="HP"> e às vezes num
        // <span class="NotInRange"> irmão (varia conforme o valor) — por isso
        // pegamos o texto da div inteira e extraímos o número por regex, em vez
        // de mirar numa classe específica (confirmado via HTML real em 08/07).
        let enemyHpPercent = null;
        const enemyImg = document.querySelector('#MonsterImageUser2');
        const enemyBox = enemyImg?.closest('table.NiceBg');
        if (enemyBox) {
            const hpRow = Array.from(enemyBox.querySelectorAll('tr'))
                .find(tr => tr.querySelector('td')?.textContent.trim().startsWith('HP:'));
            const hpText = hpRow?.querySelector('.StatBar')?.textContent || '';
            const hpMatch = hpText.match(/([\d.]+)%/);
            enemyHpPercent = hpMatch ? parseFloat(hpMatch[1]) : null;
        }

        // Detecta mensagem de captura bem sucedida
        const captureSuccess = /successfully captured/i.test(document.body.innerText);

        // Mensagem de falha do jogo (ex: "Please select a Poké Ball first
        // before trying to catch a Pokémon!", quando o arremesso é feito sem
        // a ball estar de fato selecionada do lado do servidor).
        const failEl = document.querySelector('.FailMessage');
        const failMessage = failEl?.innerText?.trim() || '';

        // Estado do Auto Hunting (mesmo botão, muda o ícone conforme liga/desliga)
        const autoHuntImg = document.querySelector('#imgBtnEnableAutoHunt');
        const autoHuntEnabled = autoHuntImg ? /auto_hunt_enabled_icon/i.test(autoHuntImg.src) : null;

        // Determina estado atual
        let currentState = 'MAP';
        if (rewardsPage)           currentState = 'REWARDS_PAGE';
        else if (battleFinished)   currentState = 'BATTLE_FINISHED';
        else if (notCapturedPopup) currentState = 'NOT_CAPTURED_POPUP';
        else if (inBattle)         currentState = 'BATTLE';
        else if (inPokemonSelect)  currentState = 'POKEMON_SELECT';
        else if (encounterButtons) currentState = 'ENCOUNTER';

        return {
            currentState,
            captureSuccess,
            popupPokemonName: nameMatch?.[1]?.trim() || '',
            popupPokemonLevel: levelMatch?.[1] || '',
            popupPokemonClass: classMatch?.[1] || '',
            moveButtons,
            enemyHpPercent,
            autoHuntEnabled,
            failMessage,
        };
    }
    """)
