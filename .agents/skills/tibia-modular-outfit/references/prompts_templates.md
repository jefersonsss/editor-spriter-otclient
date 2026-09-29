# Prompts Estruturados para Geração Modular (Tibia / New Island)

Este guia fornece os modelos de prompts obrigatórios para garantir que a IA gere outfits que respeitem o contrato anatômico e evitem sobreposição indevida de pixels.

---

## 1. Estrutura do Prompt Dividido por Seções

O *New Island Outfit Forge* analisa o prompt procurando pelas seguintes tags de isolamento:

```text
GERAL: <Descrição do conceito geral, tema, paleta e clima>
BASE: <Descrição EXCLUSIVA da Base: corpo, cabelo, pele e roupa de baixo>
HELMET: <Descrição do capacete, elmo ou acessório de cabeça>
ARMOR: <Descrição da couraça, peitoral, ombreiras e luvas>
LEGS: <Descrição das perneiras, calças de armadura ou grevas>
BOOTS: <Descrição das botas e calçados de combate>
WEAPON: <Descrição da arma empunhada na mão principal>
SHIELD: <Descrição do escudo ou item defensivo na mão secundária>
```

---

## 2. Modelos de Prompt por Componente

### Regra Mandatória da BASE (Y0)
A Base **NUNCA** pode receber referências a metal, armadura, ombreira, capacete, espada ou escudo.

> **Template do Sistema para BASE**:
> *"Classic Tibia/OTServ unarmored mannequin base: compact semi-chibi anatomy, oversized readable head, short torso, short limbs, close-fitting plain cloth undershirt and trousers made to be covered by separate armor layers. Bare hands, visible face and hair. STRICTLY NO armor plates, NO pauldrons, NO helmet, NO weapons, NO shields. Crisp 1-pixel outlines, limited palette, transparent background."*

* **Exemplo de Entrada do Usuário**:
  ```text
  BASE: Jovem guerreiro nórdico de pele clara, cabelos ruivos trançados, túnica simples de linho cru bem justa ao corpo e calça simples cinza-escura. Sem qualquer proteção de metal.
  ```

---

### Y1 - HELMET (Capacete / Elmo)
> **Template**:
> *"Isolated HELMET equipment layer only. Fits on top of the character's head. Clean 1-pixel silhouette. Do not draw character face or hair unless integrated into the helmet. Pure transparent background. No torso, no armor."*

* **Exemplo de Entrada do Usuário**:
  ```text
  HELMET: Elmo de ferro batido com chifres curtos nas laterais e visor aberto revelando os olhos.
  ```

---

### Y2 - ARMOR (Couraça / Peitoral)
> **Template**:
> *"Isolated ARMOR equipment layer only: breastplate, pauldrons, upper arm guards and gauntlets. Designed to overlay the plain cloth torso. Does not extend below the hip line. No legs, no helmet, no weapons. Transparent background."*

* **Exemplo de Entrada do Usuário**:
  ```text
  ARMOR: Peitoral de aço com cota de malha aparente nos braços, ombreiras de ferro reforçadas com rebites de bronze e manoplas de couro grosso.
  ```

---

### Y3 - LEGS (Perneiras / Calça de Combate)
> **Template**:
> *"Isolated LEGS equipment layer only: armored greaves, thigh plates and battle tassets. Starts at the belt line and ends above the ankles. Does not cover torso or feet. No boots, no chest armor. Transparent background."*

* **Exemplo de Entrada do Usuário**:
  ```text
  LEGS: Perneiras de placas de ferro articuladas sobrepostas, com joelheiras reforçadas em formato de cabeça de lobo.
  ```

---

### Y4 - BOOTS (Botas)
> **Template**:
> *"Isolated BOOTS equipment layer only: heavy battle boots, armored sabatons or reinforced leather shoes. Covers ankles and feet only. No legs, no armor. Transparent background."*

* **Exemplo de Entrada do Usuário**:
  ```text
  BOOTS: Botas pesadas de couro escuro reforçadas com placas de metal na canela e biqueira de aço.
  ```

---

### Y5 - WEAPON (Arma)
> **Template**:
> *"Isolated WEAPON equipment layer only: held in the main attack hand. Scaled appropriately for Tibia 64x64 canvas. Do not draw character body, hands or arms. Transparent background."*

* **Exemplo de Entrada do Usuário**:
  ```text
  WEAPON: Espada larga de duas lâminas com guarda em cruz de bronze e runa azul brilhante entalhada no aço.
  ```

---

### Y6 - SHIELD (Escudo)
> **Template**:
> *"Isolated SHIELD equipment layer only: held on the defensive hand/arm. Positioned slightly offset from the torso so as not to obscure the chestplate. Do not draw character body or head. Transparent background."*

* **Exemplo de Entrada do Usuário**:
  ```text
  SHIELD: Escudo redondo de madeira reforçada com borda de ferro cravada e emblema de um corvo negro no centro.
  ```

---

## 3. Exemplo Completo de Prompt Automatizado (Copie e Cole)

```text
GERAL: Paladino Sagrado da Ordem da Luz, estilo Tibia 8.6 / New Island em perspectiva isométrica clássica, detalhes nítidos de 1 pixel e contornos escuros sólidos.

BASE: Humano masculino de cabelos castanhos curtos, olhos castanhos, vestindo apenas uma camisa de pano leve branca e calças justas pretas de tecido simples. Nenhum metal, nenhuma arma, nenhum escudo.

HELMET: Elmo fechado de prata polida com detalhes em ouro na coroa e pequenas asas entalhadas nas laterais.

ARMOR: Couraça peitoral pesada de prata polida com detalhes dourados na borda, ombreiras largas em camadas e luvas blindadas.

LEGS: Perneiras de placas prateadas com faixas douradas na lateral das coxas e joelheiras de aço liso.

BOOTS: Botas de combate pesadas de aço polido com sola grossa reforçada.

WEAPON: Maça de guerra cerimonial com cabeça em formato de sol radiante e cabo de mogno envernizado.

SHIELD: Escudo de pipa (kite shield) prateado com uma cruz dourada em relevo no centro.
```
