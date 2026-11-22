"""Copia le pagine pubbliche FIPAV Trentino della societa' Team Volley C8.

Gira su GitHub Actions (il sito FIPAV blocca le letture da Google Apps
Script, ma non da qui). Salva le pagine cosi' come sono nella cartella
indicata; l'app MyT le legge da raw.githubusercontent.com quando il sito
FIPAV le rifiuta.

File prodotti:
  risultati-tutte.html            pagina risultati, tutte le date
  risultati-GG-MM-AAAA.html       pagina risultati della settimana (lunedi')
  classifica-<CId>.html           classifica di un campionato
  stato.json                      quando e cosa e' stato copiato
"""
import datetime as dt
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

COMITATO = "16"
STAGIONE = os.environ.get("FIPAV_STAGIONE", "2396")   # da cambiare ogni estate
SOCIETA = "844"
PID = "110"
CLASSIFICHE_FISSE = ["93533", "93534", "93540"]
BASE = "https://www.fipav.tn.it/"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def indirizzo_risultati(lunedi):
    return (BASE + "risultati-classifiche.aspx?ComitatoId=" + COMITATO +
            "&StId=" + STAGIONE + "&DataDa=" + urllib.parse.quote(lunedi, safe="") +
            "&StatoGara=&CId=&SId=" + SOCIETA + "&PId=" + PID + "&btFiltro=CERCA")


def scarica(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "it-IT,it;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=40) as r:
        dati = r.read()
        if r.status != 200:
            raise RuntimeError("codice %s" % r.status)
        return dati


def main(cartella):
    os.makedirs(cartella, exist_ok=True)
    ora = dt.datetime.now(ZoneInfo("Europe/Rome"))
    oggi = ora.date()
    lunedi_corrente = oggi - dt.timedelta(days=oggi.weekday())
    lunedi = [(lunedi_corrente + dt.timedelta(days=g)).strftime("%d/%m/%Y")
              for g in (-14, -7, 0, 7, 14)]

    copiati, errori = [], []

    def salva(nome, url):
        try:
            dati = scarica(url)
            with open(os.path.join(cartella, nome), "wb") as f:
                f.write(dati)
            copiati.append(nome)
            return dati
        except Exception as e:  # noqa: BLE001
            errori.append("%s: %s" % (nome, e))
            return None

    tutte = salva("risultati-tutte.html", indirizzo_risultati(""))
    for l in lunedi:
        salva("risultati-" + l.replace("/", "-") + ".html", indirizzo_risultati(l))

    codici = set(CLASSIFICHE_FISSE)
    if tutte:
        codici.update(c.decode() for c in re.findall(rb"classifica\.aspx\?CId=(\d+)", tutte, re.I))
    for cid in sorted(codici):
        salva("classifica-" + cid + ".html", BASE + "classifica.aspx?CId=" + cid)

    with open(os.path.join(cartella, "stato.json"), "w", encoding="utf-8") as f:
        json.dump({"aggiornato": ora.strftime("%d/%m/%Y %H:%M"), "stagione": STAGIONE,
                   "copiati": copiati, "errori": errori}, f, ensure_ascii=False, indent=1)

    print("Copiati:", len(copiati), "Errori:", len(errori))
    for e in errori:
        print("  ", e)
    if not copiati:
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "fipav")
