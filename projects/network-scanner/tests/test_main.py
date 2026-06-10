import main


def test_isreachable_offline_port():
    # porta 1 do localhost normalmente está fechada -> offline, rápido
    result = main.isReachable("127.0.0.1", 1, timeout=1)
    assert "offline" in result
