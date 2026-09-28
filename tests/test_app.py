"""Testes locais. Nenhuma chamada paga é feita; o provedor HTTP é uma fixture."""
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from email.parser import BytesParser
from email import policy
import unittest,tempfile,threading,base64,json,io,zipfile,csv,time,os,sys
import numpy as np
from PIL import Image
from ni_forge.core import *
from ni_forge.ai import API,ANALYSIS_SCHEMA,STAGE_QC_SCHEMA
from ni_forge.workflows import *
from ni_forge.server import create_server

COLORS=[(235,185,140),(250,210,20),(210,130,30),(130,90,50),(80,55,35),(170,180,190),(70,145,195)]
BOXES=[(44,27,8,6),(42,20,12,7),(39,33,17,11),(42,44,12,8),(41,52,14,5),(58,34,4,20),(31,34,7,13)]
def synthetic(missing=None):
    o=Outfit(999,{1:{'type':0,'frames':1,'z':1}})
    a=blank()
    for i,(x,y,w,h) in enumerate(BOXES):
        if i==missing:continue
        a[y:y+h,x:x+w]=[*COLORS[i],255]
    for p in o.poses():o.slots[(*p,0,0)]=a.copy();o.slots[(*p,0,1)]=blank()
    return o

def poly(x,y,w,h):return [{'x':x,'y':y},{'x':x+w-1,'y':y},{'x':x+w-1,'y':y+h-1},{'x':x,'y':y+h-1}]

class ProviderHandler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def send(self,obj,code=200):
        data=json.dumps(obj).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def do_GET(self):
        self.server.calls.append((self.path,None));self.send({'data':[{'id':'gpt-4.1'},{'id':'gpt-image-1.5'}]})
    def do_POST(self):
        raw=self.rfile.read(int(self.headers['Content-Length']));ctype=self.headers['Content-Type']
        assert self.headers['Authorization']=='Bearer test-key'
        if self.path=='/responses':
            body=json.loads(raw);self.server.calls.append((self.path,body));fmt=body['text']['format'];assert fmt['strict'] and fmt['type']=='json_schema'
            if fmt['name']=='stage_review':answer={'approved':True,'identity_preserved':True,'fit_coherent':True,'directions_coherent':True,'notes':['Fixture HTTP; não é análise artística real.']}
            else:
                content=body['input'][0]['content'];prompt=content[0]['text'];poses=json.loads(prompt.split('POSES: ',1)[1]);board=decode_png(base64.b64decode(content[1]['image_url'].split(',')[1]));plans=[]
                for i,p in enumerate(poses):
                    full=rgba(Image.fromarray(board[i*256:(i+1)*256,768:1024]).resize((64,64),Image.Resampling.NEAREST));regions=[];boxes=[];missing=[]
                    for y,color in enumerate(COLORS):
                        mask=np.all(full[:,:,:3]==color,axis=2);b=bbox(mask)
                        if b:
                            x0,y0,x1,y1=b;regions.append({'piece':'skin' if y==0 else PARTS[y],'polygons':[poly(x0,y0,x1-x0,y1-y0)]})
                        elif y>0:missing.append(PARTS[y])
                        if y>0:
                            x,v,w,h=BOXES[y] if not b else (b[0],b[1],b[2]-b[0],b[3]-b[1]);boxes.append({'piece':PARTS[y],'x':x,'y':v,'width':w,'height':h})
                    plans.append({'id':p['id'],'confidence':.99,'complete':not missing,'description':'Fixture geométrica','regions':regions,'isolated_addons':[],'missing_pieces':missing,'attachment_boxes':boxes,'notes':''})
                answer={'poses':plans}
            self.send({'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(answer)}]}],'usage':{'input_tokens':1,'output_tokens':1}})
        elif self.path in ['/images/edits','/images/generations']:
            if self.path.endswith('edits'):
                msg=BytesParser(policy=policy.default).parsebytes(('Content-Type: '+ctype+'\r\nMIME-Version: 1.0\r\n\r\n').encode()+raw);fields={};images=[]
                for part in msg.iter_parts():
                    name=part.get_param('name',header='content-disposition');data=part.get_payload(decode=True)
                    if name=='image[]':images.append(decode_png(data))
                    else:fields[name]=data.decode()
                assert images and all(a.shape==(1024,1024,4) for a in images)
                fields['image_count']=len(images)
            else:fields=json.loads(raw)
            self.server.calls.append((self.path,fields));assert fields['size']=='1024x1024' and fields['output_format']=='png'
            art=synthetic().get((1,0,0,0)).copy();prompt=fields['prompt']
            if 'RECONSTRUCT THE UNEQUIPPED BODY' in prompt:
                art=blank();art[24:56,40:55]=[65,100,150,255]
            elif 'Create ONLY ' in prompt:
                y=next(i for i,p in enumerate(PARTS) if 'Create ONLY '+p+' ' in prompt);art=blank();x,v,w,h=BOXES[y];art[v:v+h,x:x+w]=[*COLORS[y],255]
            self.send({'data':[{'b64_json':base64.b64encode(png(atlas16([art]*16))).decode()}],'usage':{'total_tokens':1}})
        else:self.send({'error':{'message':'Unknown route'}},404)

class FakeProvider:
    def __enter__(self):
        self.server=ThreadingHTTPServer(('127.0.0.1',0),ProviderHandler);self.server.calls=[];self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();return self
    def __exit__(self,*args):self.server.shutdown();self.server.server_close();self.thread.join()
    @property
    def url(self):return f'http://127.0.0.1:{self.server.server_port}'
    @property
    def calls(self):return self.server.calls

class GoldenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.out=reproduce_golden();cls.path=Path(cls.temp.name)/'golden.zip';cls.report=write_package(cls.out,cls.path,legacy_golden())
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_all_reference_pixels(self):
        expected=reference();self.assertEqual(len(self.out.slots),1792)
        for key,a in self.out.slots.items():self.assertTrue(np.array_equal(a,expected.slots[key]),key)
        self.assertTrue(self.report['ok']);self.assertEqual(self.report['body_overlaps'],0);self.assertEqual(self.report['empty_poses'],{});self.assertEqual(self.report['dat_references'],7168);self.assertEqual(self.report['source_difference_pixels'],0)
    def test_roundtrip(self):
        read=read_package(self.path);self.assertEqual(read.groups,self.out.groups)
        for k in self.out.slots:self.assertTrue(np.array_equal(self.out.slots[k],read.slots[k]))
    def test_quadrants_and_hashes(self):
        with zipfile.ZipFile(self.path) as z:
            prefix='outfit_1210/';mapping=csv.DictReader(io.StringIO(z.read(prefix+'mapa_sprites.csv').decode()));tiles={}
            for row in mapping:
                a=blank()
                for col,(yy,xx) in zip(['inferior_direito','inferior_esquerdo','superior_direito','superior_esquerdo'],[(32,32),(32,0),(0,32),(0,0)]):
                    sid=int(row[col])
                    if sid not in tiles:tiles[sid]=decode_png(z.read(prefix+f'sprites_individuais/sprite_{sid:06d}.png'),(32,32))
                    a[yy:yy+32,xx:xx+32]=tiles[sid]
                self.assertTrue(np.array_equal(a,decode_png(z.read(prefix+row['quadro']))))
            self.assertEqual(len(tiles)-1,1023)
            for line in z.read(prefix+'SHA256SUMS.txt').decode().splitlines():
                sha,name=line.split('  ',1);self.assertEqual(hashlib.sha256(z.read(prefix+name)).hexdigest(),sha)
    def test_old_examples(self):
        for name,look in [('antigo_1457.zip',1457),('demonhunter_289.zip',289)]:
            old=reference(name);self.assertEqual(old.look,look);self.assertEqual(len(old.slots),432);self.assertEqual(len(old.poses()),72);self.assertEqual(old.groups[1]['frames'],1);self.assertFalse(old.modular())
            with self.assertRaises(ForgeError):reproduce_golden(old)
    def test_copy_independent(self):
        c=self.out.copy();self.assertEqual(c.poses(),self.out.poses());key=next(iter(c.slots));c.slots[key][:]=0;self.assertFalse(np.array_equal(c.slots[key],self.out.slots[key]))
    def test_source_checkpoint(self):
        p=Path(self.temp.name)/'source.zip';source=reference('antigo_1457.zip');write_source(source,p);self.assertEqual(fingerprint(source),fingerprint(read_package(p)))

class GuardTests(unittest.TestCase):
    def test_path_traversal(self):
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:z.writestr('../bad.png',b'x')
        with self.assertRaises(ForgeError):read_package(b.getvalue())
    def test_wrong_size(self):
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:z.writestr('look1_g01_f00_Norte_Addon_0_z0_Base.png',png(blank((32,32))))
        with self.assertRaises(ForgeError):read_package(b.getvalue())
    def test_missing_base(self):
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:z.writestr('look1_g01_f00_Norte_Addon_1_z0_Base.png',png(blank()))
        with self.assertRaises(ForgeError):read_package(b.getvalue())
    def test_polygon_invalid(self):
        with self.assertRaises(ForgeError):polygon_mask([poly(63,63,4,4)])
    def test_global_empty_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ForgeError):write_package(make_modular(synthetic()),Path(d)/'invalid.zip')
    def test_config_needs_key_and_https(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ForgeError):API({},'',d)
            with self.assertRaises(ForgeError):API({'base_url':'http://remote.invalid'},'key',d)
    def test_extra_layers_rejected(self):
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:z.writestr('look1_g01_f00_Norte_Base_z0_L3.png',png(blank()))
        with self.assertRaises(ForgeError):read_package(b.getvalue())
    def test_opaque_generated_background_rejected(self):
        a=np.full((1024,1024,4),255,dtype=np.uint8)
        with self.assertRaises(ForgeError):split_generated(a,16,cols=4)

class APITests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.fake=FakeProvider().__enter__();self.stop=threading.Event();self.api=API({'base_url':self.fake.url},'test-key',self.temp.name,self.stop)
    def tearDown(self):self.fake.__exit__();self.temp.cleanup()
    def test_models(self):self.assertIn('gpt-image-1.5',self.api.models())
    def test_convert_actual_http_contract_and_cache(self):
        source=synthetic();out=convert_ai(source,self.api,lambda *_:None,self.stop);self.assertTrue(validate(out)['ok']);self.assertEqual(len(out.slots),56);calls=len(self.fake.calls)
        self.assertEqual(list(out.metadata['stage_approvals']),PARTS)
        self.assertEqual(out.metadata['composition'],'python_rgba_base_then_y1_to_y6')
        cached=convert_ai(source,self.api,lambda *_:None,self.stop);self.assertEqual(len(self.fake.calls),calls);self.assertGreater(self.api.hits,0)
        for p in source.poses():
            original=source.full(p)
            for y in range(1,7):
                a=out.get(p,y);visible=a[:,:,3]>0;self.assertTrue(visible.any());self.assertTrue(np.array_equal(a[visible],original[visible]))
        self.assertTrue(all(self.api.config['base_url'] not in json.dumps(out.metadata) for _ in [0]))
    def test_generate_missing_weapon(self):
        out=convert_ai(synthetic(missing=5),self.api,lambda *_:None,self.stop);self.assertTrue(validate(out)['ok']);self.assertEqual(len(out.metadata['generated_pieces']),4)
    def test_prompt_then_modularize(self):
        groups={1:{'type':0,'frames':1,'z':1},2:{'type':1,'frames':1,'z':1}}
        source=create_prompt_source('Guerreiro de bronze com escudo',2000,groups,self.api,lambda *_:None,self.stop)
        self.assertEqual(len(source.slots),16);out=convert_ai(source,self.api,lambda *_:None,self.stop);self.assertTrue(validate(out)['ok']);self.assertEqual(len(out.slots),112)
    def test_images_multiple_reference_and_generation(self):
        a=atlas16([synthetic().get((1,0,0,0))]*16);self.api.image('duas referencias',[a,a]);self.assertEqual(self.fake.calls[-1][1]['image_count'],2);self.api.image('imagem sem referencia');self.assertEqual(self.fake.calls[-1][0],'/images/generations')
    def test_cancel(self):
        self.stop.set()
        with self.assertRaises(Cancelled):self.api.models()
        self.assertEqual(len(self.fake.calls),0)
    def test_call_limit(self):
        self.api.config['max_calls']=1;self.api.models()
        with self.assertRaises(ForgeError):self.api.models()

class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.server=create_server(self.temp.name);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.base=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()
    def request(self,path,data=None,auth=True,headers=None):
        h={'X-Forge-Token':self.server.state.token} if auth else {}
        if headers:h.update(headers)
        if data is not None:h['Content-Type']='application/json'
        with urlopen(Request(self.base+path,data=None if data is None else json.dumps(data).encode(),headers=h),timeout=30) as r:return r.read(),r.headers
    def j(self,path,data=None):return json.loads(self.request(path,data)[0])
    def wait(self):
        self.server.state.worker.join(30);self.assertFalse(self.server.state.worker.is_alive());j=self.j('/api/job');self.assertEqual(j['status'],'done',j)
    def test_auth_and_html(self):
        with self.assertRaises(HTTPError) as e:self.request('/api/state',auth=False)
        self.assertEqual(e.exception.code,403)
        with self.assertRaises(HTTPError):self.request('/api/state',headers={'Origin':'https://elsewhere.invalid'})
        raw,h=self.request('/');self.assertIn(self.server.state.token.encode(),raw);self.assertIn(b'/static/app.js',raw);self.assertIn("frame-ancestors 'none'",h['Content-Security-Policy'])
    def test_offline_job_export_edit_undo_reopen(self):
        self.j('/api/golden',{'look':2400});self.wait();s=self.j('/api/state');self.assertEqual(s['result']['look'],2400);self.assertTrue(s['validation']['ok']);project=s['project'];p=s['result']['poses'][0]
        image=self.request('/api/image?'+urlencode({'pose':p,'y':1}))[0];a=decode_png(image);loc=np.argwhere(a[:,:,3]>0)[0];a[loc[0],loc[1]]=[123,45,67,255]
        self.j('/api/edit',{'pose':p,'y':1,'layer':0,'png':base64.b64encode(png(a)).decode()});self.assertEqual(self.j('/api/state')['undo'],1);self.j('/api/undo',{})
        self.assertEqual(image,self.request('/api/image?'+urlencode({'pose':p,'y':1}))[0]);raw,headers=self.request('/api/export');out=read_package(raw);self.assertEqual(out.look,2400);self.assertTrue(out.modular());self.assertIn('2400',headers['Content-Disposition'])
        self.j('/api/example',{'name':'1457'});self.j('/api/open_project',{'id':project});self.assertEqual(self.j('/api/state')['result']['look'],2400)
    def test_config_secret_not_saved(self):
        self.j('/api/config',{'key':'test-secret'});self.assertNotIn('test-secret',(Path(self.temp.name)/'config.json').read_text());self.assertNotIn('test-secret',json.dumps(self.j('/api/state')))
        self.j('/api/config',{'key':''});self.assertFalse(self.j('/api/state')['has_key'])
    def test_import_then_auto_requires_api(self):
        data=(resources()/'data/references/antigo_1457.zip').read_bytes();self.j('/api/import',{'name':'antigo.zip','data':base64.b64encode(data).decode()});self.assertEqual(self.j('/api/state')['source']['look'],1457)
        with self.assertRaises(HTTPError):self.j('/api/convert',{'look':2401})
    def test_create_http_endpoint(self):
        with FakeProvider() as fake:
            self.j('/api/config',{'key':'test-key','base_url':fake.url});self.j('/api/create',{'prompt':'Cavaleiro de bronze com arma e escudo','look':2003,'idle':1,'walk':1,'z':1});self.wait();s=self.j('/api/state');self.assertTrue(s['validation']['ok']);self.assertEqual(s['result']['look'],2003)

# Mantido separado para não poluir os contratos de produção.
from urllib.parse import urlencode
if __name__=='__main__':unittest.main()
