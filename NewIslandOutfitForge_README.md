# 🏝️ New Island Outfit Forge

> **Editor, analisador e laboratório para criação de outfits modulares do New Island / Tibia OTServ.**
>
> Estado deste commit: **v1.0 — fundação técnica funcional, geração/conversão artística por IA ainda experimental.**

---

## 📌 Objetivo do projeto

O **New Island Outfit Forge** foi criado para transformar o trabalho de edição de outfits em um fluxo organizado, reproduzível e compatível com o padrão modular usado no New Island.

O formato alvo é:

```text
Base
+ Helmet
+ Armor
+ Legs
+ Boots
+ Weapon
+ Shield
```

Cada peça deve existir de forma **independente**, manter a mesma pose/âncora do personagem e poder ser ligada ou desligada sem quebrar o restante do outfit.

O projeto também serve como uma oficina para:

- importar outfits antigos;
- visualizar FULL e peças isoladas;
- editar pixels manualmente;
- criar ou reconstruir sprites com IA;
- validar estrutura e transparência;
- gerar um ZIP pronto para o **New Island Outfit Studio**;
- reproduzir o **Golden Modular v8**, nossa principal referência técnica validada.

---

# 🚦 Estado atual

| Área | Estado | Observação |
|---|---:|---|
| Leitura de ZIP de outfit | ✅ Funcional | Suporta estrutura antiga e modular reconhecida pelo Forge |
| Estrutura modular Base + 6 addons | ✅ Funcional | Pattern Y = 7 |
| Reprodução do Golden v8 | ✅ Validada | Reprodução determinística e comparação pixel a pixel |
| Exportação para o Outfit Studio | ✅ Funcional | Estrutura reconhecida pelo importador do Studio |
| Editor de pixels | ✅ Funcional | L0/L1, pincel, borracha, conta-gotas, desfazer e PNG |
| Prévia de combinações | ✅ Funcional | Permite ligar/desligar as sete partes |
| Animação de frames | ✅ Funcional | Grupo, direção, frame, Z e FPS |
| Projetos locais | ✅ Funcional | Importações/resultados podem ser reabertos |
| Cache das chamadas de IA | ✅ Funcional | Reaproveita requisições idênticas |
| CLI | ✅ Funcional | inspect, validate, golden, convert e create |
| Conversão automática de qualquer outfit | ⚠️ Experimental | Estrutura funciona; separação artística ainda não é confiável |
| Criação completa por prompt | ⚠️ Experimental | Pode gerar bons frames, mas perde consistência entre peças/poses |
| Separação semântica Armor/Legs/Boots | ⚠️ Principal problema atual | A IA pode colocar pixels na peça errada |
| Reconstrução automática da Base | ⚠️ Precisa mudar | Hoje tenta reconstruir a base a partir do FULL |
| Montaria / Z1 gerada por IA | ⚠️ Precisa validação forte | Geometria pode variar entre frames |
| Máscaras L1 geradas automaticamente | ⚠️ Limitado | Na geração genérica podem ficar vazias |
| Validação artística automática | ❌ Não resolvida | O programa valida formato, não entende perfeitamente a identidade de cada pixel |
| Fluxo peça por peça com aprovação | ❌ Próxima prioridade | Deve substituir o modelo “faça tudo de uma vez” |

---

# 🥇 O Golden é a nossa referência técnica

O arquivo **Golden Modular v8** não deve ser tratado apenas como um outfit bonito. Ele é o nosso **contrato técnico de funcionamento**.

Ele define e valida:

```text
geometria
âncoras
tamanho dos quadros
ordem das direções
Pattern Y
Pattern Z
Layers
posição das peças
montagem dos tiles
composição dos addons
```

### Estrutura Golden validada

| Propriedade | Valor |
|---|---:|
| Quadro composto | 64 × 64 px |
| Tile | 32 × 32 px |
| Width × Height | 2 × 2 |
| Layers | 2 |
| Pattern X | 4 direções |
| Pattern Y | 7 partes |
| Pattern Z | 2 |
| Grupos | 2 |
| Frames por grupo | 8 |
| Poses | 128 |
| Quadros PNG | 1.792 |
| Referências DAT | 7.168 |
| Alpha | 0 ou 255 |

Mapeamento:

```text
Y0 = Base
Y1 = Helmet
Y2 = Armor
Y3 = Legs
Y4 = Boots
Y5 = Weapon
Y6 = Shield
```

A reprodução Golden existente no aplicativo é **determinística**. Ela não depende da IA para reconstruir o resultado validado.

> **Regra importante:** Golden é referência de estrutura, proporção, âncora e modularidade. Não significa que todos os outfits novos devem usar a aparência da armadura Golden.

---

# ✅ O que já existe no aplicativo

## 1. Interface local no navegador

O Forge roda em Python e abre uma interface web local.

Não exige:

- Node.js;
- Electron;
- banco de dados;
- servidor externo;
- extensão de navegador.

O backend fica em `127.0.0.1` e a interface usa HTML/CSS/JavaScript local.

---

## 2. Importação de outfit

O leitor reconhece os quadros e reconstrói a estrutura lógica do outfit.

Atualmente o programa trabalha com nomes semelhantes a:

```text
look1210_g01_f00_Sul_Addon_0_z0_Base.png
look1210_g01_f00_Sul_Addon_0_z0_Mascara.png
```

E também aceita o formato antigo por peça:

```text
look1457_g01_f00_Sul_Base_z0_L0.png
look1457_g01_f00_Sul_Armor_z0_L0.png
look1457_g01_f00_Sul_Helmet_z0_L0.png
```

### Atenção

Os nomes antigos como `Armor` ou `Helmet` **não são considerados prova de que a imagem contém somente aquela peça**.

Esse aprendizado é importante porque outfits antigos podem ter:

```text
Armor contendo parte de Legs
Legs contendo parte da Boots
Base ainda “contaminada” pela armadura
Addon misturando mais de um equipamento
```

---

## 3. Reprodução offline do Golden

Existe um fluxo exclusivo para o Golden:

```text
fonte Golden antiga
        ↓
receita determinística
        ↓
Golden modular
        ↓
comparação com Golden v8
```

Se qualquer quadro divergir da referência incorporada, a reprodução é rejeitada.

Isso é diferente da conversão genérica com IA.

---

## 4. Prévia modular

A interface permite selecionar:

- grupo;
- direção;
- Pattern Z;
- frame;
- FPS;
- peças ligadas/desligadas.

Combinações rápidas:

```text
Só Base
Armadura completa
Todos
```

Também é possível visualizar individualmente:

```text
Base
Helmet
Armor
Legs
Boots
Weapon
Shield
```

---

## 5. Editor de pixels

Já existe edição manual de sprites 64 × 64.

Recursos atuais:

- pincel;
- borracha;
- conta-gotas;
- tamanho do pincel;
- edição do L0;
- edição do L1;
- desfazer traços;
- desfazer edição aplicada;
- importar PNG;
- exportar PNG;
- salvar somente a pose/peça/camada atual.

### Máscara L1

As cores aceitas são:

```text
Amarelo  #FFFF00
Vermelho #FF0000
Verde    #00FF00
Azul     #0000FF
```

A máscara não pode existir fora da área visível da peça.

---

## 6. Projetos e persistência

O aplicativo salva automaticamente projetos locais.

Isso permite:

- importar uma fonte;
- fechar o aplicativo;
- reabrir o projeto;
- continuar a edição;
- preservar o resultado modular atual.

O cache da IA também é persistido por hash da requisição.

---

## 7. Exportação

O ZIP modular contém, entre outros:

```text
outfit_ID/
├── manifest.txt
├── LEIA_PRIMEIRO.txt
├── preview.png
├── validacao.json
├── forge_project.json
├── SHA256SUMS.txt
├── mapa_sprites.csv
├── quadros_compostos/
└── sprites_individuais/
```

Os quatro tiles são extraídos na ordem usada pelo formato DAT:

```text
1. inferior direito
2. inferior esquerdo
3. superior direito
4. superior esquerdo
```

Tiles idênticos são deduplicados por hash.

---

# 🧠 Como a IA funciona atualmente

Existem hoje **dois fluxos diferentes de IA**.

---

## Fluxo A — Converter outfit antigo

Hoje a conversão genérica faz aproximadamente isto:

```text
OUTFIT ANTIGO
     ↓
monta FULL de cada pose
     ↓
IA analisa regiões visuais
     ↓
cria polígonos para:
Helmet / Armor / Legs / Boots / Weapon / Shield / pele
     ↓
atribui cada pixel visível a uma peça
     ↓
reconstrói uma Base sem armadura
     ↓
gera peças que estiverem ausentes
     ↓
executa revisão visual amostral
     ↓
validação estrutural
     ↓
ZIP modular
```

Para cada pose, a análise recebe uma prancha contendo:

```text
Y0 antigo | Y1 antigo | Y2 antigo | FULL
```

O sistema tenta identificar semanticamente a função dos pixels.

### Fallback atual

Quando existem pixels visíveis que a IA não classificou, o motor atribui esses pixels à **região classificada mais próxima**.

Isso evita buracos, porém pode causar uma classificação semanticamente errada.

Exemplo:

```text
pixel visualmente próximo da Legs
mas que na verdade pertence à Boots
```

O resultado pode continuar tecnicamente válido e mesmo assim estar artisticamente errado.

---

## Fluxo B — Criar outfit por prompt

Hoje a criação nova funciona assim:

```text
prompt
  ↓
Golden convertido em guia neutro de pose
  ↓
IA cria personagem FULL equipado
  ↓
frames são reduzidos para 64 × 64
  ↓
o FULL recém-criado passa pela mesma conversão genérica
  ↓
Base + 6 peças
```

A geração usa atlas 4 × 4 com até 16 poses por imagem.

Cada célula é ampliada durante a geração e depois convertida para o quadro nativo 64 × 64 usando vizinho mais próximo.

---

# ⚠️ Problema central descoberto

## O fluxo atual tenta resolver coisas demais de uma vez

Criar um FULL e depois pedir para a IA separar tudo novamente parece simples, mas é um problema muito difícil.

A IA precisa decidir ao mesmo tempo:

```text
anatomia
pose
perspectiva
pixel art
oclusão
identidade da peça
profundidade
movimento
posição da mão
posição do pé
montaria
reconstrução de partes escondidas
```

É por isso que encontramos erros como:

- Legs trazendo pedaço da Boots;
- Boots incompleta;
- Armor invadindo Legs;
- couraça cortada;
- Weapon deslocada;
- Shield trocado ou mal posicionado;
- base maior ou menor que a referência;
- frames visualmente diferentes entre si;
- Z1/montaria inconsistente;
- peça correta em alguns frames e errada em outros.

---

# ❗ A validação atual não detecta todos esses erros

O Forge já verifica muito bem a **estrutura**.

Exemplos:

```text
✓ arquivo existe
✓ 64 × 64
✓ RGBA
✓ alpha binário
✓ máscara válida
✓ todos os slots existem
✓ peça não está globalmente vazia
✓ pacote pode ser remontado
✓ tiles podem ser reconstruídos
```

Também calcula interseção de alpha entre:

```text
Helmet
Armor
Legs
Boots
```

Porém isso **não é uma validação semântica**.

Exemplo:

```text
Legs contém 3 pixels da bota
Boots não contém esses 3 pixels
```

Não há interseção.

Estruturalmente pode passar.

Artisticamente está errado.

Esse é um dos principais pontos que a próxima versão precisa resolver.

---

# 🎯 Nova direção do projeto

A conclusão desta fase é:

> **O Forge não deve tentar ser um botão mágico “converter tudo”. Ele deve ser uma linha de montagem inteligente de outfits modulares.**

O fluxo principal deverá mudar de:

```text
Importar
  ↓
IA faz tudo
  ↓
Resultado final
```

para:

```text
Importar referências
        ↓
Escolher / validar Base
        ↓
Criar Helmet
        ↓
VALIDAR E CONGELAR
        ↓
Criar Armor
        ↓
VALIDAR E CONGELAR
        ↓
Criar Legs
        ↓
VALIDAR E CONGELAR
        ↓
Criar Boots
        ↓
VALIDAR E CONGELAR
        ↓
Criar Weapon
        ↓
VALIDAR E CONGELAR
        ↓
Criar Shield
        ↓
VALIDAR E CONGELAR
        ↓
Full Set
        ↓
Teste final
```

---

# 🧱 Regra nova: Base primeiro

A Base é a fundação do outfit.

Ela **não deve ser recriada automaticamente se já existir uma base validada adequada**.

Vamos trabalhar com uma biblioteca de bases aprovadas.

Exemplo já identificado para evolução do projeto:

```text
Base validada: outfit 1245
Golden: referência técnica
1457 Crown: referência visual do equipamento
```

Isso significa:

```text
Golden
  → estrutura / regra / geometria

1245
  → corpo/base validada

1457
  → aparência do Crown Set
```

Esses papéis não devem ser misturados.

---

# 🧩 Tipos de referência

A próxima versão deve diferenciar explicitamente três categorias.

## 1. Base validada

É o corpo sobre o qual os equipamentos serão construídos.

Exemplo:

```text
outfit 1245
```

Deve conter poses corretas e ser aprovada antes de qualquer addon.

---

## 2. Outfit de referência visual

Pode ser antigo, misturado ou não modular.

Exemplos:

```text
Crown 1457
Demonhunter
outros outfits clássicos
```

Serve para responder:

```text
Como é o capacete?
Como é a couraça?
Qual é a paleta?
Qual é o formato da bota?
Qual é a arma?
```

Não deve ser considerado automaticamente uma separação correta.

---

## 3. Template modular validado

O Golden v8 é o principal exemplo atual.

Serve para demonstrar:

```text
como a estrutura deve funcionar
como os addons são independentes
como frames e direções são preservados
como Z0/Z1 são organizados
como exportar
```

---

# 🔒 Conceito de “peça congelada”

Quando uma peça for aprovada, ela deve receber estado:

```text
APPROVED / LOCKED
```

A partir desse momento, gerar ou corrigir outra peça **não pode modificar a peça já aprovada**.

Exemplo:

```text
Base    ✅ APROVADA 🔒
Helmet  ✅ APROVADO 🔒
Armor   ✅ APROVADA 🔒
Legs    🟡 EM REVISÃO
Boots   ⚪ NÃO INICIADA
Weapon  ⚪ NÃO INICIADA
Shield  ⚪ NÃO INICIADA
```

Isso resolve um problema recorrente:

> corrigir a bota e, sem querer, alterar a Armor que já estava boa.

---

# 🛠️ O que precisamos corrigir

## P0 — Redesenhar o workflow de criação/conversão

**Prioridade máxima.**

### Hoje

```text
FULL → separação automática completa
```

### Desejado

```text
Base → Helmet → Armor → Legs → Boots → Weapon → Shield
```

Cada estágio deve permitir:

- gerar;
- visualizar;
- comparar;
- editar;
- aprovar;
- congelar;
- refazer apenas aquela peça.

---

## P0 — Biblioteca de Bases

Adicionar uma área própria:

```text
Bases validadas
├── 1245
├── Golden Base
└── futuras bases
```

O usuário deve poder escolher:

```text
[ Usar base existente ]
[ Importar nova base ]
[ Criar nova base ]
```

Uma base importada/criada só deve entrar na biblioteca depois de validação.

---

## P0 — Deixar de criar FULL primeiro

Para criação por prompt, o processo atual é:

```text
FULL completo
→ tentar separar
```

O novo processo deve ser:

```text
Base
→ Helmet isolado
→ Armor isolada
→ Legs isolada
→ Boots isolada
→ Weapon isolada
→ Shield isolado
→ composição final
```

Isso reduz drasticamente a necessidade de adivinhar regiões escondidas.

---

## P0 — Validação manual obrigatória entre etapas

Antes de avançar:

```text
[ APROVAR PEÇA ]
```

O programa não deverá considerar a peça concluída apenas porque:

```text
64 × 64 = OK
alpha = OK
arquivo = OK
```

A aprovação visual é necessária.

---

## P1 — Comparador visual lado a lado

A interface deve mostrar simultaneamente:

```text
┌────────────────┬────────────────┬────────────────┐
│ REFERÊNCIA     │ BASE           │ RESULTADO      │
│ outfit antigo │ base validada  │ peça atual     │
└────────────────┴────────────────┴────────────────┘
```

E permitir zoom alto sem suavização.

---

## P1 — Editor por peça e por pose

O erro precisa ser identificável de forma exata.

Exemplo:

```text
Projeto: Crown
Peça: Boots
Grupo: G2
Direção: Leste
Frame: 03
Z: 1
Layer: 0
```

Isso é melhor que apenas dizer:

```text
“alguma bota está errada”
```

---

## P1 — Navegação de erros

Criar painel:

```text
Problemas detectados

[!] Armor / G2 / Sul / F05 / Z0
[!] Legs  / G2 / Leste / F03 / Z1
[!] Boots / G1 / Norte / F00 / Z1
```

Clique no erro → abre diretamente a pose no editor.

---

## P1 — Melhor validação semântica

Adicionar verificações que ajudem a identificar contaminação.

Exemplos:

- perfil anatômico esperado por peça;
- faixa relativa ao corpo, sem transformar isso em regra absoluta;
- comparação com frames vizinhos;
- variação brusca de área de uma mesma peça;
- mudança brusca do bounding box;
- pixel isolado distante do restante da peça;
- componente desconectado suspeito;
- Boots avançando para região típica da coxa;
- Legs contendo fragmentos que acompanham o pé;
- Helmet desconectado da cabeça;
- Weapon sem proximidade com a mão;
- Shield sem proximidade com a mão esperada.

Esses testes devem produzir **alertas**, não apagar pixels automaticamente.

---

## P1 — Consistência temporal entre frames

Uma peça não deve mudar de design a cada frame.

Precisamos comparar:

```text
Frame 0 → Frame 1 → Frame 2 → ...
```

Detectar:

- mudança exagerada de tamanho;
- mudança de paleta;
- desaparecimento inesperado;
- troca de lado;
- deslocamento da âncora;
- detalhes que surgem e somem sem motivo.

---

## P1 — Z0 e Z1 como requisitos independentes

A montaria não pode ser um detalhe opcional.

Uma peça só estará aprovada quando passar por:

```text
Z0 ✅
Z1 ✅
```

Se o outfit tiver Pattern Z = 2.

---

## P2 — Melhorar o uso da IA

A IA deve ser usada principalmente para:

```text
analisar referência
entender identidade visual
propor reconstrução
criar uma única peça
reparar uma única pose
revisar inconsistências
```

E não para controlar tarefas determinísticas.

Python continuará responsável por:

```text
corte
composição
nomes
estrutura
64 × 64
alpha
layers
tiles
hashes
ZIP
manifest
persistência
```

---

## P2 — Geração de peça usando contexto controlado

Ao gerar Armor, a IA deveria receber apenas o necessário:

```text
Base validada
+
referência Crown
+
Armor já aprovada de frames vizinhos
+
pose atual
```

E a instrução:

```text
GERAR SOMENTE ARMOR
```

O mesmo para cada peça.

---

## P2 — Reparação localizada

Adicionar ação:

```text
[ Corrigir somente este frame ]
```

A correção deve preservar todos os outros frames.

Idealmente:

```text
frame anterior
frame atual
frame seguinte
referência visual
```

serão usados para reconstruir apenas a região problemática.

---

## P2 — Versionamento interno

Cada aprovação deveria gerar uma versão.

Exemplo:

```text
Base v1
Helmet v1
Armor v1
Armor v2
Legs v1
```

Com possibilidade de retornar à versão anterior.

---

# 📦 Modelo de projeto desejado

Uma evolução de `forge_project.json` pode registrar algo semelhante a:

```json
{
  "version": 2,
  "look": 1457,
  "name": "Crown Modular",
  "references": {
    "technical_template": "golden_v8",
    "base": "outfit_1245",
    "visual_source": "outfit_1457"
  },
  "stages": {
    "Base":   { "status": "approved", "locked": true,  "version": 1 },
    "Helmet": { "status": "approved", "locked": true,  "version": 1 },
    "Armor":  { "status": "review",   "locked": false, "version": 2 },
    "Legs":   { "status": "pending",  "locked": false, "version": 0 },
    "Boots":  { "status": "pending",  "locked": false, "version": 0 },
    "Weapon": { "status": "pending",  "locked": false, "version": 0 },
    "Shield": { "status": "pending",  "locked": false, "version": 0 }
  }
}
```

---

# ✅ Definition of Done de uma peça

Uma peça só pode ser considerada **aprovada** quando:

- [ ] existe em todos os grupos necessários;
- [ ] existe em todas as direções;
- [ ] existe em todos os frames;
- [ ] existe em todos os Pattern Z necessários;
- [ ] mantém 64 × 64;
- [ ] mantém a âncora correta;
- [ ] possui alpha binário;
- [ ] não contém pixels óbvios de outra peça;
- [ ] funciona isoladamente;
- [ ] funciona sobre a Base;
- [ ] funciona com as peças já aprovadas;
- [ ] não altera peças bloqueadas;
- [ ] mantém design coerente entre frames;
- [ ] foi visualmente aprovada.

---

# 🧪 Testes deste commit

No estado atual do projeto existem **26 testes automatizados**.

Neste commit, eles passam no ambiente Linux usado para revisão:

```text
Ran 26 tests
OK
```

Cobrem, entre outros:

- reprodução Golden;
- round-trip de pacote;
- quadrantes e hashes;
- leitura de exemplos antigos;
- validações de segurança;
- contratos HTTP simulados;
- cache;
- cancelamento;
- criação/conversão com fixtures;
- servidor local;
- edição e undo;
- persistência de projetos;
- exportação.

### O que esses testes NÃO comprovam

Eles não comprovam que uma geração da IA está artisticamente correta.

Também não substituem:

```text
teste visual
+
teste no Outfit Studio
+
teste no OTClient
```

---

# 🧪 Níveis de validação

A partir de agora vamos tratar três níveis separados.

## Nível 1 — Estrutural

```text
arquivo
dimensões
alpha
layers
slots
nomes
tiles
ZIP
```

Pode ser totalmente automatizado.

## Nível 2 — Visual/Semântico

```text
Armor é realmente Armor?
Legs contém bota?
Boots está completa?
Weapon está na mão?
Helmet acompanha a cabeça?
```

Pode receber ajuda automática, mas precisa de revisão.

## Nível 3 — Cliente

```text
importou no Studio?
carregou no DAT/SPR?
anima corretamente?
combinações funcionam no OTClient?
```

É a validação final.

---

# 🗂️ Estrutura atual do código

```text
NewIslandOutfitForge/
├── main.py
├── README.md
├── requirements.txt
├── requirements-build.txt
├── NewIslandOutfitForge.spec
│
├── ni_forge/
│   ├── core.py
│   ├── ai.py
│   ├── workflows.py
│   └── server.py
│
├── static/
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   └── logo.svg
│
├── data/
│   ├── references/
│   │   ├── golden_modular_v8.zip
│   │   ├── antigo_1457.zip
│   │   └── demonhunter_289.zip
│   └── recipes/
│       └── reconstruir_quadros.py
│
├── docs/
│   ├── PROCESSO.md
│   ├── VALIDACAO.md
│   ├── RESULTADOS_TESTES.txt
│   └── COMPATIBILIDADE_STUDIO.json
│
└── tests/
    ├── test_app.py
    └── verify_studio.py
```

---

# 🧭 Responsabilidade de cada módulo

## `ni_forge/core.py`

Responsável por tarefas determinísticas:

- estrutura `Outfit`;
- leitura do ZIP;
- composição;
- validação;
- exportação;
- criação de tiles;
- deduplicação;
- contact sheet;
- conversão de atlas gerado para 64 × 64.

## `ni_forge/ai.py`

Responsável por:

- conexão com provedor de IA;
- análise visual estruturada;
- geração/edição de imagens;
- cache;
- timeout;
- limite de chamadas;
- tratamento de erros.

## `ni_forge/workflows.py`

Responsável pelos fluxos de alto nível:

```text
reproduce_golden()
analyze()
create_prompt_source()
convert_ai()
```

É aqui que está a maior parte da lógica que precisará ser refatorada na próxima fase.

## `ni_forge/server.py`

Responsável por:

- servidor local;
- estado da sessão;
- projetos;
- endpoints;
- tarefas em background;
- importação/exportação;
- integração com a interface.

## `static/`

Interface do editor.

---

# ▶️ Executar atualmente

## Windows

```text
INICIAR_WINDOWS.bat
```

Na primeira execução, o aplicativo cria o ambiente virtual e instala as dependências.

## Linux/macOS

```bash
bash INICIAR_LINUX_MAC.sh
```

Ou manualmente:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

---

# ⌨️ CLI atual

```bash
python main.py golden --output golden_modular.zip
python main.py inspect outfit.zip
python main.py validate outfit_modular.zip
python main.py convert antigo.zip --output convertido.zip --look 2001
python main.py create --prompt "Cavaleiro com espada e escudo" --look 2002 --output novo.zip
python -m unittest discover -s tests -v
```

---

# 🏗️ Build para Windows

O projeto já possui configuração PyInstaller.

```text
GERAR_EXE_WINDOWS.bat
```

Saída esperada:

```text
dist/NewIslandOutfitForge/NewIslandOutfitForge.exe
```

Distribuir a pasta inteira de `dist`, e não somente o `.exe`.

---

# 🔐 Segurança atual

O aplicativo já possui algumas proteções importantes:

- servidor local;
- token de sessão para chamadas da interface;
- verificação de origem;
- limite de tamanho das imagens;
- limite do ZIP na interface;
- proteção contra path traversal na importação;
- chave de API não gravada junto dos projetos;
- endpoint HTTP externo recusado, exceto localhost;
- limites de chamadas e timeout configuráveis.

---

# 📋 Roadmap proposto

## v1.1 — Workflow guiado

- [ ] adicionar estados `pending / review / approved / locked`;
- [ ] implementar Base como primeira etapa;
- [ ] aprovar/congelar peças;
- [ ] refazer apenas uma peça sem tocar nas demais;
- [ ] permitir selecionar Base de referência;
- [ ] adicionar outfit 1245 como primeira base validada do catálogo;
- [ ] separar referência técnica, base e referência visual.

## v1.2 — Ferramentas de revisão

- [ ] comparação lado a lado;
- [ ] diff visual;
- [ ] heatmap de diferença;
- [ ] alertas de componentes desconectados;
- [ ] navegação direta para poses suspeitas;
- [ ] métricas de bounding box por frame;
- [ ] consistência de área/paleta entre frames;
- [ ] validação dedicada Z0/Z1.

## v1.3 — IA peça por peça

- [ ] gerar somente Helmet;
- [ ] gerar somente Armor;
- [ ] gerar somente Legs;
- [ ] gerar somente Boots;
- [ ] gerar somente Weapon;
- [ ] gerar somente Shield;
- [ ] usar peças aprovadas como referências de continuidade;
- [ ] permitir reparação de um único frame;
- [ ] impedir alteração das peças bloqueadas.

## v1.4 — Criação nova confiável

- [ ] criar/selecionar Base antes dos equipamentos;
- [ ] deixar de gerar FULL como primeira etapa;
- [ ] prompt específico por peça;
- [ ] revisão obrigatória antes de avançar;
- [ ] presets de estilo/paleta;
- [ ] biblioteca reutilizável de bases.

## v2.0 — Linha de montagem modular

Objetivo:

```text
Referências
    ↓
Base validada
    ↓
6 peças aprovadas individualmente
    ↓
validação automática + humana
    ↓
Full Set
    ↓
Studio
    ↓
OTClient
```

---

# 🚫 O que não devemos fazer novamente

Para evitar regressões, ficam registradas algumas decisões deste ciclo.

### Não assumir que o nome do addon antigo define seu conteúdo

```text
“Armor” no nome ≠ Armor isolada garantida
```

### Não usar a Base antiga automaticamente

Ela pode conter roupa/armadura já incorporada.

### Não redimensionar/recentralizar pixels antigos classificados corretamente

Coordenadas originais devem ser preservadas.

### Não considerar “carregou no cliente” igual a “ficou correto”

São critérios diferentes.

### Não corrigir uma peça regenerando o outfit inteiro

Peças aprovadas devem permanecer congeladas.

### Não confiar somente na validação estrutural

Um arquivo pode ser tecnicamente válido e artisticamente incorreto.

### Não gerar um FULL novo primeiro quando o objetivo final já é modular

Criar modular desde a origem é mais confiável.

---

# 💡 Princípio técnico do projeto

A responsabilidade deve ser dividida assim:

```text
IA
│
├── análise visual
├── entendimento de referência
├── criação/reconstrução artística
└── revisão assistida

Python
│
├── geometria
├── arquivos
├── 64 × 64
├── tiles
├── layers
├── alpha
├── composição
├── hashes
├── exportação
└── persistência

Golden
│
└── contrato técnico de modularidade

Base validada
│
└── anatomia / pose / âncora

Humano
│
└── aprovação artística final
```

---

# 🏁 Resumo deste commit

A v1.0 já possui uma **base técnica forte**:

```text
✅ editor local
✅ importação
✅ exportação
✅ pixel editor
✅ projetos
✅ cache
✅ CLI
✅ validação estrutural
✅ Golden reproduzível
✅ integração offline testada com o Studio
```

O principal trabalho daqui para frente não é reescrever tudo.

É **substituir o workflow artístico automático por um fluxo guiado, peça por peça e com aprovação**, preservando o que já funciona.

Em uma frase:

> **O motor de arquivos está no caminho certo. O que precisa amadurecer é o processo de criação visual.**

---

## New Island Outfit Forge

**Objetivo final:** transformar criação de outfit modular em um processo previsível, revisável e reutilizável — sem depender de uma única geração “perfeita” da IA.
