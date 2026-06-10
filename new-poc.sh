#!/usr/bin/env bash
#
# Cria uma nova POC em projects/<nome> a partir de template/.
#
# Uso:
#   ./new-poc.sh <nome> ["descrição curta"]
#
set -euo pipefail

# Roda sempre a partir da raiz do repo (onde este script vive)
cd "$(dirname "$0")"

name="${1:-}"
desc="${2:-A quick Python POC}"

if [ -z "$name" ]; then
    echo "uso: ./new-poc.sh <nome> [\"descrição curta\"]" >&2
    exit 1
fi

dest="projects/$name"

if [ -e "$dest" ]; then
    echo "❌ já existe: $dest" >&2
    exit 1
fi

cp -r template "$dest"

# Substitui placeholders. Usa | como delimitador do sed para a descrição,
# que pode conter / ou espaços. O nome é kebab-case simples.
sed -i "s/{{NAME}}/$name/g" "$dest/pyproject.toml" "$dest/README.md" "$dest/main.py"
sed -i "s|{{DESC}}|$desc|g" "$dest/pyproject.toml" "$dest/README.md"

# Cria o ambiente isolado (.venv) e instala as dependências (vazias por enquanto).
( cd "$dest" && uv sync )

echo
echo "✅ POC criada em $dest"
echo "   cd $dest && uv run main.py"
