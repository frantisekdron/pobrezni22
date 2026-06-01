# Pobřežní 22 — nový web

Moderní jednostránkový web pro projekt luxusního bydlení **Pobřežní 22, Karlín**.
Statický web (HTML/CSS/JS) — bez frameworku, nasaditelný kamkoliv.

Styl: **cream & gold**, dvojjazyčně **CZ/EN**, důraz na marketing a genius loci Karlína.

---

## Struktura

```
pobrezni22/
├─ index.html              # struktura všech sekcí
├─ assets/
│  ├─ css/styles.css       # design systém + komponenty
│  ├─ js/
│  │  ├─ data.js           # ⭐ DATA: byty, ceny, kontakt, texty CZ/EN
│  │  └─ main.js           # interaktivita (filtry, modal, formulář, jazyk)
│  └─ img/                 # exterior · location · interiors · floorplans · standards · brand
└─ README.md
```

Sekce: Hero → Hodnoty → **Karlín (dron)** → Dům (den/noc) → Interiéry → Standardy →
**Výběr bytů** (filtr + detail + půdorys) → Financování → **Rezervace prohlídky** → Kontakt → Footer.

---

## Co snadno upravíte — vše v `assets/js/data.js`

### 1) Dostupnost bytů
U každého bytu pole `status`:
- `"available"` — Volný
- `"reserved"` — Rezervováno
- `"sold"` — Prodáno

> ⚠️ Dle ceníkové tabulky jsou jako rezervované označené byty **1, 5, 8, 11**.
> **Potvrďte prosím aktuální stav** — pak stačí změnit `status`.

### 2) Makléř (kontakt)
Objekt `SITE.agent` — doplňte `name`, `role`, `phone`, `phoneHref`, `email`
a fotku uložte jako `assets/img/brand/makler.jpg`. Bez fotky se zobrazí elegantní iniciála.

### 3) Odeslání rezervačního formuláře
Aktuálně `SITE.FORM_ENDPOINT = ""` → formulář otevře e-mailového klienta (mailto na `info@flatbee.cz`). Funguje hned.

**Doporučeno (bez backendu, odesílá na pozadí):** [Web3Forms](https://web3forms.com) — zdarma:
1. Získejte „Access Key".
2. V `data.js`: `FORM_ENDPOINT: "https://api.web3forms.com/submit"` a `WEB3FORMS_KEY: "VÁŠ-KLÍČ"`.
Poptávky pak chodí přímo na e-mail bez otevírání klienta. (Funguje i Formspree — stačí vložit jeho URL do `FORM_ENDPOINT`.)

### 4) Texty
Slovník `I18N` — každý klíč má `cs` a `en`. Úprava textace na jednom místě.

---

## Spuštění lokálně
```bash
cd pobrezni22
python3 -m http.server 4321      # nebo: npx serve .
# otevřete http://localhost:4321
```

## Nasazení
Jde o statický web — nahrajte obsah složky `pobrezni22/` na libovolný hosting:
- **Netlify / Vercel / Cloudflare Pages** — drag & drop složky
- klasický web hosting (FTP) — nahrát do rootu domény pobrezni22.cz

---

## Vizuály
- Exteriér den/noc, dron Karlína a interiéry jsou webově optimalizované (JPEG).
- Půdorysy pater vygenerované z PDF (2.–5. NP). Byt 1 a 2 (1. NP) zatím bez půdorysu → zobrazí se 3D půdorys jako fallback.

## TODO (po dodání podkladů)
- [ ] Zapracovat **komentáře klienta**
- [ ] Doplnit **makléře** (jméno, kontakt, foto)
- [ ] Potvrdit **aktuální dostupnost** bytů
- [ ] (volitelně) Web3Forms klíč pro odesílání formuláře bez mailto
- [ ] (volitelně) doplnit promo **video** do hero/sekce (k dispozici `chundela_reality_-_pobřežní_22.mp4`)
