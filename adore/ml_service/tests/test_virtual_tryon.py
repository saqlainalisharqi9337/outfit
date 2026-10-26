"""Magic Hour client-backed clothes changer helpers."""

from app.virtual_tryon import TryOnError, api_key, image_from_payload


def test_key_loader_reads_env(monkeypatch):
    monkeypatch.setenv("ADORE_MAGIC_HOUR_API_KEY", "mhk_live_test")
    assert api_key() == "mhk_live_test"


def test_missing_downloads_is_empty():
    assert image_from_payload({"status": "complete", "downloads": []}) is None


def test_try_on_error_keeps_status():
    err = TryOnError("no credits", status=402)
    assert err.status == 402
    assert "credits" in err.message
