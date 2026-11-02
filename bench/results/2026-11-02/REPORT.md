# Tre Campanili, corsa 20261102-122038

**Esito: VALIDA.** Controlli 27/27 superati, sentinelle 18/18, anomalie 0, blocchi 18/18, taratura 7/7 nei limiti.

Modalita' full, commit `d24e5ba` con 26 file non salvati, seme 20261030, finestra 20 s. Docker 29.5.2 kernel 6.8.0-117-generic cpus 2. Python 3.13.5 · nginx version: nginx/1.26.3 · 13.7.

Bacheche: realistica 28 kB, piena 408 kB (500 annunci, ogni campo pieno). Lo scambio le scarica senza compressione: il caso peggiore.
Senza muro: ping 0.43 ms diretto, 1.37 ms attraverso nginx.

## Controlli

| Controllo | Esito |
|---|---|
| prima: senza muro lo scambio riesce | PASS |
| prima: impronta sbagliata rifiutata | PASS |
| prima: lo stesso intermediario senza guasto non disturba | PASS |
| prima: un bit cambiato per strada viene scoperto | PASS |
| prima: una finestra troppo corta fallisce | PASS |
| prima: muro chiuso, nessuno scambio, e si aspetta tutta la finestra | PASS |
| prima: il muro A-B non tocca B-C | PASS |
| prima: il muro B-C non tocca A-B, e B-C e' davvero chiuso | PASS |
| prima: A non raggiunge C da solo, solo attraverso B | PASS |
| prima: B non instrada pacchetti | PASS |
| il muro P5 sul collegamento B-C da' gli stessi numeri che su A-B | PASS |
| dopo: senza muro lo scambio riesce | PASS |
| dopo: impronta sbagliata rifiutata | PASS |
| dopo: lo stesso intermediario senza guasto non disturba | PASS |
| dopo: un bit cambiato per strada viene scoperto | PASS |
| dopo: una finestra troppo corta fallisce | PASS |
| dopo: muro chiuso, nessuno scambio, e si aspetta tutta la finestra | PASS |
| dopo: il muro A-B non tocca B-C | PASS |
| dopo: il muro B-C non tocca A-B, e B-C e' davvero chiuso | PASS |
| dopo: A non raggiunge C da solo, solo attraverso B | PASS |
| dopo: B non instrada pacchetti | PASS |
| testimone: ogni muro ha portato davvero le bacheche arrivate | PASS |
| testimone: un pacchetto per trama, mai pacchi da 64 kB | PASS |

## Taratura dei muri sulla prova di copertura

| Punto | Misurato: mediana / peggiore ms, kbit/s | Simulato | Ritardo per lato | Velocita' del filo | Esito |
|---|---|---|---|---|---|
| P1 6 metri dal Campanile | 17 / 73, 17332 | 17 / 17, 16435 | 6.85 ms | 23324 kbit/s | ok, uguale |
| P2 porta di casa | 44 / 77, 14170 | 44 / 46, 9596 | 18.648 ms | senza limite | ok, prudente |
| P3 corridoio, porta chiusa | 18 / 75, 24385 | 17 / 18, 23931 | 7.308 ms | senza limite | ok, uguale |
| P4 davanti all'ascensore | 23 / 64, 12633 | 24 / 24, 13021 | 9.795 ms | 19662 kbit/s | ok, uguale |
| P5 3 m oltre l'ascensore (bordo) | 35 / 763, 8066 | 35 / 36, 7689 | 14.342 ms | 10649 kbit/s | ok, uguale |
| G appena dentro 'buono' | 142 / 475, 2105 | 145 / 147, 2138 | 67.11 ms | 3338 kbit/s | ok, uguale |
| F appena dentro 'discreto' | 570 / 1710, 316 | 570 / 573, 304 | 273.095 ms | 364 kbit/s | ok, uguale |

'prudente': anche senza limite di velocita' il muro simulato e' piu' lento di quello vero, quindi il banco sbaglia dalla parte del pessimismo. Il ping peggiore isolato non si riproduce: al suo posto, perdite e buchi qui sotto.

## Scambio delle bacheche in una visita

| Blocco | Riusciti | 95% (Wilson) | Mediana s | p95 s | Max s | Bacheca | Verdetto della prova | Testimone A/B |
|---|---|---|---|---|---|---|---|---|
| P2 | 50/50 | 93%-100% | 0.35 | 0.36 | 0.36 | 28 kB | good 3 | 1.16x/1.16x |
| P5 + buchi di 10 s ogni 20 s | 30/30 | 89%-100% | 2.34 | 11.50 | 11.50 | 28 kB | bad 1, good 2 | 1.16x/1.16x |
| P5 + buchi di 2 s ogni 4 s | 29/30 | 83%-99% | 1.28 | 3.65 | 8.03 | 28 kB | fair 3 | 1.16x/1.17x |
| P4 | 50/50 | 93%-100% | 0.19 | 0.19 | 0.19 | 28 kB | good 3 | 1.16x/1.16x |
| G | 50/50 | 93%-100% | 1.20 | 1.21 | 1.21 | 28 kB | good 3 | 1.16x/1.16x |
| P3 | 50/50 | 93%-100% | 0.14 | 0.14 | 0.16 | 28 kB | good 3 | 1.16x/1.16x |
| P5 + 30% persi | 18/30 | 42%-75% | 4.12 | 19.65 | 19.65 | 28 kB | bad 3 | 1.28x/1.68x |
| P5 + buchi di 5 s ogni 10 s | 30/30 | 89%-100% | 1.32 | 5.49 | 8.02 | 28 kB | good 2, fair 1 | 1.16x/1.16x |
| P5 | 50/50 | 93%-100% | 0.28 | 0.29 | 0.29 | 28 kB | good 3 | 1.16x/1.16x |
| P5 + 5% persi | 30/30 | 89%-100% | 0.31 | 1.42 | 1.44 | 28 kB | good 1, fair 2 | 1.17x/1.16x |
| F bacheca piena | 0/30 | 0%-11% | - | - | - | 408 kB | - | 1.08x/- |
| P5 + 20% persi | 28/30 | 79%-98% | 2.76 | 8.65 | 13.16 | 28 kB | bad 3 | 1.23x/1.17x |
| P1 | 50/50 | 93%-100% | 0.14 | 0.14 | 0.14 | 28 kB | good 3 | 1.16x/1.16x |
| F | 50/50 | 93%-100% | 5.23 | 5.24 | 5.24 | 28 kB | fair 3 | 1.16x/1.16x |
| P5 + 50% persi | 0/30 | 0%-11% | - | - | - | 28 kB | bad 3 | 9.21x/- |
| P5 + 10% persi | 30/30 | 89%-100% | 0.88 | 3.14 | 5.36 | 28 kB | fair 3 | 1.16x/1.17x |
| P5 bacheca piena | 30/30 | 89%-100% | 0.93 | 0.95 | 0.95 | 408 kB | - | 1.09x/1.09x |
| F + 5% persi | 30/30 | 89%-100% | 6.43 | 16.61 | 18.30 | 28 kB | bad 2, fair 1 | 1.16x/1.17x |

Secondi: lo scambio intero, andata e ritorno. Testimone: byte passati dal muro di ciascun lato diviso byte delle bacheche arrivate.

## Catena A -> B -> C, sul muro del bordo (P5) in tutti e due i collegamenti

- PASS: prima volta: B riceve tutta la bacheca di A, C quella di B, A compreso
- PASS: seconda volta: niente di doppio
- PASS: canarini: da A a C passando per B, identici campo per campo
- PASS: con B-C chiuso il canarino si ferma a B, e passa appena si riapre

