# ZADÁNÍ: Webové rozhraní „Livetime Arb Dashboard"

> Tento soubor je kompletní zadání pro Claude Code. Zkopíruj CELÝ jeho obsah
> do Claude Code na svém počítači jako úvodní prompt. Je psané tak, aby z něj
> šlo postavit funkční webovou appku navazující na existující výpočetní engine.

---

## 0. Jak to zadat Claude Code (úvodní instrukce)

> Postav webovou aplikaci „Livetime Arb Dashboard" podle zadání níže.
> Pracuj iterativně: nejdřív backend + datový model, pak API, pak frontend.
> Po každé fázi spusť a ukaž, že to běží. Reused existující Python engine
> (viz §2) — neimplementuj výpočet arbitráže znovu, importuj ho.
> Po dokončení MVP napiš README se spuštěním a seed daty.

---

## 1. Kontext a cíl

Chci webový dashboard, který hledá a přehledně zobrazuje **sázkové
příležitosti** napříč sázkovkami **Tipsport, Betano, bet365, Fortuna**:

- **Surebety (arbitráž)** — vsazení všech výsledků trhu se zaručeným ziskem.
- **Value bety** — +EV jednotlivé sázky (kurz vyšší než férová pravděpodobnost).
- **Konverze bonusů / free betů** — bezztrátová (matched betting).

Příležitosti musí být **pěkně seřazené** (podle marže / EV) a u každé musí být
**jasná struktura sázky**: co vsadit, kam, za jaký kurz, za kolik Kč, a jaký je
zaručený/očekávaný zisk. Kurzy se získávají **bez API** — importem ze
zkopírovaných stránek (já je vložím, nebo je načte Claude přes WebFetch).

Cílový uživatel: já, jako sázkař s bankrollem do 100 000 Kč. Důraz na
přehlednost, rychlost zadání kurzů a kontrolu před odesláním sázky.

---

## 2. Co znovupoužít (existující engine)

V repu je Claude Code skill `livetime-arb` se scripty v Pythonu (čistá stdlib,
žádné závislosti). NEPŘEPISUJ logiku, importuj ji jako knihovnu:

- `arb.py` — `find_arb()`, `compute_arb()`, `best_legs_across_books()`,
  datové třídy `Leg`, `Arb`. Marže = `1/Σ(1/kurz) − 1`,
  vklad_i = `T·(1/kurz_i)/S`. (Ověřeno: 3.00 + 1.83 → 13.66 %, 379/621 Kč.)
- `analyze.py` — `find_value_bets()`, `fair_probs()`, `kelly_fraction()`.
- `normalize.py` — `merge_quotes()` fuzzy páruje stejné zápasy/trhy napříč
  sázkovkami (i „Zverev A." vs „Alexander Zverev").
- `ingest.py` — `parse_block()`, `parse_free()` parsují zkopírované stránky.
- `db.py` — SQLite vrstva (kotace + deník sázek).
- `freebet.py` — `free_two_books()`, `lay_freebet()`, `lay_qualifying()`.

Tyto moduly obal do backendu. Pokud potřebuješ, refaktoruj je do balíčku
`engine/`, ale zachovej chování a doplň testy.

---

## 3. Doporučený tech stack

- **Backend:** Python 3.11+, **FastAPI** + Uvicorn. Importuje engine z §2.
- **DB:** SQLite (soubor), schéma rozšiř o tabulky níže. (Migrace přes prosté
  `CREATE TABLE IF NOT EXISTS`, žádné těžké ORM nutné — klidně `sqlite3`.)
- **Frontend:** **React + TypeScript + Vite**, styl **Tailwind CSS**. Stavová
  data přes React Query (fetch z API). Žádný backend framework navíc.
- **Bez externích placených služeb.** Vše běží lokálně (`localhost`).
- Tmavé téma (čte se večer u live sázek), responzivní (i na mobilu).

> Pokud chceš jednodušší variantu pro rychlé MVP, je OK i čistý HTML +
> vanilla JS + Tailwind CDN a FastAPI servíruje statické soubory. Ale cíl je
> React SPA.

---

## 4. Datový model (DB)

Rozšiř existující `quotes` a `bets` o tohle (názvy uprav dle potřeby):

```
events        (id, sport, home, away, start_time, status)            -- spárované zápasy
quotes        (id, ts, event_id, bookmaker, market, line, outcome, odds)
opportunities (id, ts, type[surebet|value|freebet], event_id, market,
               margin, edge, payload_json, dismissed)
bets          (id, ts, opportunity_id, event, market, legs_json,
               total, payout, profit, margin, status[open|won|lost|void|settled])
bankroll      (id, bookmaker, balance, updated_at)                    -- kolik mám kde
settings      (key, value)                                            -- bankroll, kelly, filtry
```

- `legs_json` = pole noh `[{outcome, bookmaker, odds, stake}]`.
- Ukládej **historii kotací s `ts`**, ať jde zobrazit pohyb kurzu.

---

## 5. Backend API (FastAPI)

| Metoda + cesta | Funkce |
|---|---|
| `POST /api/ingest` | tělo = surový text (blokový/volný formát) → parse → uloží kotace; vrátí počet a náhled |
| `POST /api/ingest/file` | upload .txt/.csv se stejným chováním |
| `GET  /api/opportunities` | vrátí surebety + value bety + freebety; query: `min_margin`, `min_edge`, `sport`, `bookmaker`, `total`, `bankroll`, `kelly`, `sort` |
| `GET  /api/events` | seznam spárovaných zápasů a jejich kotací (pro kontrolu párování) |
| `POST /api/bets` | založ sázku z příležitosti (zapiš do deníku, status=open) |
| `PATCH /api/bets/{id}` | změň status (won/lost/void/settled) → přepočti realizovaný P/L |
| `GET  /api/bets` | deník sázek + souhrn P/L |
| `GET  /api/bankroll` | stavy po sázkovkách + doporučené rozdělení |
| `PUT  /api/bankroll` | uprav stavy |
| `GET  /api/settings` / `PUT` | bankroll, default Kelly, default filtry |
| `POST /api/freebet/calc` | kalkulačka free betu (free2/lay/qual) |

- Výpočty v `/api/opportunities` volají engine z §2. Vrať pro každou
  příležitost KOMPLETNÍ strukturu sázky (viz §7), ne jen číslo.

---

## 6. Stránky (frontend)

1. **Dashboard (/)** — hlavní seznam příležitostí, řazený, filtrovatelný.
2. **Import kurzů (/ingest)** — velké textové pole pro vložení zkopírované
   stránky + náhled naparsovaných kotací před uložením.
3. **Detail zápasu (/event/:id)** — všechny trhy a kurzy všech sázkovek vedle
   sebe (kontrola párování, pohyb kurzu).
4. **Deník sázek (/bets)** — co jsem vsadil, status, realizovaný P/L, grafy.
5. **Bankroll (/bankroll)** — kolik mám u které sázkovky + doporučené rozdělení
   100k a varování na koncentraci/limity.
6. **Bonusy (/freebet)** — kalkulačka free betů a matched bettingu.

---

## 7. KLÍČOVÉ: zobrazení příležitosti (karta sázky)

Každá příležitost je **karta** se VŠÍM, co potřebuju, abych ji vsadil bez
počítání. Layout karty surebetu:

```
┌──────────────────────────────────────────────────────────────┐
│ 🟢 SUREBET   +13.66 %   [tenis]            ⏱ 21:37  ⚠ riziko: │
│ Alexander Zverev – Taylor Fritz                       střední  │
│ Trh: Esa v zápase · hranice 28.5                              │
├──────────────────────────────────────────────────────────────┤
│  Vsaď tyto sázky (celkem 1 000 Kč):                           │
│  ┌────────────┬──────────┬───────┬──────────┐                 │
│  │ Výsledek   │ Sázkovka │ Kurz  │ Vklad    │                 │
│  ├────────────┼──────────┼───────┼──────────┤                 │
│  │ Nad 28.5   │ Tipsport │ 3.00  │  380 Kč  │ [zkopírovat]    │
│  │ Pod 28.5   │ bet365   │ 1.83  │  620 Kč  │ [zkopírovat]    │
│  └────────────┴──────────┴───────┴──────────┘                 │
│  Výplata ať padne cokoliv ~1 135 Kč → zaručený zisk +135 Kč   │
│  Σ implik. pravd.: 87.98 %  (<100 % = arbitráž)               │
│  [ Vsadit (do deníku) ]   [ Změnit vklad: 1000 ▾ ]  [ skrýt ] │
└──────────────────────────────────────────────────────────────┘
```

Požadavky na kartu:
- **Barevné odlišení typu**: surebet (zelená), value (modrá), freebet (fialová).
- **Marže/EV velké a první** — to je hlavní rozhodovací číslo.
- **Tabulka noh**: výsledek, sázkovka (s logem/štítkem), kurz, **vklad v Kč**.
- **Přepočet vkladu** — uživatel změní celkovou částku (slider/pole) a vklady
  noh se okamžitě přepočítají (volá engine / přepočet na klientu).
- **Zaokrouhlení vkladů** na nastavitelný krok (default 10 Kč) a přepočet
  zaručeného zisku z reálně zaokrouhlených vkladů (worst-case noha).
- **Tlačítko „zkopírovat"** u každé nohy (částku/kurz), ať rychle zadám sázku.
- **Tlačítko „Vsadit"** → uloží do deníku jako open.
- **Rizikový štítek** (viz §8).
- U **value betu**: místo tabulky noh jeden řádek „vsaď X Kč na Y @ kurz",
  férová pravd., EV %, doporučený Kelly vklad z bankrollu.
- U **freebetu**: vstupy (výše free betu, kurzy) → výstup co vsadit a jistý zisk.

---

## 7b. Wireframe — Deník sázek (/bets)

```
┌─ DENÍK SÁZEK ───────────────────────────────────────────────────────────┐
│  Souhrn:  Vsazeno 142 600 Kč · Realiz. P/L +4 380 Kč · ROI +3.1%         │
│           Otevřené: 6 sázek (14 200 Kč)   [ Export CSV ]  [ Filtr ▾ ]    │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ [graf kumulativního P/L v čase — čára, zelená/červená zóna]        │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│  P/L po sázkovkách:  Tipsport +1 920 · Betano +1 040 · Fortuna +1 420 ·  │
│                      bet365 0 (jen kurzy)                                 │
├──────────────────────────────────────────────────────────────────────────┤
│ Datum     Zápas / Trh           Typ      Vklad   Kurzy/nohy   Stav  P/L   │
│ 20.6 21:3 Zverev–Fritz · Esa28.5 SUREBET 1 000  T3.00/b1.83  ✅won +135  │
│ 20.6 20:1 Slavia–Sparta · 1X2    SUREBET 1 000  3 nohy       ⏳open  —    │
│ 19.6 18:4 Plzeň–Baník · O2.5     VALUE   1 500  T2.05        ❌lost -1500 │
│ 19.6 17:0 Nymburk–Brno · O158.5  SUREBET   800  T1.95/b1.95  ✅sett +18  │
│ 18.6     uvítací bonus Betano     FREEBET 1 000  free2       ✅won +720  │
│  …                                                                        │
│  Řádek rozkliknu → detail: všechny nohy, kurzy, sázkovky, očekávaný vs.  │
│  skutečný zisk (odhalí void/chybu), poznámka, [ změnit stav ▾ ]          │
└──────────────────────────────────────────────────────────────────────────┘
```
- Stav sázky: `open → won / lost / void / settled`. Změna stavu přepočítá P/L.
- U surebetu ukaž **očekávaný** zisk vs. **skutečný** — když se liší, byl
  problém (void jedné nohy, jiná pravidla) → upozorni červeně.
- Filtry: typ, sázkovka, sport, stav, období. Export do CSV.

## 7c. Wireframe — Bankroll & zdraví účtů (/bankroll)

```
┌─ BANKROLL & ZDRAVÍ ÚČTŮ ──────────────────────────────────────────────────┐
│  Celkem v oběhu: 100 000 Kč    Volné: 38 400 Kč    Cílový Kelly: ¼        │
│  Doporučené rozdělení (diverzifikace): ●●●● rovnoměrně, max 30k/sázkovku   │
├────────────────────────────────────────────────────────────────────────────┤
│ Sázkovka  Zůstatek  Max vklad  Obrat   P/L     Mug/Ostré  Zdraví          │
│ Tipsport  24 500 Kč  5 000 Kč   62 000 +1 920   1:6        🟢 OK          │
│ Betano    21 000 Kč  3 000 Kč↓  31 000 +1 040   1:9        🟠 limit klesá │
│ Fortuna   16 900 Kč  5 000 Kč   28 000 +1 420   1:5        🟢 OK          │
│ bet365         —        —          —     —        —         ⚪ jen kurzy   │
├────────────────────────────────────────────────────────────────────────────┤
│  ⚠ Betano: max vklad spadl 5 000 → 3 000 Kč = blíží se limitace.          │
│     Doporučení: zařaď 1–2 mug bety, sniž objem, rotuj na Fortunu.          │
│  ⚠ Koncentrace OK (žádná sázkovka > 30 % bankrollu).                       │
│  [ Upravit zůstatky ]   [ Přidat sázkovku ]   [ Onboarding průvodce ▾ ]    │
└────────────────────────────────────────────────────────────────────────────┘
```
- **Max vklad + trend (↑/↓)** je hlavní signál blížící se limitace (viz
  `ACCOUNT_LONGEVITY.md` §7). Klesající = 🟠/🔴 a konkrétní doporučení.
- **Mug/Ostré** poměr na sázkovku (kamuflážní vs. arb sázky) — appka navrhne
  mug bet, když poměr klesne pod cíl.
- **Koncentrace**: varuj, když je na jedné sázkovce moc kapitálu/obratu.
- Navrhovaný vklad u příležitosti nesmí překročit zůstatek dané sázkovky.
- **Onboarding průvodce**: fáze rozjezdu (týden 1–2 bonusy → měsíc 1 lehké
  arby → měsíc 2+ navyšování) se stropy vkladů podle fáze.

## 8. Řazení, filtry, rizikové indikátory

**Řazení** (přepínatelné): podle marže/EV (default), podle času startu, podle
sázkovky, podle sportu, podle absolutního zisku v Kč při daném vkladu.

**Filtry:** typ (surebet/value/freebet), min. marže (default **5 %**, ale
posuvník od 0,5 %), min. EV, sport, konkrétní sázkovky, jen live / jen
prematch, skrýt zamítnuté.

**Rizikový indikátor** u každé příležitosti (barevný štítek + tooltip):
- **🔴 vysoké**: marže > ~8 % (pravděpodobně palpable error / rozdílná
  pravidla), nebo exotický trh, nebo velmi krátký čas do startu.
- **🟠 střední**: marže 3–8 %, live (kurz se rychle hýbe).
- **🟢 nízké**: marže 0,5–3 %, likvidní trh (1X2, počet gemů…).
- Tooltip vysvětlí proč (viz `STRATEGY.md` §3) + checklist „než vsadíš":
  ✔ stejný zápas ✔ stejný trh ✔ stejná hranice ✔ stejná pravidla skreče.

---

## 8b. Plán životnosti účtů (account longevity) — POVINNÁ součást

> Hlavní riziko byznysu je **limitace účtů** sázkovkami, ne matematika.
> Appka musí aktivně pomáhat „vypadat jako rekreační sázkař" — **legálně**
> (vlastní jméno, jeden účet na sázkovku, poctivé KYC; žádné multiúčty ani
> falešné identity). Detailní plán je v `ACCOUNT_LONGEVITY.md`. Implementuj:

- **Round stakes**: vklady zaokrouhluj (krok 10–50 Kč) a zobraz varování,
  když by vklad vyšel „podezřele přesný".
- **Mug bet tracker**: na stránce Bankroll/Deník u každé sázkovky veď poměr
  ostrých vs. kamuflážních (mug) sázek a navrhni, kdy vsadit mug bet.
- **Account health**: u každé sázkovky max povolený vklad, obrat, P/L a
  **trend limitu** (klesající max vklad = červené varování o blížící se
  limitaci).
- **Anti-burst**: appka NEsází automaticky bleskově; vede uživatele zadávat
  sázky lidsky, varuje před nárazem mnoha sázek z jednoho účtu krátce po sobě.
- **Diverzifikační rozpočet**: doporučené rozdělení 100k tak, aby na žádné
  sázkovce nebyl podezřele velký objem; varování na koncentraci.
- **Tempo/škálování**: onboarding průvodce (týden 1–2 bonusy a mug bety →
  měsíc 1 lehké arby → měsíc 2+ navyšování) a strop vkladů podle fáze.
- Nikdy nenabízej obcházení geoblokace ani multiúčty — naopak na to upozorni.

## 9. Bankroll a money management

- Stránka **Bankroll**: tabulka „sázkovka → aktuální zůstatek". Součet = volný
  kapitál.
- **Doporučené rozdělení 100k** napříč sázkovkami (rovnoměrně / dle limitů),
  varování když je moc kapitálu na jedné sázkovce.
- **Velikost sázky**: u surebetu default 1 000 Kč (nastavitelné), u value betu
  **zlomkový Kelly** (default ¼ Kelly, strop ~1–2 % bankrollu na sázku).
- Kontrola: navrhovaný vklad nesmí překročit zůstatek u dané sázkovky →
  jinak červené varování.

---

## 10. Deník sázek a P/L

- Po „Vsadit" se sázka uloží jako **open**. Později nastavím výsledek
  (won/lost/void/settled).
- **Souhrn**: počet sázek, realizovaný P/L, ROI, P/L po sázkovkách, P/L v čase
  (graf). U surebetu očekávaný zisk vs. skutečný (odhalí chyby/voidy).
- Export deníku do CSV.

---

## 11. Import kurzů — UX (důležité, děje se nejčastěji)

- Velké textové pole + příklad blokového formátu (z `ingest.py`):
  ```
  @book tipsport
  @sport tenis
  @event Alexander Zverev | Taylor Fritz
  @market Esa v zápase | 28.5
  Nad | 3.00
  Pod | 1.78
  ```
- Po vložení **náhled tabulky** naparsovaných kotací (sázkovka, zápas, trh,
  výsledek, kurz) + kolik se spárovalo do existujících zápasů, než uložím.
- Tlačítko „Uložit do DB" → spustí přepočet příležitostí.
- Bonus: tlačítko „Načíst přes Clauda/WebFetch" (volitelné, když poběží agent).

---

## 12. Nefunkční požadavky

- **Žádný klíč/API třetích stran nutný.** Vše lokálně.
- Rychlost: přepočet příležitostí pod ~1 s pro stovky kotací.
- Přehlednost na mobilu (sázím u telefonu).
- Data persistentní (SQLite soubor), neztratit deník při restartu.
- Kód čistý, otestovaný (pytest na engine + 2–3 API testy).

---

## 13. Akceptační kritéria (Definition of Done pro MVP)

1. Vložím blokový text se 4 sázkovkami → appka uloží kotace a spáruje zápas.
2. Dashboard ukáže surebet **+13.66 %** (Tipsport 3.00 / bet365 1.83) se
   správnými vklady **380 / 620 Kč** a zaručeným ziskem ~135 Kč.
3. Zobrazí i **value bety** nad zadaným EV a umožní filtr min. marže 5 %.
4. Změním celkový vklad → vklady noh se přepočítají.
5. „Vsadit" zapíše sázku do deníku; změna statusu přepočítá P/L.
6. Freebet kalkulačka vrátí jistý zisk pro free2/lay.
7. Rizikový štítek a checklist se zobrazí u každé příležitosti.
8. README: jak spustit backend i frontend + seed data.

---

## 14. Fázování (doporučené pořadí práce)

1. **Engine jako balíček** + pytest (potvrď 13.66 % a value bety).
2. **Backend FastAPI**: `/ingest`, `/opportunities`, `/events` + SQLite.
3. **Frontend MVP**: Import + Dashboard s kartami a filtry (akcept. kritéria 1–4).
4. **Deník + Bankroll** (kritéria 5).
5. **Freebet + rizikové štítky + detail zápasu** (kritéria 6–7).
6. **Leštění**: mobil, grafy P/L, export CSV, README.

---

## 15. Důležité upozornění, které appka musí zobrazovat

V patičce / u karet zobrazuj varování ze `STRATEGY.md`:
- 20 %+ „jasných" surebetů reálně skoro neexistuje — bývá to chyba sázkovky
  (palpable error), kterou stornují, nebo rozdílná pravidla trhu.
- Hlavní riziko není matematika, ale **limitace účtů** sázkovkami.
- Stabilní výdělek = objem malých marží (1–3 %) + bonusy.
- Ověř pravidla obou sázkovek pro daný trh (skreč/odstoupení) PŘED sázkou.
- Sázej zodpovědně (18+). Daně v ČR konzultuj s poradcem.

> Pozn.: bet365 v ČR oficiálně nepůsobí — ber ho primárně jako zdroj kurzu
> k porovnání, ne nutně jako sázkovku, kam reálně sázíš.

--- KONEC ZADÁNÍ ---
```
```
