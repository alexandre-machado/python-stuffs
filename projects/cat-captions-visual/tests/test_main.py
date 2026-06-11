import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import main


def test_main_runs():
    # smoke test: main() roda sem levantar exceção
    main.main()


@patch("urllib.request.urlopen")
def test_local_lm_studio_run(mock_urlopen, tmp_path):
    # Mock return value of urlopen to simulate streaming
    mock_response = MagicMock()
    mock_response.__iter__.return_value = [
        b'data: {"choices": [{"delta": {"content": "Gatinha "}}]}\n',
        b'data: {"choices": [{"delta": {"content": "fofa "}}]}\n',
        b'data: {"choices": [{"delta": {"content": "dormindo."}}]}\n',
        b'data: [DONE]\n'
    ]
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    # Setup media dir and image
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    img_file = media_dir / "cat1.jpg"
    img_file.write_bytes(b"dummy image data")

    # Setup output path
    output_file = tmp_path / "output.md"

    # Call main with local/lm-studio parameters
    args = [
        "--media-dir", str(media_dir),
        "--output", str(output_file),
        "--lm-studio",
    ]
    exit_code = main.main(args)

    # Assertions
    assert exit_code == 0
    assert output_file.exists()
    
    content = output_file.read_text(encoding="utf-8")
    assert "Gerado via qwen/qwen3.6-35b-a3b (LM Studio Local)" in content
    assert "[cat1.jpg]" in content
    assert "Gatinha fofa dormindo." in content

    # Verify that urlopen was called once with the correct URL
    assert mock_urlopen.call_count == 1
    args_list, kwargs = mock_urlopen.call_args
    req = args_list[0]
    assert req.full_url == "http://localhost:1234/v1/chat/completions"
    assert req.method == "POST"
