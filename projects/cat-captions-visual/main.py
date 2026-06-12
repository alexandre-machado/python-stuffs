import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
import mimetypes
import os
import re
import shutil
import sys
import threading
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


class ConsoleProgressBar:
    def __init__(self, total: int, completed_start: int):
        self.total = total
        self.completed = completed_start
        self.processed_this_session = 0
        self.start_time = time.time()
        self.current_files = set()
        self.active = False
        self.thread = None
        self.lock = threading.Lock()
        self.spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.spinner_idx = 0
        self.lines_drawn = 0
        self.is_tty = sys.stdout.isatty()
        self.speed_str = "-- img/s"
        self.eta_datetime = None

    def start_image(self, file_name: str):
        with self.lock:
            self.current_files.add(file_name)
            self.active = True
            if self.is_tty:
                if self.thread is None or not self.thread.is_alive():
                    self.thread = threading.Thread(target=self._run, daemon=True)
                    self.thread.start()
            else:
                print(f"Processando {file_name}...")

    def finish_image(self, file_name: str, success: bool):
        with self.lock:
            self.current_files.discard(file_name)
            if not self.current_files:
                self.active = False
        
        if self.thread and not self.active:
            self.thread.join(timeout=0.5)
        
        if self.is_tty:
            self._clear_lines()
            
        with self.lock:
            if success:
                self.completed += 1
            self.processed_this_session += 1
            
            # Atualiza velocidade e ETA no fim de cada imagem processada
            elapsed = time.time() - self.start_time
            if self.processed_this_session > 0 and elapsed > 0:
                speed = self.processed_this_session / elapsed
                if speed >= 1.0:
                    self.speed_str = f"{speed:.2f} img/s"
                else:
                    self.speed_str = f"{1.0 / speed:.2f} s/img"
                
                remaining = self.total - self.completed
                if remaining > 0:
                    eta_seconds = remaining / speed
                    self.eta_datetime = datetime.now() + timedelta(seconds=eta_seconds)
                else:
                    self.eta_datetime = None

    def print_log(self, message: str):
        """Imprime mensagens de log (como retentativas) sem bagunçar a barra."""
        with self.lock:
            if self.is_tty:
                self._clear_lines()
            print(message)
            if self.is_tty:
                self._draw_lines()

    def _clear_lines(self):
        if self.lines_drawn > 0:
            sys.stdout.write(f"\033[{self.lines_drawn}A\r")
            for _ in range(self.lines_drawn):
                sys.stdout.write("\033[K\n")
            sys.stdout.write(f"\033[{self.lines_drawn}A\r")
            sys.stdout.flush()
            self.lines_drawn = 0

    def _draw_lines(self):
        if not self.active or not self.current_files:
            return

        # Determinamos o caractere do spinner atual
        spinner = self.spinner_chars[self.spinner_idx]
        self.spinner_idx = (self.spinner_idx + 1) % len(self.spinner_chars)
        
        # Geramos uma linha de processamento para cada imagem ativa
        files_list = sorted(list(self.current_files))
        lines = []
        for file_name in files_list:
            lines.append(f"{spinner} Processando {file_name}")

        percent = (self.completed / self.total) * 100 if self.total > 0 else 0
        
        # Calcular o ETA regressivo na tela
        if self.eta_datetime is not None:
            remaining_sec = (self.eta_datetime - datetime.now()).total_seconds()
            if remaining_sec > 0:
                if remaining_sec < 3600:
                    eta_str = f"ETA: {int(remaining_sec // 60):02d}:{int(remaining_sec % 60):02d}"
                else:
                    hours = int(remaining_sec // 3600)
                    mins = int((remaining_sec % 3600) // 60)
                    secs = int(remaining_sec % 60)
                    eta_str = f"ETA: {hours:02d}:{mins:02d}:{secs:02d}"
            else:
                eta_str = "ETA: 00:00"
            eta_str += f" ({self.eta_datetime.strftime('%H:%M:%S')})"
        else:
            eta_str = "ETA: --"

        bar_width = 20
        filled = int(bar_width * (self.completed / self.total)) if self.total > 0 else 0
        bar = "█" * filled + "░" * (bar_width - filled)

        # Adiciona a última linha (a barra de progresso)
        lines.append(f"[{bar}] {percent:.1f}% ({self.completed}/{self.total}) | {self.speed_str} | {eta_str}")

        if self.lines_drawn > 0:
            sys.stdout.write(f"\033[{self.lines_drawn}A\r")

        for line in lines:
            sys.stdout.write(line + "\033[K\n")
        sys.stdout.flush()
        self.lines_drawn = len(lines)

    def _run(self):
        while True:
            with self.lock:
                if not self.active:
                    break
                self._draw_lines()
            time.sleep(0.1)

    def stop(self):
        with self.lock:
            self.active = False
        if self.thread:
            self.thread.join(timeout=0.5)
        if self.is_tty:
            self._clear_lines()


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
    parser.add_argument(
        "--parallel",
        type=int,
        default=2,
        help="Quantidade de imagens a processar em paralelo (padrao: 2)",
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
    from io import BytesIO

    mime_type = _mime_type_for_image(img_path)

    if mime_type == "image/webp":
        try:
            from PIL import Image
            with Image.open(img_path) as img:
                if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                    img = img.convert("RGB")
                buffer = BytesIO()
                img.save(buffer, format="JPEG")
                image_bytes = buffer.getvalue()
                mime_type = "image/jpeg"
        except ImportError:
            with img_path.open("rb") as file_obj:
                image_bytes = file_obj.read()
    else:
        with img_path.open("rb") as file_obj:
            image_bytes = file_obj.read()

    img_b64 = base64.b64encode(image_bytes).decode("utf-8")

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
                except json.JSONDecodeError:
                    continue
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
    print_func=print,
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
                    print_func(
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
                print_func(
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
                print_func(
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
                print_func(
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

    all_images = _iter_images(media_dir)
    progress_bar = ConsoleProgressBar(total=len(all_images), completed_start=len(completed))

    if is_local:
        header_text = f"Gerado via {args.model} (LM Studio Local)\n"
    else:
        header_text = "Gerado via Gemini\n"
    header_lines = ["# Descrições visuais - Miau Duda\n", header_text, "---\n"]

    write_lock = threading.Lock()
    abort_all = False
    futures = {}

    def process_one_image(img_path):
        nonlocal abort_all
        if abort_all:
            return

        progress_bar.start_image(img_path.name)
        try:
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
                print_func=progress_bar.print_log,
            )
        except Exception as e:
            text, error_text, abort_batch = None, str(e), False

        with write_lock:
            if abort_all:
                progress_bar.finish_image(img_path.name, success=False)
                return

            if text is not None:
                text = " ".join(text.replace("\n", " ").replace("\r", " ").split())
                entries[img_path.name] = text
                completed.add(img_path.name)
                _write_output(output, entries, header_lines)
                progress_bar.finish_image(img_path.name, success=True)
                
                columns = shutil.get_terminal_size().columns
                prefix = f"OK {img_path.name} ["
                suffix = "]"
                max_text_len = columns - len(prefix) - len(suffix)
                if len(text) > max_text_len and max_text_len > 3:
                    display_text = text[:max_text_len - 3] + "..."
                else:
                    display_text = text
                print(f"{prefix}{display_text}{suffix}")
            else:
                progress_bar.finish_image(img_path.name, success=False)
                print(f"ERRO {img_path.name}: {error_text}")
                entries[img_path.name] = f"erro: {error_text}"
                _write_output(output, entries, header_lines)

            if abort_batch:
                abort_all = True

    try:
        try:
            images_to_process = [img for img in all_images if img.name not in completed]
            for img in all_images:
                if img.name in completed:
                    print(f"SKIP {img.name} (ja concluido no output)")

            if images_to_process:
                with ThreadPoolExecutor(max_workers=args.parallel) as executor:
                    futures = {executor.submit(process_one_image, img): img for img in images_to_process}
                    for future in as_completed(futures):
                        if abort_all:
                            for f in futures:
                                f.cancel()
                        future.result()
        except KeyboardInterrupt:
            interrupted = True
            active_files = list(progress_bar.current_files)
            progress_bar.stop()
            for file_name in sorted(active_files):
                print(f"CANCELED {file_name}")
            for f in futures:
                f.cancel()
            _write_output(output, entries, header_lines)
            os._exit(130)

        progress_bar.stop()
        _write_output(output, entries, header_lines)
        print(f"Salvo em {output}")
    finally:
        progress_bar.stop()
        if client is not None:
            client.close()

    return 130 if interrupted else 0


if __name__ == "__main__":
    raise SystemExit(main())
