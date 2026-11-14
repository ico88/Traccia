# Verifica anteprima 0.3

Data: 14 novembre 2026.

- 24 test automatici: materie e persistenza, importazione e validazione formati, duplicati, limiti upload, cleanup degli errori, migrazione database, accesso audio e Range, risorse web, login/logout browser, protezione delle richieste con cookie e compatibilità bearer.
- Verifica manuale nel browser locale: accesso, creazione materia, importazione WAV da 45 secondi senza data, aggiornamento della lista, logout e nuovo accesso.
- Ascolto avviato dal lettore sulla registrazione MP3 completa; durata visualizzata 1:14:51 e selezione velocità 1,5× verificata.
- Layout osservato nella viewport stretta del browser di prova. Verifiche ulteriori su altri browser e dimensioni desktop ancora da completare.

Il campione reale e gli screenshot contenenti dati di studio restano fuori dal repository. La verifica manuale conferma il flusso osservato, non costituisce una misura della qualità didattica o audio.

I test emettono un avviso di deprecazione di Starlette relativo a httpx nel TestClient; non ci sono test falliti. CI GitHub non attiva per il permesso workflow mancante nella credenziale.
