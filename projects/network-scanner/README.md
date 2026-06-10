# network-scanner

Varre a sub-rede `192.168.0.0/24` em paralelo procurando hosts com a porta **554
(RTSP)** aberta — útil para localizar câmeras IP na rede local. Usa um pool de
processos e barra de progresso (`tqdm`).

## Rodar

```bash
uv run main.py
```

> Depende da rede local: o resultado varia conforme os hosts ativos. A faixa de IPs
> está fixa em `192.168.0.0/24` no `main()`.

## Testar

```bash
uv run pytest
```
