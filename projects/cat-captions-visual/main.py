import argparse
from datetime import UTC, datetime, timedelta
import mimetypes
import os
import re
import time
from pathlib import Path


PROMPT = """
Esta foto é da Miau Duda, uma gata Russian Blue / Chartreux cinza.
Descreva em 1 a 2 frases curtas e diretas:

- onde ela está e o que está fazendo
- qual o vibe ou expressão dela (entediada, alerta, dramática, confortável, etc.)
- se tem algo inusitado ou engraçado na cena

Não repita que ela é cinza ou que tem olhos âmbar. 
Não comece com "A gata" ou "Uma gata".
Escreva como uma nota rápida de contexto para quem já conhece ela.
"""

LEGACY_MODEL_ALIASES = {
    "gemini-1.5-flash": "gemini-2.5-flash",
    "gemini-1.5-pro": "gemini-2.5-pro",
}

OUTPUT_HEADER_LINES = ["# Descrições visuais - Miau Duda\n", "Gerado via Gemini\n", "---\n"]


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera descrições visuais de fotos usando Gemini ou LM Studio local."
    )
    parser.add_argument("--media-dir", type=Path, help="Diretório com imagens .jpg/.webp")
    parser.add_argument("--output", type=Path, help="Arquivo .md de saída com as descrições")
    parser.add_argument(
        "--api-key",
        help="Chave da API Gemini (ou token da API local se necessario). Se omitido, usa GEMINI_API_KEY do ambiente.",
    )
    parser.add_argument(
        "--model",
        default="gemini-2.5-flash",
        help="Modelo a usar (padrao: gemini-2.5-flash ou qwen/qwen3.6-35b-a3b se local/lm-studio)",
    )
    parser.add_argument(
        "--api-version",
        default="v1",
        help="Versao da API Gemini (padrao: v1)",
    )
    parser.add_argument(
        "--base-url",
        help="URL base da API local / OpenAI-compatible (ex: http://localhost:1234/v1).",
    )
    parser.add_argument(
        "--lm-studio",
        action="store_true",
        help="Usa preset do LM Studio local (URL: http://localhost:1234/v1, modelo: qwen/qwen3.6-35b-a3b).",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=-1,
        help=(
            "Quantidade maxima de retentativas em erro 429/503. "
            "Use -1 para infinito (padrao: -1)."
        ),
    )
    parser.add_argument(
        "--retry-base-seconds",
        type=float,
        default=3.0,
        help="Tempo base para retentativa quando sem RetryInfo (padrao: 3.0)",
    )
    parser.add_argument(
        "--continue-on-quota-exhausted",
        action="store_true",
        help=(
            "Continua processando arquivos mesmo quando detectar quota diaria esgotada. "
            "Por padrao o lote e interrompido nesse caso."
        ),
    )
    return parser.parse_args(argv)


def _iter_images(media_dir: Path) -> list[Path]:
    patterns = ("*.jpg", "*.JPG", "*.webp", "*.WEBP")
    images: list[Path] = []
    for pattern in patterns:
        images.extend(sorted(media_dir.glob(pattern)))
    return sorted(images)


def _normalize_cli_path(raw_path: Path) -> Path:
    path_str = str(raw_path)
    if os.name != "nt" and len(path_str) >= 3 and path_str[1:3] == ":\\":
        drive = path_str[0].lower()
        rest = path_str[3:].replace("\\", "/")
        return Path(f"/mnt/{drive}/{rest}")
    return raw_path


def _mime_type_for_image(img_path: Path) -> str:
    guessed, _ = mimetypes.guess_type(str(img_path))
    return guessed or "image/jpeg"


def _normalize_model_name(model: str) -> tuple[str, str | None]:
    name = model.strip()
    if name.startswith("models/"):
        name = name.split("/", 1)[1]

    mapped = LEGACY_MODEL_ALIASES.get(name)
    if mapped:
        return mapped, f"Modelo legado '{name}' ajustado para '{mapped}'."
    return name, None


def _is_quota_exhausted_error(error_text: str) -> bool:
    upper = error_text.upper()
    return "RESOURCE_EXHAUSTED" in upper or " 429 " in f" {error_text} "


def _is_daily_quota_exhausted(error_text: str) -> bool:
    return "GenerateRequestsPerDayPerProjectPerModel-FreeTier" in error_text


def _is_transient_service_error(error_text: str) -> bool:
    upper = error_text.upper()
    return (
        "UNAVAILABLE" in upper
        or " 503 " in f" {error_text} "
        or "DEADLINE_EXCEEDED" in upper
        or "INTERNAL" in upper
    )


def _extract_retry_seconds(error_text: str, fallback_seconds: float) -> float:
    patterns = [
        r"retry in\s+([0-9]+(?:\.[0-9]+)?)s",
        r"'retryDelay':\s*'([0-9]+)s'",
        r'"retryDelay":\s*"([0-9]+)s"',
    ]
    for pattern in patterns:
        match = re.search(pattern, error_text, flags=re.IGNORECASE)
        if match:
            return max(float(match.group(1)), 0.0)
    return max(fallback_seconds, 0.0)


def _compute_backoff_seconds(base_seconds: float, attempt: int) -> float:
    return max(base_seconds, 0.0) * (2 ** max(attempt - 1, 0))


def _seconds_until_next_utc_day(buffer_seconds: float = 5.0) -> float:
    now_utc = datetime.now(UTC)
    next_day_utc = (now_utc + timedelta(days=1)).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    seconds = (next_day_utc - now_utc).total_seconds()
    return max(seconds + max(buffer_seconds, 0.0), 0.0)


def _parse_existing_output(output: Path) -> tuple[dict[str, str], set[str]]:
    if not output.exists():
        return {}, set()

    content = output.read_text(encoding="utf-8")
    matches = re.findall(
        r"^\[(.+?)\]\n(.*?)(?=^\[.+?\]\n|\Z)",
        content,
        flags=re.MULTILINE | re.DOTALL,
    )

    entries: dict[str, str] = {}
    completed: set[str] = set()

    for file_name, body in matches:
        normalized_body = body.strip()
        entries[file_name] = normalized_body
        if not normalized_body.lower().startswith("erro:"):
            completed.add(file_name)

    return entries, completed


def _build_output_lines(entries: dict[str, str], header_lines: list[str]) -> list[str]:
    lines = header_lines.copy()
    for file_name, text in entries.items():
        lines.append(f"[{file_name}]\n{text}\n")
    return lines


def _write_output(output: Path, entries: dict[str, str], header_lines: list[str]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(_build_output_lines(entries, header_lines)), encoding="utf-8")


def _describe_image_openai(
    base_url: str,
    model: str,
    img_path: Path,
    prompt: str,
    api_key: str | None = None,
) -> str:
    import base64
    import json
    import urllib.request

    with img_path.open("rb") as file_obj:
        image_bytes = file_obj.read()
    img_b64 = base64.b64encode(image_bytes).decode("utf-8")
    mime_type = _mime_type_for_image(img_path)

    url = f"{base_url.rstrip('/')}/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{img_b64}"
                        }
                    }
                ]
            }
        ],
        "stream": True,
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    full_content = []
    print("  [Streaming] ", end="", flush=True)
    # Timeout aumentado para 600 segundos (10 minutos). Lendo a resposta em partes (stream/keep-alive)
    with urllib.request.urlopen(req, timeout=600) as response:
        for line in response:
            line_str = line.decode("utf-8").strip()
            if not line_str:
                continue
            if line_str.startswith("data: "):
                data_content = line_str[6:]
                if data_content == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_content)
                    choices = chunk.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            full_content.append(content)
                            print(content, end="", flush=True)
                except json.JSONDecodeError:
                    continue
    print()  # Quebra de linha após o término do stream
    return "".join(full_content).strip() or "sem resposta do modelo"


def _describe_image(
    *,
    client,
    types,
    model: str,
    img_path: Path,
    prompt: str,
    max_retries: int,
    retry_base_seconds: float,
    continue_on_quota_exhausted: bool,
    base_url: str | None = None,
    api_key: str | None = None,
) -> tuple[str | None, str | None, bool]:
    with img_path.open("rb") as file_obj:
        image_bytes = file_obj.read()

    max_attempts = None if max_retries < 0 else max(1, max_retries + 1)
    attempt = 1
    while True:
        try:
            if base_url:
                text = _describe_image_openai(
                    base_url=base_url,
                    model=model,
                    img_path=img_path,
                    prompt=prompt,
                    api_key=api_key,
                )
                return text, None, False
            else:
                response = client.models.generate_content(
                    model=model,
                    contents=[
                        prompt,
                        types.Part.from_bytes(
                            data=image_bytes,
                            mime_type=_mime_type_for_image(img_path),
                        ),
                    ],
                )
                text = (response.text or "").strip() or "sem resposta do modelo"
                return text, None, False
        except Exception as exc:  # noqa: BLE001 - API pode retornar tipos diferentes
            error_text = str(exc)
            is_last_attempt = max_attempts is not None and attempt >= max_attempts

            if base_url:
                if not is_last_attempt:
                    backoff_seconds = _compute_backoff_seconds(retry_base_seconds, attempt)
                    print(
                        f"Erro na conexao local ({error_text}) para {img_path.name}; "
                        f"aguardando {backoff_seconds:.1f}s e tentando novamente..."
                    )
                    time.sleep(backoff_seconds)
                    attempt += 1
                    continue
                return None, error_text, False

            is_quota_error = _is_quota_exhausted_error(error_text)
            daily_quota_exhausted = _is_daily_quota_exhausted(error_text)

            if daily_quota_exhausted and not is_last_attempt:
                retry_delay_seconds = _extract_retry_seconds(
                    error_text,
                    fallback_seconds=60.0,
                )
                next_day_wait_seconds = _seconds_until_next_utc_day(buffer_seconds=5.0)
                # Para quota diaria, retryDelay curto nao representa o reset da cota.
                wait_seconds = max(retry_delay_seconds, next_day_wait_seconds)
                resume_at_utc = datetime.now(UTC) + timedelta(seconds=wait_seconds)
                print(
                    f"Quota diaria esgotada para {img_path.name}; aguardando {wait_seconds:.1f}s "
                    f"(retoma por volta de {resume_at_utc:%Y-%m-%d %H:%M:%S} UTC)"
                )
                time.sleep(wait_seconds)
                attempt += 1
                continue

            if daily_quota_exhausted and is_last_attempt:
                hint = "Aumente --max-retries ou use -1 para esperar ate a cota voltar."
                return None, f"{error_text}\n{hint}", not continue_on_quota_exhausted

            if is_quota_error and not is_last_attempt:
                backoff_seconds = _compute_backoff_seconds(retry_base_seconds, attempt)
                wait_seconds = _extract_retry_seconds(
                    error_text,
                    fallback_seconds=backoff_seconds,
                )
                print(
                    f"Quota/limite para {img_path.name}; aguardando {wait_seconds:.1f}s "
                    f"(tentativa {attempt}{'' if max_attempts is None else f'/{max_attempts}'})"
                )
                time.sleep(wait_seconds)
                attempt += 1
                continue

            if _is_transient_service_error(error_text) and not is_last_attempt:
                backoff_seconds = _compute_backoff_seconds(retry_base_seconds, attempt)
                wait_seconds = _extract_retry_seconds(
                    error_text,
                    fallback_seconds=backoff_seconds,
                )
                print(
                    f"Servico temporariamente indisponivel para {img_path.name}; "
                    f"aguardando {wait_seconds:.1f}s "
                    f"(tentativa {attempt}{'' if max_attempts is None else f'/{max_attempts}'})"
                )
                time.sleep(wait_seconds)
                attempt += 1
                continue

            if "NOT_FOUND" in error_text and "model" in error_text.lower():
                hint = (
                    "Modelo nao encontrado. Tente --model gemini-2.5-flash ou rode com "
                    "um modelo valido do projeto/chave atual."
                )
                return None, f"{error_text}\n{hint}", False

            return None, error_text, False


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    is_local = bool(args.base_url or args.lm_studio)
    if args.lm_studio:
        if not args.base_url:
            args.base_url = "http://localhost:1234/v1"
        if args.model == "gemini-2.5-flash":
            args.model = "qwen/qwen3.6-35b-a3b"
    elif args.base_url and args.model == "gemini-2.5-flash":
        args.model = "qwen/qwen3.6-35b-a3b"

    if not is_local:
        normalized_model, model_message = _normalize_model_name(args.model)
        args.model = normalized_model
        if model_message:
            print(model_message)

    if not args.media_dir or not args.output:
        print("Informe --media-dir e --output para executar a geracao.")
        return 0

    api_key = args.api_key or os.environ.get("GEMINI_API_KEY")
    client = None
    types = None

    if not is_local:
        if not api_key:
            print("Informe --api-key ou defina GEMINI_API_KEY no ambiente.")
            return 1

        try:
            from google import genai
            from google.genai import types
        except ImportError:
            print("Dependencia ausente: google-genai.")
            print("Instale com: uv add google-genai")
            return 1

        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(api_version=args.api_version),
        )

    media_dir = _normalize_cli_path(args.media_dir)
    output = _normalize_cli_path(args.output)

    if not media_dir.exists() or not media_dir.is_dir():
        print(f"Diretorio invalido: {media_dir}")
        return 1

    entries, completed = _parse_existing_output(output)
    if completed:
        print(
            f"Retomando do output existente: {len(completed)} arquivo(s) ja concluidos; "
            "eles serao pulados."
        )
    interrupted = False

    if is_local:
        header_text = f"Gerado via {args.model} (LM Studio Local)\n"
    else:
        header_text = "Gerado via Gemini\n"
    header_lines = ["# Descrições visuais - Miau Duda\n", header_text, "---\n"]

    try:
        try:
            for img_path in _iter_images(media_dir):
                if img_path.name in completed:
                    print(f"SKIP {img_path.name} (ja concluido no output)")
                    continue

                print(f"Processando {img_path.name}...")
                text, error_text, abort_batch = _describe_image(
                    client=client,
                    types=types,
                    model=args.model,
                    img_path=img_path,
                    prompt=PROMPT,
                    max_retries=args.max_retries,
                    retry_base_seconds=args.retry_base_seconds,
                    continue_on_quota_exhausted=args.continue_on_quota_exhausted,
                    base_url=args.base_url,
                    api_key=api_key,
                )

                if text is not None:
                    entries[img_path.name] = text
                    completed.add(img_path.name)
                    _write_output(output, entries, header_lines)
                    print(f"OK {img_path.name}")
                    continue

                print(f"ERRO {img_path.name}: {error_text}")
                entries[img_path.name] = f"erro: {error_text}"
                _write_output(output, entries, header_lines)

                if abort_batch:
                    print(
                        "Quota diaria esgotada detectada; interrompendo o lote. "
                        "Use --continue-on-quota-exhausted para forcar continuidade."
                    )
                    break
        except KeyboardInterrupt:
            interrupted = True
            print("Interrompido pelo usuario (Ctrl+C). Salvando resultado parcial...")

        _write_output(output, entries, header_lines)
        print(f"Salvo em {output}")
    finally:
        if client is not None:
            client.close()

    return 130 if interrupted else 0


if __name__ == "__main__":
    raise SystemExit(main())
