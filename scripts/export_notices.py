"""Export installed distribution licenses for the exact development environment."""
from pathlib import Path
from importlib import metadata
import argparse,json,platform,sys

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);rows=[]
 for d in sorted(metadata.distributions(),key=lambda d:d.metadata['Name'].casefold()):
  name=d.metadata['Name'];licenses=[]
  for f in d.files or []:
   lower=str(f).lower()
   if '.dist-info/' not in lower or not any(part in lower for part in ['license','copying','notice','authors']):continue
   source=Path(d.locate_file(f))
   if not source.is_file():continue
   target=a.output/'packages'/(name+'-'+d.version)/str(f).split('.dist-info/',1)[1];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes());licenses.append(str(target.relative_to(a.output)))
  expression=d.metadata.get('License-Expression') or d.metadata.get('License') or 'See included license files / upstream'
  if len(expression)>150:expression=expression.splitlines()[0] or 'See license text'
  rows.append({'name':name,'version':d.version,'declared_license':expression,'license_files':licenses,'project_urls':d.metadata.get_all('Project-URL') or []})
 (a.output/'inventory.json').write_text(json.dumps({'python':sys.version,'platform':platform.platform(),'scope':'Installed build environment; includes build/test packages which may not be bundled. Individual libraries retain their licenses.','distributions':rows},ensure_ascii=False,indent=2))
 import shutil
 for license_file in (Path(__file__).resolve().parents[1]/'third_party').glob('*'):
  if license_file.is_file():shutil.copy2(license_file,a.output/license_file.name)
 (a.output/'README.txt').write_text('Traccia is GPL-3.0-or-later. Third-party components retain their licenses.\nExact Python environment inventory: inventory.json.\nNative runtime notices: runtimes/licenses in the application.\nCorresponding source archives and build instructions are provided with the GitHub release.\nhttps://github.com/ico88/Traccia/releases\n')
 print('Exported',len(rows),'distribution records; preserve these notices with the build.')
if __name__=='__main__':main()
