# Validação desta entrega

26 testes automatizados aprovados em Linux, Python 3.12.14, Pillow 12.3.0, NumPy 2.3.5 e SciPy 1.17.0. O relatório de execução está em `RESULTADOS_TESTES.txt`. Os comandos CLI `inspect`, `golden` e `validate` também foram executados.

| Verificação | Resultado |
|---|---|
| Reprodução do Golden v8 | 1.792 quadros comparados pixel a pixel; todos idênticos |
| Recomposição da armadura Golden antiga | 128 poses; zero pixels diferentes |
| Interseção entre Helmet/Armor/Legs/Boots Golden | Zero |
| Peças Golden vazias | Nenhuma |
| Exportar e reabrir ZIP | Todos os pixels preservados |
| Recompor os quadros pelos tiles 32×32 | Todos os pixels preservados; 1.023 tiles não vazios únicos |
| Referências DAT | 7.168, sem slots ausentes |
| Leitura dos exemplos antigos | 1457 e Demonhunter: 72 poses, 432 quadros e três linhas Y cada |
| API por HTTP real contra provedor local simulado | Responses com schema, edits multipart, múltiplas referências, geração, cache, limite e cancelamento |
| Conversão genérica e criação por prompt | Fluxos completos com imagens de fixture; peças ausentes geradas pelo provedor simulado |
| Servidor local | Sessão, origem, importação, criação, exportação, edição, desfazer, persistência e reabertura |
| JavaScript | Sintaxe validada e ações exercitadas com DOM simulado, Canvas nativo e servidor Python real |

## Compatibilidade com o editor fornecido

Além dos testes do aplicativo, a saída foi processada pelas classes originais do New Island Outfit Studio v3.2 fornecido pelo usuário:

1. `OutfitPackageImporter.scan` reconheceu os 1.792 quadros, os dois grupos, 2×2 tiles, Layers=2, PatternY=7, PatternZ=2 e oito frames por grupo.
2. A importação criou um LookType em um DAT/SPR sintético temporário.
3. O teste gravou e reabriu os binários, recompôs os quadros e comparou todos os pixels: **1.792 idênticos**.
4. A substituição de um LookType existente preservou os metadados de animação que já estavam no DAT sintético.

Detalhes em `COMPATIBILIDADE_STUDIO.json`. Para repetir essa verificação opcional, forneça a pasta do seu editor:

```bash
python tests/verify_studio.py /caminho/newisland_outfit_studio_v3_2
```

Nenhum DAT/SPR real do cliente foi alterado. Os binários sintéticos usados pelo teste são temporários e não são arquivos para substituir os do jogo.

## O que ainda depende do ambiente de uso

- **API real:** não havia chave de API disponível nesta sessão. Os contratos e os fluxos foram testados com um servidor local de fixtures. A qualidade artística, os limites e as permissões da conta real não foram verificados. O aplicativo faz chamadas reais quando uma chave é configurada; os testes simulados não são usados no produto.
- **Windows e executável:** o código Python foi executado em Linux. Os atalhos Windows e o arquivo PyInstaller estão incluídos, mas o `.exe` Windows não foi compilado nem executado nesta sessão.
- **Navegador real:** os handlers HTTP, JavaScript e Canvas foram exercitados; não havia um navegador instalado para inspeção visual completa da interface. A prévia PNG do Golden foi aberta e conferida.
- **Cliente New Island:** o v8 foi informado pelo usuário como validado. Esta entrega compara a reprodução com ele e testa o importador original offline; não executa OTCv8 nem o servidor do jogo.

A validação de formato não declara que qualquer desenho produzido pela IA está artisticamente aprovado. A interface mantém as prévias, a animação, o relatório e o editor de pixels disponíveis para revisão.
