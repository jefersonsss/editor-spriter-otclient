"""Formato do projeto, importação segura e composição determinística de sprites."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
import io, re, json, zipfile, hashlib, csv, math, copy
from collections import Counter
import numpy as np
from PIL import Image, ImageDraw

PARTS = ['Base', 'Helmet', 'Armor', 'Legs', 'Boots', 'Weapon', 'Shield']
DIRS = ['Norte', 'Leste', 'Sul', 'Oeste']
SIZE = 64
PATTERN = re.compile(r'^look(\d+)_g(\d+)_f(\d+)_(Norte|Leste|Sul|Oeste)_(?:Addon_(\d+)_z(\d+)_(Base|Mascara)(?:_sid\d+)?|(Base|Helmet|Armor|Legs|Boots|Weapon|Shield|Y\d+)_z(\d+)_L(\d+))\.png$', re.I)
Pose = tuple[int, int, int, int]  # group, frame, direction, z
Slot = tuple[int, int, int, int, int, int]  # pose + y, layer

class ForgeError(Exception): pass
class Cancelled(ForgeError): pass

def blank(size=(64,64)): return np.zeros((size[1],size[0],4), dtype=np.uint8)
def rgba(im):
    a=np.array(im.convert('RGBA'));a[a[:,:,3]==0]=0;return a
def png(a):
    b=io.BytesIO();Image.fromarray(np.asarray(a,dtype=np.uint8)).save(b,'PNG');return b.getvalue()
def decode_png(data, expected=None):
    with Image.open(io.BytesIO(data)) as im:
        if im.width*im.height>20_000_000:raise ForgeError('Imagem excede o limite de 20 megapixels.')
        if expected and im.size != expected:raise ForgeError(f'PNG deve ter {expected[0]}×{expected[1]} pixels.')
        return rgba(im)
def over(a,b):
    out=a.copy();m=b[:,:,3]>0;out[m]=b[m];return out
def binary(a):
    out=a.copy();out[:,:,3]=np.where(out[:,:,3]>=128,255,0);out[out[:,:,3]==0]=0;return out
def digest(a):return hashlib.sha256(a.tobytes()).hexdigest()
def pose_id(p):return '_'.join(map(str,p))
def parse_pose(s):
    vals=tuple(map(int,str(s).split('_')))
    if len(vals)!=4:raise ForgeError('Pose inválida.')
    return vals
def checker(a, scale=4):
    bg=Image.new('RGBA',(64,64),(44,54,64,255));d=ImageDraw.Draw(bg)
    for y in range(0,64,8):
        for x in range(0,64,8):
            if (x//8+y//8)%2:d.rectangle((x,y,x+7,y+7),fill=(54,65,76,255))
    bg.alpha_composite(Image.fromarray(a));return bg.resize((64*scale,64*scale),Image.Resampling.NEAREST)

@dataclass
class Outfit:
    look: int
    groups: dict[int, dict]
    slots: dict[Slot, np.ndarray] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    def poses(self):
        return [(g,f,d,z) for g,v in sorted(self.groups.items()) for f in range(v['frames']) for d in range(4) for z in range(v['z'])]
    def get(self, pose, y=0, layer=0):return self.slots.get((*pose,y,layer),blank())
    def full(self,pose,bits=None,base=True):
        a=blank()
        for y in range(max((k[4] for k in self.slots),default=0)+1):
            if (y==0 and base) or (y>0 and (bits is None or bits&(1<<(y-1)))):a=over(a,self.get(pose,y))
        return a
    def modular(self):return set(self.slots)=={(*p,y,l) for p in self.poses() for y in range(7) for l in range(2)}
    def summary(self):
        ys=sorted({k[4] for k in self.slots})
        return {'look':self.look,'groups':self.groups,'poses':[pose_id(p) for p in self.poses()], 'images':len(self.slots),'ys':ys,'modular':self.modular(),'notes':self.notes,'metadata':self.metadata}
    def copy(self):return Outfit(self.look,copy.deepcopy(self.groups),{k:v.copy() for k,v in self.slots.items()},self.notes.copy(),copy.deepcopy(self.metadata))

def read_package(source: bytes | str | Path) -> Outfit:
    if isinstance(source,bytes):z=zipfile.ZipFile(io.BytesIO(source))
    else:z=zipfile.ZipFile(source)
    with z:
        if len(z.infolist())>30000 or sum(i.file_size for i in z.infolist())>256*1024**2:raise ForgeError('ZIP excede os limites de tamanho/quantidade de arquivos.')
        slots={};groups={};looks=set();notes=[];meta={}
        for info in z.infolist():
            path=PurePosixPath(info.filename.replace('\\','/'))
            if path.is_absolute() or '..' in path.parts:raise ForgeError('ZIP contém caminho inválido.')
            if info.file_size>32*1024**2:raise ForgeError('Arquivo interno excessivamente grande.')
            m=PATTERN.match(path.name)
            if not m:continue
            look,g,f,d,y,zv,layer,piece,zs,ls=m.groups()
            look,g,f=int(look),int(g),int(f);di=next(i for i,s in enumerate(DIRS) if s.lower()==d.lower())
            if y is None:
                y=int(piece[1:]) if piece.lower().startswith('y') else next(i for i,s in enumerate(PARTS) if s.lower()==piece.lower())
                zv=int(zs);layer=int(ls)
            else:y=int(y);zv=int(zv);layer=0 if layer.lower()=='base' else 1
            if not (1<=g<=8 and 0<=f<64 and 0<=zv<8 and 0<=y<7 and 0<=layer<2):raise ForgeError('Índice fora do perfil: até 7 linhas Y e 2 camadas são aceitas.')
            a=decode_png(z.read(info))
            if a.shape!=(64,64,4):raise ForgeError(f'{path.name}: este perfil New Island requer 64×64; nenhuma imagem antiga é redimensionada automaticamente.')
            key=g,f,di,zv,y,layer
            if key in slots:raise ForgeError(f'Dois quadros para o mesmo slot: {path.name}.')
            if np.any((a[:,:,3]!=0)&(a[:,:,3]!=255)):notes.append(f'{path.name}: alpha parcial convertido para SPR RGB.')
            slots[key]=binary(a);looks.add(look)
            group_type=g-1
            for part in path.parts:
                gm=re.fullmatch(r'group_(\d+)_type_(\d+)',part,re.I)
                if gm and int(gm[1])==g:group_type=int(gm[2])
            acc=groups.setdefault(g,{'type':group_type,'frames':0,'z':0})
            if acc['type']!=group_type:raise ForgeError('Tipo de grupo inconsistente.')
            acc['frames']=max(acc['frames'],f+1);acc['z']=max(acc['z'],zv+1)
        if not slots:
            # Exportação nativa PixelLab 3.x: aproveita as rotações coerentes que
            # o próprio gerador já produziu, em vez de recriá-las imagem a imagem.
            manifests=[]
            for info in z.infolist():
                if PurePosixPath(info.filename).suffix.lower()=='.json' and info.file_size<=2*1024**2:
                    try:
                        candidate=json.loads(z.read(info))
                        if candidate.get('export_version') and isinstance(candidate.get('states'),list):manifests.append(candidate)
                    except (UnicodeDecodeError,json.JSONDecodeError):pass
            if manifests:
                manifest=manifests[0];states=manifest['states']
                if not states:raise ForgeError('Exportação PixelLab sem estados.')
                state=states[0];character=state.get('character',{});size=character.get('size',{})
                if size!={'width':64,'height':64}:raise ForgeError('A exportação PixelLab precisa usar sprites 64×64.')
                rotations=state.get('frames',{}).get('rotations',{})
                names=set(z.namelist());mapping={'north':0,'east':1,'south':2,'west':3}
                groups={1:{'type':0,'frames':1,'z':1}};look=2000
                for direction,di in mapping.items():
                    filename=str(rotations.get(direction,''))
                    if not filename or filename not in names:raise ForgeError(f'Exportação PixelLab sem rotação {direction}.')
                    a=decode_png(z.read(filename),expected=(64,64));slots[(1,0,di,0,0,0)]=binary(a)
                    for y in range(7):
                        for layer in range(2):slots.setdefault((1,0,di,0,y,layer),blank())
                looks={look};meta={'origin':'pixellab_export','pixellab_group_id':str(manifest.get('group_id','')),'pixellab_character_id':str(character.get('id','')),'pixellab_export_version':str(manifest.get('export_version',''))}
                notes.append('Importação PixelLab: rotações diagonais foram preservadas no ZIP de origem, mas o perfil atual usa Norte/Leste/Sul/Oeste. LookType inicial 2000; ajuste antes de exportar.')
            else:raise ForgeError('Nenhum PNG de outfit reconhecido no ZIP.')
        if len(looks)!=1:raise ForgeError('Importe apenas um LookType por ZIP.')
        if sum(v['frames']*v['z']*4 for v in groups.values())>1024:raise ForgeError('Outfit excede 1.024 poses.')
        outfit=Outfit(looks.pop(),groups,slots,notes,meta)
        for p in outfit.poses():
            if (*p,0,0) not in slots:raise ForgeError(f'Base de origem ausente em {pose_id(p)}; não é possível compor o FULL.')
        for n in z.namelist():
            if PurePosixPath(n).name=='forge_project.json':
                obj=json.loads(z.read(n));outfit.metadata=obj.get('metadata',{});outfit.notes+=obj.get('notes',[])
                break
        if {k[4] for k in slots}<={0,1,2}:outfit.notes.append('Os nomes Base/Helmet/Armor de uma exportação antiga não comprovam o conteúdo: a conversão analisa o FULL.')
        return outfit

def make_modular(source, look=None):
    return Outfit(look or source.look,{g:dict(v) for g,v in source.groups.items()}, {(*p,y,l):blank() for p in source.poses() for y in range(7) for l in range(2)})

def fingerprint(outfit):
    h=hashlib.sha256()
    for p in outfit.poses():h.update(str(p).encode());h.update(outfit.full(p).tobytes())
    return h.hexdigest()

def validate(outfit, source=None):
    errors=[];warnings=list(dict.fromkeys(outfit.notes));empty=Counter();counts=Counter();overlaps=0;diff=0
    if not 1<=outfit.look<=65535:errors.append('LookType deve estar entre 1 e 65535.')
    for p in outfit.poses():
        for y in range(7):
            for l in range(2):
                key=(*p,y,l)
                if key not in outfit.slots:errors.append(f'Slot ausente: {key}');continue
                a=outfit.slots[key]
                if a.shape!=(64,64,4):errors.append(f'Tamanho inválido: {key}');continue
                if np.any((a[:,:,3]!=0)&(a[:,:,3]!=255)):errors.append(f'Alpha parcial: {key}')
                if l==0:
                    n=int(np.count_nonzero(a[:,:,3]));counts[PARTS[y]]+=n
                    if not n:empty[PARTS[y]]+=1
                else:
                    visible=a[:,:,3]>0;colors=a[:,:,:3][visible]
                    if len(colors) and not all(tuple(c) in {(255,255,0),(255,0,0),(0,255,0),(0,0,255)} for c in colors):errors.append(f'Cor de máscara inválida: {key}')
                    if np.any(visible&(outfit.get(p,y)[:,:,3]==0)):errors.append(f'Máscara fora da peça: {key}')
        if source and p in source.poses():diff+=int(np.count_nonzero(np.any(outfit.full(p,bits=15)!=source.full(p),axis=2)))
        for y in range(1,5):
            for j in range(y+1,5):overlaps+=int(np.count_nonzero((outfit.get(p,y)[:,:,3]>0)&(outfit.get(p,j)[:,:,3]>0)))
    for part,n in empty.items():
        if n==len(outfit.poses()):errors.append(f'{part} vazio em todas as poses.')
        else:warnings.append(f'{part} oculto/vazio em {n} poses; confira a animação.')
    if overlaps:warnings.append(f'{overlaps} pixels de interseção entre peças corporais: revisar a ordem de pintura.')
    return {'ok':not errors,'errors':errors[:100],'warnings':list(dict.fromkeys(warnings)), 'poses':len(outfit.poses()),'images':len(outfit.slots),'dat_references':len(outfit.poses())*7*2*4,'empty_poses':dict(empty),'opaque_pixels':dict(counts),'body_overlaps':overlaps,'source_difference_pixels':diff if source else None,'art_review':outfit.metadata.get('art_review','revisão visual recomendada'),'live_client_test':False}

def write_package(outfit, destination, source=None):
    report=validate(outfit,source)
    if not report['ok']:raise ForgeError('Exportação bloqueada: '+'; '.join(report['errors'][:5]))
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    prefix=f'outfit_{outfit.look}';tiles={};tile_ids={};mapping=[];hashes=[]
    temporary=destination.with_suffix('.tmp')
    try:
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            def add(name,data):
                if isinstance(data,str):data=data.encode('utf-8')
                z.writestr(prefix+'/'+name,data);hashes.append(hashlib.sha256(data).hexdigest()+'  '+name)
            for key,a in sorted(outfit.slots.items()):
                g,f,d,zv,y,l=key;name=f'quadros_compostos/group_{g:02d}_type_{outfit.groups[g]["type"]:02d}/look{outfit.look}_g{g:02d}_f{f:02d}_{DIRS[d]}_Addon_{y}_z{zv}_{"Base" if l==0 else "Mascara"}.png'
                add(name,png(a));ids=[]
                for yy,xx in [(32,32),(32,0),(0,32),(0,0)]:
                    tile=a[yy:yy+32,xx:xx+32]
                    if not tile[:,:,3].any():sid=0
                    else:
                        h=digest(tile)
                        if h not in tile_ids:
                            sid=len(tile_ids)+1;tile_ids[h]=sid;tiles[sid]=tile.copy()
                        sid=tile_ids[h]
                    ids.append(sid)
                mapping.append([name,*ids])
            add('sprites_individuais/sprite_000000.png',png(blank((32,32))))
            for sid,tile in tiles.items():add(f'sprites_individuais/sprite_{sid:06d}.png',png(tile))
            sio=io.StringIO();w=csv.writer(sio);w.writerow(['quadro','inferior_direito','inferior_esquerdo','superior_direito','superior_esquerdo']);w.writerows(mapping);add('mapa_sprites.csv',sio.getvalue())
            add('manifest.txt',f'New Island Outfit Forge 1.0\nLookType: {outfit.look}\nWidth=2 Height=2 Layers=2 PatternX=4 PatternY=7\nGrupos: {json.dumps(outfit.groups)}\nY0=Base Y1=Helmet Y2=Armor Y3=Legs Y4=Boots Y5=Weapon Y6=Shield\nQuadros: {len(outfit.slots)}\nReferencias DAT: {report["dat_references"]}\nSprites locais nao vazios: {len(tiles)}\nOrdem DAT: inferior-direito, inferior-esquerdo, superior-direito, superior-esquerdo.\nIDs locais; o editor cria os SPR IDs finais.\n')
            add('validacao.json',json.dumps(report,ensure_ascii=False,indent=2))
            add('forge_project.json',json.dumps({'version':1,'metadata':outfit.metadata,'notes':outfit.notes},ensure_ascii=False,indent=2))
            add('LEIA_PRIMEIRO.txt','Importe este ZIP na aba Importar ZIP / Pasta do New Island Outfit Studio.\nA origem é o LookType no manifest; criar novo utiliza o próximo ID do DAT.\nSalve SPR antes de DAT. Confira todos os addons e estados antes de usar no cliente.\nA prévia e a revisão também estão disponíveis ao reabrir este ZIP no Outfit Forge.\nOs testes estruturais não substituem a revisão artística no cliente.\n')
            add('preview.png',png(rgba(contact_sheet(outfit))))
            z.writestr(prefix+'/SHA256SUMS.txt','\n'.join(hashes))
        temporary.replace(destination)
    finally:temporary.unlink(missing_ok=True)
    return report

def write_source(outfit,destination):
    """Checkpoint interno, inclusive para uma fonte antiga com somente 3 linhas Y."""
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=destination.with_suffix('.tmp')
    try:
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as z:
            for (g,f,d,zv,y,l),a in sorted(outfit.slots.items()):
                name=f'outfit_{outfit.look}/quadros_compostos/group_{g:02d}_type_{outfit.groups[g]["type"]:02d}/look{outfit.look}_g{g:02d}_f{f:02d}_{DIRS[d]}_Addon_{y}_z{zv}_{"Base" if l==0 else "Mascara"}.png'
                z.writestr(name,png(a))
            z.writestr(f'outfit_{outfit.look}/forge_project.json',json.dumps({'version':1,'metadata':outfit.metadata,'notes':outfit.notes},ensure_ascii=False))
        temporary.replace(destination)
    finally:temporary.unlink(missing_ok=True)

def contact_sheet(outfit,frame=0):
    g=min(outfit.groups);im=Image.new('RGB',(4*256,3*276+35),(23,31,40));d=ImageDraw.Draw(im)
    for col in range(4):
        p=(g,min(frame,outfit.groups[g]['frames']-1),col,0)
        for row,bits in enumerate([0,15,63]):
            x=col*256;y=row*276+30;im.paste(checker(outfit.full(p,bits),4),(x,y));d.text((x+8,y-18),f'{DIRS[col]} / addons {bits}',fill='white')
    return im

def atlas(frames, cols=2, cell=512, labels=False):
    """Grade explícita; nunca recorta/recentraliza a fonte antiga."""
    rows=math.ceil(len(frames)/cols);im=Image.new('RGBA',(cols*cell,rows*cell))
    for i,a in enumerate(frames):im.alpha_composite(Image.fromarray(a).resize((cell,cell),Image.Resampling.NEAREST),((i%cols)*cell,(i//cols)*cell))
    return rgba(im)

def split_generated(a,count, cols=2, chroma=False):
    """Somente arte recém-gerada é convertida da grade para pixels nativos."""
    rows=math.ceil(count/cols);h,w=a.shape[:2]
    if w%cols or h%rows:raise ForgeError('A API devolveu uma grade com dimensões incompatíveis.')
    out=[]
    for i in range(count):
        tile=a[(i//cols)*h//rows:(i//cols+1)*h//rows,(i%cols)*w//cols:(i%cols+1)*w//cols].copy()
        if chroma:
            r,g,b=tile[:,:,:3].transpose(2,0,1).astype(int);bg=(r>150)&(b>150)&(g<120)&(r>g+65)&(b>g+65);tile[bg]=0
        native=binary(rgba(Image.fromarray(tile).resize((64,64),Image.Resampling.NEAREST)))
        if np.count_nonzero(native[:,:,3])>3072:raise ForgeError('Um quadro gerado ocupa mais de 75% da célula. Confira transparência/fundo ou use chroma magenta; um fundo opaco não será importado como addon.')
        out.append(native)
    return out
