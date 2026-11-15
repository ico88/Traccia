"""Bounded subprocess worker: extract embedded raster figures from PDF slides."""
from pathlib import Path
import argparse,hashlib,json,resource
from PIL import Image,PngImagePlugin

def extract(source,output):
 from pypdf import PdfReader
 Image.MAX_IMAGE_PIXELS=20_000_000
 if source.stat().st_size>50*1024**2:raise ValueError('PDF exceeds 50 MiB')
 # This worker handles untrusted compressed PDF/image data away from the server.
 try:resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
 except (ValueError,OSError):pass
 reader=PdfReader(source)
 if reader.is_encrypted:raise ValueError('Encrypted PDFs are not supported')
 if len(reader.pages)>200:raise ValueError('PDF exceeds 200 pages')
 digest=hashlib.sha256(source.read_bytes()).hexdigest();figures=[];warnings=[];total=0
 for page_number,page in enumerate(reader.pages,1):
  for key in page.images.keys():
   if len(figures)>=100:raise ValueError('PDF exceeds the 100-figure limit')
   try:obj=page.images[key];image=obj.image
   except Exception:warnings.append({'page':page_number,'reason':'Unsupported or invalid embedded image'});continue
   if image is None:continue
   if image.width*image.height>20_000_000:raise ValueError('An image exceeds 20 megapixels')
   image=image.convert('RGBA' if 'A' in image.getbands() else 'RGB');filename=f'figure-{len(figures)+1:04}.png';target=output/filename
   meta=PngImagePlugin.PngInfo();meta.add_text('source_pdf_sha256',digest);meta.add_text('source_pdf_page',str(page_number));meta.add_text('source_pdf_object',str(key)[:300])
   image.save(target,format='PNG',pnginfo=meta);total+=target.stat().st_size
   if target.stat().st_size>20*1024**2 or total>100*1024**2:raise ValueError('Extracted image size limit exceeded')
   figures.append({'filename':filename,'page':page_number,'object':str(key)[:300],'width':image.width,'height':image.height});image.close()
 (output/'result.json').write_text(json.dumps({'sha256':digest,'page_count':len(reader.pages),'figures':figures,'warnings':warnings}))
def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(argv);a.output.mkdir(exist_ok=True);extract(a.input,a.output)
if __name__=='__main__':main()
