"""Render an existing private experiment as a standalone, offline HTML review page."""
import argparse
import html
import json
from pathlib import Path
import statistics


def render(data):
    escape=html.escape
    engines=sorted({row['engine'] for row in data['results']})
    summary=''.join('<tr><td>'+escape(engine)+'</td><td>'+f"{statistics.median(row['wall_seconds'] for row in data['results'] if row['engine']==engine):.2f} s"+'</td></tr>' for engine in engines)
    sections=[]
    for case in data['cases']:
        audio=escape(Path(case['path']).name,quote=True)
        texts=[]
        for row in data['results']:
            if (row['sample'],row['condition'])!=(case['sample'],case['condition']):continue
            score=row.get('scores');metrics=f"WER {score['wer']:.1%} · CER {score['cer']:.1%}" if score else 'Accuratezza non misurata'
            texts.append(f"<article><h3>{escape(row['engine'])}</h3><small>{row['wall_seconds']:.2f} s · {metrics}</small><p>{escape(row['text'])}</p></article>")
        sections.append(f"<section><h2>{escape(case['sample'])} · {escape(case['condition'])}</h2><p>Inizio nella lezione: {case['start_seconds']:.0f} s · stesso WAV per entrambi i modelli</p><audio controls preload='none' src='{audio}'></audio><div class='columns'>{''.join(texts)}</div></section>")
    return """<!doctype html><html lang='it'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Confronto Fluid e Whisper — AulaLocale</title><style>body{margin:0;background:#f4f6f2;color:#25382d;font:17px/1.55 system-ui,sans-serif}main{max-width:1150px;margin:auto;padding:32px}h1{font-size:2.2rem;line-height:1.15}h2{font-size:1.3rem}section{background:white;border:1px solid #dce4d9;border-radius:18px;margin:24px 0;padding:24px}.columns{display:grid;grid-template-columns:1fr 1fr;gap:28px}small{color:#536558}audio{width:100%;max-width:550px}td,th{text-align:left;padding:8px 28px 8px 0}article p{white-space:pre-wrap}.notice{padding:18px;background:#e6ecdd;border-radius:12px}@media(max-width:700px){main{padding:16px}.columns{grid-template-columns:1fr}}</style><main><h1>Fluid Speech Pro e Whisper Turbo</h1><p>Prova locale su Mac M4 · 3 estratti × 3 condizioni × 2 modelli</p><p class='notice'>Testi automatici da verificare con l’audio. WER/CER non disponibili senza un riferimento umano. Nessun modello è dichiarato vincitore. Questa pagina non invia dati in rete e non modifica le trascrizioni dell’app.</p><h2>Tempo mediano per estratto di 45 secondi</h2><p>Processo nuovo per ogni caso: importazioni, caricamento e inferenza inclusi. Preparazione esclusa; cache già riscaldate da prove precedenti.</p><table><tr><th>Modello</th><th>Tempo</th></tr>"""+summary+'</table>'+''.join(sections)+"<footer>Fluid Speech Pro by FluidVoice · CC BY 4.0. Clean mode disattivata. I file JSON e il modello dei riferimenti restano accanto a questa pagina.</footer></main></html>"


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('results',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():parser.error('Choose a new output file')
    if args.output.parent.resolve()!=args.results.parent.resolve():parser.error('Keep the HTML beside results and WAV files')
    args.output.write_text(render(json.loads(args.results.read_text())))


if __name__=='__main__':main()
