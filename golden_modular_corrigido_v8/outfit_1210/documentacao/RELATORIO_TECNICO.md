# Golden modular v8 — reconstrução e validação

## Materiais analisados

| Entrada fornecida | Função nesta revisão |
|---|---|
| `outfit_goldenset_antigo(6).zip` | Fonte dos pixels, das poses e das âncoras do Golden 1210. |
| `demonhunter(2).zip` | Comparação do esquema de exportação do outfit 289: direções, Z, layers e grupos. |
| `golden_modular_documented_v7(5).zip` | Diagnóstico dos recortes e dos addons vazios. |
| `newisland_outfit_studio_v3_2(3).zip` | Código do importador, divisão dos tiles e leitores/escritores SPR/DAT usados nos testes. |

O Golden antigo tem 768 quadros: dois grupos, oito frames em cada, quatro
direções, três valores Y, dois valores Z e dois layers. O Demonhunter tem
432 quadros; o primeiro grupo tem um frame, o segundo tem oito. Seu manifest
lista nomes modulares, mas os PNGs fornecidos contêm somente três linhas Y.
Esses nomes não demonstram que haja seis equipamentos separados.

## Problemas identificados no v7

Os 1.792 quadros do v7 já têm 64×64; o problema observado nesses arquivos não
é simplesmente a dimensão do canvas. Armor/Legs dividem partes do corpo por
faixas horizontais que cortam a couraça. Weapon/Shield são transparentes em
todas as poses. A base conserva a aparência dos relevos da armadura e a
separação das botas por componente mais baixo não resolve todas as poses.

Na caminhada, há componentes que reúnem luva e bota, e há fragmentos de bota
sem pixels de máscara colorida. Portanto, separar somente por componente
conectado ou somente pela posição vertical perde a identidade da peça.

## Reconstrução

1. Preservação integral da matriz 64×64 de cada estado. Os pixels antigos
   mantêm suas coordenadas e cores; não há recorte do bounding box seguido de
   recentralização, redimensionamento ou normalização da silhueta.
2. Helmet usa diretamente o antigo Addon 2.
3. Máscaras originais do Addon 1 identificam mãos e pés. Componentes que
   contêm ambas as marcações são separados pela distância aos pixels marcados;
   fragmentos sem marcação são classificados pela região anatômica.
4. Couraça e perneiras usam contornos curvos por direção/variação, acompanhando
   o deslocamento da cabeça na pose. As mangas têm contornos próprios.
5. Cada pixel visível da armadura tem um único dono entre Helmet, Armor,
   Legs e Boots. As outras peças não repintam a região do capacete, que está
   antes delas na ordem Y.
6. A Base mantém cabelo, rosto e pele das mãos. A roupa foi reconstruída com
   uma silhueta interna, paleta de tecido azul, calça escura e calçado de couro.
   O sombreado da roupa não reutiliza o relevo metálico do Golden.
7. Weapon e Shield são novas artes: espada e broquel gerados com a ferramenta
   integrada de imagem, convertidos para footprints de 7×19 e 9×10 pixels,
   com alpha binário, e ancorados nas mãos. A espada é orientada conforme a
   direção. O posicionamento respeita a área de 64×64 e a oclusão da cabeça.
   Esse preparo das artes novas não redimensiona os pixels do Golden original.

A separação não tenta recuperar uma anatomia original inexistente sob a
armadura; a roupa simples é uma reconstrução. No esquema de overlays Y0..Y6,
desenhar a perneira por cima da couraça e esperar que desapareça quando Armor
for ativada não funciona sem outra regra de composição. Aqui as peças mantêm
regiões visíveis disjuntas, adequadas à ordem de pintura existente.

## Estrutura e ordem

| Parâmetro | Valor |
|---|---|
| Grupos | G1 type 00 e G2 type 01 |
| Frames | 8 por grupo |
| Tile / quadro | 32×32 / 64×64 |
| Width / Height | 2 / 2 |
| Layers | 2 |
| Pattern X / Y / Z | 4 / 7 / 2 |
| Referências por grupo / total | 3.584 / 7.168 |
| Quadros PNG | 1.792 |
| Alpha | Somente 0 ou 255 |

O código do editor usa `px=(width-w-1)*32` e `py=(height-h-1)*32`.
Logo, os quatro tiles seguem: inferior direito, inferior esquerdo, superior
direito e superior esquerdo. O manifest e o CSV registram essa mesma ordem.
IDs locais são deduplicados por hash dos pixels RGBA. O ID local zero
representa transparência. O importador não interpreta esses IDs como SPR IDs
do cliente; ele importa os quadros e cria novas referências.

## Evidências de teste

Os valores completos estão em `validacao.json`.

- 128 poses: 2 grupos × 8 frames × 4 direções × 2 Z.
- Igualdade RGBA exata entre o Golden antigo completo e a reconstrução com
  Helmet, Armor, Legs e Boots sobre a nova Base, em todas as poses.
- Zero interseções de alpha entre os quatro equipamentos corporais.
- Capacete idêntico ao Addon 2 original em todas as poses.
- Todos os seis addons têm conteúdo visível em todas as poses.
- 64 combinações por pose exercitadas automaticamente, verificando a
  composição e a preservação da cobertura da Base. Isso não significa uma
  avaliação artística individual de todas as 8.192 imagens.
- Análise, importação, escrita SPR/DAT e reabertura pelas classes reais do
  editor enviado; todos os 1.792 quadros reconstruídos permaneceram idênticos.
- Importação como novo LookType e substituição de um LookType existente.
- Preservação dos metadados de animação existentes no teste de substituição.
- Conferência dos quatro tiles individuais contra cada quadro composto.
- Revisão visual dos painéis de Base, Armor, Legs e conjunto completo nas
  quatro direções e nos oito frames de caminhada, em Z0 e Z1.

## Limites da verificação

Não foi fornecido o Tibia.dat/Tibia.spr real do cliente, nem o código de seu
renderer. O teste usa arquivos temporários sintéticos produzidos pelo editor.
Não comprova a execução dentro do OTCv8/servidor nem altera sua configuração.

O pacote PNG não contém as durações originais de cada frame, displacement ou
as flags completas do DAT. O importador do Studio tenta reaproveitar esses
dados do LookType existente/de origem; quando não existem metadados de
animação, ele aplica sua rotina de geração padrão. Por isso, o relatório
afirma igualdade dos quadros e preservação do esquema observado, sem inventar
metadados que não vieram nos anexos.

## Reprodução dos quadros

Instale as dependências de `requirements.txt` e execute
`python reconstruir_quadros.py` dentro de `documentacao`.
O script lê o ZIP original incluído e os dois assets novos já preparados.
Regrava `quadros_compostos`, `coordenadas_poses.json` e painéis de diagnóstico.
Depois de alterar contornos ou assets, importe novamente os quadros no Studio;
as prévias HTML/GIF, o manifest e os relatórios desta entrega representam a
versão verificada e não são atualizados por esse script de reconstrução.

Prompt usado na geração das peças novas: “Transparent pixel-art equipment
sheet for a classic Tibia-like 32×32 game; exactly two isolated objects:
short steel sword with gold crossguard and brown grip, and a small golden
round buckler with silver boss; hard pixel edges, dark outline, limited
palette; sword final footprint about 7×19, shield about 11×12; no character,
text or exterior shadows.” Modo: ferramenta de imagem integrada. O broquel
foi preparado em 9×10 para caber nas poses extremas sem deslocar o personagem.

Testes finais adicionais: 1.792 quadros foram reproduzidos em uma pasta independente pelo script distribuído, com igualdade exata. A lógica da prévia HTML foi executada em JavaScript com DOM simulado e canvas nativo: igualdade dos dois canvases em 128 poses com os quatro equipamentos corporais; botões, seleção e animação passaram. Não havia navegador instalado para validar visualmente a página completa.
