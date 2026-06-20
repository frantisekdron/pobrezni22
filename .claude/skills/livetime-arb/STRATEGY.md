# Strategie, rizika a plán bankrollu (100 000 Kč)

> Tohle je upřímné zhodnocení, ne prodejní řeč. Arbitráž a matched betting
> **fungují** a jsou legální, ale „bezpečný zaručený výdělek" má v praxi
> háčky, které rozhodují o tom, jestli vyděláš, nebo o peníze přijdeš.
> Čti to celé předtím, než pošleš do hry 100k.

---

## 1. Realita čísel: co je dosažitelné

| Marže surebetu | Jak časté | Co to obvykle znamená |
|---|---|---|
| 0,5 – 2 % | běžné, denně desítky | reálná arbitráž z rozdílu kurzů – tady se vydělává |
| 2 – 5 % | méně časté, live | rychlé pohyby kurzů, musíš být svižný |
| 5 – 10 % | vzácné | často rozdílná pravidla trhu, nebo kurz hned spadne |
| **20 %+ „jasných"** | **skoro nikdy poctivě** | **typicky CHYBA sázkovky → sázku stornují (viz §3)** |

**Odpověď na „najdeš jasných 20 % a výš?":** Engine je najde a spočítá (viz
3‑cestný test = 21,97 %). Ale „jasných 20 %", kde se nedá prohrát a sázkovka
to *proplatí*, v praxi prakticky neexistují. Když se 20 % objeví, je to skoro
vždy jeden ze tří případů:

1. **Palpable error** — překlep v kurzu. Sázkovka má v podmínkách právo
   takovou sázku zrušit a vrátit vklad (ne ale druhou nohu na jiné sázkovce →
   tam zůstaneš nekrytý a můžeš prodělat).
2. **Rozdílná pravidla trhu** — „esa v zápase" se u dvou sázkovek počítá jinak
   (skreč, retired, walkover), takže to *není* opačná strana téhož.
3. **Kurz už neexistuje** — než klikneš, je pryč.

Ten tvůj příklad **13,66 %** je výjimečně vysoký a spadá přesně do téhle
rizikové zóny — proto v §3 trvám na ověření pravidel skreče. Stabilní byznys
se staví na **0,5–3 %** marži a na **bonusech** (matched betting), ne na lovu
20 %.

---

## 2. Tři způsoby, jak „matematicky nemůžeš prohrát"

Skill umí všechny tři spočítat:

1. **Arbitráž (surebet)** — `analyze.py`, `arb.py`. Vsadíš všechny výsledky
   trhu u sázkovek s nejvyššími kurzy, `Σ(1/kurz) < 1`. Jistý zisk.
2. **N‑cestná arbitráž** — stejné, ale 3+ výsledky (1X2). Vzácnější, ale když
   se sejde, marže bývá vyšší.
3. **Konverze bonusů / free betů** — `freebet.py`. Nejstabilnější +EV cesta.
   Free bet (stake se nevrací) přetavíš na ~70–80 % jeho hodnoty v hotovosti
   tím, že vsadíš opačný výsledek jinde. Sázkovky bonusy rozdávají rády, takže
   tě za to nelimitují tak rychle jako za arby.

A jedna „skoro": **value bety** (`analyze.py`) — kurz vyšší než férová
pravděpodobnost z konsensu. Není to jistota na jednu sázku, ale dlouhodobě
+EV. Sázej je zlomkovým Kelly (`--kelly 0.25`), ne all‑in.

---

## 3. Rizika (od nejnebezpečnějšího)

**① Limitace a rušení účtů („gubbing") — #1 zabiják byznysu.**
Sázkovky aktivně hledají arbitrážníky a vítěze. Když tě označí, sníží ti
maximální vklad (klidně na 20 Kč), zpomalí výplaty, nebo účet zavřou. Tvých
100k pak nemáš kam vsadit. **Tohle, ne matematika, rozhoduje o úspěchu.**

**② Leg risk (nekrytá noha).** Vsadíš první nohu, druhý kurz se hne nebo
zmizí → zůstaneš s jednostrannou sázkou. U live je to časté. Proto: nejdřív
ta hůř dostupná/pomalejší noha, pak rychlá.

> **➜ Preferuj PREMATCH (před výkopem), ne live.** Doporučená výchozí strategie:
> prematch kurzy jsou stabilní (drží minuty až hodiny), takže obě nohy stihneš
> v klidu a leg risk je minimální. Navíc se prematch líp sbírá (žádné
> websockety/anti-bot jako u live) a je míň pravděpodobné, že jde o palpable
> error. Live ber jen jako bonus, když máš jistý a rychlý postup. Marže prematch
> arbů bývají menší (0,5–2 %), ale o to bezpečnější — a to je přesně cíl.

**③ Palpable error / void.** Sázkovka stornuje „chybný" kurz a vrátí jen svůj
vklad. Druhá noha jinde platí → ztráta. Riziko roste s marží (proto pozor na
20 %).

**④ Rozdílná pravidla zúčtování.** Skreč, prodloužení, „dead heat", jiný počet
setů, jiná definice trhu. Pak to nejsou opačné strany. **Vždy ověř pravidla
obou sázkovek pro daný trh.**

**⑤ Likvidita a limity vkladů.** Na exotický trh tě sázkovka nepustí s velkým
vkladem. 100k najednou nikam nedáš.

**⑥ KYC, výběry, zamrzlý kapitál.** Peníze rozdělené po 5–6 sázkovkách,
výběry trvají, identifikace, denní/měsíční limity.

**⑦ Daně (ČR).** Výhry z hazardu od provozovatele s českou licencí bývají pro
hráče osvobozené **do ročního čistého zisku ~1 mil. Kč** (§ 4 zákona o daních
z příjmů), nad to se daní. U zahraničních/nelicencovaných sázkovek to platí
jinak. **Není to daňová rada — ověř s daňovým poradcem** podle své situace.

**⑧ Psychologie a chyby.** Špatně zadaný vklad, špatná noha, špatná hranice.
Při rychlém live se chybuje. Proto deník (DB) a kontrola před odesláním.

---

## 4. Bezpečný plán pro 100 000 Kč

### Fáze 0 — příprava (než vsadíš korunu)
- Účty u **Tipsport, Betano, Fortuna** (české licence; bet365 v ČR oficiálně
  nepůsobí — počítej s ním spíš jako se zdrojem kurzu k porovnání než kam
  reálně sázíš, pokud k němu nemáš legální přístup).
- Rozděl kapitál: **nepouštěj 100k najednou.** Začni s **20–30k** rozprostřenými
  po sázkovkách (např. 8k/8k/8k). Zbytek drž jako rezervu / na navýšení, až
  ověříš, že ti to klape a účty nelimitují.
- Založ DB a deník: `python3 scripts/db.py init`.

### Fáze 1 — měsíc 1: bonusy (nejbezpečnější rozjezd)
- Odemkni uvítací bonusy a free bety, převeď je přes `freebet.py`. To je
  prakticky bezrizikový výnos a „zamaskuje" tě jako rekreačního sázkaře.
- Cíl: poznat mechaniku výběrů/limitů a vydělat prvních pár tisíc bez tlaku.

### Fáze 2 — měsíc 2+: arby 1–3 % + value bety
- Sázej **surebety od ~1,5 %** (ne čekej na 5 %+ — těch je málo a jsou
  rizikovější). Filtr: `analyze.py --min-margin 1.5`.
- Stake na jeden surebet drž v rámci limitů a „rekreačně" vypadajících částek:
  **500–3000 Kč**, ne 50k najednou.
- Value bety zlomkovým Kelly (`--kelly 0.25`, max ~1–2 % bankrollu na sázku).

### Account management (aby tě nezabili dřív, než vyděláš)
- Sázej i „normálně": kulaté částky, populární trhy, občas akumulátor.
- Neber pokaždé úplně nejvyšší kurz na trhu na minutu přesně.
- Rozlož aktivitu v čase, neber 30 arbů za hodinu z jednoho účtu.
- Vybírej zisky postupně, ne nárazově po každé sázce.

### Realistické očekávání výnosu
- Disciplinovaný arbér/matched bettor: řádově **jednotky % měsíčně** z aktivního
  kapitálu, **dokud účty žijí**. Není to „13,66 % z každé sázky pořád".
- Hlavní strop není matematika, ale **kolik a jak dlouho tě sázkovky nechají
  sázet**. Proto se začíná malým kapitálem a škáluje se opatrně.

---

## 5. Pracovní postup s tímto skillem

```bash
cd .claude/skills/livetime-arb/scripts
python3 db.py init

# 1) Zkopíruj live stránku sázkovky (nebo ji načte Claude přes WebFetch),
#    vlož do bloku a importuj do DB (zopakuj pro každou sázkovku/zápas):
python3 ingest.py paste_tipsport.txt --db
python3 ingest.py paste_bet365.txt  --db

# 2) Najdi VŠECHNY příležitosti (surebety + value bety) nad 5 %:
python3 analyze.py --db --min-margin 5 --min-edge 5 -B 100000

# …nebo realisticky od 1,5 %:
python3 analyze.py --db --min-margin 1.5 --min-edge 2 -B 100000

# 3) Bonus/free bet na jisto:
python3 freebet.py free2 1000 2.00 2.10

# 4) Ověř pravidla obou sázkovek pro daný trh, pak sázej.
#    Zaznamenej do deníku (status open → won/settled/voided).
```

---

## 6. Shrnutí na jednu větu

Vyděláš na **objemu malých jistých marží (1–3 %) + bonusech**, ne na lovu
20 %; rozhodující riziko není matematika, ale **limitace účtů**, takže začni
s menším kapitálem, sázej nenápadně a 100k nasaď až po ověření, že ti systém
i účty drží.
