from pathlib import Path
import re, json, hashlib, csv, io, base64
from collections import defaultdict, Counter
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

HERE=Path(__file__).resolve().parent
import zipfile
SOURCE_ZIP=HERE/'fontes/golden_original.zip'
SOURCE=zipfile.ZipFile(SOURCE_ZIP)
OUT=HERE.parent
DI=['Norte','Leste','Sul','Oeste']
PARTS=['Base','Helmet','Armor','Legs','Boots','Weapon','Shield']
FILES={}
for name in SOURCE.namelist():
    if '/quadros_compostos/' not in name or not name.endswith('.png'):continue
    m=re.search(r'g(\d+)_f(\d+)_(\w+)_Addon_(\d+)_z(\d+)_(Base|Mascara)',name)
    if not m:continue
    g,f,d,a,z,l=m.groups()
    FILES[int(g),int(f),d,int(a),int(z),int(l=='Mascara')]=name
def load(g,f,d,a,z,l=0):return np.array(Image.open(io.BytesIO(SOURCE.read(FILES[g,f,d,a,z,l]))).convert('RGBA'))

def image(a): return Image.fromarray(a.astype('uint8'))
def blank(): return np.zeros((64,64,4),dtype=np.uint8)
def overlay(a,b):
    c=a.copy(); k=b[:,:,3]>0; c[k]=b[k]; return c
def masked(a,m):
    b=a.copy();b[~m]=0;return b
def color_mask(a,c): return np.all(a[:,:,:3]==c,axis=2)&(a[:,:,3]>0)
def polygon(pts):
    im=Image.new('1',(64,64));ImageDraw.Draw(im).polygon(pts,fill=1);return np.array(im,dtype=bool)
def bbox(m):
    yy,xx=np.where(m)
    return [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1] if len(xx) else None

# Coordenadas desenhadas sobre o quadro real de referência, nunca normalizadas
# pelo bounding box do corpo. O deslocamento é apenas o da cabeça entre poses.
REF={
 ('Norte',0):{'hair':(32,31),'head':[(35,30),(40,30),(44,33),(45,37),(45,42),(43,44),(39,45),(35,43),(33,40),(31,38),(31,34)],
              'hem':[(0,54),(44,54),(46,55),(50,55),(52,53),(52,51),(54,50),(63,50)]},
 ('Leste',0):{'hair':(31,32),'head':[(34,32),(38,32),(39,34),(42,34),(44,36),(45,39),(46,42),(45,44),(42,45),(36,45),(33,42),(31,38),(31,34)],
              'hem':[(0,51),(42,51),(44,52),(48,52),(51,51),(52,49),(54,49),(63,49)]},
 ('Norte',1):{'hair':(22,24),'head':[(25,23),(30,23),(34,26),(35,30),(35,35),(33,37),(29,38),(25,36),(23,33),(21,31),(21,27)],
              'hem':[(0,46),(31,46),(33,48),(39,48),(42,47),(43,43),(43,38),(45,37),(63,37)]},
 ('Leste',1):{'hair':(14,25),'head':[(17,25),(21,25),(22,27),(25,27),(27,29),(28,32),(29,35),(28,37),(25,38),(19,38),(16,35),(14,31),(14,27)],
              'hem':[(0,40),(24,41),(27,42),(30,44),(33,44),(35,42),(36,40),(63,40)]},
}

def body(g,f,d,z):
    trans=d in ['Sul','Oeste']; canon={'Sul':'Leste','Oeste':'Norte'}.get(d,d)
    a0=load(g,f,canon,0,z);a1=load(g,f,canon,1,z);a2=load(g,f,canon,2,z)
    m0=load(g,f,canon,0,z,1);m1=load(g,f,canon,1,z,1)
    ref=REF[canon,z];hb=bbox(color_mask(m0,(255,255,0)))
    dx,dy=hb[0]-ref['hair'][0],hb[1]-ref['hair'][1]
    head=polygon([(x+dx,y+dy) for x,y in ref['head']])&(a0[:,:,3]>0)
    rr,gg,bb=a0[:,:,:3].transpose(2,0,1).astype(int)
    golden=(rr>30)&(bb<rr*.30)&(gg>rr*.30)
    head&=~golden
    # Todos os pixels de cabelo/colar que pertencem à máscara antiga permanecem.
    head|=color_mask(m0,(255,255,0))|color_mask(m0,(255,0,0))
    # Couraça com barra curva; braços/luvas são identificados separadamente.
    hem=[(x+dx,y+dy) for x,y in ref['hem']]
    upper=polygon([(-10,-10),(74,-10)]+list(reversed(hem)))
    # Manga/ombreira lateral da pose montada: não pertence à perneira.
    if canon=='Leste' and z==1:
        upper|=polygon([(13+dx,33+dy),(27+dx,33+dy),(29+dx,43+dy),(26+dx,45+dy),(18+dx,45+dy)])
    if canon=='Leste' and z==0:
        upper|=polygon([(36+dx,44+dy),(42+dx,44+dy),(44+dx,49+dy),(44+dx,53+dy),(41+dx,54+dy),(37+dx,53+dy)])
    connected,n=ndi.label(a1[:,:,3]>0,np.ones((3,3)))
    boots1=np.zeros((64,64),bool);hands1=np.zeros((64,64),bool)
    for k in range(1,n+1):
        comp=connected==k
        foot_seeds=comp&color_mask(m1,(0,255,0));hand_seeds=comp&color_mask(m1,(0,0,255))
        if foot_seeds.any() and hand_seeds.any():
            # Nas poses de caminhada a luva pode tocar a bota. As cores da
            # máscara separam os dois lados dentro do mesmo componente.
            fd=ndi.distance_transform_edt(~foot_seeds);hd=ndi.distance_transform_edt(~hand_seeds)
            boot_region=comp&(fd<hd)
            boots1|=boot_region;hands1|=comp&~boot_region
        elif foot_seeds.any():boots1|=comp
        elif hand_seeds.any():hands1|=comp
        elif (comp&upper).sum()>comp.sum()/2:hands1|=comp
        else:boots1|=comp
    hand_labels,hand_count=ndi.label(hands1,np.ones((3,3)))
    hand_components=[hand_labels==k for k in range(1,hand_count+1)]
    assert boots1.any(),(g,f,d,z,'boots absent')
    upper|=ndi.binary_dilation(hands1,iterations=1)
    bodyalpha=a0[:,:,3]>0
    boots0=bodyalpha&ndi.binary_dilation(boots1,iterations=1)&~upper&~head
    legs0=bodyalpha&~upper&~boots0&~head
    armor0=bodyalpha&~legs0&~boots0&~head
    # Pele das mãos: mantida na base. A luva antiga continua pertencendo à armor.
    r,gc,b=a0[:,:,:3].transpose(2,0,1).astype(int)
    skin=(r>40)&(r<=240)&(r>b+25)&(b>=r*.30)&(gc>b+12)&(gc<r*.85)&(gc>r*.48)
    handskin=skin&ndi.binary_dilation(hands1,iterations=1)&bodyalpha&~head
    # Inclui pequenos contornos das mãos, limitados aos componentes das luvas.
    dark=(r<65)&(gc<45)&(b<30)
    keep_hands=handskin|(ndi.binary_dilation(handskin)&dark&bodyalpha&hands1)
    armor0&=~keep_hands;legs0&=~keep_hands;boots0&=~keep_hands
    # Sob o novo Y1 o capacete vem antes dos demais addons. Nenhuma outra peça
    # pode voltar a pintar sobre ele. Luvas e botas também têm dono único.
    armor0&=~boots1
    legs0&=~(boots1|hands1)
    boots0&=~hands1
    gear=[a2,overlay(masked(a0,armor0),masked(a1,hands1)),masked(a0,legs0),overlay(masked(a0,boots0),masked(a1,boots1))]
    for i in range(1,4):gear[i][a2[:,:,3]>0]=0
    full=overlay(overlay(a0,a1),a2)
    regions=[armor0,legs0,boots0]
    # Roupa nova: silhueta interna e sombreamento de tecido, sem reutilizar
    # relevos, rebites, brilhos ou paleta da armadura.
    base=blank();newmask=blank()
    bodyreg=armor0|legs0|boots0
    interior=ndi.distance_transform_edt(bodyalpha)
    bodykeep=bodyreg&(interior>1.0)
    yy,xx=np.indices((64,64))
    palettes=[[(25,39,49),(43,69,85),(69,98,115),(92,119,130)],
              [(29,29,32),(43,43,48),(61,61,67),(77,78,83)],
              [(29,20,16),(51,34,24),(71,47,32),(91,64,44)]]
    for ri,reg in enumerate(regions):
        regkeep=bodykeep&reg
        dist=ndi.distance_transform_edt(regkeep)
        # Superfícies de tecido com duas faixas suaves de luz, sem metal.
        shade=np.where(dist<=1,0,np.where(dist<=2,1,2))
        shade=np.where((dist>=3)&((xx+yy)%7<3),3,shade)
        for si,col in enumerate(palettes[ri]):base[regkeep&(shade==si)]=(*col,255)
        newmask[regkeep]=(*( (255,0,0),(0,255,0),(0,0,255) )[ri],255)
    base[head|keep_hands]=a0[head|keep_hands]
    newmask[head]=m0[head]
    # O colar pertence à roupa e os pixels de pele não recebem máscara.
    newmask[keep_hands]=0
    # A composição completamente equipada é uma verificação independente
    # importante: exatamente a mesma imagem do Golden original.
    test=base.copy()
    for p in gear:test=overlay(test,p)
    missing=(full[:,:,3]>0)&(test[:,:,3]==0)
    assert not missing.any(),(g,f,d,z,'pixel sem dono',int(missing.sum()))
    allparts=[base]+gear
    if trans:
        allparts=[np.transpose(p,(1,0,2)).copy() for p in allparts]
        newmask=np.transpose(newmask,(1,0,2)).copy()
        hand_components=[x.T for x in hand_components]
    return allparts,newmask,hand_components,{'head_shift':[int(dx),int(dy)],'hem':hem,'canonical':canon,'transpose':trans}

def prepare_equipment():
    return np.array(Image.open(HERE/'assets/sword.png').convert('RGBA')), np.array(Image.open(HERE/'assets/shield.png').convert('RGBA'))

def place(sprite,x,y):
    h,w=sprite.shape[:2];out=blank()
    assert x>=0 and y>=0 and x+w<=64 and y+h<=64,(x,y,w,h)
    out[y:y+h,x:x+w]=sprite;return out

def equipment(g,f,d,z,components,sword,shield):
    centers=[]
    for m in components:
        yy,xx=np.where(m);centers.append((int(round(xx.mean())),int(round(yy.mean()))))
    # Z1 do Norte/Oeste tem uma mão parcialmente oculta; âncora documentada.
    if len(centers)==1:
        can='Norte';m=load(g,f,can,0,z,1);hb=bbox(color_mask(m,(255,255,0)))
        dx,dy=hb[0]-22,hb[1]-24
        p=(25+dx,37+dy)
        if d=='Oeste':p=p[::-1]
        centers.append(p)
    if d=='Norte':wh=max(centers,key=lambda p:p[0]);sh=min(centers,key=lambda p:p[0])
    elif d=='Leste':wh=max(centers,key=lambda p:p[1]);sh=min(centers,key=lambda p:p[1])
    elif d=='Sul':wh=min(centers,key=lambda p:p[0]);sh=max(centers,key=lambda p:p[0])
    else:wh=min(centers,key=lambda p:p[1]);sh=max(centers,key=lambda p:p[1])
    if d in ['Norte','Oeste']:
        weapon=place(sword,wh[0]-3,wh[1]-16)
    else:
        spr=np.rot90(sword,1).copy();weapon=place(spr,wh[0]-16,wh[1]-3)
    # Centro do escudo se afasta 2 pixels do tronco para não encobrir a couraça.
    offsets={'Norte':(-2,0),'Leste':(3,-1),'Sul':(0,0),'Oeste':(-1,0)}
    ox,oy=offsets[d];sx,sy=sh[0]+ox-4,sh[1]+oy-5
    shield_image=place(shield,sx,sy)
    # As peças das mãos ficam atrás da cabeça; não cobrem rosto/capacete.
    head_mask=(load(g,f,d,2,z)[:,:,3]>0) | color_mask(load(g,f,d,0,z,1),(255,255,0))
    weapon[head_mask]=0; shield_image[head_mask]=0
    return weapon,shield_image,{'weapon_hand':wh,'shield_hand':sh,'shield_top_left':[sx,sy]}

def build():
    OUT.mkdir(parents=True,exist_ok=True);sword,shield=prepare_equipment();allstates={};coords={}
    for g in [1,2]:
      for f in range(8):
       for d in DI:
        for z in [0,1]:
         parts,mask,comps,meta=body(g,f,d,z)
         weapon,shieldpart,anchors=equipment(g,f,d,z,comps,sword,shield)
         parts.extend([weapon,shieldpart]);meta.update(anchors)
         allstates[g,f,d,z]=parts;coords[f'g{g}_f{f}_{d}_z{z}']=meta
         folder=OUT/'quadros_compostos'/f'group_{g:02d}_type_{g-1:02d}';folder.mkdir(parents=True,exist_ok=True)
         for y,p in enumerate(parts):
          for layer,arr in [('Base',p),('Mascara',mask if y==0 else blank())]:
           image(arr).save(folder/f'look1210_g{g:02d}_f{f:02d}_{d}_Addon_{y}_z{z}_{layer}.png')
    (OUT/'coordenadas_poses.json').write_text(json.dumps(coords,ensure_ascii=False,indent=2))
    return allstates

def preview(states):
    font=ImageFont.load_default()
    for z in [0,1]:
      out=Image.new('RGB',(10*200,4*220+50),(28,33,40));dr=ImageDraw.Draw(out)
      dr.text((15,14),f'Golden reconstruído / G1 F0 Z{z} / prévia ampliada 3x',fill='white',font=font)
      for row,d in enumerate(DI):
       pp=states[1,0,d,z];full=blank();old=blank()
       for p in pp:full=overlay(full,p)
       for y in range(3):old=overlay(old,load(1,0,d,y,z))
       armoronly=overlay(pp[0],pp[2]);legsonly=overlay(pp[0],pp[3]);items=pp+[full,armoronly,legsonly]
       for col,im in enumerate(items):
        bg=Image.new('RGBA',(64,64),(65,70,78,255));bg.alpha_composite(image(im));bg=bg.resize((192,192),Image.Resampling.NEAREST)
        x=col*200+4;y=row*220+70;out.paste(bg,(x,y))
        name=(PARTS+['Completo','Base+Armor','Base+Legs'])[col]
        dr.text((x,y-20),f'{d} {name}',fill='white',font=font)
      out.save(HERE/f'rebuilt_z{z}.png')

if __name__=='__main__':
    states=build();preview(states)
    print('states',len(states),'PNGs',len(list((OUT/'quadros_compostos').rglob('*.png'))))
