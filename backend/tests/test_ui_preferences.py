from fastapi.testclient import TestClient


def test_get_ui_preferences_reflects_settings(client: TestClient, test_settings):
    test_settings.ui.theme = "sunset"
    test_settings.ui.accent_color = "warm"
    test_settings.ui.sidebar_collapsed = True

    response = client.get("/api/ui/preferences")

    assert response.status_code == 200
    assert response.json() == {
        "theme": "sunset",
        "accent_color": "warm",
        "sidebar_collapsed": True,
    }


def test_update_ui_preferences_updates_settings_and_saves(client: TestClient, test_settings, monkeypatch):
    saved = {}

    def fake_save(cfg):
        saved["theme"] = cfg.ui.theme
        saved["accent"] = cfg.ui.accent_color
        saved["collapsed"] = cfg.ui.sidebar_collapsed

    monkeypatch.setattr("app.main.save_config", fake_save)

    response = client.put(
        "/api/ui/preferences",
        json={"theme": "synthwave", "accent_color": "sand", "sidebar_collapsed": False},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Preferences saved"
    assert body["theme"] == "synthwave"

    assert test_settings.ui.theme == "synthwave"
    assert test_settings.ui.accent_color == "sand"
    assert not test_settings.ui.sidebar_collapsed

    assert saved == {"theme": "synthwave", "accent": "sand", "collapsed": False}
