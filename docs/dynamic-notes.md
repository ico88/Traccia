# Dispense dinamiche — prima implementazione 0.8

Le lezioni nuove o corrette aggiornano una proposta di dispensa per argomenti. La versione accettata resta invariata fino alla revisione dello studente. Qwen3 4B continua a essere eseguito localmente tramite llama.cpp; nessun servizio esterno.

## Flusso

1. La proposta registra gli identificativi delle trascrizioni considerate (`generation.covered_revisions`). Una richiesta senza nuove revisioni non avvia il modello e restituisce 409 con messaggio esplicativo.
2. Le nuove lezioni vengono sintetizzate. Se una fonte cambia, vengono ricostruite le sezioni automatiche che la citano e le lezioni collegate a quelle sezioni, per evitare di perdere contenuti delle altre fonti.
3. Il modello sceglie se un nuovo contenuto appartiene a un capitolo automatico esistente. Una seconda chiamata propone fusione, separazione o possibile contrasto.
4. La fusione conserva l’identità del capitolo e tutti i riferimenti di entrambi gli input; richiede citazioni valide provenienti da entrambi. Le correzioni manuali non vengono instradate al modello per la riscrittura e vengono preservate integralmente. Eventuali nuovi contenuti rimangono in sezioni separate.
5. La proposta mostra sezioni nuove, aggiornate, invariate e protette. Per gli aggiornamenti è disponibile il testo precedente. Le sezioni ricostruite che sostituiscono sezioni precedenti vengono elencate separatamente.
6. Solo le sezioni nuove/aggiornate e le sostituzioni richiedono una nuova conferma. Fonti cambiate o dispensa modificata nel frattempo impediscono l’accettazione. Anche il salvataggio finale della generazione ricontrolla la revisione di base.

I possibili contrasti rimangono due sezioni separate e collegate, senza scegliere quale sia corretta. La segnalazione resta visibile anche nella dispensa accettata, nella stampa e negli export Markdown/ZIP. È un’indicazione del modello, non un controllo completo delle contraddizioni.

## Limiti espliciti

- La ricerca dei candidati usa sovrapposizione di parole nel titolo/testo e al massimo 12 sezioni candidate, poi una scelta semantica del modello. Non è un indice di embedding o una garanzia di trovare ogni duplicazione.
- La fusione viene evitata se i testi sommati superano 3500 caratteri o il contesto completo supera 12000 caratteri. In quel caso viene conservata una sezione separata; non viene troncato un capitolo per farlo rientrare nel prompt.
- Le fonti grezze delle due sezioni sono fornite al modello di fusione; la validità strutturale e la presenza dei riferimenti non certificano che ogni frase sia supportata.
- Le parti automatiche possono perdere sfumature, accorpare male argomenti o non segnalare contrasti. Rimane necessaria la revisione del testo e dei riferimenti.
- Quando tutte le sezioni di un argomento sono manuali, l’app aggiunge materiale separato anziché modificarle automaticamente. La riscrittura assistita delle parti manuali non è implementata.
- Le dispense precedenti senza la mappa degli input possono richiedere una prima ricostruzione completa delle parti automatiche. Le parti manuali restano preservate. I dati sono nello schema SQLite 5 esistente: evitare il downgrade dell’app su un archivio aggiornato.
- La cronologia completa delle dispense e il ripristino dall’interfaccia restano da sviluppare; le versioni precedenti rimangono archiviate nel database.

## API

`GET /api/v1/subjects/{id}/notes` aggiunge a ogni proposta `changes`, con stato per capitolo, testo precedente per gli aggiornamenti e sezioni sostituite.

Per accettare:

```json
{
  "reviewed_chapter_ids": ["UUID delle sezioni nuove o aggiornate"],
  "reviewed_removed_chapter_ids": ["UUID delle sezioni precedenti sostituite"]
}
```

Gli insiemi devono corrispondere esattamente alle modifiche della proposta. `reviewed_removed_chapter_ids` è facoltativo quando non ci sono sostituzioni. Non inviare gli ID delle sezioni automatiche invariate. Richieste incomplete/estranee vengono rifiutate, senza modificare la versione accettata.

## Verifica reale del modello

Archivio separato, trascrizioni sintetiche note e nessuna registrazione universitaria reale modificata. Primo testo: esame scritto di 60 minuti. Secondo testo: stesso esame di 60 minuti, con 10 domande aperte. Qwen ha aggiornato un solo capitolo esistente, conservandone l’ID, unendo le informazioni e le due fonti. Una nota manuale aggiunta al caso di prova è rimasta identica. Prima proposta circa 4,91 s; aggiornamento circa 9,52 s, singole esecuzioni sul M4, non benchmark generalizzabili.

Terzo testo: durata di 90 minuti, non 60. Il modello ha preservato il capitolo precedente e creato una sezione distinta segnalata come possibile contrasto. Proposta lasciata non approvata. Nel browser verificati il confronto prima/dopo, l’accettazione della seconda lezione, la conservazione della nota manuale e la segnalazione del contrasto con collegamento al capitolo precedente.

Sono prove funzionali su un esempio piccolo e controllato; non qualificano dispense di corsi reali o l’accuratezza farmacologica. Nessun motore audio è stato cambiato in questa fase.
