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
from ni_forge.ai import API,PixelLabAPI,ANALYSIS_SCHEMA
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
        self.server.calls.append((self.path,None));self.send({'type':'usd','usd':10} if self.path=='/balance' else {'data':[{'id':'gpt-4.1'},{'id':'gpt-image-1.5'}]})
    def do_POST(self):
        raw=self.rfile.read(int(self.headers['Content-Length']));ctype=self.headers['Content-Type']
        auth=self.headers['Authorization']
        if auth=='Bearer empty-credit':self.send({'detail':'Insufficient credits'},402);return
        if auth=='Bearer flaky-key' and not getattr(self.server,'flaky_failed',False):self.server.flaky_failed=True;self.send({'detail':'Inference stream ended without producing a result.'},502);return
        assert auth in ['Bearer test-key','Bearer backup-key','Bearer flaky-key']
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
        elif self.path=='/generate-image-bitforge':
            body=json.loads(raw);self.server.calls.append((self.path,body));assert body['image_size']=={'width':64,'height':64} and body['isometric'] and body['no_background']
            generated=body.get('init_image')
            if generated is None:
                a=blank();a[16:52,25:40]=[70,90,120,255]
                generated={'type':'base64','base64':base64.b64encode(png(a)).decode(),'format':'png'}
            self.send({'image':generated,'usage':{'type':'usd','usd':.01}})
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
    def test_import_pixellab_export_uses_native_cardinal_rotations(self):
        b=io.BytesIO();directions=['south','south-east','east','north-east','north','north-west','west','south-west']
        manifest={'group_id':'group-safe','states':[{'character':{'id':'character-safe','size':{'width':64,'height':64}},'frames':{'rotations':{d:f'Idle/rotations/{d}.png' for d in directions},'animations':{}}}],'export_version':'3.1'}
        with zipfile.ZipFile(b,'w') as z:
            z.writestr('manifest.json',json.dumps(manifest))
            for i,direction in enumerate(directions):
                a=blank();a[20:24,20+i:24+i]=[20+i,80,120,255];z.writestr(f'Idle/rotations/{direction}.png',png(a))
        outfit=read_package(b.getvalue());self.assertTrue(outfit.modular());self.assertEqual(outfit.metadata['origin'],'pixellab_export')
        self.assertEqual([int(outfit.get((1,0,d,0))[20,:,3].sum()) for d in range(4)],[1020]*4)
        self.assertTrue(outfit.notes[-1].startswith('Importação PixelLab:'))
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
    def test_neutral_guide_removes_golden_appearance(self):
        source=synthetic().get((1,0,0,0));neutral=neutral_guide(source);visible=neutral[:,:,3]>0
        self.assertTrue(np.array_equal(visible,source[:,:,3]>0));self.assertTrue(np.all(neutral[:,:,0]==neutral[:,:,1]));self.assertTrue(np.all(neutral[:,:,1]==neutral[:,:,2]));self.assertFalse(np.array_equal(neutral,source))
    def test_conform_allows_new_contour_inside_safe_margin(self):
        guide=blank();guide[20:50,25:40]=[80,80,80,255];art=blank();art[15:55,29:36]=[20,180,220,255]
        out=conform_to_guide(art,guide);allowed=ndi.binary_dilation(guide[:,:,3]>0,iterations=2)
        self.assertTrue(np.all((out[:,:,3]>0)<=allowed));self.assertFalse(np.array_equal(out[:,:,3]>0,guide[:,:,3]>0))
    def test_pixellab_prompt_requests_one_sprite_not_an_atlas(self):
        prompt=pixellab_sprite_prompt('guerreiro original','Base',(1,0,2,0),'south')
        self.assertIn('exactly one 64x64',prompt);self.assertIn('unarmored base',prompt)
        self.assertIn('lower-right 32x32',prompt);self.assertIn('modular mannequin base',prompt)
        self.assertNotIn('1024x1024',prompt);self.assertNotIn('4 columns',prompt);self.assertNotIn('CELLS',prompt)
    def test_pixellab_base_prompt_excludes_other_equipment_sections(self):
        request=pixellab_sprite_prompt('IDENTITY\nHuman warrior\nBASE\nPlain gray shirt\nHELMET\nHorned gold helmet\nWEAPON\nHuge sword','Base',(1,0,2,0),'south')
        self.assertIn('Human warrior',request);self.assertIn('Plain gray shirt',request)
        self.assertNotIn('Horned gold helmet',request);self.assertNotIn('Huge sword',request)
    def test_full_character_is_rejected_for_isolated_addon(self):
        guide=blank();guide[10:18,25:39]=[100,100,100,255]
        with self.assertRaisesRegex(ForgeError,'personagem completo'):conform_to_guide(synthetic().get((1,0,0,0)),guide,'Helmet')
    def test_pixellab_base_is_preserved_and_moved_to_tibia_anchor(self):
        art=blank();art[12:49,23:42]=[18,72,131,255]
        guide=synthetic().get((1,0,0,0))
        out=accept_pixellab_sprite(art,guide,'Base')
        self.assertEqual(np.count_nonzero(out[:,:,3]),np.count_nonzero(art[:,:,3]))
        self.assertEqual(bbox(out[:,:,3]>0)[2:],bbox(guide[:,:,3]>0)[2:])
        self.assertTrue(np.all(out[out[:,:,3]>0,:3]==[18,72,131]))
    def test_oversized_equipped_character_is_rejected_as_base(self):
        art=blank();art[8:60,10:58]=[90,100,110,255]
        with self.assertRaisesRegex(ForgeError,'Base grande demais'):accept_pixellab_sprite(art,synthetic().get((1,0,0,0)),'Base')
    def test_fragmented_pixellab_result_is_not_checkpointed(self):
        art=blank()
        for y,x in [(4,4),(12,50),(31,6),(55,55)]:art[y:y+3,x:x+3]=[255,255,255,255]
        with self.assertRaisesRegex(ForgeError,'fragmentos'):accept_pixellab_sprite(art,synthetic().get((1,0,0,0)),'Base')

class APITests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.fake=FakeProvider().__enter__();self.stop=threading.Event();self.api=API({'base_url':self.fake.url},'test-key',self.temp.name,self.stop)
    def tearDown(self):self.fake.__exit__();self.temp.cleanup()
    def test_models(self):self.assertIn('gpt-image-1.5',self.api.models())
    def test_convert_actual_http_contract_and_cache(self):
        source=synthetic();out=convert_ai(source,self.api,lambda *_:None,self.stop);self.assertTrue(validate(out)['ok']);self.assertEqual(len(out.slots),56);calls=len(self.fake.calls)
        self.assertEqual(list(out.metadata['stage_approvals']),['Base','Helmet','Armor','Legs','Boots','Shield','Weapon'])
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
    def test_pixellab_contract_and_key_rotation(self):
        logs=[];api=PixelLabAPI({'pixellab_base_url':self.fake.url},['empty-credit','backup-key'],self.temp.name,self.stop,logs.append)
        guide=synthetic().get((1,0,0,0));out=api.sprite('cavaleiro',guide,blank(),'south')
        self.assertEqual(out.shape,(64,64,4));self.assertEqual(api.key_index,1)
        calls=[c for c in self.fake.calls if c[0]=='/generate-image-bitforge'];self.assertEqual(len(calls),1);self.assertEqual(api.calls,2);self.assertIn('init_image',calls[0][1]);self.assertEqual(calls[0][1]['init_image_strength'],300);self.assertEqual(calls[0][1]['coverage_percentage'],30);self.assertEqual(calls[0][1]['style_strength'],0)
        self.assertTrue(any('debug seguro' in line and 'base64_bytes' in line and 'south' in line for line in logs));self.assertNotIn('iVBOR',json.dumps(logs))
    def test_pixellab_retries_transient_502(self):
        api=PixelLabAPI({'pixellab_base_url':self.fake.url},['flaky-key'],self.temp.name,self.stop)
        out=api.sprite('cavaleiro resiliente',synthetic().get((1,0,0,0)),blank(),'south')
        self.assertEqual(out.shape,(64,64,4));self.assertEqual(api.calls,2)
    def test_pixellab_cache_version_invalidates_old_malformed_result(self):
        api=PixelLabAPI({'pixellab_base_url':self.fake.url},['backup-key'],self.temp.name,self.stop)
        guide=synthetic().get((1,0,0,0));api.sprite('novo guerreiro',guide,blank(),'south')
        calls=len([c for c in self.fake.calls if c[0]=='/generate-image-bitforge'])
        old_request={'endpoint':api.config['pixellab_base_url'],'payload':{'obsolete':True}}
        old=(Path(self.temp.name)/(hashlib.sha256(json.dumps(old_request,sort_keys=True).encode()).hexdigest()+'.json'))
        old.write_text(json.dumps({'image':{'base64':base64.b64encode(png(blank())).decode()}}))
        api.sprite('outro guerreiro',guide,blank(),'south')
        self.assertEqual(len([c for c in self.fake.calls if c[0]=='/generate-image-bitforge']),calls+1)
    def test_sequential_creation_emits_batch_checkpoints(self):
        class Failing:
            config={'background':'transparent'}
            def __init__(self):self.calls=0
            def sprite(self,prompt,guide,context,direction,component='Base'):
                self.calls+=1
                if self.calls==10:raise ForgeError('falha simulada')
                return guide.copy()
        groups={1:{'type':0,'frames':1,'z':1},2:{'type':1,'frames':1,'z':1}};saved=[]
        with self.assertRaises(ForgeError):create_sequential('Cavaleiro consistente',2006,groups,Failing(),lambda *_:None,self.stop,checkpoint=lambda name,out,done,total:saved.append((name,done,total,out)))
        self.assertEqual(saved[0][:3],('Base',1,8));self.assertTrue(saved[0][3].get((1,0,2,0),0)[:,:,3].any())
    def test_rejected_sample_stops_after_first_paid_sprite(self):
        class Counting:
            config={'background':'transparent'}
            def __init__(self):self.calls=0
            def sprite(self,prompt,guide,context,direction,component='Base'):self.calls+=1;return guide.copy()
        api=Counting();groups={1:{'type':0,'frames':1,'z':1},2:{'type':1,'frames':1,'z':1}}
        with self.assertRaises(Cancelled):create_sequential('Cavaleiro para amostra',2007,groups,api,lambda *_:None,self.stop,approve=lambda *_:False)
        self.assertEqual(api.calls,1)
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
        limit=time.time()+30
        while self.server.state.worker.is_alive() and time.time()<limit:
            if self.j('/api/job')['status']=='awaiting_approval':self.j('/api/approve_stage',{'approved':True})
            time.sleep(.05)
        self.server.state.worker.join(1);self.assertFalse(self.server.state.worker.is_alive());j=self.j('/api/job');self.assertEqual(j['status'],'done',j)
    def test_auth_and_html(self):
        with self.assertRaises(HTTPError) as e:self.request('/api/state',auth=False)
        self.assertEqual(e.exception.code,403)
        with self.assertRaises(HTTPError):self.request('/api/state',headers={'Origin':'https://elsewhere.invalid'})
        raw,h=self.request('/');self.assertIn(self.server.state.token.encode(),raw);self.assertIn(b'/static/app.js?v=1.1.0-pixellab',raw);self.assertIn(b'PixelLab API dispon',raw);self.assertIn("frame-ancestors 'none'",h['Content-Security-Policy'])
        self.assertEqual(self.j('/api/state')['version'],'1.1.0-pixellab')
    def test_offline_job_export_edit_undo_reopen(self):
        self.j('/api/golden',{'look':2400});self.wait();s=self.j('/api/state');self.assertEqual(s['result']['look'],2400);self.assertTrue(s['validation']['ok']);project=s['project'];p=s['result']['poses'][0]
        image=self.request('/api/image?'+urlencode({'pose':p,'y':1}))[0];a=decode_png(image);loc=np.argwhere(a[:,:,3]>0)[0];a[loc[0],loc[1]]=[123,45,67,255]
        self.j('/api/edit',{'pose':p,'y':1,'layer':0,'png':base64.b64encode(png(a)).decode()});self.assertEqual(self.j('/api/state')['undo'],1);self.j('/api/undo',{})
        self.assertEqual(image,self.request('/api/image?'+urlencode({'pose':p,'y':1}))[0]);raw,headers=self.request('/api/export');out=read_package(raw);self.assertEqual(out.look,2400);self.assertTrue(out.modular());self.assertIn('2400',headers['Content-Disposition'])
        self.j('/api/example',{'name':'1457'});self.j('/api/open_project',{'id':project});self.assertEqual(self.j('/api/state')['result']['look'],2400)
    def test_config_secret_not_saved(self):
        self.j('/api/config',{'key':'test-secret','pixellab_keys':'pixel-secret-1\npixel-secret-2'});config=(Path(self.temp.name)/'config.json').read_text();state=json.dumps(self.j('/api/state'))
        self.assertNotIn('test-secret',config);self.assertNotIn('pixel-secret',config);self.assertNotIn('test-secret',state);self.assertNotIn('pixel-secret',state)
        self.j('/api/config',{'key':''});self.assertFalse(self.j('/api/state')['has_key'])
    def test_import_then_auto_requires_api(self):
        data=(resources()/'data/references/antigo_1457.zip').read_bytes();self.j('/api/import',{'name':'antigo.zip','data':base64.b64encode(data).decode()});self.assertEqual(self.j('/api/state')['source']['look'],1457)
        with self.assertRaises(HTTPError):self.j('/api/convert',{'look':2401})
    def test_codex_is_not_misrepresented_as_image_api(self):
        self.j('/api/config',{'provider':'codex'})
        with self.assertRaises(HTTPError) as e:self.j('/api/create',{'prompt':'Cavaleiro com escudo e espada','look':2005,'idle':1,'walk':1,'z':1})
        self.assertEqual(e.exception.code,400)
    def test_create_http_endpoint(self):
        with FakeProvider() as fake:
            self.j('/api/config',{'key':'test-key','base_url':fake.url});self.j('/api/create',{'prompt':'Cavaleiro de bronze com arma e escudo','look':2003,'idle':1,'walk':1,'z':1});self.wait();s=self.j('/api/state');self.assertTrue(s['validation']['ok']);self.assertEqual(s['result']['look'],2003)
            self.assertEqual(list(s['result']['metadata']['stage_approvals']),['Base','Helmet','Armor','Legs','Boots','Shield','Weapon'])
            self.assertTrue(all(v['approved_by']=='user' for v in s['result']['metadata']['stage_approvals'].values()))
            # A IA fornece desenho e contorno próprios dentro da margem segura da
            # pose; exigir o alpha Golden exato faria a criação apenas copiá-lo.
            out=self.server.state.result;guide=reference()
            for p in out.poses():
                gp=(min(p[0],max(guide.groups)),p[1]%8,p[2],p[3]%2)
                for y in range(7):
                    generated=out.get(p,y)[:,:,3]>0;allowed=ndi.binary_dilation(guide.get(gp,y)[:,:,3]>0,iterations=2)
                    self.assertTrue(generated.any(),(p,y));self.assertFalse(np.any(generated & ~allowed),(p,y))
    def test_create_with_pixellab_provider(self):
        with FakeProvider() as fake:
            self.j('/api/config',{'provider':'pixellab','pixellab_base_url':fake.url,'pixellab_keys':'empty-credit\nbackup-key','max_calls':200})
            self.j('/api/create',{'prompt':'Cavaleiro isométrico com arma e escudo','look':2004,'idle':1,'walk':1,'z':1});self.wait()
            s=self.j('/api/state');self.assertEqual(s['result']['metadata']['engine'],'sequential_creation');self.assertEqual(s['source']['metadata']['origin'],'creation_pose_guide');self.assertTrue(s['validation']['ok'])
    def test_pixellab_shows_first_sample_before_more_spending(self):
        with FakeProvider() as fake:
            self.j('/api/config',{'provider':'pixellab','pixellab_base_url':fake.url,'pixellab_keys':'backup-key','max_calls':200})
            self.j('/api/create',{'prompt':'Cavaleiro para aprovar primeiro','look':2008,'idle':1,'walk':1,'z':1})
            limit=time.time()+10
            while time.time()<limit and self.j('/api/job')['status']!='awaiting_approval':time.sleep(.05)
            job=self.j('/api/job');self.assertEqual(job['review_kind'],'sample');self.assertIn('Base',job['stage'])
            self.assertEqual(len([c for c in fake.calls if c[0]=='/generate-image-bitforge']),1)
            raw,_=self.request('/api/export_checkpoint');self.assertEqual(read_package(raw).look,2008)
            self.j('/api/approve_stage',{'approved':True})
            while time.time()<limit and (self.j('/api/job')['status']!='awaiting_approval' or self.j('/api/job').get('review_kind')!='pose'):time.sleep(.05)
            job=self.j('/api/job');self.assertEqual(job['review_kind'],'pose');self.assertEqual(len([c for c in fake.calls if c[0]=='/generate-image-bitforge']),2)
            self.j('/api/approve_stage',{'approved':False});self.server.state.worker.join(5);self.assertEqual(self.j('/api/job')['status'],'cancelled')

# Mantido separado para não poluir os contratos de produção.
from urllib.parse import urlencode
if __name__=='__main__':unittest.main()
