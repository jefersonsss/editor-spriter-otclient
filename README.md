# New Island Outfit Forge 1.0

Aplicativo Python com interface local no navegador para transformar outfits antigos em Base + seis addons e criar outfits novos a partir de texto. Inclui os dois outfits antigos anexados, o Golden modular v8 e a receita que reproduz esse Golden, sem API.

## Iniciar no Windows

1. Extraia **toda a pasta** do ZIP para um diretório de sua escolha.
2. Instale [Python 3.11 ou mais recente, 64 bits](https://www.python.org/downloads/). As dependências fixadas são voltadas a Python 3.11–3.14.
3. Execute `INICIAR_WINDOWS.bat`. A primeira execução cria um ambiente `.venv` e instala as bibliotecas pela internet.
4. O navegador abre a interface local. Mantenha o terminal aberto; `Ctrl+C` encerra o aplicativo.
5. Clique em **Reproduzir Golden validado** para testar todo o fluxo localmente.

Não precisa instalar servidor web, Node, banco de dados ou uma extensão do navegador. O aplicativo escuta somente em `127.0.0.1`, em uma porta disponível. Não publica arquivos na internet.

Linux/macOS: execute `bash INICIAR_LINUX_MAC.sh`. Em distribuições Debian/Ubuntu, o sistema pode exigir o pacote `python3-venv` antes de criar o ambiente. Também pode instalar manualmente:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

## Operações disponíveis

| Operação | Como funciona | API |
|---|---|---|
| Reproduzir Golden | Executa a receita original e compara cada pixel com o v8 incorporado | Não |
| Abrir/editar pacote modular | Mantém os quadros, permite pintar arte/máscaras e exportar novamente | Não |
| Converter outro outfit antigo | Analisa visualmente o FULL, separa as peças, reconstrói o corpo limpo e gera peças ausentes | Sim |
| Criar por prompt | Gera Base e cada addon separadamente, pausando para aprovação humana | Sim |

### Converter um antigo

Em **Importar outfit**, abra o ZIP exportado pelo seu editor. Confira a fonte composta, informe o LookType de saída e clique em **Transformar em modular**.

O modo **Automático** reconhece a matriz Golden, preserva pacotes que já têm sete linhas completas e usa IA para outras fontes. É possível forçar IA ou selecionar explicitamente a receita Golden; a receita recusa matrizes diferentes.

Os exemplos 1457 e Demonhunter têm somente Y0–Y2. Seus manifestos mencionam nomes modulares, mas esses nomes não demonstram que as peças estejam separadas. Por isso o motor visual examina as imagens e o FULL, em vez de simplesmente renomear addons.

### Criar por prompt

Em **Criar por prompt**, descreva o personagem, cores, materiais, capacete, couraça, perneiras, botas, arma e escudo. Escolha o LookType, frames parado/andando e Pattern Z. O padrão é a geometria do Golden: quatro direções, dois grupos, oito frames por grupo e Z=2. O Forge mostra Base, Helmet, Armor, Legs, Boots, Shield e Weapon individualmente; examine direções e animações e aprove cada etapa para liberar a seguinte.

Exemplo: “Cavaleiro das marés, armadura de bronze envelhecido, capacete aberto com crista azul, perneiras articuladas, botas de couro, tridente curto e escudo redondo com concha. Pixel art Tibia e proporções do Golden.”

O programa cria arte nova e usa a base Golden em tons neutros como guia de pose. Ele não apresenta uma recoloração do Golden como se fosse um personagem novo. A consistência de desenho entre frames depende do modelo; confira as quatro direções e animações.

### Configuração da API

Em **Configuração**, informe sua chave, salve e teste a conexão. A chave permanece na memória da sessão; os arquivos de configuração e os ZIPs não a incluem. Como alternativa, defina `OPENAI_API_KEY` no ambiente antes de iniciar. A assinatura do ChatGPT não fornece automaticamente acesso pago à API.

Os modelos iniciais configuráveis são `gpt-4.1` para análise visual estruturada e `gpt-image-1.5` para geração/edição de imagens. A conta precisa ter acesso aos modelos. O teste de conexão lista modelos; a autorização para gerar imagens é verificada no uso. O aplicativo usa requisições HTTP reais, sem depender da sessão do ChatGPT.

O endpoint padrão é `https://api.openai.com/v1`. Provedores alternativos precisam oferecer os mesmos contratos: `/responses` com imagens e JSON Schema estrito, `/images/edits` multipart com uma ou mais `image[]`, `/images/generations` e PNG em `b64_json`. A escolha de endpoint envia a chave a esse provedor.

**Consumo:** uma conversão de 128 poses usa aproximadamente 32 análises e 8 atlas de corpo; peças ausentes exigem atlas adicionais. A criação por prompt gera sete etapas, com até 8 atlas por etapa: Base, Helmet, Armor, Legs, Boots, Shield e Weapon. Retentativas e alterações de configuração podem gerar chamadas adicionais. Isso não é uma estimativa de preço; consulte a cobrança da sua conta.

Qualidade, fundo, limite de chamadas, timeout e lote visual são ajustáveis. O limite de chamadas interrompe a tarefa quando atingido. **Cancelar** interrompe entre etapas; uma chamada já enviada pode terminar e ser cobrada. Um timeout também não comprova que o provedor deixou de processar a chamada.

### Prévia e editor de pixels

Selecione grupo, direção, Z e frame. Use **Animar**, altere FPS e ligue/desligue os sete componentes. **Só base**, **Armadura completa** e **Todos** facilitam a comparação.

Clique em uma peça para editar seus pixels. Há pincel, borracha, conta-gotas (`Shift` + clique), desfazer traços, desfazer edições aplicadas, importação/exportação de PNG 64×64 e seleção de L0/L1. **Aplicar edição** salva somente a pose, peça e camada selecionadas. Trocar de pose ou exportar aplica edições pendentes. Fechar a aba com pixels ainda pendentes exibe o aviso do navegador.

L1 aceita apenas amarelo `(255,255,0)`, vermelho `(255,0,0)`, verde `(0,255,0)` e azul `(0,0,255)`, dentro da arte visível. A geração genérica pode produzir camadas de máscara vazias; pinte L1 se desejar recoloração no cliente. A receita Golden preserva exatamente suas máscaras. A prévia mostra a arte e a máscara editável, sem simular o shader de recoloração do cliente.

## Formato exportado

| Campo | Valor |
|---|---|
| Width × Height | 2 × 2 |
| Tile individual | 32 × 32 |
| Quadro composto | 64 × 64 |
| Layers | 2 (L0 arte, L1 máscara) |
| Pattern X | 4 (Norte, Leste, Sul, Oeste) |
| Pattern Y | 7 (Base, Helmet, Armor, Legs, Boots, Weapon, Shield) |
| Grupos, frames e Z | Preservados na conversão; configurados na criação |
| Transparência SPR | Binária, sem alpha parcial |

O arquivo `outfit_ID_modular.zip` inclui uma pasta `outfit_ID`, `manifest.txt`, `quadros_compostos/`, `sprites_individuais/`, `mapa_sprites.csv`, `validacao.json`, `forge_project.json`, `preview.png` e `SHA256SUMS.txt`.

Os quatro quadrantes são exportados na ordem DAT **inferior direito, inferior esquerdo, superior direito, superior esquerdo**. Sprite local zero é transparente. Tiles iguais são deduplicados. Os IDs locais não são os IDs definitivos do SPR.

Importe o ZIP no **New Island Outfit Studio**, na aba de importação ZIP/pasta. O editor cria os IDs SPR. Ao criar um outfit novo, o Studio usa o próximo ID do DAT; o LookType no ZIP identifica a origem. A saída contém geometria e quadros, não as flags e durações do seu DAT. Esses metadados são tratados pelo editor de destino. Salve SPR antes de DAT e revise o resultado no cliente.

## Projetos e retomada

As importações e as edições aplicadas são salvas automaticamente. A aba **Projetos** reabre as fontes e resultados. No Windows, ficam em `%LOCALAPPDATA%\NewIslandOutfitForge`; em Linux/macOS, em `$XDG_DATA_HOME/NewIslandOutfitForge` ou `~/.local/share/NewIslandOutfitForge`.

O cache guarda respostas e imagens por hash da requisição, sem chave. Ao repetir a mesma operação com os mesmos parâmetros, etapas concluídas são reaproveitadas. Alterar prompt, modelo, qualidade ou imagens muda o hash. Uma geração concluída de FULL é salva como fonte de projeto antes de iniciar a modularização; se esta falhar, reabra a fonte e converta novamente. Respostas recebidas após cancelamento não são garantidas no cache.

Arquivos `.zip` de saída podem ser reabertos no próprio aplicativo. Para uma cópia completa da oficina, copie a pasta de dados com o app fechado. O histórico de desfazer edições aplicadas é da sessão atual; as versões finais das imagens permanecem salvas.

## Gerar executável depois

No **Windows**, execute `GERAR_EXE_WINDOWS.bat`. Ele instala PyInstaller e usa `NewIslandOutfitForge.spec`. O resultado será:

`dist/NewIslandOutfitForge/NewIslandOutfitForge.exe`

Distribua a **pasta inteira**, incluindo `_internal`. O executável abre a mesma interface e não precisa de Python instalado no computador de destino. A chave de API continua necessária para as operações de IA. O build deve ser feito no sistema operacional de destino; esta entrega não inclui um binário Windows pré-compilado ou assinado.

## Linha de comando

```bash
python main.py golden --output golden_modular.zip
python main.py inspect data/references/antigo_1457.zip
python main.py validate golden_modular.zip
python main.py convert antigo.zip --output convertido.zip --look 2001
python main.py create --prompt "Cavaleiro de bronze com lança e escudo redondo" --look 2002 --output novo.zip
python main.py --workspace minha_oficina --no-browser --port 8765
python -m unittest discover -s tests -v
```

Na CLI, forneça a chave por `OPENAI_API_KEY`. A configuração da interface é reutilizada pela CLI da mesma pasta de trabalho. A chave digitada na interface não é compartilhada com outros processos.

## Organização e limites

`ni_forge/core.py` trata o formato, composição, recortes de tiles e validação. `workflows.py` contém os dois motores. `ai.py` implementa os contratos HTTP e cache. `server.py` fornece a interface local. `static/` contém HTML/CSS/JavaScript sem CDN. `data/` inclui referências e receita. `tests/` verifica os fluxos.

O Golden é uma reprodução determinística; ela foi comparada com todos os quadros da referência fornecida. Na criação, a IA produz Base, Helmet, Armor, Legs, Boots, Shield e Weapon separadamente. A geometria validada determina obrigatoriamente a silhueta, pose diagonal/isométrica, direção, escala e âncora; a IA fornece o desenho e as cores, sem poder transformar frames em giros do personagem. A interface pausa depois de cada peça para revisão. Sprites aprovados são bloqueados por hash e, ao final, o Python compõe o FULL.

Veja [docs/VALIDACAO.md](docs/VALIDACAO.md) para a cobertura efetivamente executada e [docs/PROCESSO.md](docs/PROCESSO.md) para o tratamento da geometria.

Referências oficiais dos contratos implementados: [Images API](https://developers.openai.com/api/docs/guides/image-generation), [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [GPT Image 1.5](https://developers.openai.com/api/docs/models/gpt-image-1.5) e [GPT-4.1](https://developers.openai.com/api/docs/models/gpt-4.1).
