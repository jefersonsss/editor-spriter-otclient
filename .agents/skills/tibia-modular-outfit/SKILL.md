---
name: tibia-modular-outfit
description: >-
  Create, convert, and validate Tibia / OTClient modular outfits with 1 Base and 6 Addons (Helmet, Armor, Legs, Boots, Weapon, Shield) using Pattern Y = 7, Layers = 2, 64x64 composed frames, and 32x32 tiles. Use when generating new outfits automatically, separating legacy outfits, enforcing strict unarmored base constraints, or exporting ZIP packages for New Island Outfit Studio and Object Builder.
---

# Tibia & New Island Modular Outfit Skill

Esta skill guia o agente e o usuário na criação e validação **100% automatizada** de outfits modulares para OTClient e Tibia moderno, respeitando a arquitetura validada de **1 Base + 6 Addons** (`Pattern Y = 7`).

---

## 📌 Regras Fundamentais da Arquitetura

1. **A Base (Y0) NUNCA possui armadura ou armas**:
   * Contém **exclusivamente** corpo limpo, pele, cabelo e roupa íntima/túnica de tecido fino bem justa.
   * **PROIBIDO** desenhar ombreiras, elmos, peitorais, perneiras, botas de ferro, espadas ou escudos na Base. O manequim deve ser enxuto para que todas as peças sobrepostas encaixem perfeitamente.
2. **Os 6 Addons (Y1 a Y6) são camadas isoladas e modulares**:
   * **Y1 - Helmet**: Apenas o elmo / capacete / tiara.
   * **Y2 - Armor**: Peitoral, ombreiras, braçadeiras e luvas. Não invade a linha da virilha.
   * **Y3 - Legs**: Perneiras / calças de combate da cintura até o tornozelo.
   * **Y4 - Boots**: Botas / sapatos cobrindo tornozelo e pés.
   * **Y5 - Weapon**: Arma na mão de ataque, sem desenhar corpo ou braços.
   * **Y6 - Shield**: Escudo na mão defensiva com offset de 1–2px do tronco.
3. **Padrão Técnico de Renderização**:
   * Quadros compostos: $64 \times 64\text{ px}$.
   * Tiles: $32 \times 32\text{ px}$ ($2 \times 2$ tiles por quadro).
   * Ordem DAT: **Inferior Direito**, **Inferior Esquerdo**, **Superior Direito**, **Superior Esquerdo**.
   * Camadas: **L0** (Arte RGB, sem alpha parcial) e **L1** (Máscara de 4 cores: Amarelo, Vermelho, Verde, Azul).
   * Padrão Golden: $128\text{ poses}$ ($2\text{ grupos} \times 8\text{ frames} \times 4\text{ direções} \times 2\text{ Z}$).

---

## 🚀 Fluxo Automatizado de Criação

### Passo 1: Preparar o Prompt Estruturado
Utilize o particionamento por tags para evitar contaminação entre peças. Consulte o guia completo em [Modelos de Prompts](./references/prompts_templates.md).

```text
GERAL: <Estilo e conceito geral do personagem>
BASE: <Apenas corpo, cabelo e roupa simples justa - SEM metal ou armas>
HELMET: <Apenas o capacete>
ARMOR: <Apenas a armadura do tronco/ombros/luvas>
LEGS: <Apenas as perneiras>
BOOTS: <Apenas as botas>
WEAPON: <Apenas a arma>
SHIELD: <Apenas o escudo>
```

### Passo 2: Executar a Geração Automática via CLI
Para gerar sem necessitar de intervenção no navegador, utilize o script de automação ou o comando nativo do projeto:

```bash
# Opção A: Script dedicado da skill
python .agents/skills/tibia-modular-outfit/scripts/auto_forge.py create \
  --prompt "caminho/para/prompt.txt" \
  --look 2000 \
  --output "dist/outfit_2000_modular.zip" \
  --idle 8 --walk 8 --z 2

# Opção B: CLI nativa do New Island Forge
python main.py create \
  --prompt "GERAL: Paladino... BASE: ..." \
  --look 2000 \
  --output "dist/outfit_2000_modular.zip" \
  --idle 8 --walk 8 --z 2
```

O fluxo sequencial (`create_sequential`):
1. Gera a **Base (Y0)** condicionada ao manequim neutro.
2. Gera cada um dos 6 Addons na ordem anatômica: `Helmet -> Armor -> Legs -> Boots -> Shield -> Weapon`.
3. Executa o *congelamento de slots* com verificação SHA256 (`slot_fingerprint`), garantindo que nenhuma peça posterior modifique pixels de peças já aprovadas.

### Passo 3: Validação Automática de Integridade
Antes de importar para o client, valide o pacote gerado:

```bash
python main.py validate "dist/outfit_2000_modular.zip"
```

Critérios verificados automaticamente:
* `ok: true`
* `errors: []`
* `dat_references: 7168` (para 128 poses padrão)
* `body_overlaps: 0` (zero sobreposição indevida entre Helmet, Armor, Legs e Boots)
* Ausência de alpha parcial ($0 < \text{alpha} < 255$).
* Cores da máscara L1 contidas estritamente no conjunto permitido.

---

## 📦 Importação no OTClient / Object Builder / Outfit Studio

O ZIP gerado contém toda a estrutura exigida pelas ferramentas de OTServ:
* `manifest.txt`: Metadados do LookType, grupos, direções e layers.
* `quadros_compostos/`: PNGs $64 \times 64$ organizados por grupo e tipo.
* `sprites_individuais/`: Tiles $32 \times 32$ deduplicados com `sprite_000000.png` transparente.
* `mapa_sprites.csv`: Mapeamento de cada quadro composto para os 4 IDs locais de sprites.
* `validacao.json`: Relatório técnico estrutural.
* `preview.png`: Contact sheet com todas as direções e estados.

### Procedimento no New Island Outfit Studio:
1. Abra o **New Island Outfit Studio**.
2. Vá até a aba **Importar ZIP / Pasta**.
3. Selecione o arquivo `outfit_LOOK_modular.zip`.
4. O Studio aloca os novos IDs de SPR e cria a entrada de DAT automaticamente mantendo os 7 slots.
5. Salve o **SPR** antes de salvar o **DAT**.

---

## 📚 Documentação Complementar

* [Especificação Técnica Completa](./references/outfit_specification.md): Detalhes de coordenadas, quadrantes e contratos de bytes.
* [Modelos de Prompts](./references/prompts_templates.md): Biblioteca de prompts testados para guerreiros, magos, paladinos e arqueiros.
* [Script auto_forge.py](./scripts/auto_forge.py): Utilitário de linha de comando para automação em lote.
