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

## Projetos

| Projeto | O que faz |
| --- | --- |
| `asciichart-demo` | Plota um gráfico ASCII de valores aleatórios no terminal. |
| `network-scanner` | Varre `192.168.0.0/24` procurando hosts com a porta 554 (RTSP) aberta. |
| `multiprocessing-examples` | Exemplos de `multiprocessing.Pool` (`imap`/`apply_async`) com `tqdm`. |
| `3d-mesh-beliche` | Gera a malha 3D de uma beliche e exporta para STL/DAE (código em PT). |

## Estrutura

```
.
├── new-poc.sh        # scaffold de novas POCs
├── template/         # modelo copiado pelo new-poc.sh
└── projects/         # uma pasta por POC, cada uma com seu próprio ambiente
```

> O devcontainer usa Python 3.11. Se for usá-lo, instale o `uv` dentro do container
> (ver pré-requisito acima); ele não vem na imagem base.
