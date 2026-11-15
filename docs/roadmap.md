# Roadmap

## Implementato nel ramo sviluppo

- Archivio materie e lezioni, metadati, importazione assistita e drag and drop.
- UI biblioteca / area di studio / dispensa / modelli locali.
- Audio originale e derivati, tre preset tradizionali, confronto sincronizzato.
- Coda persistente, avanzamento, annullamento e recupero.
- Download esplicito dei pesi con revisioni e checksum.
- Trascrizione nativa locale con segmenti temporali e correzioni versionate.
- Proposte di dispensa da trascrizioni, fonti, accettazione e protezione delle modifiche manuali.
- Immagini della materia, mappe dei capitoli, esportazione e backup/ripristino.
- Pulizia IA GTCRN, revisione guidata dei passaggi, confronto delle modifiche della dispensa e primo consolidamento incrementale per argomenti.
- Interfaccia inglese/italiano, preferenza persistente e lingua separata per trascrizione e nuove sezioni della dispensa.
- Finestra Mac WebKit, registrazione microfono con recupero bozze, ruoli dei parlanti, isolamento VoxLock sperimentale e guadagno selezionabile.
- Script di build dei runtime e configurazione Docker.

## Prossime verifiche e sviluppi

1. Qualità su più lezioni reali, riferimento manuale e confronto WER/CER; lessico specialistico e confini dei blocchi.
2. Qualificazione del consolidamento tematico implementato, migliore ricerca dei capitoli correlati e verifica semantica delle citazioni.
3. Anteprima della pulizia su un intervallo e qualificazione percettiva del motore GTCRN sul rumore d’aula (riascolto dei segmenti già implementato).
4. Cronologia delle dispense nell'interfaccia e riconciliazione degli asset orfani.
5. Supporto slide/PDF con estrazione figure e schemi didattici generati verificabili.
6. Build container e benchmark effettivo sul server i7; successivamente autenticazione e archivi multiutente.
7. Licenza del progetto e inventario di ridistribuzione; firma Developer ID, notarizzazione, aggiornamenti e prova su Mac pulito.
8. Attivazione CI GitHub dopo disponibilità del permesso workflow.

Promozioni su main soltanto dopo conferma esplicita. Nessuna data di rilascio o qualità garantita prima delle verifiche.
