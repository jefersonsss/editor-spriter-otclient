#!/usr/bin/env python3
"""Script utilitário automatizado para geração e validação de outfits modulares (Pattern Y = 7).
Permite executar a criação de outfits de ponta a ponta sem necessidade de navegador.
"""
import sys, os, json, argparse, threading
from pathlib import Path

# Adiciona a raiz do projeto ao sys.path
ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ni_forge.core import read_package, write_package, validate, ForgeError, PARTS
from ni_forge.ai import API, PixelLabAPI, DEFAULTS
from ni_forge.workflows import create_sequential, reproduce_golden, legacy_golden, reference

def build_api(workspace: Path, provider: str = None):
    config = DEFAULTS.copy()
    config_file = workspace / 'config.json'
    if config_file.exists():
        try:
            config.update({k: v for k, v in json.loads(config_file.read_text(encoding='utf-8')).items() if k in DEFAULTS})
        except Exception:
            pass
    if provider:
        config['provider'] = provider

    cache_dir = workspace / 'cache'
    stop_event = threading.Event()
    progress = lambda msg: print(f"[{msg}]", flush=True)

    if config.get('provider') == 'pixellab':
        keys = [k for k in os.environ.get('PIXELLAB_API_KEYS', '').split(',') if k.strip()]
        if not keys:
            raise ForgeError("PIXELLAB_API_KEYS não configurada no ambiente ou no workspace.")
        return PixelLabAPI(config, keys, cache_dir, stop_event, progress)
    else:
        key = os.environ.get('OPENAI_API_KEY', '')
        if not key:
            raise ForgeError("OPENAI_API_KEY não configurada no ambiente ou no workspace.")
        return API(config, key, cache_dir, stop_event, progress)

def auto_create(prompt: str, look: int, output_zip: Path, workspace: Path, idle: int = 8, walk: int = 8, z: int = 2, provider: str = None):
    print(f"--- Iniciando Criação Automática do Outfit (LookType {look}) ---")
    print(f"Modo: 1 Base (Roupa Limpa) + 6 Addons (Helmet, Armor, Legs, Boots, Weapon, Shield)")
    
    service = build_api(workspace, provider)
    groups = {
        1: {'type': 0, 'frames': idle, 'z': z},
        2: {'type': 1, 'frames': walk, 'z': z}
    }
    
    stop_event = threading.Event()
    progress_bar = lambda pct, msg: print(f"[{pct:3d}%] {msg}", flush=True)

    result = create_sequential(
        prompt=prompt,
        look=look,
        groups=groups,
        api=service,
        progress=progress_bar,
        stop=stop_event,
        approve=None,        # Modo não-interativo / 100% automático
        checkpoint=None,
        approve_pose=None
    )

    print("\nValidando integridade do pacote gerado...")
    report = validate(result)
    if not report['ok']:
        print("❌ Erros de validação encontrados:")
        for err in report['errors']:
            print(f"  - {err}")
        sys.exit(1)

    print(f"✅ Validação OK: {report['images']} imagens, {report['dat_references']} referências DAT.")
    output_zip = Path(output_zip)
    write_package(result, output_zip)
    print(f"📦 Pacote exportado com sucesso: {output_zip.resolve()}")

def main():
    parser = argparse.ArgumentParser(description="Automação do New Island Outfit Forge")
    sub = parser.add_subparsers(dest="command")

    create_p = sub.add_parser("create", help="Gera um outfit modular novo automaticamente")
    create_p.add_argument("--prompt", required=True, help="Texto do prompt ou caminho para arquivo .txt")
    create_p.add_argument("--look", type=int, default=2000, help="LookType de destino (ex: 2000)")
    create_p.add_argument("--output", type=Path, required=True, help="Caminho do arquivo ZIP de saída")
    create_p.add_argument("--workspace", type=Path, default=ROOT / "build_workspace", help="Pasta para cache e dados")
    create_p.add_argument("--provider", choices=["openai", "pixellab"], default=None, help="Provedor de imagem")
    create_p.add_argument("--idle", type=int, default=8, help="Frames parado")
    create_p.add_argument("--walk", type=int, default=8, help="Frames andando")
    create_p.add_argument("--z", type=int, default=2, help="Pattern Z")

    val_p = sub.add_parser("validate", help="Valida um pacote ZIP existente")
    val_p.add_argument("zip_path", type=Path, help="Caminho do ZIP a ser inspecionado")

    args = parser.parse_args()

    if args.command == "create":
        prompt_text = args.prompt
        if Path(prompt_text).is_file():
            prompt_text = Path(prompt_text).read_text(encoding="utf-8")
        auto_create(
            prompt=prompt_text,
            look=args.look,
            output_zip=args.output,
            workspace=args.workspace,
            idle=args.idle,
            walk=args.walk,
            z=args.z,
            provider=args.provider
        )
    elif args.command == "validate":
        pkg = read_package(args.zip_path)
        res = validate(pkg)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        sys.exit(0 if res.get('ok', False) else 1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
