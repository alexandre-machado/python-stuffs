# cat-captions-visual

descrições visuais das fotos da Duda

## Rodar

### Com a API do Gemini:

```bash
uv run main.py --media-dir "/caminho/para/media" --output "/caminho/saida/captions-visual.md" --api-key "SUA_KEY"
```

Também funciona usando variável de ambiente para a chave:

```bash
export GEMINI_API_KEY="SUA_KEY"
uv run main.py --media-dir "/caminho/para/media" --output "/caminho/saida/captions-visual.md"
```

### Com o LM Studio local (OpenAI-compatible):

Usando o preset padrão (`http://localhost:1234/v1` e modelo `qwen/qwen3.6-35b-a3b`):

```bash
uv run main.py --media-dir "/caminho/para/media" --output "/caminho/saida/captions-visual.md" --lm-studio
```

Ou especificando um modelo e URL customizados:

```bash
uv run main.py --media-dir "/caminho/para/media" --output "/caminho/saida/captions-visual.md" --base-url "http://localhost:1234/v1" --model "qwen/qwen3.6-35b-a3b"
```

Exemplo com caminho Windows (quando executando no Linux/WSL):

```bash
uv run main.py --media-dir "D:\instagram-miau.duda\media\other" --output "D:\repos\alexandre-machado\documents\english career\post-07-agente-miau-duda\captions-visual.md"
```

O script converte automaticamente `D:\...` para `/mnt/d/...` em Linux/WSL.

Parâmetros disponíveis:

- `--media-dir`: diretório com imagens (`.jpg` e `.webp`)
- `--output`: arquivo `.md` de saída
- `--api-key`: chave da API Gemini ou token da API local se necessário (opcional)
- `--model`: modelo a usar (padrão: `gemini-2.5-flash` ou `qwen/qwen3.6-35b-a3b` se `--lm-studio`/`--base-url` for utilizado)
- `--api-version`: versão da API Gemini (padrão: `v1`)
- `--base-url`: URL base para API local / compatível com OpenAI (ex: `http://localhost:1234/v1`)
- `--lm-studio`: usa preset pré-configurado do LM Studio local
- `--max-retries`: retentativas em erro (`-1` = infinito, padrão: `-1`)
- `--retry-base-seconds`: espera base de retentativa (padrão: `3.0`)
- `--continue-on-quota-exhausted`: continua o lote mesmo detectando quota diária esgotada (apenas para Gemini)

Obs.: Para a API Gemini, nomes legados como `gemini-1.5-flash` e `models/gemini-1.5-flash` são convertidos automaticamente para `gemini-2.5-flash`.

Exemplo para reduzir falhas por limite temporário:

```bash
uv run main.py --media-dir "/caminho/para/media" --output "/caminho/saida/captions-visual.md" --max-retries 4 --retry-base-seconds 8
```

O script salva o output a cada iteração (sucesso ou erro) e, quando já existe um arquivo de saída, ele identifica pelo próprio output quais imagens já foram concluídas e pula essas entradas no próximo run.

Quando detectar cota diária esgotada (429 com quota `PerDay`), o script passa a esperar automaticamente pelo `retryDelay` informado pela API e tenta novamente, mostrando no log o horário estimado de retomada.

Para listar modelos disponíveis para a chave atual (sem expor a chave no comando):

```bash
curl "https://generativelanguage.googleapis.com/v1/models?key=$GEMINI_API_KEY" | grep gemini-2.0-flash
```

Se aparecer erro citando `v1beta`, force a versão estável no script:

```bash
uv run main.py --api-version v1 --media-dir "/caminho/para/media" --output "/caminho/saida/captions-visual.md"
```

Se interromper com `Ctrl+C`, o script salva o resultado parcial no arquivo de saída antes de encerrar.

## Dependências

```bash
uv add google-genai
uv add <pacote>        # adiciona uma dependência
uv add --dev <pacote>  # adiciona dependência de desenvolvimento
```

## Testar

```bash
uv run pytest
```

## Contribuição

- As descrições de Pull Requests (PRs) e as mensagens de commit devem ser escritas obrigatoriamente em **inglês**.

