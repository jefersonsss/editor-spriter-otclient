#!/usr/bin/env python3
"""Execute sem argumentos para abrir o aplicativo local."""
from pathlib import Path
import argparse,json,os,sys,threading
from ni_forge.core import read_package,write_package,write_source,validate,fingerprint,ForgeError
from ni_forge.ai import API,DEFAULTS
from ni_forge.server import serve,workspace_default
from ni_forge.workflows import reproduce_golden,legacy_golden,convert_ai,create_prompt_source

def main(argv=None):
    parser=argparse.ArgumentParser(description='New Island Outfit Forge · base + 6 addons')
    parser.add_argument('--workspace',type=Path,default=workspace_default(),help='Pasta de projetos/cache/configuração')
    parser.add_argument('--no-browser',action='store_true',help='Exibir URL sem abrir navegador')
    parser.add_argument('--port',type=int,default=0,help='Porta local; 0 escolhe automaticamente')
    sub=parser.add_subparsers(dest='command')
    p=sub.add_parser('inspect',help='Inspecionar um ZIP');p.add_argument('input',type=Path)
    p=sub.add_parser('validate',help='Validar um ZIP modular');p.add_argument('input',type=Path)
    p=sub.add_parser('golden',help='Reproduzir Golden v8 offline');p.add_argument('--output',required=True,type=Path);p.add_argument('--look',type=int,default=1210)
    p=sub.add_parser('convert',help='Converter um outfit existente');p.add_argument('input',type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--look',type=int);p.add_argument('--engine',choices=['auto','golden','ai'],default='auto');p.add_argument('--prompt',default='')
    p=sub.add_parser('create',help='Criar um outfit novo usando API');p.add_argument('--prompt',required=True);p.add_argument('--look',type=int,default=2000);p.add_argument('--output',required=True,type=Path);p.add_argument('--idle',type=int,choices=range(1,9),default=8);p.add_argument('--walk',type=int,choices=range(1,9),default=8);p.add_argument('--z',type=int,choices=[1,2],default=2)
    args=parser.parse_args(argv)
    if args.command is None:serve(args.workspace,args.port,not args.no_browser);return 0
    progress=lambda n,m:print(f'[{n:3d}%] {m}',flush=True)
    try:
        if args.command in ['inspect','validate']:
            source=read_package(args.input);out=source.summary() if args.command=='inspect' else validate(source)
            print(json.dumps(out,ensure_ascii=False,indent=2));return 0 if out.get('ok',True) else 2
        stop=threading.Event();source=None
        def api():
            config=DEFAULTS.copy();p=args.workspace/'config.json'
            if p.exists():config.update({k:v for k,v in json.loads(p.read_text()).items() if k in DEFAULTS})
            return API(config,os.environ.get('OPENAI_API_KEY',''),args.workspace/'cache',stop,print)
        if args.command=='golden':source=legacy_golden();result=reproduce_golden(source,args.look,progress,stop)
        elif args.command=='convert':
            source=read_package(args.input);golden=fingerprint(source)==fingerprint(legacy_golden())
            if args.engine=='golden' or (args.engine=='auto' and golden):result=reproduce_golden(source,args.look,progress,stop)
            elif args.engine=='auto' and source.modular():result=source.copy();result.look=args.look or result.look
            else:result=convert_ai(source,api(),progress,stop,args.look,args.prompt)
        else:
            service=api();groups={1:{'type':0,'frames':args.idle,'z':args.z},2:{'type':1,'frames':args.walk,'z':args.z}}
            source=create_prompt_source(args.prompt,args.look,groups,service,progress,stop)
            write_source(source,args.output.with_name(args.output.stem+'_fonte.zip'))
            result=convert_ai(source,service,progress,stop,args.look,args.prompt)
        report=write_package(result,args.output,source);print(f'\nPacote: {args.output.resolve()}\n{report["images"]} quadros / {report["dat_references"]} referências DAT.');return 0
    except KeyboardInterrupt:print('\nInterrompido. Cache preservado.',file=sys.stderr);return 130
    except (ForgeError,OSError,ValueError) as e:print(f'Erro: {e}',file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
