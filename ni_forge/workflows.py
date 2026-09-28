from __future__ import annotations
from pathlib import Path
import sys,importlib.util,json,math,copy
import numpy as np
from scipy import ndimage as ndi
from PIL import Image,ImageDraw
from .core import *
from .ai import API,ANALYZE_PROMPT,ANALYSIS_SCHEMA,QC_SCHEMA

def resources():return Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))
def reference(name='golden_modular_v8.zip'):return read_package(resources()/'data/references'/name)
def legacy_golden():return read_package(resources()/'data/recipes/fontes/golden_original.zip')
def check_stop(stop):
    if stop and stop.is_set():raise Cancelled('Cancelado. O cache está preservado para retomada.')

def reproduce_golden(source=None,look=None,progress=None,stop=None):
    progress=progress or (lambda n,msg:None)
    src=source or legacy_golden()
    if fingerprint(src)!=fingerprint(legacy_golden()):raise ForgeError('A receita Golden só se aplica à mesma matriz visual validada. Use a conversão por IA para este outfit.')
    p=resources()/'data/recipes/reconstruir_quadros.py';spec=importlib.util.spec_from_file_location('forge_golden_recipe',p);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    result=make_modular(src,look);sword,shield=module.prepare_equipment()
    for i,pose in enumerate(src.poses()):
        check_stop(stop);g,f,d,z=pose
        pieces,mask,components,meta=module.body(g,f,DIRS[d],z)
        w,s,anchors=module.equipment(g,f,DIRS[d],z,components,sword,shield)
        for y,a in enumerate(pieces+[w,s]):result.slots[(*pose,y,0)]=a
        result.slots[(*pose,0,1)]=mask
        if i%8==0:progress(int(i/len(src.poses())*90),f'Reproduzindo Golden: pose {i+1}/{len(src.poses())}')
    result.metadata={'engine':'golden_recipe_v8','art_review':'referência Golden informada como validada no cliente pelo usuário','source_fingerprint':fingerprint(src)}
    # Este teste impede que um ajuste local transforme a reprodução em aproximação.
    valid=reference()
    for key,a in result.slots.items():
        if not np.array_equal(a,valid.slots[key]):raise ForgeError('A reprodução Golden divergiu da referência incorporada.')
    progress(100,'Golden reproduzido e comparado com a referência.');return result

def analysis_board(source,poses):
    im=Image.new('RGBA',(1024,256*len(poses)),(48,58,69,255))
    for row,p in enumerate(poses):
        for col,a in enumerate([source.get(p,0),source.get(p,1),source.get(p,2),source.full(p)]):
            im.alpha_composite(Image.fromarray(a).resize((256,256),Image.Resampling.NEAREST),(col*256,row*256))
    return rgba(im)

def polygon_mask(polygons):
    out=Image.new('1',(64,64));d=ImageDraw.Draw(out)
    if not isinstance(polygons,list):raise ForgeError('Polígonos inválidos na análise.')
    for poly in polygons:
        if len(poly)<3:continue
        points=[]
        for p in poly:
            x,y=int(p['x']),int(p['y'])
            if not(0<=x<=64 and 0<=y<=64):raise ForgeError('A IA devolveu coordenadas fora do quadro 64×64.')
            points.append((min(x,63),min(y,63)))
        d.polygon(points,fill=1)
    return np.array(out,dtype=bool)

def label_pose(source,pose,plan):
    full=source.full(pose);active=full[:,:,3]>0;labels=np.full((64,64),-1,dtype=np.int8)
    masks={i:np.zeros((64,64),bool) for i in range(7)}
    for region in plan.get('regions',[]):
        name=region['piece'];y=0 if name=='skin' else PARTS.index(name)
        masks[y]|=polygon_mask(region['polygons'])
    # Dono único: capacete tem prioridade sobre couraça, depois perneiras/botas.
    for y in [1,2,3,4,5,6,0]:labels[(labels<0)&masks[y]&active]=y
    for identified in plan.get('isolated_addons',[]):
        sy=identified['source_y'];name=identified['piece']
        if sy<=0 or name not in PARTS[1:] or identified['confidence']<.90:continue
        a=source.get(pose,sy);visible=(a[:,:,3]>0)&np.all(a==full,axis=2)
        labels[visible]=PARTS.index(name)
    uncovered=active&(labels<0);notes=[]
    if uncovered.any():
        seeds=labels>=0
        if not seeds.any():raise ForgeError('Análise sem regiões utilizáveis. Nenhum recorte arbitrário foi aplicado.')
        distance,idx=ndi.distance_transform_edt(~seeds,return_indices=True)
        labels[uncovered]=labels[idx[0][uncovered],idx[1][uncovered]]
        percentage=100*int(uncovered.sum())/max(1,int(active.sum()))
        notes.append(f'{pose_id(pose)}: {percentage:.1f}% dos pixels tiveram dono inferido pela região visual mais próxima.')
        if percentage>25 or np.any(distance[uncovered]>8):notes.append(f'{pose_id(pose)}: segmentação incerta; revisar esta pose no editor de pixels.')
    labels[~active]=-1
    return labels,notes

def analyze(source,api,progress,stop):
    plans={};poses=source.poses();batch=max(1,min(4,int(api.config['vision_batch'])))
    for start in range(0,len(poses),batch):
        check_stop(stop);pp=poses[start:start+batch]
        descriptions=[{'id':pose_id(p),'row':i,'group':p[0],'frame':p[1],'direction':DIRS[p[2]],'z':p[3]} for i,p in enumerate(pp)]
        prompt=ANALYZE_PROMPT+'\nPOSES: '+json.dumps(descriptions,ensure_ascii=False)
        answer=api.vision(prompt,[analysis_board(source,pp)],ANALYSIS_SCHEMA)
        found={v.get('id'):v for v in answer.get('poses',[])}
        if len(answer.get('poses',[]))!=len(pp) or set(found)!={pose_id(p) for p in pp}:raise ForgeError('A análise visual omitiu ou duplicou uma pose; reduza o lote e retome.')
        for p in pp:
            plan=found[pose_id(p)]
            if not(0<=plan['confidence']<=1):raise ForgeError('Confiança inválida na análise visual.')
            plans[p]=plan
        progress(5+int(25*(start+len(pp))/len(poses)),f'Análise visual: {start+len(pp)}/{len(poses)} poses')
    return plans

GRID_PROMPT='''TECHNICAL GAME SPRITE ATLAS. Exactly 1024x1024 PNG. Fixed 4 columns x 4 rows, each cell 256x256 = an enlarged 64x64 native tile. Native pixels form 4x4 solid blocks. Never print grid lines, labels, text, shadows or background patterns. Transparent exterior. Each cell contains precisely the requested pose at the same anchor and scale as that cell in the pose guide. Do not center sprites in cells. Keep the character at the original bottom-right-oriented anchor shown in the guide. Do not merge cells or spill between them. Empty/padded cells stay transparent. All poses are one identical character/equipment design; only direction and animation vary. Crisp Tibia pixel art, limited palette, no antialiasing. Directions are literal north/back, east/right, south/front, west/left; do not substitute three-quarter poses for all directions.'''

def generation_batches(poses):
    # Ordem por grupo/Z/direção/frame para manter a leitura do atlas consistente.
    ordered=sorted(poses,key=lambda p:(p[0],p[3],p[2],p[1]))
    for i in range(0,len(ordered),16):yield ordered[i:i+16]

def atlas16(arrays):return atlas(arrays+[blank()]*(16-len(arrays)),cols=4,cell=256)
def pose_descriptions(poses):return json.dumps([{'cell':i,'row':i//4,'col':i%4,'id':pose_id(p),'direction':DIRS[p[2]],'frame':p[1],'group':p[0],'z':p[3]} for i,p in enumerate(poses)],ensure_ascii=False)

def bbox(mask):
    ys,xs=np.where(mask)
    if not len(xs):return None
    return int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)

def align_new(art,target):
    """Encaixe restrito a arte NOVA. Nunca altera fonte/equipamento antigo."""
    bb=bbox(art[:,:,3]>0);tb=bbox(target)
    if bb is None or tb is None:raise ForgeError('A geração produziu uma peça vazia ou sem âncora.')
    x0,y0,x1,y1=bb;tx0,ty0,tx1,ty1=tb
    # A referência oferece a área anatômica; preserva proporção da arte nova.
    ratio=min((tx1-tx0)/(x1-x0),(ty1-ty0)/(y1-y0))
    w=max(1,round((x1-x0)*ratio));h=max(1,round((y1-y0)*ratio))
    tile=rgba(Image.fromarray(art[y0:y1,x0:x1]).resize((w,h),Image.Resampling.NEAREST))
    x=tx0+(tx1-tx0-w)//2;y=ty1-h;out=blank();out[y:y+h,x:x+w]=tile
    return binary(out)

def create_prompt_source(prompt,look,groups,api,progress,stop):
    if len(prompt.strip())<8:raise ForgeError('Descreva o personagem e seu equipamento no prompt.')
    guide=reference();source=Outfit(look,groups);poses=source.poses();first_style=None
    for bi,pp in enumerate(generation_batches(poses)):
        check_stop(stop);guides=[]
        for p in pp:
            gp=(min(p[0],max(guide.groups)),p[1]%8,p[2],p[3]%2);a=guide.get(gp,0).copy()
            # Silhueta neutra: a referência dita a pose, não o design Golden.
            gray=np.mean(a[:,:,:3],axis=2).astype(np.uint8);a[:,:,:3]=np.stack([gray]*3,axis=2);guides.append(a)
        req=GRID_PROMPT+'\nDESIGN COMPLETELY NEW: '+prompt+'\nCreate FULL equipped character with separate recognizable helmet, torso armor, battle leggings, boots, one weapon and shield. This is new artwork; do not recolor/reuse the Golden costume. Use the supplied neutral silhouettes ONLY as pose/scale guides.\nCELLS: '+pose_descriptions(pp)
        refs=[atlas16(guides)]+([first_style] if first_style is not None else [])
        generated=api.image(req,refs)
        if first_style is None:first_style=generated
        art=split_generated(generated,16,cols=4,chroma=api.config['background']!='transparent')
        for p,a,g in zip(pp,art,guides):
            # Novas armas podem usar a margem, mas a escala segue o guia.
            target=ndi.binary_dilation(g[:,:,3]>0,iterations=3)
            source.slots[(*p,0,0)]=align_new(a,target);source.slots[(*p,0,1)]=blank()
        progress(int(20*(bi+1)/math.ceil(len(poses)/16)),f'Criando FULL por prompt: lote {bi+1}/{math.ceil(len(poses)/16)}')
    source.metadata={'prompt':prompt,'origin':'new_prompt'};return source

def convert_ai(source,api,progress,stop,look=None,prompt=''):
    plans=analyze(source,api,progress,stop);result=make_modular(source,look);labels={};generated_info={}
    for p in source.poses():
        lab,notes=label_pose(source,p,plans[p]);labels[p]=lab;result.notes.extend(notes)
        if plans[p]['confidence']<.8:result.notes.append(f'{pose_id(p)}: confiança visual {plans[p]["confidence"]:.2f}; revisar.')
        if not plans[p]['complete']:result.notes.append(f'{pose_id(p)}: a análise considerou o FULL incompleto; confira as peças novas.')
        full=source.full(p)
        for y in range(1,7):
            a=full.copy();a[lab!=y]=0;result.slots[(*p,y,0)]=a
    # Corpo novo de verdade, condicionado ao FULL e às poses.
    batches=list(generation_batches(source.poses()))
    for i,pp in enumerate(batches):
        check_stop(stop);req=GRID_PROMPT+'\nRECONSTRUCT THE UNEQUIPPED BODY in each cell. Plain fitted small blue/neutral cloth tunic, simple trousers, small leather shoes, bare head with hair, face and hands. REMOVE ALL metal armor, helmet, shoulder plates, bracers, weapons and shields. Clothing silhouette must be smaller than the equipment. Do not merely desaturate or recolor armor. Reconstruct the body hidden behind the equipment. Exactly preserve anatomical pose and anchor.\nCHARACTER: '+prompt+'\nCELLS: '+pose_descriptions(pp)
        a=api.image(req,atlas16([source.full(p) for p in pp]));art=split_generated(a,16,cols=4,chroma=api.config['background']!='transparent')
        for p,new in zip(pp,art):
            full=source.full(p);lab=labels[p];body=(lab>=0)&(lab<=4)
            if not body.any():raise ForgeError('A análise não identificou uma região para reconstruir o corpo.')
            new=align_new(new,body)
            garment=(lab>=2)&(lab<=4);inner=ndi.distance_transform_edt(body)>1
            allowed=body&(~garment|inner);new[~allowed]=0
            # Somente pele/cabelo identificados são preservados do FULL, nunca Y0 inteiro.
            new[lab==0]=full[lab==0]
            if np.count_nonzero(new[:,:,3])<20:raise ForgeError('A Base reconstruída ficou vazia/inadequada; a geração precisa ser revisada.')
            result.slots[(*p,0,0)]=new
        progress(35+int(25*(i+1)/len(batches)),f'Reconstruindo roupa-base: lote {i+1}/{len(batches)}')
    # Uma peça pode não existir no outfit antigo. Cria arte nova nos seus pontos de encaixe.
    for y in range(1,7):
        absent=[p for p in source.poses() if not result.get(p,y)[:,:,3].any()]
        for pp in generation_batches(absent):
            req=GRID_PROMPT+f'\nCreate ONLY {PARTS[y]} equipment for each character pose in the guide; every other pixel must be transparent. No body or other equipment. Match the source material/style and anatomy. The equipment must be wearable at the exact same location. Character request: {prompt}.\nCELLS: '+pose_descriptions(pp)
            a=api.image(req,atlas16([source.full(p) for p in pp]));art=split_generated(a,16,cols=4,chroma=api.config['background']!='transparent')
            for p,new in zip(pp,art):
                boxes={b['piece']:b for b in plans[p].get('attachment_boxes',[])};box=boxes.get(PARTS[y])
                if not box:raise ForgeError(f'A análise não forneceu encaixe para {PARTS[y]} em {pose_id(p)}.')
                x,v,w,h=[int(box[k]) for k in ['x','y','width','height']]
                if min(x,v)<0 or min(w,h)<1 or x+w>64 or v+h>64:raise ForgeError('Caixa de encaixe inválida devolvida pela IA.')
                target=np.zeros((64,64),bool);target[v:v+h,x:x+w]=True;new=align_new(new,target)
                # Peças corporais respeitam os pixels anteriores na ordem Y.
                if y<=4:
                    for earlier in range(1,y):new[result.get(p,earlier)[:,:,3]>0]=0
                    if y==1:
                        for later in range(2,5):result.slots[(*p,later,0)][new[:,:,3]>0]=0
                if not new[:,:,3].any():raise ForgeError(f'{PARTS[y]} gerado não cabe sem encobrir outra peça em {pose_id(p)}; revise a análise.')
                result.slots[(*p,y,0)]=new;generated_info[pose_id(p)+'_'+PARTS[y]]='created_missing'
        progress(60+y*5,f'Peça {PARTS[y]} concluída')
    # Revisão visual da IA é registrada separadamente dos testes de formato.
    sample=[p for p in source.poses() if p[1]==0][:8]
    panels=[]
    for p in sample:
        for y in [0,2,3]:panels.append(result.get(p,y))
        panels.append(result.full(p))
    qc=api.vision('Review this Tibia modular outfit. For each row the four cells are CLEAN BASE, ARMOR ONLY, LEGS ONLY, FULL. Check that Base is actually unarmored clothing, pieces fit, torso is not cut by pants, and the directions are coherent. Do not certify client compatibility. Return structured checks and concrete notes.',[atlas(panels,cols=4,cell=128)],QC_SCHEMA,'outfit_review')
    if qc['needs_revision'] or not all(qc[k] for k in ['base_clean','pieces_fit','directions_coherent']):result.notes+=['Revisão visual da IA solicita ajuste: '+str(s) for s in (qc['notes'] or ['Verifique corpo, encaixes e direções.'])]
    result.metadata={'engine':'vision_and_images','prompt':prompt,'source_fingerprint':fingerprint(source),'analysis':{pose_id(p):v for p,v in plans.items()},'generated_pieces':generated_info,'quality_review':qc,'api_models':{'vision':api.config['vision_model'],'image':api.config['image_model']},'api_calls':api.calls,'cache_hits':api.hits,'usage':api.usage,'art_review':'Revisar as prévias; geração artística por IA não equivale a aprovação no cliente.'}
    report=validate(result,source)
    if not report['ok']:raise ForgeError('Resultado não passou na validação: '+'; '.join(report['errors'][:4]))
    progress(100,'Conversão concluída. Confira as prévias e o relatório antes de importar no cliente.');return result
