import asyncio
from playwright.async_api import async_playwright

async def get_game_state(page):
    return await page.evaluate("""
    () => {
        const getText = (sel) => document.querySelector(sel)?.innerText?.trim() || '';
        const exists = (sel) => !!document.querySelector(sel);
        
        // Detecta botões de Battle e Try Run visíveis
        const allLinks = Array.from(document.querySelectorAll('a, button, input[type=button]'));
        
        const battleButtons = allLinks
            .filter(el => {
                const text = (el.innerText || el.value || '').trim();
                return /^battle$/i.test(text) && el.offsetParent !== null;
            })
            .map(el => ({ tag: el.tagName, text: (el.innerText || el.value)?.trim(), id: el.id, class: el.className, href: el.href }));
            
        const runButtons = allLinks
            .filter(el => {
                const text = (el.innerText || el.value || '').trim();
                return /try.?run/i.test(text) && el.offsetParent !== null;
            })
            .map(el => ({ tag: el.tagName, text: (el.innerText || el.value)?.trim(), id: el.id, class: el.className, href: el.href }));

        // Detecta popup Not Captured
        const notCapturedPopup = Array.from(document.querySelectorAll('*'))
            .filter(el => /not captured/i.test(el.innerText) && el.offsetParent !== null)
            .map(el => ({ tag: el.tagName, id: el.id, class: el.className, text: el.innerText?.trim().substring(0, 100) }))
            .slice(0, 3);

        // Detecta moves na batalha (tem PP:)
        const moves = allLinks
            .filter(el => /PP:/i.test(el.innerText) && el.offsetParent !== null)
            .map(el => ({ tag: el.tagName, text: el.innerText?.trim(), id: el.id, class: el.className, href: el.href }));

        // Detecta HP bars
        const hpBars = Array.from(document.querySelectorAll('[id*=hp], [class*=hp], [id*=HP], [class*=HP]'))
            .filter(el => el.offsetParent !== null)
            .map(el => ({ tag: el.tagName, id: el.id, class: el.className, text: el.innerText?.trim().substring(0, 30), style: el.style?.width }))
            .slice(0, 10);

        // Detecta nome do pokemon encontrado
        const pokemonName = Array.from(document.querySelectorAll('*'))
            .filter(el => el.children.length === 0 && /level:\s*\d+/i.test(el.innerText) && el.offsetParent !== null)
            .map(el => ({ tag: el.tagName, id: el.id, class: el.className, text: el.innerText?.trim() }))
            .slice(0, 3);

        // Detecta Throw Pokeball
        const throwBall = allLinks
            .filter(el => /throw/i.test(el.innerText || el.value || '') && el.offsetParent !== null)
            .map(el => ({ tag: el.tagName, text: (el.innerText || el.value)?.trim(), id: el.id, class: el.className, href: el.href }));

        return {
            battleButtons,
            runButtons,
            notCapturedPopup,
            moves,
            hpBars,
            throwBall,
            pokemonName
        };
    }
    """)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        
        page = None
        for p_item in context.pages:
            if "pokemonpets" in p_item.url:
                page = p_item
                break
        
        if not page:
            print("❌ Aba do PokemonPets não encontrada!")
            return
            
        print(f"✅ Conectado em: {page.url}")
        print("🔍 Monitorando... ative o Auto Hunting no jogo!\n")
        
        last_state = None
        
        while True:
            try:
                state = await get_game_state(page)
                
                # Detecta qual tela está ativa
                if state['moves']:
                    current = 'BATTLE'
                elif state['notCapturedPopup']:
                    current = 'NOT_CAPTURED_POPUP'
                elif state['battleButtons'] or state['runButtons']:
                    current = 'ENCOUNTER'
                else:
                    current = 'MAP'
                
                # Só printa quando o estado muda
                if current != last_state:
                    print(f"\n{'='*50}")
                    print(f"🎮 ESTADO: {current}")
                    print(f"{'='*50}")
                    
                    if state['battleButtons']:
                        print("\n▶ BATTLE BUTTONS:")
                        for el in state['battleButtons']:
                            print(f"  {el}")
                            
                    if state['runButtons']:
                        print("\n▶ RUN BUTTONS:")
                        for el in state['runButtons']:
                            print(f"  {el}")
                            
                    if state['notCapturedPopup']:
                        print("\n▶ NOT CAPTURED POPUP:")
                        for el in state['notCapturedPopup']:
                            print(f"  {el}")
                            
                    if state['moves']:
                        print("\n▶ MOVES:")
                        for el in state['moves']:
                            print(f"  {el}")
                            
                    if state['hpBars']:
                        print("\n▶ HP BARS:")
                        for el in state['hpBars']:
                            print(f"  {el}")
                            
                    if state['throwBall']:
                        print("\n▶ THROW BALL:")
                        for el in state['throwBall']:
                            print(f"  {el}")
                            
                    if state['pokemonName']:
                        print("\n▶ POKEMON ENCONTRADO:")
                        for el in state['pokemonName']:
                            print(f"  {el}")
                    
                    last_state = current
                    
            except Exception as e:
                print(f"⚠️ Erro: {e}")
                
            await asyncio.sleep(1)

asyncio.run(main())