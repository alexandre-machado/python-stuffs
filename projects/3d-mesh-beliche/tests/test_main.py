import main


def test_draw_block_volume():
    # bloco 2x3x4 deve ter volume 24
    box = main.draw_block("teste", 0, 0, 0, 2.0, 3.0, 4.0)
    assert box.volume == 24.0
    assert box.metadata["name"] == "teste"
