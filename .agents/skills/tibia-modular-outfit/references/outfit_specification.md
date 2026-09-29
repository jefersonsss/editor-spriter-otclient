# Especificação Técnica do Sistema Modular de Outfits (New Island / OTClient)

Este documento define os contratos matemáticos, anatômicos e de arquivos para outfits modulares com 1 Base e 6 Addons (`Pattern Y = 7`).

---

## 1. Geometria e Formato de Exportação

| Propriedade | Valor | Detalhes |
|---|---:|---|
| **Quadro Composto** | $64 \times 64\text{ px}$ | Tela nativa de trabalho de cada pose |
| **Tiles Individuais** | $32 \times 32\text{ px}$ | Divisão padrão do motor de renderização Tibia/OTClient ($2 \times 2$ tiles) |
| **Width × Height** | $2 \times 2$ | 4 tiles por quadro composto |
| **Layers** | $2$ | **L0**: Arte visível em cores (RGBA)<br>**L1**: Máscara de recolorização do cliente |
| **Pattern X** | $4$ | Direções na ordem: **Norte (0)**, **Leste (1)**, **Sul (2)**, **Oeste (3)** |
| **Pattern Y** | $7$ | **Y0**: Base (apenas roupa/corpo)<br>**Y1**: Helmet<br>**Y2**: Armor<br>**Y3**: Legs<br>**Y4**: Boots<br>**Y5**: Weapon<br>**Y6**: Shield |
| **Pattern Z** | $2$ | **Z0**: A pé<br>**Z1**: Montado |
| **Grupos** | $2$ | **Grupo 1 (type 0)**: Parado (Idle)<br>**Grupo 2 (type 1)**: Andando (Walk) |
| **Frames por Grupo** | $8$ | 8 fases de animação (passos sincronizados) |
| **Total de Poses** | $128$ | $2\text{ grupos} \times 8\text{ frames} \times 4\text{ direções} \times 2\text{ Z}$ |
| **Total de Quadros PNG** | $1.792$ | $128\text{ poses} \times 7\text{ linhas Y} \times 2\text{ camadas (L0, L1)}$ |
| **Total de Referências DAT** | $7.168$ | $1.792\text{ quadros} \times 4\text{ tiles por quadro}$ |

---

## 2. Ordem de Quadrantes no DAT / SPR

Para cada quadro $64 \times 64$, os 4 tiles $32 \times 32$ são ordenados estritamente na convenção de importação do Tibia/Object Builder:
1. **Inferior Direito** (coordenadas $[32:64, 32:64]$) - Âncora principal do personagem
2. **Inferior Esquerdo** (coordenadas $[32:64, 0:32]$)
3. **Superior Direito** (coordenadas $[0:32, 32:64]$)
4. **Superior Esquerdo** (coordenadas $[0:32, 0:32]$)

Tile com todos os pixels transparentes recebe o Sprite ID `0` (vazio). Tiles repetidos são deduplicados automaticamente no mapa de sprites.

---

## 3. Contrato Anatômico dos 7 Componentes

### Regra de Ouro da Base (Y0)
* **O QUE É**: O manequim anatômico humanoide. Contém **apenas** cabeça, cabelo, rosto, tronco magro, braços, mãos, pernas e pés cobertos por **roupa de baixo justa / túnica simples de tecido / calça justa**.
* **O QUE NUNCA PODE CONTER**:
  * ❌ Nenhuma ombreira, couraça, peitoral de metal, cota de malha ou placa.
  * ❌ Nenhum capacete, elmo ou diadema protetor.
  * ❌ Nenhuma perneira reforçada ou greva.
  * ❌ Nenhuma bota blindada.
  * ❌ Absolutamente **nenhuma arma** (espada, cajado, machado, faca, etc.).
  * ❌ Absolutamente **nenhum escudo** ou acessório secundário.
* **Por quê?** Se a Base tiver volume de armadura ou armas desenhadas, ao equipar uma Armor diferente ou desequipar a Weapon, o sprite ficará corrompido ou sobreposto ("pixels brigando").

### Especificação dos 6 Addons (Y1 a Y6)

1. **Y1 - Helmet (Capacete)**:
   * Cobre a cabeça/cabelo. Fica na camada visual acima do rosto/cabelo da Base.
   * Não pode pintar sobre o tronco ou ombros.
2. **Y2 - Armor (Couraça / Peitoral)**:
   * Peitoral, ombreiras, braçadeiras e luvas de armadura.
   * Não deve invadir a área das pernas (coxas) para não colidir com o Y3 (Legs).
3. **Y3 - Legs (Perneiras / Calça de Combate)**:
   * Cintura, coxas e canelas.
   * Deve ser desenhada para encaixar logo abaixo da barra da Armor (Y2) e terminar antes da altura do tornozelo para dar espaço às Boots (Y4).
4. **Y4 - Boots (Botas)**:
   * Pés e tornozelos.
   * Encaixa nas extremidades inferiores do Y3 (Legs).
5. **Y5 - Weapon (Arma)**:
   * Espada, machado, cetro, arco, cajado ou clava.
   * Ancorada estritamente na mão ativa do personagem (Norte: mão direita aparente; Leste: mão frontal; Sul: mão esquerda aparente; Oeste: mão frontal).
   * Não deve cobrir a cabeça ou rosto.
6. **Y6 - Shield (Escudo)**:
   * Escudo ou tomo/foco de defesa.
   * Ancorado na mão secundária, posicionado com leve afastamento do tronco ($1\text{ a }2\text{ px}$) para não mascarar a arte da Armor (Y2).

---

## 4. Regras de Camadas (Layers L0 e L1)

* **L0 (Arte)**:
  * RGB puro com canal Alpha binário ($0$ totalmente transparente ou $255$ totalmente opaco).
  * Sem anti-aliasing ou semi-transparência ($1 \dots 254$ é proibido em formatos SPR legados).
* **L1 (Máscara de Cores / Recoloração do Cliente)**:
  * Controla a caixa de diálogo "Set Outfit" no cliente OTClient/Tibia.
  * Aceita **apenas** 4 cores exatas dentro da área visível da peça:
    * **Amarelo** `(255, 255, 0)`: Head (cabelo/detalhe do capacete)
    * **Vermelho** `(255, 0, 0)`: Primary (peitoral/cor primária)
    * **Verde** `(0, 255, 0)`: Secondary (detalhes secundários/pernas)
    * **Azul** `(0, 0, 255)`: Detail (botas/detalhes menores)
  * Qualquer pixel em L1 fora dos pixels visíveis de L0 é considerado erro crítico.
