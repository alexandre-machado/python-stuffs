# cat-captions-visual

descrições visuais das fotos da Duda

## Rodar

```bash
uv run main.py --media-dir "/caminho/para/media" --output "/caminho/saida/captions-visual.md" --api-key "SUA_KEY"
```

Também funciona usando variável de ambiente para a chave:

```bash
export GEMINI_API_KEY="SUA_KEY"
uv run main.py --media-dir "/caminho/para/media" --output "/caminho/saida/captions-visual.md"
```

Exemplo com caminho Windows (quando executando no Linux/WSL):

```bash
uv run main.py --media-dir "D:\instagram-miau.duda\media\other" --output "D:\repos\alexandre-machado\documents\english career\post-07-agente-miau-duda\captions-visual.md"
```

O script converte automaticamente `D:\...` para `/mnt/d/...` em Linux/WSL.

Parâmetros disponíveis:

- `--media-dir`: diretório com imagens (`.jpg` e `.webp`)
- `--output`: arquivo `.md` de saída
- `--api-key`: chave da API Gemini (opcional se `GEMINI_API_KEY` estiver definida)
- `--model`: modelo Gemini (padrão: `gemini-2.5-flash`)
- `--api-version`: versão da API Gemini (padrão: `v1`)
- `--max-retries`: retentativas em erro 429/503 (`-1` = infinito, padrão: `-1`)
- `--retry-base-seconds`: espera base quando sem `retryDelay` na resposta (padrão: `3.0`)
- `--continue-on-quota-exhausted`: continua o lote mesmo detectando quota diária esgotada

Obs.: nomes legados como `gemini-1.5-flash` e `models/gemini-1.5-flash` são convertidos automaticamente para `gemini-2.5-flash`.

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
