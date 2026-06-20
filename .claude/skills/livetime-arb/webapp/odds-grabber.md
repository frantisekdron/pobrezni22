# Sběr REÁLNÝCH kurzů z živé stránky (běží v tvém prohlížeči)

Servery sázkovek (Tipsport, Fortuna, Betano, bet365) **blokují přístup z
datacentra/botů (HTTP 403)** a kurzy renderují až JavaScriptem. Z žádného
serveru/sandboxu je tedy spolehlivě nestáhneš a **historie kurzů neexistuje**
(jen živé kurzy *teď*). Reálná data proto ber **u sebe v prohlížeči** — máš
CZ IP, reálný browser a přihlášení. Je to legální (díváš se na stránku, kterou
máš normálně otevřenou).

## Postup (30 sekund)

1. Otevři živý zápas na stránce sázkovky.
2. **Označ myší** oblast s kurzy (názvy výsledků + čísla kurzů).
3. **Zkopíruj** (Cmd+C) — nebo použij bookmarklet níže, který z výběru rovnou
   udělá řádky „výsledek | kurz".
4. V appce → záložka **Import kurzů → Volný text**, vyplň kontext (sázkovka,
   sport, zápas, trh, hranice) a **vlož** (Cmd+V) → Naparsovat & uložit.
5. Zopakuj pro další sázkovku (stejný zápas). V **Příležitostech** přepni
   *Zdroj dat* na „Moje DB" → appka spočítá surebety/value bety z reálných dat.

## Bookmarklet „Kurzy → schránka"

Vytvoř si novou záložku v prohlížeči a do pole *URL/adresa* vlož celý tento
řádek (včetně `javascript:`). Pak na stránce sázkovky označ kurzy a klikni na
záložku — vyčištěné řádky „výsledek | kurz" se zkopírují do schránky.

```
javascript:(function(){var s=(window.getSelection||function(){return{toString:function(){return''}}})().toString();if(!s){alert('Nejdřív označ kurzy na stránce.');return;}var out=s.split('\n').map(function(l){l=l.trim();var m=l.match(/(\d{1,3}[.,]\d{1,2})\s*$/);if(!m)return null;var odds=m[1].replace(',','.');var label=l.slice(0,m.index).replace(/[\s:|>-]+$/,'').trim();return label?label+' | '+odds:null;}).filter(Boolean).join('\n');if(!out){alert('V označeném textu jsem nenašel kurzy (číslo na konci řádku).');return;}navigator.clipboard.writeText(out).then(function(){alert('Zkopírováno '+out.split('\n').length+' řádků kurzů. Vlož je do Importu → Volný text.');});})();
```

## Chceš to přesnější pro konkrétní sázkovku?

Každá sázkovka má jinou strukturu stránky. Když mi **pošleš ukázku** (zkopíruj
kus živé stránky jednoho zápasu z jedné sázkovky), napíšu ti přesnější
bookmarklet/selektory pro tu danou sázkovku, ať to vytahuje i názvy trhů a
hranice automaticky.

## Plně automatické (volitelné, na tvém Macu)

Když budeš chtít sběr bez ručního označování, jde lokálně rozjet řízený
prohlížeč (Playwright/Chromium) přihlášený tvým účtem, který kurzy vytáhne a
zapíše do `data/odds.db`. To už ale vyžaduje instalaci a údržbu selektorů per
sázkovka — dej vědět a připravím skript do `scripts/bookmakers/`.
```
