# Como o motor preserva a geometria

A importação lê os quadros 64×64 dos ZIPs fornecidos e normaliza apenas a transparência parcial para alpha binário, necessário ao SPR RGB. Não recorta pelo contorno, não redimensiona a fonte e não troca a origem do quadro. Qualquer entrada com outra dimensão é recusada neste perfil.

O leitor reconhece os nomes `lookID_gGG_fFF_Direcao_Addon_Y_zZ_Base|Mascara.png` e `lookID_gGG_fFF_Direcao_Peca_zZ_LN.png`. Os grupos/tipos vêm das pastas. Todos os frames/direções/Z precisam ter Y0L0. O manifest não substitui a inspeção dos arquivos.

## Receita Golden

O motor executa `data/recipes/reconstruir_quadros.py` com a fonte e os dois assets originais incorporados. A entrada é conferida por impressão digital do FULL. O resultado é comparado pixel a pixel com os 1.792 quadros do v8 antes de ser aceito. Modificar a receita de modo que altere a referência causa erro explícito.

O Golden possui 128 poses, sete linhas e duas camadas: 1.792 quadros e 7.168 referências de tiles. Nenhuma linha é um placeholder vazio.

## Conversão de outro outfit

1. Compõe o FULL de cada pose e apresenta à análise as três linhas antigas e a composição completa. A fonte antiga não é assumida como corpo sem equipamento.
2. Solicita polígonos nativos 64×64 para pele/cabelo e cada equipamento. Addons antigos só são classificados como peças isoladas quando a análise identifica sua natureza. Cada pixel visível recebe um dono único.
3. Copia os pixels das peças identificadas para o mesmo `(x,y)` da fonte. Lacunas nos polígonos são atribuídas à região identificada mais próxima, com anotação quantitativa no relatório. Incerteza grande vira observação para revisão.
4. Solicita à API um corpo reconstruído em roupa simples, sem metal, capacete, arma ou escudo. Apenas pele/cabelo identificados podem ser preservados; Y0 antigo inteiro nunca vira a nova base. A roupa nova usa a área anatômica do corpo e recuo de borda sob armadura.
5. Apresenta a Base isolada ao usuário. Somente após a aprovação humana ela é bloqueada por hash e o fluxo avança.
6. Processa, na ordem, Helmet, Armor, Legs, Boots, Shield e Weapon. Cada componente é mostrado na interface, aprovado pelo usuário e bloqueado antes de iniciar o seguinte; uma etapa não pode alterar slots já bloqueados.
7. Compõe o FULL deterministicamente em Python (`Base + Y1 ... Y6`), sem pedir à IA que reinterprete o conjunto completo.
8. Valida slots, dimensões, alpha, máscaras e peças globalmente vazias. Exporta somente quando a estrutura e todas as aprovações passam. Interseções e peças ocultas são reportadas separadamente.

## Criação por prompt

Usa as silhuetas validadas do Golden como contrato geométrico. Em vez de gerar um FULL para depois tentar separá-lo, cria diretamente a Base e um addon por vez. Cada atlas agrupa as quatro direções por frame para que animação não seja confundida com rotação. A IA fornece cores e desenho, mas a etapa local reconforma o alpha à silhueta do guia; pose diagonal/isométrica, direção, escala e âncora não ficam a critério do modelo. Os componentes aprovados são enviados como contexto visual bloqueado e cada etapa pausa para revisão humana.

A grade rígida é uma exigência enviada à API, não uma garantia matemática de que o modelo desenhará corretamente. Formato/dimensões são verificados; anatomia, coerência de animação, segmentação e detalhes artísticos exigem inspeção das prévias. O aplicativo permite editar PNGs nativos sem alterar outros frames.

## Saída

Os quatro tiles são extraídos diretamente dos quadrantes fixos `(32,32)`, `(0,32)`, `(32,0)`, `(0,0)`, em ordem DAT. A exportação é atômica e inclui um mapa CSV que permite reconstruir cada quadro com os mesmos pixels. SPR IDs reais e metadados DAT ficam a cargo do editor fornecido pelo usuário.
