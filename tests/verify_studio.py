"""Verificação opcional com as classes do editor original fornecido pelo usuário.
python tests/verify_studio.py /caminho/newisland_outfit_studio_v3_2
Não abre nem modifica arquivos reais do cliente.
"""
from pathlib import Path
import sys,tempfile,json,zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ni_forge.core import *
from ni_forge.workflows import reproduce_golden,legacy_golden

def verify(editor):
    sys.path.insert(0,str(Path(editor).resolve()))
    from newisland_outfit_studio import OutfitPackageImporter,OutfitTransformer
    from newisland_sprite_core import TibiaSpr860Extended,TibiaDat860Extended,DatItemInfo
    result=reproduce_golden();checked=0
    with tempfile.TemporaryDirectory() as tmp:
        folder=Path(tmp);pack=folder/'golden.zip';write_package(result,pack,legacy_golden())
        # O ZIP acaba de ser gerado pelo próprio teste em um diretório temporário.
        with zipfile.ZipFile(pack) as z:z.extractall(folder/'input')
        analysis=OutfitPackageImporter.scan(folder/'input')
        assert analysis.image_count==1792 and analysis.missing_slots==0
        assert [(g.width,g.height,g.frames,g.pattern_z,g.pattern_y,g.layers) for g in analysis.groups]==[(2,2,8,2,7,2)]*2
        spr=TibiaSpr860Extended();dat=TibiaDat860Extended();dat.signature=0x12345678;dat.frame_groups=True;dat.frame_durations=False
        dat.last_item_id=100;dat.items[100]=DatItemInfo(100,1,1,None,1,1,1,1,1,[0])
        transformer=OutfitTransformer(spr,dat)
        outfit,stats=OutfitPackageImporter(spr,dat,transformer).import_analysis(analysis,create_new=True)
        assert sum(len(g.sprite_ids) for g in outfit.groups)==7168
        spr.save(folder/'Tibia.spr',make_backup=False);dat.save(folder/'Tibia.dat',make_backup=False,sprite_count=spr.sprite_count)
        spr2=TibiaSpr860Extended();spr2.load(folder/'Tibia.spr');dat2=TibiaDat860Extended()
        dat2.load(folder/'Tibia.dat',extended=True,frame_groups=True,frame_durations=False,sprite_count=spr2.sprite_count,auto_detect=False)
        transform2=OutfitTransformer(spr2,dat2)
        for entry in analysis.entries:
            group=dat2.outfits[outfit.outfit_id].groups[entry.group_num-1]
            actual=np.array(transform2.build_slice_image(group,frame=entry.frame,z=entry.z,y=entry.y,x=entry.x,layer=entry.layer))
            assert np.array_equal(actual,decode_png(entry.path.read_bytes())),entry.path.name
            checked+=1
        dat2.frame_durations=True
        for group in dat2.outfits[outfit.outfit_id].groups:
            group.animation_metadata=bytes([0])+int(0).to_bytes(4,'little',signed=True)+bytes([255])+b''.join(int(t).to_bytes(4,'little')*2 for t in [100,110,120,130,140,150,160,170])
        expected=[g.animation_metadata for g in dat2.outfits[outfit.outfit_id].groups]
        replaced,replaced_stats=OutfitPackageImporter(spr2,dat2,transform2).import_analysis(analysis,create_new=False,target_outfit_id=outfit.outfit_id)
        assert [g.animation_metadata for g in replaced.groups]==expected
        spr2.save(folder/'replace.spr',make_backup=False);dat2.save(folder/'replace.dat',make_backup=False,sprite_count=spr2.sprite_count)
    return {'ok':True,'quadros_identicos_apos_spr_dat':checked,'slots_faltantes':analysis.missing_slots,'referencias_dat':7168,'importacao_novo':stats,'substituicao':replaced_stats,'metadados_animacao_preservados':True,'cliente_executado':False,'dat_spr':'Sintéticos, somente para teste temporário.'}

if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('Uso: python tests/verify_studio.py /caminho/do/editor_original')
    print(json.dumps(verify(sys.argv[1]),ensure_ascii=False,indent=2))
