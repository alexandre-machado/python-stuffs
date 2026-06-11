# python-stuffs

Coleção de **POCs rápidas em Python**, cada uma isolada em seu próprio mini-projeto e
ambiente. A ideia é prototipar uma ideia rápido, deixar organizada e guardada para
reuso futuro — sem uma POC pisar na dependência da outra.

Cada projeto vive em `projects/<nome>/` com seu próprio `.venv`, `pyproject.toml` e
`uv.lock`, gerenciados por [uv](https://docs.astral.sh/uv/).

## Pré-requisito

[uv](https://docs.astral.sh/uv/) instalado:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Criar uma nova POC

```bash
./new-poc.sh meu-experimento "uma frase do que isso faz"
cd projects/meu-experimento
uv run main.py
```

O `new-poc.sh` copia o `template/`, preenche nome/descrição e já cria o `.venv`.

## Trabalhar numa POC existente

```bash
cd projects/<nome>
uv run main.py        # roda
uv add requests       # adiciona uma dependência
uv run pytest         # roda os testes
```

## VS Code

Abra o **workspace** (não a pasta raiz nem cada projeto individualmente):

```bash
code python-stuffs.code-workspace
```

Você vê o repo inteiro numa janela só, mas cada projeto continua usando o **seu próprio `.venv`** — a extensão de Python detecta o interpretador de cada pasta automaticamente. 

> [!NOTE]
> O VS Code não suporta padrões de busca/curinga (como `projects/*`) para incluir pastas automaticamente no arquivo `.code-workspace`. Por isso, o script `new-poc.sh` registra cada POC nova no arquivo automaticamente durante a criação.

### Testes e Formatação
* **Testes (pytest)**: O painel de testes está configurado no nível do workspace. Para evitar erros de descoberta de testes na raiz do projeto (que não possui ambiente Python próprio nem dependências), a descoberta foi desabilitada especificamente na pasta raiz do repositório em [.vscode/settings.json](file:///home/ubuntu-24/repos/alexandre-machado/python-stuffs/.vscode/settings.json), enquanto continua ativa e funcional para todos os sub-projetos listados no workspace.
* **Formatação (black)**: Configurada para rodar automaticamente via extensão recomendada.

## Projetos

| Projeto | O que faz |
| --- | --- |
| `asciichart-demo` | Plota um gráfico ASCII de valores aleatórios no terminal. |
| `network-scanner` | Varre `192.168.0.0/24` procurando hosts com a porta 554 (RTSP) aberta. |
| `multiprocessing-examples` | Exemplos de `multiprocessing.Pool` (`imap`/`apply_async`) com `tqdm`. |
| `3d-mesh-beliche` | Gera a malha 3D de uma beliche e exporta para STL/DAE (código em PT). |
| `cat-captions-visual` | Gera descrições visuais de fotos usando a API do Gemini ou LM Studio local. |

## Estrutura

```
.
├── new-poc.sh        # scaffold de novas POCs
├── template/         # modelo copiado pelo new-poc.sh
└── projects/         # uma pasta por POC, cada uma com seu próprio ambiente
```

> O Dev Container está configurado e pronto para uso! Ele utiliza Python 3.11, instala
> automaticamente o `uv` e pré-configura todas as extensões do VS Code necessárias.
