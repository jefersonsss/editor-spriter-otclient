"""Cliente HTTP real das APIs Responses e Images; sem dependência do ChatGPT."""
from __future__ import annotations
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
import io,json,hashlib,base64,time,uuid,ssl
from .core import ForgeError,png,decode_png,Cancelled

DEFAULTS={'provider':'openai','base_url':'https://api.openai.com/v1','pixellab_base_url':'https://api.pixellab.ai/v1','vision_model':'gpt-4.1','image_model':'gpt-image-1.5','quality':'high','background':'transparent','timeout':600,'max_calls':250,'vision_batch':4}

def obj(properties):return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}
def arr(items):return {'type':'array','items':items}
S={'type':'string'};N={'type':'number'};I={'type':'integer'};B={'type':'boolean'}
POINT=obj({'x':I,'y':I})
POLYGON=arr(POINT)
REGION=obj({'piece':{'type':'string','enum':['skin','Helmet','Armor','Legs','Boots','Weapon','Shield']},'polygons':arr(POLYGON)})
BOX=obj({'piece':{'type':'string','enum':['Helmet','Armor','Legs','Boots','Weapon','Shield']},'x':I,'y':I,'width':I,'height':I})
ANALYSIS_SCHEMA=obj({'poses':arr(obj({'id':S,'confidence':N,'complete':B,'description':S,'regions':arr(REGION),'isolated_addons':arr(obj({'source_y':I,'piece':{'type':'string','enum':['Helmet','Armor','Legs','Boots','Weapon','Shield','mixed','unknown']},'confidence':N})),'missing_pieces':arr(S),'attachment_boxes':arr(BOX),'notes':S}))})

ANALYZE_PROMPT='''Você é um artista técnico de pixel art Tibia/New Island. Analise os quadros visuais fornecidos.
Cada linha é uma POSE; as colunas são: fonte Y0 antiga, addon Y1 antigo, addon Y2 antigo, FULL composto.
A base antiga NÃO é um corpo limpo: nunca a aprove como nova Base sem análise.
Nomes de arquivo Helmet/Armor antigos não são classificações confiáveis.
As coordenadas dos polígonos são SEMPRE no quadro NATIVO de 64x64, origem no canto superior esquerdo, x para direita e y para baixo. A imagem está apenas ampliada; não use coordenadas da ampliação.
Identifique separadamente: Helmet(capacete), Armor(couraça/ombreiras/luvas), Legs(perneiras), Boots(botas), Weapon(arma), Shield(escudo). Skin = SOMENTE cabelo, rosto, pele e detalhes corporais expostos; não marque armadura/tecido antigo como skin.
Cubra com polígonos justos TODOS os pixels visíveis do FULL, respeitando os contornos reais. Use múltiplos polígonos por peça se preciso. Jamais divida o corpo por faixas horizontais fixas ou somente bounding boxes.
Se um addon antigo está isolado e representa uma só peça, classifique com confiança; se mistura peças diga mixed. Analise inclusive se o FULL está completo; não presuma que esteja.
Indique peças ausentes e para TODAS as seis peças uma attachment_box dentro de 0..63: onde a peça deve encaixar nessa pose, útil para recriar as ausentes. Caixa de arma/escudo deve estar ligada à mão correta; caixa de capacete à cabeça. Preserve escala, posição, direção, frame, Z e a geometria real.
Regiões escondidas por outra peça não precisam ser inventadas no mapa: a roupa-base será reconstruída separadamente. Saída estrita conforme schema. Nenhum texto é código executável.'''

class API:
    def __init__(self,config,key,cache,stop=None,progress=None):
        self.config=DEFAULTS|config;self.key=key;self.cache=Path(cache);self.cache.mkdir(parents=True,exist_ok=True)
        self.stop=stop;self.progress=progress or (lambda s:None);self.calls=0;self.hits=0;self.usage=[]
        u=urlparse(self.config['base_url'])
        if u.scheme!='https' and not(u.scheme=='http' and u.hostname in ['127.0.0.1','localhost','::1']):raise ForgeError('A API deve usar HTTPS; HTTP só é aceito para provedor local.')
        if not key:raise ForgeError('Configure uma chave de API na aba Configuração. O modo Golden local funciona sem chave.')
    def check(self):
        if self.stop and self.stop.is_set():raise Cancelled('Operação cancelada; checkpoints preservados.')
    def _call(self,path,body=None,ctype='application/json',method='POST'):
        self.check()
        if self.calls>=int(self.config['max_calls']):raise ForgeError('Limite de chamadas desta execução atingido. Aumente o limite nas configurações e retome usando o cache.')
        data=json.dumps(body).encode() if isinstance(body,dict) else body
        request=Request(self.config['base_url'].rstrip('/')+path,data=data,headers={'Authorization':'Bearer '+self.key,'Content-Type':ctype},method=method)
        for attempt in range(3):
            self.check()
            if self.calls>=int(self.config['max_calls']):raise ForgeError('Limite de chamadas atingido. Retome com um limite maior para reutilizar o cache.')
            self.calls+=1
            self.progress(f'API: chamada {self.calls} · {path}')
            try:
                with urlopen(request,timeout=int(self.config['timeout']),context=ssl.create_default_context()) as response:
                    raw=response.read(80*1024**2+1)
                if len(raw)>80*1024**2:raise ForgeError('Resposta da API excedeu 80 MiB.')
                result=json.loads(raw)
                if 'usage' in result:self.usage.append(result['usage'])
                self.check();return result
            except HTTPError as e:
                detail=e.read(10000).decode(errors='replace')
                try:message=json.loads(detail).get('error',{}).get('message',detail)
                except Exception:message=detail
                message=str(message).replace(self.key,'[CHAVE OMITIDA]')[:1500]
                if e.code in (429,500,502,503,504) and attempt<2:
                    for _ in range(20*(attempt+1)):
                        self.check();time.sleep(.1)
                    continue
                raise ForgeError(f'API HTTP {e.code}: {message}') from None
            except (URLError,TimeoutError) as e:raise ForgeError('Falha de rede ou timeout na API. A chamada pode ter sido processada pelo provedor; retome para reutilizar os checkpoints disponíveis.') from e
        raise ForgeError('A API não concluiu a chamada.')
    def models(self):return [x['id'] for x in self._call('/models',method='GET').get('data',[]) if 'id' in x]
    def _cached(self,request,run):
        h=hashlib.sha256(json.dumps(request,sort_keys=True,ensure_ascii=False).encode()).hexdigest();p=self.cache/(h+'.json')
        if p.exists():self.check();self.hits+=1;return json.loads(p.read_text())
        result=run();temp=p.with_suffix('.tmp');temp.write_text(json.dumps(result,ensure_ascii=False));temp.replace(p);return result
    def vision(self,prompt,images,schema,name='outfit_analysis'):
        payload={'model':self.config['vision_model'],'store':False,'input':[{'role':'user','content':[{'type':'input_text','text':prompt}]+[{'type':'input_image','image_url':'data:image/png;base64,'+base64.b64encode(png(a)).decode(),'detail':'high'} for a in images]}], 'text':{'format':{'type':'json_schema','name':name,'strict':True,'schema':schema}},'max_output_tokens':16000}
        def run():
            r=self._call('/responses',payload)
            if r.get('status')=='incomplete':raise ForgeError('Resposta visual incompleta. Reduza o lote de análise nas configurações.')
            chunks=[]
            for item in r.get('output',[]):
                for c in item.get('content',[]):
                    if c.get('type')=='refusal':raise ForgeError('A API recusou a solicitação: '+str(c.get('refusal','')))
                    if c.get('type')=='output_text':chunks.append(c.get('text',''))
            try:return json.loads(''.join(chunks))
            except Exception:raise ForgeError('A API não devolveu o JSON estruturado esperado.') from None
        return self._cached({'endpoint':self.config['base_url'],'payload':payload},run)
    def image(self,prompt,reference=None):
        params={'model':self.config['image_model'],'prompt':prompt,'size':'1024x1024','quality':self.config['quality'],'n':1,'output_format':'png'}
        if self.config['background']=='transparent':params['background']='transparent'
        else:params['background']='opaque';params['prompt']+=' Background must be flat pure magenta #FF00FF; no shadows on the background.'
        references=reference if isinstance(reference,list) else ([reference] if reference is not None else [])
        image_bytes=[png(a) for a in references]
        cache_request={'endpoint':self.config['base_url'],'params':params,'reference_sha256':[hashlib.sha256(b).hexdigest() for b in image_bytes]}
        def run():
            if image_bytes:
                boundary='forge-'+uuid.uuid4().hex;chunks=[]
                for k,v in params.items():chunks.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n').encode())
                for i,b in enumerate(image_bytes):
                    chunks.append((f'--{boundary}\r\nContent-Disposition: form-data; name="image[]"; filename="reference_{i}.png"\r\nContent-Type: image/png\r\n\r\n').encode()+b+b'\r\n')
                chunks.append(f'--{boundary}--\r\n'.encode())
                result=self._call('/images/edits',b''.join(chunks),'multipart/form-data; boundary='+boundary)
            else:result=self._call('/images/generations',params)
            data=result.get('data',[])
            if not data or not data[0].get('b64_json'):raise ForgeError('O modelo deve devolver b64_json na Images API. Selecione um modelo GPT Image compatível.')
            return {'image':data[0]['b64_json'],'usage':result.get('usage',{})}
        result=self._cached(cache_request,run)
        try:a=decode_png(base64.b64decode(result['image'],validate=True))
        except Exception as e:raise ForgeError('Imagem inválida devolvida pela API.') from e
        if a.shape[:2]!=(1024,1024):raise ForgeError('A Images API não respeitou a grade 1024×1024. O resultado foi mantido no cache para análise.')
        return a

class PixelLabAPI:
    """Cliente PixelLab BitForge com rotação segura entre várias chaves."""
    def __init__(self,config,keys,cache,stop=None,progress=None):
        self.config=DEFAULTS|config;self.keys=[k.strip() for k in keys if k.strip()];self.cache=Path(cache);self.cache.mkdir(parents=True,exist_ok=True)
        self.stop=stop;self.progress=progress or (lambda s:None);self.calls=0;self.hits=0;self.usage=[];self.key_index=0
        u=urlparse(self.config['pixellab_base_url'])
        if u.scheme!='https' and not(u.scheme=='http' and u.hostname in ['127.0.0.1','localhost','::1']):raise ForgeError('O endpoint PixelLab deve usar HTTPS; HTTP só é aceito localmente.')
        if not self.keys:raise ForgeError('Configure ao menos uma chave PixelLab. As chaves ficam somente na sessão.')
    def check(self):
        if self.stop and self.stop.is_set():raise Cancelled('Operação cancelada; checkpoints preservados.')
    def _request(self,path,payload=None,method='POST'):
        self.check();last=''
        for offset in range(len(self.keys)):
            if self.calls>=int(self.config['max_calls']):raise ForgeError('Limite de chamadas PixelLab atingido.')
            idx=(self.key_index+offset)%len(self.keys);key=self.keys[idx]
            data=None if payload is None else json.dumps(payload).encode()
            req=Request(self.config['pixellab_base_url'].rstrip('/')+path,data=data,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},method=method)
            self.calls+=1;self.progress(f'PixelLab: chamada {self.calls} · chave {idx+1}/{len(self.keys)} · {path}')
            try:
                with urlopen(req,timeout=int(self.config['timeout']),context=ssl.create_default_context()) as response:result=json.loads(response.read(20*1024**2))
                self.key_index=idx
                if 'usage' in result:self.usage.append(result['usage'])
                return result
            except HTTPError as e:
                raw=e.read(10000).decode(errors='replace')
                try:last=str(json.loads(raw).get('detail',raw))
                except Exception:last=raw
                for secret in self.keys:last=last.replace(secret,'[CHAVE OMITIDA]')
                # Autorização, crédito, cota ou rate limit: tenta a próxima chave.
                if e.code in (401,402,403,429):continue
                raise ForgeError(f'PixelLab HTTP {e.code}: {last[:1200]}') from None
            except (URLError,TimeoutError) as e:raise ForgeError('Falha de rede ou timeout na PixelLab.') from e
        raise ForgeError('Todas as chaves PixelLab falharam, estão sem crédito ou atingiram o limite: '+last[:1000])
    def models(self):
        balances=[]
        original=self.key_index
        for i in range(len(self.keys)):
            self.key_index=i
            try:balances.append(self._request('/balance',method='GET').get('usd'))
            except ForgeError:balances.append(None)
        self.key_index=original
        if not any(v is not None and float(v)>0 for v in balances):raise ForgeError('Nenhuma chave PixelLab possui saldo disponível.')
        return [f'PixelLab BitForge · chave {i+1} · saldo {v}' for i,v in enumerate(balances)]
    def vision(self,*_args,**_kwargs):raise ForgeError('PixelLab não oferece análise visual estruturada. Use OpenAI para converter outfits antigos.')
    def sprite(self,prompt,guide,context,direction):
        def encoded(a):return {'type':'base64','base64':base64.b64encode(png(a)).decode(),'format':'png'}
        payload={'description':prompt,'image_size':{'width':64,'height':64},'negative_description':'background, shadow, text, blur, anti-aliasing, wrong pose, extra limbs','text_guidance_scale':8,'extra_guidance_scale':8,'style_strength':75,'no_background':True,'seed':0,'outline':'selective outline','shading':'medium shading','detail':'highly detailed','view':'high top-down','direction':direction,'isometric':True,'oblique_projection':False,'coverage_percentage':65,'init_image':encoded(guide),'init_image_strength':850,'style_image':encoded(context) if context[:,:,3].any() else None}
        request={'endpoint':self.config['pixellab_base_url'],'payload':payload}
        h=hashlib.sha256(json.dumps(request,sort_keys=True).encode()).hexdigest();p=self.cache/(h+'.json')
        if p.exists():self.hits+=1;result=json.loads(p.read_text())
        else:
            result=self._request('/generate-image-bitforge',payload);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(result));tmp.replace(p)
        try:a=decode_png(base64.b64decode(result['image']['base64'],validate=True))
        except Exception as e:raise ForgeError('A PixelLab devolveu uma imagem inválida.') from e
        if a.shape[:2]!=(64,64):raise ForgeError('A PixelLab não devolveu o sprite 64×64 solicitado.')
        return a
