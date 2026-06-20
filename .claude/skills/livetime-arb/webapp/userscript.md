# Automatický sběr kurzů přes TVŮJ prohlížeč (userscript)

Tohle je ta „automatická" cesta — kód, který **běží v tvém prohlížeči** na
stránkách sázkovek, sám sebere **všechny zobrazené kurzy (všechny trhy)** a
pošle je do dashboardu. Tvoje IP + tvůj browser → žádné 403. Já (AI v sandboxu)
do tvého prohlížeče nevidím, takže ti dávám tohle: nainstaluješ jednou, pak to
jede automaticky.

## Instalace (5 minut)

1. Nainstaluj rozšíření **Tampermonkey** (Chrome/Edge/Brave/Firefox/Safari).
2. Spusť dashboard na Macu: `cd webapp && python3 server.py` (poběží na :8000).
3. V Tampermonkey → *Vytvořit nový skript* → smaž obsah → vlož celý
   `webapp/userscript.user.js` → ulož (Cmd+S).
4. Otevři živou stránku sázkovky (Tipsport / Fortuna / Betano / bet365).
   Vpravo dole naskočí panel **🟢 Livetime Arb**.
5. Vyplň **Sport** (např. tenis), klikni **Sejmi & odešli** — nebo **Auto 20s**
   pro průběžný sběr. Kurzy se pošlou do dashboardu.
6. V dashboardu → **Příležitosti** → *Zdroj dat* na **„Moje DB"** → spočítají
   se surebety a value bety ze **všech** stažených trhů.

Zopakuj na druhé sázkovce (stejné zápasy) → appka je spáruje a porovná.

## Doporučení: sbírej PREMATCH, ne live

Nejjednodušší a nejbezpečnější je sbírat **prematch** kurzy (zápasy před
výkopem): jsou stabilní, drží dlouho, obě nohy v klidu stihneš (skoro žádný
leg risk) a sbírají se snáz. Otevři přehled lig / nadcházejících zápasů a
nech panel „Sejmi & odešli" projet. Live je bonus, ne základ. Tomu odpovídá i
nižší, ale jistější marže (0,5–2 %).

## Důležité / omezení

- **Přesnost:** generický scanner bere každý prvek, co vypadá jako kurz, a
  hledá k němu nejbližší popisek a nadpis trhu. Zabere hodně, ale **názvy trhů
  a výsledků nemusí sedět vždy** (každá sázkovka má jinou, často obfuskovanou
  stránku). Surebet potřebuje správně spárované opačné strany — po stažení si
  v Příležitostech zkontroluj, že nohy dávají smysl.
- **Přesné adaptéry:** v `userscript.user.js` je `ADAPTERS = {}` — sem patří
  přesné selektory pro každou sázkovku. **Pošli mi ukázku** (zkopíruj kus HTML
  jednoho živého zápasu z jedné sázkovky, nebo screenshot DOM v DevTools) a já
  ti adaptér doplním, ať to vytahuje názvy trhů i hranice přesně.
- **Mixed-content:** skript posílá data přes `GM_xmlhttpRequest` (privilegovaně
  přes Tampermonkey), takže https stránka může poslat na http://localhost.
  Proto je nutný Tampermonkey, ne obyčejný bookmarklet.
- **ToS:** čteš data ze své vlastní relace pro osobní použití. Nepřetěžuj
  servery (Auto 20s stačí), nedistribuuj data. Sázej jen u licencovaných
  sázkovek, 18+.

## Nouzová varianta (když userscript zlobí)

Záložka **Import → Volný text**: na stránce označ kurzy myší, zkopíruj, vlož,
doplň kontext (sázkovka/zápas/trh). Viz `odds-grabber.md`.
