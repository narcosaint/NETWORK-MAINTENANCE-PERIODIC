import os,sys,secrets,subprocess,time,json,socket
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root/'backend'),str(root/'tests/browser')]
from sqlalchemy import URL
from sqlalchemy.orm import Session
from alembic import command
from alembic.config import Config
from app.models import User
from app.security import hash_password
from app.database import build_engine
from workflow import run
import tempfile
name='hotel-web-test-'+secrets.token_hex(5)
docker=['docker','--host','unix:///var/run/docker.sock']
env=os.environ.copy();env.update(POSTGRES_USER='web_test',POSTGRES_DB='hotel_web_staging',POSTGRES_PASSWORD=secrets.token_urlsafe(32),POSTGRES_HOST='127.0.0.1')
server=None
api_container=None
photo_temp=tempfile.TemporaryDirectory(prefix='hotel-web-photos-')
env['PHOTO_STORAGE_ROOT']=photo_temp.name
artifacts=root/'artifacts/web';artifacts.mkdir(parents=True,exist_ok=True)
try:
 subprocess.run(docker+['run','--detach','--rm','--name',name,'--publish','127.0.0.1::5432','--tmpfs','/var/lib/postgresql/data','--env','POSTGRES_PASSWORD','--env','POSTGRES_DB','--env','POSTGRES_USER','postgres:17.6-bookworm'],env=env,stdout=subprocess.DEVNULL,check=True)
 for _ in range(60):
  if subprocess.run(docker+['exec',name,'pg_isready','-U','web_test','-d','hotel_web_staging'],capture_output=True).returncode==0:break
  time.sleep(.3)
 ports=json.loads(subprocess.check_output(docker+['inspect','--format','{{json .NetworkSettings.Ports}}',name]));env['POSTGRES_PORT']=ports['5432/tcp'][0]['HostPort']
 os.environ.update({k:v for k,v in env.items() if k.startswith('POSTGRES_')})
 # pg_isready on the socket can see the entrypoint's temporary init server.
 # Wait for the actual published TCP connection before applying migrations.
 from sqlalchemy import text
 from sqlalchemy.exc import OperationalError
 for attempt in range(60):
  probe=build_engine()
  try:
   with probe.connect() as conn:conn.execute(text('SELECT 1'))
   break
  except OperationalError:
   if attempt==59:raise
   time.sleep(.3)
  finally:probe.dispose()
 config=Config(str(root/'alembic.ini'));command.upgrade(config,'head')
 password=secrets.token_urlsafe(20)
 engine=build_engine()
 with Session(engine) as session:
  session.add(User(username='web_admin',name='Supervisor Uji',role='supervisor',active=True,password_hash=hash_password(password)));session.commit()
 engine.dispose()
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 env['PYTHONPATH']=str(root/'backend')
 log=(artifacts/'server.log').open('w')
 if os.environ.get('HOTEL_BROWSER_IMAGE'):
  api_container='hotel-browser-api-'+secrets.token_hex(5)
  env['PHOTO_STORAGE_ROOT']='/app/storage/photos'
  keys=['POSTGRES_USER','POSTGRES_PASSWORD','POSTGRES_DB','POSTGRES_HOST','POSTGRES_PORT','PHOTO_STORAGE_ROOT']
  flags=[arg for key in keys for arg in ('--env',key)]
  subprocess.run(docker+['run','--detach','--rm','--name',api_container,'--network','host',
       '--tmpfs','/app/storage/photos:uid=999,gid=999,mode=0700']+flags+
       [os.environ['HOTEL_BROWSER_IMAGE'],'uvicorn','app.main:app','--host','127.0.0.1','--port',str(port)],
       env=env,check=True,stdout=subprocess.DEVNULL)
 else:
  server=subprocess.Popen([str(root/'.venv/bin/uvicorn'),'app.main:app','--host','127.0.0.1','--port',str(port)],env=env,cwd=root,stdout=log,stderr=log)
 from urllib.request import urlopen
 for _ in range(40):
  try:
   with urlopen(f'http://127.0.0.1:{port}/health',timeout=1):break
  except OSError:time.sleep(.3)
 run(f'http://127.0.0.1:{port}',password,artifacts)
finally:
 if server:server.terminate();server.wait(timeout=10)
 if api_container:subprocess.run(docker+['stop','--time','5',api_container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 subprocess.run(docker+['stop','--time','5',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 photo_temp.cleanup()
 print('Isolated browser-test database and photo files cleaned up.',flush=True)
