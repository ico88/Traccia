"""Generate a source-linked study diagram from accepted notes; infer no causal links."""
import json,textwrap
from PIL import Image,ImageDraw,ImageFont,PngImagePlugin

def draw(notes,lesson_titles,path,language='en'):
 chapters=notes['chapters'][:8];height=150+len(chapters)*150;canvas=Image.new('RGB',(1400,height),'#faf8f4');pen=ImageDraw.Draw(canvas)
 title='Course notes → lecture evidence' if language=='en' else 'Dispensa → fonti delle lezioni'
 pen.text((36,24),title,font=ImageFont.load_default(size=30),fill='#763b29')
 description='Arrows mean “cites”, not cause or correctness. Up to 8 chapters and 3 references per chapter.' if language=='en' else 'Le frecce indicano citazioni, non causalità o correttezza. Fino a 8 capitoli e 3 fonti per capitolo.'
 pen.text((36,72),description,font=ImageFont.load_default(size=16),fill='#6b625b')
 for i,chapter in enumerate(chapters):
  y=125+i*150;pen.rounded_rectangle((36,y,560,y+125),radius=15,fill='#f2dfd3',outline='#b9775b')
  heading='\n'.join(textwrap.wrap(chapter['title'],width=42)[:3]);pen.multiline_text((56,y+20),heading,font=ImageFont.load_default(size=21),fill='#332e2a',spacing=5)
  pen.line((575,y+62,640,y+62),fill='#a45438',width=3);pen.polygon([(640,y+62),(629,y+56),(629,y+68)],fill='#a45438')
  lines=[]
  for ref in chapter['sources'][:3]:
   seconds=ref.get('start',0);name=lesson_titles.get(ref['lesson_id'],ref['lesson_id']);lines.append(f"{name[:55]} · {int(seconds//60)}:{int(seconds%60):02}")
  if not lines:lines=['No source references' if language=='en' else 'Nessun riferimento']
  pen.multiline_text((665,y+22),'\n'.join(lines),font=ImageFont.load_default(size=17),fill='#51473f',spacing=12)
 info=PngImagePlugin.PngInfo();info.add_text('source_revision',notes['id']);info.add_text('source_anchors',json.dumps([{'chapter_id':c['id'],'sources':c['sources']} for c in chapters]));info.add_text('meaning','Edges represent citations only; no new scientific facts or causal relationships inferred.')
 canvas.save(path,format='PNG',pnginfo=info)
 return canvas.size
