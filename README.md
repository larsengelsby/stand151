# Stand 151 · salgsoversigt

Tjekker hver 3. time, hvilke varer der ligger på stand 151 i Børneloppen Lyngby.
Forsvinder en vare, tælles den som solgt. Dashboardet viser, hvad du har solgt og tjent.

## Opsætning (ca. 10 minutter)

1. **Opret en gratis konto** på github.com, hvis du ikke har en.
2. **Opret et nyt repository**: klik **+** øverst til højre → **New repository**.
   Kald det fx `stand151`, vælg **Public**, og klik **Create repository**.
   (Public er nødvendigt for et gratis dashboard. Der ligger kun varer, som Børneloppen
   allerede viser offentligt, og intet om dig.)
3. **Upload filerne**: klik **uploading an existing file**, og træk disse ind fra den
   udpakkede mappe: `tjek_stand.py`, `README.md` og mappen `docs`. Klik **Commit changes**.
4. **Opret tidsplanen**: klik **Add file → Create new file**. Skriv filnavnet præcis
   `.github/workflows/tjek.yml`, indsæt indholdet af filen `tjek.yml` fra mappen
   `.github/workflows`, og klik **Commit changes**.
   (Mapper, der starter med punktum, er ofte skjulte i Windows, derfor dette trin.)
5. **Giv tjekket lov til at gemme**: **Settings → Actions → General**, rul ned til
   *Workflow permissions*, vælg **Read and write permissions**, og klik **Save**.
6. **Slå dashboardet til**: **Settings → Pages**. Under *Branch* vælger du **main** og
   mappen **/docs**, og klikker **Save**. Efter et minut står adressen øverst,
   fx `https://ditbrugernavn.github.io/stand151/`. Gem den på telefonens hjemmeskærm.
7. **Kør første tjek**: fanen **Actions** → **Tjek stand** → **Run workflow**.
   Efter ca. et minut skal der stå et grønt flueben.

Det første tjek registrerer bare, hvad der ligger på standen. Salg dukker op fra
næste tjek, ca. 3 timer senere.

## Hvis noget går galt

- **Rødt kryds under Actions**: klik på kørslen og fold trinnet *Hent standen* ud.
  Står der "Fandt ingen varer", har Børneloppen sandsynligvis ændret deres side, eller
  de blokerer kald fra GitHub. Send teksten til Claude, så kan programmet tilpasses.
  Programmet gemmer aldrig noget ved fejl, så dine tal bliver ikke ødelagt.
- **GitHub sender en mail ved fejl**, så du opdager det.
- **Kommission**: skriv procenten i feltet på dashboardet. Den huskes på den enhed,
  du skrev den på.

## Godt at vide

- En vare, der lægges på en anden stand, tages ud, eller som en kunde går rundt med,
  tælles også som "solgt". Dukker den op igen ved et senere tjek, fjernes den fra salget.
- GitHub kan forsinke planlagte kørsler med op til en halv time, når der er travlt.
- Anden stand eller butik: ret `BUTIK_ID` og `STAND` øverst i `tjek_stand.py`
  (Lyngby er butik 21).
