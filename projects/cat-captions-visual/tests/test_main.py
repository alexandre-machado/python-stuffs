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


@patch("urllib.request.urlopen")
def test_local_lm_studio_run_webp(mock_urlopen, tmp_path):
    from PIL import Image
    import io

    # Mock return value of urlopen to simulate streaming
    mock_response = MagicMock()
    mock_response.__iter__.return_value = [
        b'data: {"choices": [{"delta": {"content": "Gatinha no webp."}}]}\n',
        b'data: [DONE]\n'
    ]
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    # Setup media dir and create a real 1x1 transparent WebP image
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    
    img = Image.new("RGBA", (1, 1), color=(255, 0, 0, 128))
    img_bytes_io = io.BytesIO()
    img.save(img_bytes_io, format="WEBP")
    
    img_file = media_dir / "cat1.webp"
    img_file.write_bytes(img_bytes_io.getvalue())

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
    assert "[cat1.webp]" in content
    assert "Gatinha no webp." in content

    # Verify that urlopen was called and check the payload mime type
    assert mock_urlopen.call_count == 1
    args_list, kwargs = mock_urlopen.call_args
    req = args_list[0]
    payload = json.loads(req.data.decode("utf-8"))
    
    image_url_block = payload["messages"][0]["content"][1]["image_url"]["url"]
    # Check that it converted the webp image to jpeg format
    assert image_url_block.startswith("data:image/jpeg;base64,")

