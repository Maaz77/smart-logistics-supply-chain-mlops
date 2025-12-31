from src.utils.common import read_yaml


def test_read_yaml(tmp_path):
    d = tmp_path / "configs"
    d.mkdir()
    p = d / "test.yaml"
    p.write_text("key: value")

    content = read_yaml(str(p))
    assert content == {"key": "value"}
