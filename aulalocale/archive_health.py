"""Inspect archive references; quarantine only unreferenced derivatives while closed.

No original recording, recording draft or database row is removed. Quarantine is reversible.
"""
from contextlib import closing,contextmanager
from pathlib import Path,PurePosixPath
from uuid import uuid4,UUID
import argparse,fcntl,hashlib,json,re,sqlite3

PATTERN=re.compile(r'^[a-f0-9-]{36}(?:\.edits)?\.(?:mp3|wav|png|json)$')
DIRECTORIES={'enhanced','materials','speakers','evidence'}
def checksum(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
 return h.hexdigest()
def inspect(root,connect):
 expected=set();missing=[]
 with closing(connect()) as c:
  expected.update('originals/'+r[0] for r in c.execute('SELECT storage_name FROM lessons'))
  expected.update('materials/'+r[0] for r in c.execute('SELECT filename FROM materials'))
  for identifier,status,preset in c.execute('SELECT id,status,preset FROM audio_jobs'):
   if status in ('completed','queued','running','interrupted'):
    expected.update('enhanced/'+identifier+ext for ext in ['.mp3','.wav'])
    if status=='completed' and not (root/'enhanced'/(identifier+'.mp3')).is_file():missing.append('enhanced/'+identifier+'.mp3')
    if status=='completed' and preset.startswith(('gtcrn-','voxlock-')) and not (root/'enhanced'/(identifier+'.wav')).is_file():missing.append('enhanced/'+identifier+'.wav')
  for identifier,status,kind in c.execute("SELECT id,status,kind FROM study_jobs WHERE kind IN ('speakers','evidence')"):
   directory='speakers' if kind=='speakers' else 'evidence'
   if status in ('completed','queued','running','interrupted'):
    expected.add(directory+'/'+identifier+'.json')
    if kind=='speakers':expected.add(directory+'/'+identifier+'.edits.json')
    if status=='completed' and not (root/directory/(identifier+'.json')).is_file():missing.append(directory+'/'+identifier+'.json')

 for name in expected:
  if name.startswith(('originals/','materials/')) and not (root/name).is_file():missing.append(name)
 orphans=[];unknown=[];original_orphans=[]
 for directory in [*sorted(DIRECTORIES),'originals']:
  for p in sorted((root/directory).glob('*')):
   name=directory+'/'+p.name
   if name in expected:continue
   if directory=='originals':original_orphans.append(name)
   elif p.is_file() and not p.is_symlink() and safe_derivative(name):orphans.append(name)
   else:unknown.append(name)
 return {'missing':sorted(set(missing)),'orphan_derivatives':orphans,'unreferenced_originals':original_orphans,'unclassified':unknown,'original_policy':'Originals are never moved or deleted by this tool.'}

@contextmanager
def exclusive(root):
 with (root/'audio-worker.lock').open('a') as lease:
  try:fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise RuntimeError('Close the app/service before quarantining or restoring assets')
  yield

def safe_derivative(name):
 p=PurePosixPath(name)
 if len(p.parts)!=2 or p.parts[0] not in DIRECTORIES or '\\' in name or not PATTERN.fullmatch(p.parts[1]):return False
 allowed={'enhanced':('.mp3','.wav'),'materials':('.png',),'speakers':('.json','.edits.json'),'evidence':('.json',)}
 identifier=p.parts[1].split('.',1)[0];suffix=p.parts[1][len(identifier):]
 try:return str(UUID(identifier))==identifier and suffix in allowed[p.parts[0]]
 except ValueError:return False

def quarantine(root,connect):
 with exclusive(root):
  if (root/'quarantine').is_symlink() or any((root/d).is_symlink() for d in DIRECTORIES):raise ValueError('Managed asset directories must not be symbolic links')
  report=inspect(root,connect);folder=root/'quarantine'/str(uuid4());entries=[]
  for name in report['orphan_derivatives']:
   if not safe_derivative(name):raise ValueError('Unsafe asset path')
   entries.append({'path':name,'sha256':checksum(root/name)})
  if not entries:return None
  folder.mkdir(parents=True);manifest=folder/'manifest.json';manifest.write_text(json.dumps({'entries':entries},indent=2))
  for entry in entries:
   name=entry['path'];target=folder/name;target.parent.mkdir(exist_ok=True);(root/name).rename(target)
  return manifest

def restore(root,manifest):
 manifest=manifest.resolve()
 if manifest.parent.parent!= (root/'quarantine').resolve():raise ValueError('Manifest must be inside this archive quarantine')
 entries=json.loads(manifest.read_text())['entries']
 with exclusive(root):
  if (root/'quarantine').is_symlink() or any((root/d).is_symlink() for d in DIRECTORIES):raise ValueError('Managed asset directories must not be symbolic links')
  for entry in entries:
   name=entry['path']
   if not safe_derivative(name):raise ValueError('Unsafe asset path')
   source=manifest.parent/name;target=root/name
   if not source.resolve().is_relative_to(manifest.parent) or not target.resolve().is_relative_to(root.resolve()):raise ValueError('Unsafe asset link')
   if target.exists():
    if source.exists() or checksum(target)!=entry['sha256']:raise ValueError('Restore would overwrite an existing file')
   elif not source.is_file() or source.is_symlink() or checksum(source)!=entry['sha256']:raise ValueError('Quarantine checksum mismatch')
  for entry in entries:
   source=manifest.parent/entry['path'];target=root/entry['path']
   if source.exists():target.parent.mkdir(exist_ok=True);source.rename(target)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data',type=Path,required=True);group=p.add_mutually_exclusive_group();group.add_argument('--quarantine',action='store_true');group.add_argument('--restore',type=Path);a=p.parse_args();root=a.data.resolve()
 if not (root/'aulalocale.sqlite3').is_file():p.error('Archive not found')
 connect=lambda:sqlite3.connect('file:'+str(root/'aulalocale.sqlite3')+'?mode=ro',uri=True)
 if a.restore:restore(root,a.restore);print('Quarantined derivatives restored without overwriting originals.')
 elif a.quarantine:print(quarantine(root,connect) or 'No recognized orphan derivatives')
 else:print(json.dumps(inspect(root,connect),indent=2))
if __name__=='__main__':main()
