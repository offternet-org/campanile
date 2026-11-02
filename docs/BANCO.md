# Tre Campanili su un computer

English version: [BENCH.md](BENCH.md).

Due Campanili in due appartamenti, una visita di pochi secondi: la bacheca passa, intatta, e un
messaggio arriva fino a un terzo Campanile? Campanile non si sincronizza ancora. Questo banco
misura se il Wi-Fi di un palazzo vero lo reggerebbe, prima di scrivere la sincronizzazione.

**In breve:** dove un telefono aveva segnale, due Campanili si sono scambiati le bacheche in meno
di 0,4 s, 50 volte su 50. Un messaggio è passato da A a C attraverso B intatto, 20 volte su 20.
Due limiti arrivano molto prima della radio: una bacheca piena non sta in una visita al limite
del "discreto", e i collegamenti che perdono un quinto dei pacchetti cominciano a cedere.

Corsa del 2 novembre 2026, valida: 27 controlli su 27 superati.
[Resoconto](../bench/results/2026-11-02/REPORT.md) · [dati grezzi](../bench/results/2026-11-02/).

## Cosa è vero e cosa è sostituito

| Vero | Sostituito |
|---|---|
| Campanile e le sue risposte, dietro nginx scritto da `raspberry/nginx-site.sh`, su Debian 13 come Raspberry Pi OS Trixie | Lo scambio delle bacheche, che Campanile non fa ancora: [agent.py](../bench/agent.py) scarica la bacheca del vicino, la controlla byte per byte (SHA-256) e aggiunge ciò che manca |
| I numeri dei collegamenti: cinque punti di un appartamento e del suo pianerottolo, misurati il 30 ottobre 2026 con un iPhone e la [prova di copertura di Campanile](../campanile/web/coverage.js) | Ogni collegamento: un ritardo e una velocità (netem di Linux), tarati finché la stessa prova di copertura dà i numeri del telefono |
| Le bacheche: 120 annunci per Campanile, 28 kB; e la più grande che si possa mandare a un telefono, 500 annunci con ogni campo pieno, 408 kB | La finestra di una visita: 30 s, meno 10 s per agganciarsi al Wi-Fi del vicino. Una scelta, non una misura |
| Il verdetto che dà la prova di copertura (`api.coverage_verdict`) | Lo scambio scarica la bacheca senza compressione, il caso peggiore: nginx la comprimerebbe |

Ogni Campanile gira nel suo container; A e C stanno su due reti separate, B su tutte e due. A
raggiunge C solo attraverso B, e B non instrada pacchetti.

## Come si controlla da solo

Un numero vale solo se prima il banco è stato visto fallire dove deve. Prima di misurare, e di
nuovo alla fine:

- senza muro lo scambio riesce; con il muro chiuso non passa niente, e aspetta tutta la
  finestra prima di dirlo;
- una bacheca controllata con l'impronta sbagliata viene rifiutata, e un solo bit cambiato per
  strada viene scoperto, mentre lo stesso intermediario senza guasto lascia passare tutto;
- una finestra troppo corta fallisce;
- il muro su A-B non tocca B-C, e viceversa; A non raggiunge C da solo;
- per ogni blocco, i contatori dei pacchetti mostrano che le bacheche hanno attraversato davvero
  il muro, un pacchetto per trama.

Anche la taratura si controlla: lo stesso muro sui due collegamenti dà gli stessi numeri,
misurati fianco a fianco. Una corsa che salta un controllo, o si ferma a metà, dice NON VALIDA. A
ogni modifica di Campanile o del banco la [CI](../.github/workflows/bench.yml) lancia una
versione corta (`--ci`, circa 2 minuti). Tolto il controllo dell'impronta dal codice, quella CI
fallisce.

## Risultati

I cinque punti misurati, e i collegamenti più poveri che la prova di copertura chiama ancora
"buono" e "discreto":

| Collegamento | Misurato dal telefono | Scambi riusciti in 20 s | Il più lento |
|---|---|---|---|
| A 6 metri | 17 ms, 17,3 Mbit/s | 50/50 | 0,14 s |
| Porta di casa | 44 ms, 14,2 Mbit/s | 50/50 | 0,36 s |
| Corridoio, porta chiusa | 18 ms, 24,4 Mbit/s | 50/50 | 0,16 s |
| Davanti all'ascensore | 23 ms, 12,6 Mbit/s | 50/50 | 0,19 s |
| 3 m oltre l'ascensore, il bordo | 35 ms, 8,1 Mbit/s | 50/50 | 0,29 s |
| Appena dentro "buono" | 142 ms, 2,1 Mbit/s | 50/50 | 1,21 s |
| Appena dentro "discreto" | 570 ms, 0,3 Mbit/s | 50/50 | 5,24 s |

50 su 50 vuol dire almeno 93% con il 95% di fiducia (intervallo di Wilson). Alla porta di casa,
anche senza limite di velocità, il collegamento simulato resta più lento di quello vero: lì il
banco sbaglia dalla parte del pessimismo.

Condizioni più dure, sul collegamento del bordo:

| Condizione | Scambi riusciti in 20 s | Il più lento |
|---|---|---|
| Bacheca piena, 408 kB | 30/30 | 0,95 s |
| Bacheca piena al limite del "discreto" | **0/30** | mai in tempo |
| 5% di pacchetti persi | 30/30 | 1,44 s |
| 10% persi | 30/30 | 5,36 s |
| 20% persi | 28/30 | 13,2 s |
| 30% persi | 18/30 | 19,7 s |
| 50% persi | 0/30 | mai in tempo |
| Collegamento giù 2 s ogni 4 s | 29/30 | 8,0 s |
| Giù 5 s ogni 10 s | 30/30 | 8,0 s |
| Giù 10 s ogni 20 s | 30/30 | 11,5 s |
| "Discreto" con il 5% persi | 30/30 | 18,3 s |

**La catena**, sul collegamento del bordo in tutti e due i tratti: la prima volta B ha ricevuto i
120 annunci di A, e C ne ha ricevuti 240, quelli di A compresi. La seconda volta niente è stato
aggiunto due volte. 20 annunci di prova su 20 sono passati da A a C, identici campo per campo.
Con B-C interrotto, un annuncio ha aspettato in B ed è ripartito appena il collegamento è tornato.

**La prova di copertura come semaforo:** nei blocchi dove diceva "buono" o "discreto", 469
scambi su 470 sono arrivati in tempo. Dove diceva "scarso", alcuni sì e alcuni no.

**Cosa vuol dire per la sincronizzazione, quando la scriveremo:** mandare solo le novità, mai la
bacheca intera; e riprovare da sola dopo un buco, invece di aspettare TCP: su un collegamento mai
giù per più di 2 s, gli scambi hanno impiegato fino a 8 s, con ogni probabilità per l'attesa
crescente di TCP fra un tentativo e l'altro.

## Cosa non dice

- **Se due Raspberry Pi si vedono.** I collegamenti copiano un iPhone e un router di casa a
  5 GHz, lungo un piano. Un Raspberry Pi ha un'antenna piccola e di solito lavora a 2,4 GHz; i
  piani non sono stati misurati. Servono due Raspberry veri.
- **Il ping peggiore del bordo** (763 ms in una prova) non è riprodotto: al suo posto perdite e
  buchi, più duri di lui.
- **La compressione:** una sincronizzazione vera chiederebbe a nginx il gzip e sarebbe più veloce
  di queste cifre.
- **Il processore e i consumi di un Raspberry Pi:** i container giravano su un Mac, 2 processori.
- **I 10 s per agganciarsi al Wi-Fi del vicino** sono supposti, non misurati.

## Lanciarlo

```sh
python3 bench/chain.py            # il banco intero, circa 90 minuti
python3 bench/chain.py --quick    # ogni passo una volta, circa 15 minuti
python3 bench/chain.py --ci       # il controllo corto, circa 2 minuti
```

Serve solo Docker su un kernel Linux con netem (Linux, oppure Docker Desktop / Colima su un Mac).
Ogni corsa scrive in `bench/runs/` il resoconto, i dati grezzi e la configurazione, compresa
l'impronta esatta del codice che ha usato. Altro in [bench/README.md](../bench/README.md).
