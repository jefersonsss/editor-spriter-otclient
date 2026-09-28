"""Interface local. Nenhum servidor público, conta ou telemetria do aplicativo."""
from __future__ import annotations
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse,parse_qs
from pathlib import Path
import os,sys,json,threading,secrets,base64,time,uuid,mimetypes,webbrowser,traceback
from .core import *
from .ai import API,PixelLabAPI,DEFAULTS
from .workflows import resources,reference,legacy_golden,reproduce_golden,convert_ai,create_sequential

APP_VERSION='1.1.0-pixellab'

def workspace_default():
    if os.name=='nt':return Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'NewIslandOutfitForge'
    return Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))/'NewIslandOutfitForge'

def integer(v,lo,hi,label):
    try:n=int(v)
    except (TypeError,ValueError):raise ForgeError(label+' deve ser um número inteiro.') from None
    if not lo<=n<=hi:raise ForgeError(f'{label} deve estar entre {lo} e {hi}.')
    return n

class State:
    def __init__(self,workspace):
        self.root=Path(workspace);self.root.mkdir(parents=True,exist_ok=True)
        for d in ['projects','cache','downloads']: (self.root/d).mkdir(exist_ok=True)
        self.config=DEFAULTS.copy();p=self.root/'config.json'
        if p.exists():
            try:self.config.update({k:v for k,v in json.loads(p.read_text()).items() if k in DEFAULTS})
            except (ValueError,OSError):pass
        self.key=os.environ.get('OPENAI_API_KEY','');self.pixellab_keys=[k for k in os.environ.get('PIXELLAB_API_KEYS','').split(',') if k];self.lock=threading.RLock();self.source=None;self.result=None
        self.project=None;self.title='Novo projeto';self.revision=0;self.undo=[];self.token=secrets.token_urlsafe(32)
        self.stop=threading.Event();self.job={'status':'idle','progress':0,'message':'Pronto','logs':[]};self.worker=None
        self.approval=threading.Event();self.approval_decision=None
    def free(self):
        if self.job['status'] in ['running','awaiting_approval']:raise ForgeError('Há uma tarefa em execução. Aguarde, aprove ou cancele antes de alterar o projeto.')
    def api(self):
        if self.config['provider']=='codex':raise ForgeError('Codex é um agente de programação, não um provedor de geração de imagens incorporável. Use PixelLab ou OpenAI API; o Forge não acessa credenciais privadas do Codex/ChatGPT.')
        cls=PixelLabAPI if self.config['provider']=='pixellab' else API
        credentials=self.pixellab_keys if cls is PixelLabAPI else self.key
        return cls(self.config.copy(),credentials,self.root/'cache',self.stop,lambda m:self.progress(None,m))
    def progress(self,n,message):
        with self.lock:
            if n is not None:self.job['progress']=max(self.job['progress'],min(99,int(n)))
            self.job['message']=str(message);self.job['logs']=(self.job['logs']+[str(message)])[-100:]
    def start(self,title,fn):
        with self.lock:
            self.free();self.stop=threading.Event();self.job={'status':'running','progress':0,'message':title,'logs':[title],'started':time.time()}
            def run():
                try:
                    fn()
                    with self.lock:self.job.update(status='done',progress=100,message='Concluído. Confira a prévia e a validação.')
                except Cancelled as e:
                    with self.lock:self.job.update(status='cancelled',message=str(e))
                except Exception as e:
                    message=str(e).replace(self.key,'[CHAVE OMITIDA]') if self.key else str(e)
                    with self.lock:self.job.update(status='error',message=message or type(e).__name__)
                    # Não registra requisições HTTP nem credenciais.
                finally:
                    with self.lock:self.job['finished']=time.time()
            self.worker=threading.Thread(target=run,name='OutfitForgeJob',daemon=True);self.worker.start()
    def new_project(self,source,title):
        self.source=source;self.result=source.copy() if source.modular() else None;self.title=title[:100];self.undo=[]
        self.project=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8];self.revision+=1
        self.persist()
    def persist(self):
        if not self.project:return
        folder=self.root/'projects'/self.project;folder.mkdir(exist_ok=True)
        if self.source:write_source(self.source,folder/'source.zip')
        if self.result:
            write_source(self.result,folder/'working.zip')
        meta={'id':self.project,'title':self.title,'look':(self.result or self.source).look if self.result or self.source else None,'updated':time.time(),'has_result':self.result is not None}
        tmp=folder/'project.tmp';tmp.write_text(json.dumps(meta,ensure_ascii=False),encoding='utf-8');tmp.replace(folder/'project.json')
    def list_projects(self):
        out=[]
        for p in (self.root/'projects').glob('*/project.json'):
            try:out.append(json.loads(p.read_text(encoding='utf-8')))
            except (OSError,ValueError):continue
        return sorted(out,key=lambda v:v.get('updated',0),reverse=True)[:50]
    def snapshot(self):
        with self.lock:
            return {'source':self.source.summary() if self.source else None,'result':self.result.summary() if self.result else None,
                'validation':validate(self.result,self.source) if self.result else None,'project':self.project,'title':self.title,
                'revision':self.revision,'job':dict(self.job),'config':self.config,'has_key':bool(self.pixellab_keys if self.config['provider']=='pixellab' else self.key),'projects':self.list_projects(),'undo':len(self.undo),'version':APP_VERSION}
    def accept_result(self,result):
        with self.lock:self.result=result;self.undo=[];self.revision+=1;self.persist()
    def review_stage(self,name,result):
        with self.lock:
            if self.project is None:self.new_project(result.copy(),'Prompt em criação')
            self.accept_result(result.copy());self.approval.clear();self.approval_decision=None
            self.job.update(status='awaiting_approval',stage=name,message=f'Revise {name} nas poses e animações. Aprove para criar a próxima peça.')
        while not self.approval.wait(.2):
            if self.stop.is_set():raise Cancelled('Criação cancelada durante a revisão.')
        if self.stop.is_set():raise Cancelled('Criação cancelada durante a revisão.')
        with self.lock:
            accepted=self.approval_decision;self.job.update(status='running',message=f'{name} aprovado. Criando próxima etapa…')
        return accepted
    def action(self,path,data):
        if path=='/api/cancel':self.stop.set();self.approval.set();return {'ok':True,'message':'Cancelamento solicitado. Uma requisição já enviada terminará antes de parar.'}
        if path=='/api/approve_stage':
            with self.lock:
                if self.job['status']!='awaiting_approval':raise ForgeError('Não há uma etapa aguardando aprovação.')
                self.approval_decision=bool(data.get('approved'));self.approval.set();return {'ok':True}
        with self.lock:
            self.free()
            if path=='/api/config':
                c=self.config.copy()
                for k in DEFAULTS:
                    if k in data:c[k]=data[k]
                c['timeout']=integer(c['timeout'],30,1800,'Timeout');c['max_calls']=integer(c['max_calls'],1,2000,'Limite de chamadas');c['vision_batch']=integer(c['vision_batch'],1,4,'Lote visual')
                if c['quality'] not in ['low','medium','high','auto']:raise ForgeError('Qualidade inválida.')
                if c['background'] not in ['transparent','magenta']:raise ForgeError('Fundo inválido.')
                if c['provider'] not in ['openai','pixellab','codex']:raise ForgeError('Provedor inválido.')
                u=urlparse(str(c['base_url']))
                if (u.scheme!='https' and not(u.scheme=='http' and u.hostname in ['127.0.0.1','localhost','::1'])) or u.username or u.password:raise ForgeError('Endpoint inválido: use HTTPS ou um servidor local.')
                pu=urlparse(str(c['pixellab_base_url']))
                if (pu.scheme!='https' and not(pu.scheme=='http' and pu.hostname in ['127.0.0.1','localhost','::1'])) or pu.username or pu.password:raise ForgeError('Endpoint PixelLab inválido: use HTTPS ou um servidor local.')
                for k in ['image_model','vision_model']:
                    if not isinstance(c[k],str) or not c[k].strip():raise ForgeError('Informe os modelos da API.')
                if 'key' in data:self.key=str(data['key']).strip()
                if 'pixellab_keys' in data:self.pixellab_keys=[k.strip() for k in str(data['pixellab_keys']).replace('\r','').replace(',','\n').split('\n') if k.strip()]
                self.config=c;tmp=self.root/'config.tmp';tmp.write_text(json.dumps(c,indent=2),encoding='utf-8');tmp.replace(self.root/'config.json')
                return {'ok':True,'has_key':bool(self.key)}
            if path=='/api/test_api':
                api=self.api()
                def task():
                    api.stop=self.stop;models=api.models();self.progress(99,f'Conexão OK. {len(models)} modelos listados. A disponibilidade de geração será verificada na primeira criação.')
                self.start('Testando conexão com a API',task);return {'ok':True}
            if path=='/api/import':
                raw=base64.b64decode(data.get('data',''),validate=True)
                if len(raw)>32*1024**2:raise ForgeError('O ZIP deve ter até 32 MiB.')
                source=read_package(raw);self.new_project(source,str(data.get('name','Outfit importado')));return {'ok':True}
            if path=='/api/example':
                names={'golden_old':('Golden original',legacy_golden),'golden_v8':('Golden modular v8',lambda:reference()),'1457':('Outfit antigo 1457',lambda:reference('antigo_1457.zip')),'demonhunter':('Demonhunter antigo',lambda:reference('demonhunter_289.zip'))}
                key=data.get('name')
                if key not in names:raise ForgeError('Exemplo desconhecido.')
                title,fn=names[key];self.new_project(fn(),title);return {'ok':True}
            if path=='/api/open_project':
                key=str(data.get('id',''))
                if not re.fullmatch(r'\d{8}-\d{6}-[0-9a-f]{8}',key):raise ForgeError('Projeto inválido.')
                folder=self.root/'projects'/key;m=json.loads((folder/'project.json').read_text(encoding='utf-8'))
                source=read_package(folder/'source.zip');result=read_package(folder/'working.zip') if m['has_result'] else None
                self.source=source;self.result=result;self.project=key;self.title=m['title'];self.undo=[];self.revision+=1;return {'ok':True}
            if path=='/api/golden':
                look=integer(data.get('look',1210),1,65535,'LookType')
                def task():
                    self.new_project(legacy_golden(),'Golden reproduzido');self.accept_result(reproduce_golden(self.source,look,self.progress,self.stop))
                self.start('Reproduzindo Golden v8 localmente',task);return {'ok':True}
            if path=='/api/convert':
                if self.source is None:raise ForgeError('Importe um ZIP primeiro.')
                look=integer(data.get('look',self.source.look),1,65535,'LookType');engine=data.get('engine','auto')
                if engine not in ['auto','golden','ai']:raise ForgeError('Motor inválido.')
                golden=fingerprint(self.source)==fingerprint(legacy_golden())
                if engine=='golden' and not golden:raise ForgeError('A fonte não é a matriz Golden validada. Selecione Automático ou IA.')
                local=(engine!='ai' and (golden or self.source.modular()))
                if not local and self.config['provider']!='openai':raise ForgeError('A conversão de outfit antigo exige análise visual estruturada da OpenAI. PixelLab é usada somente para criar sprites novos.')
                if not local and not self.key:raise ForgeError('Configure sua chave OpenAI para converter este outfit. A reprodução Golden funciona sem chave.')
                def task():
                    if local:
                        if golden:out=reproduce_golden(self.source,look,self.progress,self.stop)
                        else:out=self.source.copy();out.look=look;out.notes.append('Fonte já modular: sprites preservados; não houve nova segmentação.')
                    else:out=convert_ai(self.source,self.api(),self.progress,self.stop,look,str(data.get('prompt',''))[:8000])
                    self.accept_result(out)
                self.start('Convertendo outfit',task);return {'ok':True}
            if path=='/api/create':
                prompt=str(data.get('prompt','')).strip()
                if not 8<=len(prompt)<=8000:raise ForgeError('O prompt deve conter entre 8 e 8.000 caracteres.')
                look=integer(data.get('look',2000),1,65535,'LookType');idle=integer(data.get('idle',8),1,8,'Frames parado');walk=integer(data.get('walk',8),1,8,'Frames andando');nz=integer(data.get('z',2),1,2,'Pattern Z')
                if self.config['provider']=='openai' and not self.key:raise ForgeError('Configure sua chave OpenAI antes de criar por prompt.')
                if self.config['provider']=='pixellab' and not self.pixellab_keys:raise ForgeError('Configure ao menos uma chave PixelLab antes de criar por prompt.')
                groups={1:{'type':0,'frames':idle,'z':nz},2:{'type':1,'frames':walk,'z':nz}}
                if self.config['provider']=='codex':raise ForgeError('Codex não gera imagens para aplicativos. Selecione PixelLab ou OpenAI API.')
                def task():
                    api=self.api();out=create_sequential(prompt,look,groups,api,self.progress,self.stop,self.review_stage)
                    with self.lock:self.source=out.copy();self.title='Prompt: '+prompt[:70]
                    self.accept_result(out)
                self.start('Criando novo outfit por prompt',task);return {'ok':True}
            if path in ['/api/edit','/api/undo','/api/save_project','/api/rename']:
                if self.result is None:raise ForgeError('Crie ou carregue um resultado modular primeiro.')
                if path=='/api/rename':self.result.look=integer(data.get('look'),1,65535,'LookType')
                elif path=='/api/edit':
                    pose=parse_pose(data.get('pose',''));y=integer(data.get('y'),0,6,'Peça');l=integer(data.get('layer',0),0,1,'Camada');key=(*pose,y,l)
                    if key not in self.result.slots:raise ForgeError('Slot inexistente.')
                    a=binary(decode_png(base64.b64decode(data.get('png',''),validate=True),(64,64)))
                    if l==1:
                        colors=a[:,:,:3][a[:,:,3]>0]
                        if any(tuple(c) not in {(255,255,0),(255,0,0),(0,255,0),(0,0,255)} for c in colors):raise ForgeError('Máscara aceita somente amarelo, vermelho, verde, azul ou transparência.')
                        if np.any((a[:,:,3]>0)&(self.result.get(pose,y)[:,:,3]==0)):raise ForgeError('A máscara precisa ficar dentro dos pixels visíveis da peça.')
                    self.undo.append((key,self.result.slots[key].copy(),self.result.get(pose,y,1).copy()));self.undo=self.undo[-100:]
                    self.result.slots[key]=a
                    if l==0:self.result.slots[(*pose,y,1)][a[:,:,3]==0]=0
                    self.result.metadata['manually_edited']=True
                    self.result.metadata['art_review']='Resultado editado após a geração. Revise as peças e a animação novamente no cliente.'
                elif path=='/api/undo':
                    if not self.undo:raise ForgeError('Não há edição para desfazer.')
                    key,a,mask=self.undo.pop();self.result.slots[key]=a;self.result.slots[(*key[:4],key[4],1)]=mask
                self.revision+=1;self.persist();return {'ok':True}
            raise ForgeError('Operação desconhecida.')

class Handler(BaseHTTPRequestHandler):
    server_version='NewIslandOutfitForge/'+APP_VERSION
    def log_message(self,*args):pass  # URLs de sessão não aparecem em logs.
    @property
    def state(self):return self.server.state
    def send(self,status,data,ctype='application/json; charset=utf-8',headers=None):
        if isinstance(data,(dict,list)):data=json.dumps(data,ensure_ascii=False).encode('utf-8')
        elif isinstance(data,str):data=data.encode('utf-8')
        self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        for k,v in (headers or {}).items():self.send_header(k,v)
        self.end_headers()
        try:self.wfile.write(data)
        except (BrokenPipeError,ConnectionResetError):pass
    def authorized(self,q):
        host=f'127.0.0.1:{self.server.server_port}';alternate=f'localhost:{self.server.server_port}'
        if self.headers.get('Host') not in [host,alternate]:return False
        origin=self.headers.get('Origin')
        if origin and origin not in ['http://'+host,'http://'+alternate]:return False
        token=self.headers.get('X-Forge-Token') or q.get('token',[''])[0]
        return secrets.compare_digest(token,self.state.token)
    def route(self):
        u=urlparse(self.path);q=parse_qs(u.query);path=u.path
        # Static resources never contain the session token and expose no project data.
        if path.startswith('/static/') and self.command=='GET':
            name=path.removeprefix('/static/')
            if name not in ['app.js','style.css','logo.svg']:return self.send(404,{'error':'Não encontrado.'})
            p=resources()/'static'/name;return self.send(200,p.read_bytes(),mimetypes.guess_type(name)[0] or 'application/octet-stream')
        if not self.authorized(q):return self.send(403,{'error':'Sessão inválida. Abra o endereço exibido pelo aplicativo no terminal.'})
        if self.command=='POST':
            length=integer(self.headers.get('Content-Length',0),1,46*1024**2,'Tamanho da requisição')
            data=json.loads(self.rfile.read(length));return self.send(200,self.state.action(path,data))
        if path=='/':return self.send(200,(resources()/'static/index.html').read_text(encoding='utf-8').replace('__TOKEN__',self.state.token),'text/html; charset=utf-8')
        if path=='/api/state':return self.send(200,self.state.snapshot())
        if path=='/api/job':
            with self.state.lock:return self.send(200,dict(self.state.job))
        if path=='/api/image':
            with self.state.lock:
                o=self.state.result if q.get('kind',['result'])[0]=='result' else self.state.source
                if o is None:raise ForgeError('Nenhum outfit carregado.')
                p=parse_pose(q.get('pose',[''])[0])
                if p not in o.poses():raise ForgeError('Pose inválida.')
                y=integer(q.get('y',[-1])[0],-1,6,'Peça');layer=integer(q.get('layer',[0])[0],0,1,'Camada')
                a=o.get(p,y,layer) if y>=0 else o.full(p,integer(q.get('bits',[63])[0],0,63,'Addons'),q.get('base',['1'])[0]!='0')
                return self.send(200,png(a),'image/png')
        if path=='/api/export':
            with self.state.lock:
                self.state.free()
                if self.state.result is None:raise ForgeError('Nenhum resultado para exportar.')
                p=self.state.root/'downloads'/f'outfit_{self.state.result.look}_modular.zip';write_package(self.state.result,p,self.state.source)
                return self.send(200,p.read_bytes(),'application/zip',{'Content-Disposition':f'attachment; filename="{p.name}"'})
        if path=='/api/report':
            if self.state.result is None:raise ForgeError('Nenhum resultado para validar.')
            return self.send(200,validate(self.state.result,self.state.source))
        return self.send(404,{'error':'Não encontrado.'})
    def handle_request(self):
        try:self.route()
        except (ForgeError,ValueError,KeyError,OSError,zipfile.BadZipFile) as e:self.send(400,{'error':str(e)})
        except Exception as e:self.send(500,{'error':f'Falha interna: {type(e).__name__}. O projeto e o cache permanecem salvos.'})
    do_GET=handle_request
    do_POST=handle_request

def create_server(workspace=None,port=0):
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler);server.daemon_threads=True;server.state=State(workspace or workspace_default());return server

def serve(workspace=None,port=0,open_browser=True):
    server=create_server(workspace,port);url=f'http://127.0.0.1:{server.server_port}/?token={server.state.token}'
    print(f'\nNew Island Outfit Forge {APP_VERSION}\nPixelLab disponível em Configuração > Provedor.\n{url}\n\nMantenha esta janela aberta. Ctrl+C encerra o aplicativo.\n',flush=True)
    if open_browser:threading.Timer(.4,lambda:webbrowser.open(url)).start()
    try:server.serve_forever()
    except KeyboardInterrupt:server.state.stop.set()
    finally:server.server_close()
