/* ============================================================================
   POBŘEŽNÍ 22 — datové jádro
   Jediný zdroj pravdy: konfigurace, byty, komerce, jazykový slovník (CZ/EN).
   ----------------------------------------------------------------------------
   AKTUALIZACE DOSTUPNOSTI: stačí změnit pole `status` u bytu níže.
   Hodnoty: "available" (volný) | "reserved" (rezervováno) | "sold" (prodáno)
   Pozn.: dle ceníkové tabulky jsou rezervované byty 1, 5, 8, 11 — POTVRĎTE s klientem.
============================================================================ */

const SITE = {
  // Kontakt / značka
  company: "Flatbee Capital s.r.o.",
  companyId: "IČ 23166452",
  phone: "+420 721 461 411",
  phoneHref: "+420721461411",
  email: "info@flatbee.cz",
  address: "Pobřežní 285/22, 186 00 Praha 8 — Karlín",
  instagram: "https://www.instagram.com/",
  completion: "09/2026",

  // Makléř — DOPLNIT (jméno, telefon, e-mail, foto do assets/img/brand/makler.webp)
  agent: {
    name: "Jméno Makléře",
    role: "Váš průvodce projektem",
    phone: "+420 721 461 411",
    phoneHref: "+420721461411",
    email: "info@flatbee.cz",
    photo: "assets/img/brand/makler.webp" // zatím placeholder
  },

  // Odeslání formuláře:
  //  - FORM_ENDPOINT prázdné  -> otevře e-mailového klienta (mailto) na info@flatbee.cz (funguje ihned)
  //  - FORM_ENDPOINT = Web3Forms/Formspree URL -> odešle na pozadí (AJAX), bez backendu
  // Web3Forms: vložte "https://api.web3forms.com/submit" a níže WEB3FORMS_KEY
  FORM_ENDPOINT: "",
  WEB3FORMS_KEY: ""
};

/* ---------------------------------------------------------------------------
   BYTY — dle ceníkové tabulky „Tabulka pro obchodníky Karlín"
   plocha = podlahová (interiér), extra = balkon/terasa/pavlač/dvorek,
   sklep = m², total = celková plocha včetně extra a sklepa, price = Kč
--------------------------------------------------------------------------- */
/* plan = obrázek karty/půdorysu daného bytu (konzistentně pro všechny).
   mezonet:true POUZE byt 14 (jediný s vnitřním schodištěm). */
const APARTMENTS = [
  { id: 1,  floor: 1, layout: "2+kk", area: 28.0, extra: null,                 cellar: null, total: 28.0, price: 5490000,  status: "reserved", plan: "byt-1",  img: "assets/img/interiors/viz-06.webp" },
  { id: 2,  floor: 1, layout: "2+kk", area: 34.9, extra: {t:"dvorek", m:20.8}, cellar: null, total: 55.7, price: 7790000,  status: "available", plan: "byt-2",  img: "assets/img/interiors/viz-02.webp" },
  { id: 3,  floor: 2, layout: "3+kk", area: 71.3, extra: null,                 cellar: 2.2,  total: 73.5, price: 14140000, status: "available", plan: "byt-3",  img: "assets/img/interiors/viz-01.webp" },
  { id: 4,  floor: 2, layout: "2+kk", area: 66.3, extra: {t:"pavlač", m:5.4},  cellar: 1.7,  total: 73.4, price: 13640000, status: "available", plan: "byt-4",  img: "assets/img/interiors/viz-04.webp" },
  { id: 5,  floor: 2, layout: "2+kk", area: 35.5, extra: {t:"balkon", m:2.7},  cellar: 1.4,  total: 39.6, price: 7340000,  status: "reserved", plan: "byt-5",  img: "assets/img/interiors/viz-08.webp" },
  { id: 6,  floor: 3, layout: "3+kk", area: 70.4, extra: null,                 cellar: 1.7,  total: 72.1, price: 13840000, status: "available", plan: "byt-6",  img: "assets/img/interiors/viz-03.webp" },
  { id: 7,  floor: 3, layout: "2+kk", area: 65.7, extra: {t:"pavlač", m:5.4},  cellar: 1.7,  total: 72.8, price: 13540000, status: "available", plan: "byt-7",  img: "assets/img/interiors/viz-05.webp" },
  { id: 8,  floor: 3, layout: "2+kk", area: 35.6, extra: {t:"balkon", m:2.7},  cellar: 1.5,  total: 39.8, price: 7240000,  status: "reserved", plan: "byt-8",  img: "assets/img/interiors/viz-09.webp" },
  { id: 9,  floor: 4, layout: "3+kk", area: 71.3, extra: null,                 cellar: 2.2,  total: 73.5, price: 14140000, status: "available", plan: "byt-9",  img: "assets/img/interiors/viz-01.webp" },
  { id: 10, floor: 4, layout: "2+kk", area: 67.1, extra: {t:"pavlač", m:5.4},  cellar: 1.7,  total: 74.2, price: 13840000, status: "available", plan: "byt-10", img: "assets/img/interiors/viz-06.webp" },
  { id: 11, floor: 4, layout: "2+kk", area: 35.7, extra: {t:"balkon", m:2.7},  cellar: 1.5,  total: 39.9, price: 7440000,  status: "reserved", plan: "byt-11", img: "assets/img/interiors/viz-07.webp" },
  { id: 12, floor: 5, layout: "2+kk", area: 51.3, extra: {t:"terasa", m:3.9},  cellar: 1.7,  total: 56.9, price: 10540000, status: "available", plan: "byt-13", img: "assets/img/interiors/mezonet-obyvak.webp" },
  { id: 13, floor: 5, layout: "3+kk", area: 79.3, extra: {t:"terasa", m:3.2},  cellar: 2.3,  total: 84.8, price: 17140000, status: "available", plan: "byt-13", img: "assets/img/interiors/viz-04.webp" },
  { id: 14, floor: 5, layout: "3+kk", area: 80.4, extra: null,                 cellar: 2.6,  total: 83.0, price: 17440000, status: "available", plan: "byt-14", mezonet: true, img: "assets/img/interiors/byt14-3.webp" }
];

/* Patra domu (pro průzkumník) — pozice pásu na VÝKRESU fasády v %
   Výkres: mansarda 5.NP nahoře, pak 3 řady oken (4./3./2.NP), dole přízemí 1.NP */
const FLOORS = [
  { n: 5, top: 2,  h: 21, label: { cs: "5. NP — podkroví", en: "5th floor — attic" } },
  { n: 4, top: 23, h: 16, label: { cs: "4. NP", en: "4th floor" } },
  { n: 3, top: 39, h: 15, label: { cs: "3. NP", en: "3rd floor" } },
  { n: 2, top: 54, h: 15, label: { cs: "2. NP", en: "2nd floor" } },
  { n: 1, top: 69, h: 27, label: { cs: "1. NP — přízemí", en: "Ground floor" } }
];

/* KOMERČNÍ PROSTORY */
const COMMERCIAL = [
  { code: "285/101", floor: "1.PP", area: 23.8, price: 2357414 },
  { code: "285/102", floor: "1.PP", area: 38.3, price: 3793680 },
  { code: "285/103", floor: "1.PP", area: 64.8, price: 6418550 },
  { code: "285/105", floor: "1.NP", area: 72.2, price: 13286207 }
];

/* GALERIE INTERIÉRŮ */
const GALLERY = [
  { src: "assets/img/interiors/byt14-5.webp",         cap: { cs: "Mezonet 3+kk — obytný prostor se schodištěm", en: "Maisonette 3+kk — living space with staircase" } },
  { src: "assets/img/interiors/byt14-1.webp",         cap: { cs: "Kuchyňská linka pod schodištěm", en: "Kitchen beneath the staircase" } },
  { src: "assets/img/interiors/mezonet-obyvak.webp",  cap: { cs: "Otevřený obývací prostor s kuchyní", en: "Open living & kitchen" } },
  { src: "assets/img/interiors/byt14-3.webp",         cap: { cs: "Horní galerie mezonetu", en: "Maisonette upper gallery" } },
  { src: "assets/img/interiors/byt14-7.webp",         cap: { cs: "Jídelní kout s výhledem do ložnice", en: "Dining nook overlooking the bedroom" } },
  { src: "assets/img/interiors/mezonet-loznice.webp", cap: { cs: "Podkrovní ložnice", en: "Attic bedroom" } },
  { src: "assets/img/interiors/viz-01.webp",          cap: { cs: "Obývací pokoj", en: "Living room" } },
  { src: "assets/img/interiors/viz-06.webp",          cap: { cs: "Výhled do ulice", en: "View to the street" } },
  { src: "assets/img/interiors/viz-08.webp",          cap: { cs: "Ložnice", en: "Bedroom" } },
  { src: "assets/img/interiors/viz-09.webp",          cap: { cs: "Ložnice se šatnou", en: "Bedroom with walk-in closet" } }
];

/* STANDARDY PROVEDENÍ (z architektonického sampleboardu, 06/2025) */
const STANDARDS = [
  { icon: "parquet", t: { cs: "Dubové parkety", en: "Oak parquet" },
    d: { cs: "Dvouvrstvé dubové parkety v přírodním i barveném provedení do světlých odstínů, s frézovanou mikrospárou. Soklové lišty po obvodu všech místností.",
         en: "Two-layer oak parquet in natural and tinted light shades with a milled micro-joint. Skirting along every room." } },
  { icon: "door", t: { cs: "Repliky původních dveří", en: "Replica heritage doors" },
    d: { cs: "Interiérové historizující dveře jako přesné repliky dochovaných originálů — jedno i dvoukřídlé, s možností leptané skleněné výplně. Doplněno moderní bezfalcovou variantou.",
         en: "Heritage interior doors faithfully replicating the originals — single & double leaf, with optional etched glass. Complemented by a modern frameless line." } },
  { icon: "tile", t: { cs: "Obklady & dlažby", en: "Tiles & paving" },
    d: { cs: "Velkoformátové obklady s motivem kamene a jemného terazza, doplněné barevnými glazovanými pásky. Formáty 600×600 a 1200×600 mm.",
         en: "Large-format tiles with stone and fine terrazzo motifs, accented by coloured glazed strips. Formats 600×600 and 1200×600 mm." } },
  { icon: "bath", t: { cs: "Prémiová sanita", en: "Premium sanitaryware" },
    d: { cs: "Závěsné WC Vitra, umyvadla SAT Cube, baterie a sprchové systémy SAT v provedení černá/chrom, splachování Geberit Sigma50.",
         en: "Vitra wall-hung WCs, SAT Cube basins, SAT taps & shower systems in black/chrome, Geberit Sigma50 flush plates." } },
  { icon: "switch", t: { cs: "Elektro ABB Levit", en: "ABB Levit electrics" },
    d: { cs: "Vypínače a zásuvky ABB Levit v odstínu ledová bílá, sjednocený design v celém bytě.",
         en: "ABB Levit switches and sockets in ice white, a consistent design throughout the apartment." } },
  { icon: "window", t: { cs: "Historická fasáda", en: "Restored façade" },
    d: { cs: "Citlivě obnovená klasicistní fasáda s původní štukovou výzdobou, špaletová okna a klenuté vstupy zachované v původním duchu.",
         en: "A sensitively restored Neoclassical façade with original stucco, box windows and arched entrances kept in their original spirit." } }
];

/* PROJEKT — GPS poloha domu (Pobřežní 285/22, Karlín) */
const PROJECT_GEO = { lat: 50.09285, lng: 14.44895 };

/* LOKALITA — body zájmu s dostupností pěšky + reálné GPS souřadnice pro mapu */
const LOCATION_POINTS = [
  { min: 3,  lat: 50.08960, lng: 14.43840, img: "assets/img/poi/poi-florenc.webp",   t: { cs: "Metro Florenc (B, C)", en: "Florenc metro (B, C)" } },
  { min: 4,  lat: 50.09430, lng: 14.44230, img: "assets/img/poi/poi-stvanice.webp",  t: { cs: "Náplavka & ostrov Štvanice", en: "Riverside & Štvanice island" } },
  { min: 5,  lat: 50.09250, lng: 14.45040, img: "assets/img/poi/poi-kostel.webp",    t: { cs: "Karlínské náměstí & kostel", en: "Karlín square & church" } },
  { min: 6,  lat: 50.09120, lng: 14.44760, img: "assets/img/poi/poi-kavarny.webp",   t: { cs: "Kavárny a restaurace", en: "Cafés & restaurants" } },
  { min: 10, lat: 50.08930, lng: 14.42870, img: "assets/img/poi/poi-palladium.webp", t: { cs: "OC Palladium & centrum", en: "Palladium & city centre" } },
  { min: 12, lat: 50.08620, lng: 14.45170, img: "assets/img/poi/poi-vitkov.webp",    t: { cs: "Park na vrchu Vítkov", en: "Vítkov hill park" } }
];

/* JAZYKOVÝ SLOVNÍK */
const I18N = {
  // NAV
  "nav.about":      { cs: "Dům",         en: "The house" },
  "nav.karlin":     { cs: "Karlín",      en: "Karlín" },
  "nav.interiors":  { cs: "Interiéry",   en: "Interiors" },
  "nav.standards":  { cs: "Standardy",   en: "Standards" },
  "nav.flats":      { cs: "Byty",        en: "Residences" },
  "nav.financing":  { cs: "Financování", en: "Financing" },
  "nav.contact":    { cs: "Kontakt",     en: "Contact" },
  "nav.reserve":    { cs: "Rezervovat prohlídku", en: "Book a viewing" },

  // HERO
  "hero.eyebrow":   { cs: "Rezidence v srdci Karlína", en: "A residence in the heart of Karlín" },
  "hero.title":     { cs: "Pobřežní 22", en: "Pobřežní 22" },
  "hero.subtitle":  { cs: "Historický dům, znovuzrozený pro současné bydlení — na jedné z nejprestižnějších adres Prahy.",
                      en: "A historic house reborn for contemporary living — at one of Prague's most prestigious addresses." },
  "hero.kicker":    { cs: "Historický dům · 14 rezidencí · Dokončení 2026", en: "Historic house · 14 residences · Ready 2026" },
  "hero.sound":     { cs: "Zvuk", en: "Sound" },
  "hero.cta1":      { cs: "Vybrat byt", en: "Choose a residence" },
  "hero.cta2":      { cs: "Rezervovat prohlídku", en: "Book a viewing" },
  "hero.scroll":    { cs: "Objevte více", en: "Discover more" },
  "hero.stat1":     { cs: "Volných bytů", en: "Available" },
  "hero.stat2":     { cs: "Dispozice", en: "Layouts" },
  "hero.stat3":     { cs: "Cena od", en: "Price from" },
  "hero.stat4":     { cs: "Dokončení", en: "Completion" },

  // INTRO / hodnoty
  "intro.eyebrow":  { cs: "O projektu", en: "The project" },
  "intro.lead":     { cs: "Adresa, která má duši", en: "An address with a soul" },
  "intro.text":     { cs: "Pobřežní 22 spojuje půvab historického činžovního domu s precizní rekonstrukcí a moderním komfortem. Vzniká tu kolekce čtrnácti bytů — od kompaktních 2+kk po prostorné 3+kk s terasami — v lokalitě, kterou dnes vyhledává celá Praha.",
                      en: "Pobřežní 22 unites the charm of a historic townhouse with a meticulous renovation and modern comfort. A collection of fourteen residences — from compact 2+kk to spacious 3+kk with terraces — in the district all of Prague now seeks out." },
  "intro.v1t":      { cs: "Prestižní adresa", en: "Prestigious address" },
  "intro.v1d":      { cs: "Pobřežní ulice v dosahu Vltavy, Florence i centra.", en: "Pobřežní street, steps from the Vltava, Florenc and the centre." },
  "intro.v2t":      { cs: "Citlivá rekonstrukce", en: "Sensitive renovation" },
  "intro.v2d":      { cs: "Obnovená klasicistní fasáda, repliky původních prvků.", en: "A restored Neoclassical façade and replica heritage details." },
  "intro.v3t":      { cs: "14 jedinečných bytů", en: "14 unique homes" },
  "intro.v3d":      { cs: "Každý byt s vlastním charakterem, sklepem a soukromím.", en: "Each home with its own character, cellar and privacy." },
  "intro.v4t":      { cs: "Dokončení 2026", en: "Ready in 2026" },
  "intro.v4d":      { cs: "Nastěhujte se do nového domova v září 2026.", en: "Move into your new home in September 2026." },

  // KARLÍN
  "karlin.eyebrow": { cs: "Genius loci", en: "Genius loci" },
  "karlin.title":   { cs: "Karlín — nejživější čtvrť Prahy", en: "Karlín — Prague's most vibrant quarter" },
  "karlin.text":    { cs: "Mezi řekou Vltavou a zeleným vrchem Vítkov leží čtvrť, která se proměnila v synonymum dobrého života. Karlín dnes spojuje industriální minulost, novou architekturu, ateliéry, kavárny a parky — a přitom je pár minut od historického jádra Prahy. Bydlet zde znamená mít vše na dosah a přesto vlastní klid.",
                      en: "Between the Vltava river and the green Vítkov hill lies a quarter that has become a byword for the good life. Karlín blends an industrial past with new architecture, studios, cafés and parks — all just minutes from Prague's historic core. To live here is to have everything within reach, yet keep your own calm." },
  "karlin.points":  { cs: "Vše na dosah", en: "Everything within reach" },
  "karlin.here":    { cs: "Pobřežní 22", en: "Pobřežní 22" },
  "karlin.reach":   { cs: "V pěší dostupnosti", en: "Within walking distance" },
  "karlin.note":    { cs: "Najeďte na body — ukážou se na mapě", en: "Hover the points — they show on the map" },
  "karlin.cap1":    { cs: "Karlín při západu slunce — kostel sv. Cyrila a Metoděje a vrch Vítkov", en: "Karlín at sunset — the Church of Sts Cyril & Methodius and Vítkov hill" },
  "karlin.cap2":    { cs: "Pohled k Vltavě, ostrovu Štvanice a Žižkovské věži", en: "Towards the Vltava, Štvanice island and the Žižkov tower" },

  // DŮM
  "house.eyebrow":  { cs: "Dům & rekonstrukce", en: "The house & renovation" },
  "house.title":    { cs: "Klasická krása, současný komfort", en: "Classic beauty, modern comfort" },
  "house.text":     { cs: "Činžovní dům s klasicistní fasádou prochází kompletní a citlivou rekonstrukcí. Štuková výzdoba, klenuté vstupy i špaletová okna zůstávají věrné původnímu duchu, zatímco interiéry, rozvody a technologie odpovídají nárokům dnešního bydlení. Výsledkem je dům, který ctí svou historii a zároveň nabízí pohodlí nové výstavby.",
                      en: "This townhouse with its Neoclassical façade is undergoing a complete, sensitive renovation. The stucco ornament, arched entrances and box windows stay true to the original spirit, while the interiors, services and technology meet the demands of contemporary living. The result is a house that honours its history yet offers the comfort of new construction." },
  "house.f1":       { cs: "Den", en: "By day" },
  "house.f2":       { cs: "Noc", en: "By night" },
  "house.tag1":     { cs: "Klasicistní fasáda", en: "Neoclassical façade" },
  "house.tag2":     { cs: "Kompletní rekonstrukce", en: "Full renovation" },
  "house.tag3":     { cs: "Sklep ke každému bytu", en: "Cellar with every flat" },
  "house.capline":  { cs: "Pobřežní 285/22 — obnovená klasicistní fasáda", en: "Pobřežní 285/22 — the restored Neoclassical façade" },

  // ATMOSFÉRICKÉ PÁSY
  "atmos.line1":    { cs: "Žít na adrese, kterou si pamatují", en: "Live at an address people remember" },
  "atmos.sub1":     { cs: "Pobřežní 22 — tam, kde se Karlín potkává s Vltavou", en: "Pobřežní 22 — where Karlín meets the Vltava" },
  "atmos.line2":    { cs: "Dům, který po setmění září", en: "A house that glows after dark" },
  "atmos.sub2":     { cs: "Modrá hodina nad Pobřežní ulicí", en: "Blue hour over Pobřežní street" },

  // VIDEOPROHLÍDKA
  "reel.eyebrow":   { cs: "Videoprohlídka", en: "Video tour" },
  "reel.title":     { cs: "Atmosféra, kterou musíte vidět", en: "An atmosphere you have to see" },
  "reel.text":      { cs: "Projděte se rezidencí a jejím okolím — od fasády po interiér.", en: "Take a walk through the residence and its surroundings — from façade to interior." },
  "reel.play":      { cs: "Přehrát se zvukem", en: "Play with sound" },

  // INTERIÉRY
  "int.eyebrow":    { cs: "Interiéry", en: "Interiors" },
  "int.title":      { cs: "Světlo, dřevo a klid", en: "Light, wood and calm" },
  "int.text":       { cs: "Vizualizace bytů ukazují materiálovou poctivost a vzdušnost prostoru — dubové parkety, přirozené světlo a čisté linie.", en: "The apartment visualisations show honest materials and airy space — oak floors, natural light and clean lines." },

  // STANDARDY
  "std.eyebrow":    { cs: "Standardy provedení", en: "Specification standards" },
  "std.title":      { cs: "Materiály, na kterých záleží", en: "Materials that matter" },
  "std.text":       { cs: "Výběr povrchů a prvků vychází z architektonického návrhu rekonstrukce. Kvalita v každém detailu.", en: "The choice of surfaces and fittings follows the architectural renovation design. Quality in every detail." },

  // BYTY
  "flats.eyebrow":  { cs: "Výběr bytů", en: "Choose your home" },
  "flats.title":    { cs: "Najděte svůj byt", en: "Find your residence" },
  "flats.text":     { cs: "Proklikejte se domem — vyberte podlaží přímo na fasádě a objevte byty. U každého najdete 3D dispozici i rezervaci prohlídky.", en: "Explore the building — pick a floor right on the façade and discover the homes. Each opens a 3D layout and a viewing request." },
  "flats.filterLayout":  { cs: "Dispozice", en: "Layout" },
  "flats.filterFloor":   { cs: "Patro", en: "Floor" },
  "flats.filterStatus":  { cs: "Dostupnost", en: "Availability" },
  "flats.all":      { cs: "Vše", en: "All" },
  "flats.avail":    { cs: "Volné", en: "Available" },
  "flats.th.unit":  { cs: "Byt", en: "Unit" },
  "flats.th.floor": { cs: "Patro", en: "Floor" },
  "flats.th.layout":{ cs: "Dispozice", en: "Layout" },
  "flats.th.area":  { cs: "Plocha", en: "Area" },
  "flats.th.extra": { cs: "Venkovní", en: "Outdoor" },
  "flats.th.price": { cs: "Cena", en: "Price" },
  "flats.th.status":{ cs: "Stav", en: "Status" },
  "flats.detail":   { cs: "Detail", en: "Detail" },
  "flats.empty":    { cs: "Žádný byt neodpovídá filtru.", en: "No residence matches the filter." },
  "flats.count":    { cs: "Zobrazeno", en: "Showing" },
  "flats.of":       { cs: "z", en: "of" },
  "flats.commercial": { cs: "Komerční prostory", en: "Commercial units" },
  "flats.commercialText": { cs: "K dispozici jsou také nebytové prostory v 1. PP a 1. NP — ideální pro obchod, kancelář či ateliér.", en: "Commercial units are also available on the lower ground and ground floor — ideal for retail, office or studio." },

  // PRŮZKUMNÍK DOMU
  "exp.hint":       { cs: "Vyberte podlaží přímo na fasádě", en: "Select a floor right on the façade" },
  "exp.plate":      { cs: "Schematický pohled · Karlín", en: "Schematic elevation · Karlín" },
  "exp.all":        { cs: "Celý dům", en: "Whole building" },
  "exp.overview":   { cs: "Přehled všech bytů", en: "All residences" },
  "exp.floorAvail": { cs: "volných", en: "available" },
  "exp.unitsOn":    { cs: "Byty na podlaží", en: "Residences on this floor" },
  "exp.empty":      { cs: "Na tomto podlaží nejsou byty odpovídající filtru.", en: "No residences on this floor match the filter." },
  "exp.from":       { cs: "od", en: "from" },
  "exp.detail":     { cs: "Prohlédnout byt", en: "View residence" },
  "exp.soldout":    { cs: "Vyprodáno", en: "Sold out" },

  // STAVY
  "status.available": { cs: "Volný",       en: "Available" },
  "status.reserved":  { cs: "Rezervováno", en: "Reserved" },
  "status.sold":      { cs: "Prodáno",     en: "Sold" },

  // MODAL
  "modal.layout":   { cs: "Dispozice", en: "Layout" },
  "modal.floor":    { cs: "Patro", en: "Floor" },
  "modal.interior": { cs: "Vnitřní plocha", en: "Interior area" },
  "modal.outdoor":  { cs: "Venkovní plocha", en: "Outdoor space" },
  "modal.cellar":   { cs: "Sklep", en: "Cellar" },
  "modal.total":    { cs: "Celková plocha", en: "Total area" },
  "modal.price":    { cs: "Celková cena", en: "Total price" },
  "modal.plan":     { cs: "Půdorys patra", en: "Floor plan" },
  "modal.plan3d":   { cs: "3D mezonet", en: "3D maisonette" },
  "modal.reserve":  { cs: "Rezervovat prohlídku tohoto bytu", en: "Book a viewing of this residence" },
  "modal.noplan":   { cs: "Půdorys na vyžádání", en: "Plan on request" },

  // FINANCOVÁNÍ
  "fin.eyebrow":    { cs: "Financování", en: "Financing" },
  "fin.title":      { cs: "Cesta k vašemu bytu", en: "The path to your home" },
  "fin.text":       { cs: "Přehledný splátkový plán a hypoteční servis zdarma. Provedeme vás celým procesem od rezervace po předání.", en: "A clear payment schedule and free mortgage service. We guide you through the whole process, from reservation to handover." },
  "fin.s1t":        { cs: "Rezervace", en: "Reservation" },
  "fin.s1d":        { cs: "72 hodin na rozmyšlenou, poté rezervační poplatek 250 000 Kč.", en: "72 hours to decide, then a CZK 250,000 reservation fee." },
  "fin.s2t":        { cs: "20 % do 10 dnů", en: "20% within 10 days" },
  "fin.s2d":        { cs: "Úhrada první části kupní ceny po podpisu smlouvy.", en: "First part of the price after signing the contract." },
  "fin.s3t":        { cs: "30 % do 60 dnů", en: "30% within 60 days" },
  "fin.s3d":        { cs: "Druhá splátka v průběhu výstavby.", en: "Second instalment during construction." },
  "fin.s4t":        { cs: "50 % při předání", en: "50% on handover" },
  "fin.s4d":        { cs: "Doplatek po dokončení — plánováno 09/2026.", en: "Balance on completion — planned 09/2026." },
  "fin.partnerTitle": { cs: "Hypoteční servis zdarma", en: "Free mortgage service" },
  "fin.partnerText":  { cs: "Ve spolupráci s hypotečním specialistou Milošem Soukupem zajistíme zpracování hypotéky i odhad nemovitosti zdarma a vyjednáme nejlepší podmínky napříč bankami.", en: "Together with mortgage specialist Miloš Soukup we arrange your mortgage and property appraisal free of charge and negotiate the best terms across banks." },

  // REZERVACE / FORMULÁŘ
  "form.eyebrow":   { cs: "Rezervace prohlídky", en: "Book a viewing" },
  "form.title":     { cs: "Přijďte se podívat", en: "Come and see it" },
  "form.text":      { cs: "Nechte nám kontakt a my se vám ozveme s termínem prohlídky. Rádi zodpovíme jakýkoli dotaz.", en: "Leave us your details and we'll get back with a viewing date. Happy to answer any question." },
  "form.name":      { cs: "Jméno a příjmení", en: "Full name" },
  "form.email":     { cs: "E-mail", en: "Email" },
  "form.phone":     { cs: "Telefon", en: "Phone" },
  "form.unit":      { cs: "Byt o který mám zájem", en: "Residence of interest" },
  "form.unitAny":   { cs: "Nezávazně / nevím", en: "Not sure yet" },
  "form.message":   { cs: "Zpráva (nepovinné)", en: "Message (optional)" },
  "form.gdpr":      { cs: "Souhlasím se zpracováním osobních údajů za účelem vyřízení poptávky.", en: "I consent to the processing of my personal data to handle this enquiry." },
  "form.submit":    { cs: "Odeslat poptávku", en: "Send enquiry" },
  "form.sending":   { cs: "Odesílám…", en: "Sending…" },
  "form.success":   { cs: "Děkujeme! Ozveme se vám co nejdříve.", en: "Thank you! We'll be in touch shortly." },
  "form.error":     { cs: "Něco se nepovedlo. Zavolejte nám prosím na " + SITE.phone + ".", en: "Something went wrong. Please call us at " + SITE.phone + "." },
  "form.required":  { cs: "Vyplňte prosím povinná pole.", en: "Please fill in the required fields." },

  // KONTAKT
  "contact.eyebrow":{ cs: "Kontakt", en: "Contact" },
  "contact.title":  { cs: "Promluvme si o vašem novém domově", en: "Let's talk about your new home" },
  "contact.callus": { cs: "Zavolejte nám", en: "Call us" },
  "contact.writeus":{ cs: "Napište nám", en: "Email us" },
  "contact.visit":  { cs: "Adresa projektu", en: "Project address" },
  "contact.agentRole": { cs: "Prodej projektu", en: "Project sales" },

  // FOOTER
  "footer.tagline": { cs: "Luxusní bydlení v srdci Karlína", en: "Luxury living in the heart of Karlín" },
  "footer.nav":     { cs: "Navigace", en: "Navigation" },
  "footer.contact": { cs: "Kontakt", en: "Contact" },
  "footer.legal":   { cs: "Informace v této prezentaci mají ilustrativní charakter a nejsou návrhem na uzavření smlouvy. Vizualizace jsou orientační.", en: "The information in this presentation is illustrative and does not constitute an offer. Visualisations are indicative." },
  "footer.rights":  { cs: "Všechna práva vyhrazena.", en: "All rights reserved." },
  "footer.madeby":  { cs: "vyrobeno s láskou", en: "made with love by" },
  "a11y.skip":      { cs: "Přeskočit na výběr bytů", en: "Skip to residences" }
};
