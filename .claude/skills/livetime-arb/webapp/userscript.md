# Automatický sběr VŠECH kurzů (odchyt API) — userscript

Žádné klikání zápas po zápasu. Skript běží v tvém prohlížeči a **odchytává
datový tok, který si stránka sázkovky sama stahuje** (její interní JSON API).
Když otevřeš přehled soutěže / nadcházející zápasy, stránka načte **desítky
zápasů najednou** — a skript ten JSON zachytí a pošle do dashboardu. Plně
automaticky, tvoje IP + tvá relace → žádné 403.

## Instalace

1. Nainstaluj **Tampermonkey** (rozšíření prohlížeče).
2. Spusť dashboard: `cd webapp && python3 server.py` (port 8000).
3. Tampermonkey → *Vytvořit nový skript* → vlož celý `userscript.user.js` →
   ulož (Cmd+S).

## Použití (automatické)

1. Otevři sázkovku a dej **přehled** — celý fotbal, „Nadcházející", soutěž
   (MS 2026), apod. (Ne jeden zápas — celý seznam.)
2. **Reloadni stránku** (aby se hooky chytly i prvního načtení) a kousek
   **roluj** (doladuje se lazy-load dalších zápasů).
3. Panel vpravo dole ukazuje: `📡 zachyceno API odpovědí: N`.
4. Otevři **http://localhost:8000/api/raw** — uvidíš seznam zachycených
   odpovědí (sázkovka, velikost, URL).

## Důležité — jeden krok spolupráce

Každá sázkovka má **jiný tvar JSONu**. Aby z toho dashboard udělal kurzy,
musím pro každou sázkovku napsat malý parser. K tomu potřebuju **jednu ukázku**:

- Otevři **http://localhost:8000/api/raw/sample?book=tipsport** (a totéž pro
  `fortuna`, `betano`) → zobrazí se zachycený JSON.
- Pošli mi ho (stačí zkopírovat) → napíšu parser → od té chvíle se kurzy
  parsují automaticky a sypou do Příležitostí.

Tohle je nutné udělat **jen jednou na sázkovku**. Pak už je sběr plně
automatický (otevřeš přehled → vše naskočí v dashboardu).

## Záloha: DOM scanner

V panelu je tlačítko **„Sejmi DOM (záloha)"** — když by API odchyt selhal,
vytáhne kurzy z viditelné stránky (méně spolehlivé, viz `odds-grabber.md`).

## Poznámky

- Skript posílá data lokálně přes `GM_xmlhttpRequest` (proto Tampermonkey,
  ne bookmarklet — kvůli mixed-content https→localhost).
- Sbírej hlavně **prematch** (stabilní, snadné).
- Čteš data ze své relace pro osobní použití; nepřetěžuj servery. 18+,
  jen licencované sázkovky.
