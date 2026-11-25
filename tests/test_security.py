import pytest

@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_nginx_blocks_documentation(http_client, path):
    """ Nginx zwraca 403 dla publicznej dokumentacji Swagger/ReDoc """
    response = http_client.get(path)
    assert response.status_code == 403

@pytest.mark.parametrize("method", ["PUT", "DELETE", "PATCH", "OPTIONS"])
def test_nginx_blocks_methods(http_client, method):
    """ Nginx odrzuca metody inne niż GET i POST """
    response = http_client.request(method, "/")
    assert response.status_code == 405

def test_nginx_security_headers(http_client):
    """ Weryfikacja naglowkow bezpieczenstwa dodawanych przez Nginx """
    response = http_client.get("/")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert "max-age=31536000" in response.headers.get("Strict-Transport-Security", "")

def test_nginx_oversized_payload(http_client, rasp_headers):
    """ Nginx odrzuca zadania przekraczajace client_max_body_size 16k """
    huge_payload = {"data": "A" * 20_000}
    response = http_client.post(
        "/api/auth/courier-login",
        json = huge_payload,
        headers = rasp_headers,
    )
    assert response.status_code == 413

def test_api_missing_invalid_api_key(http_client, seed_data):
    """ Endpointy IoT i Admin odrzucaja brak lub bledny naglowek x-api-key """
    machine_id = seed_data["machine_id"]

    res_no_key = http_client.get(f"/api/machines/{machine_id}/lockers")
    assert res_no_key.status_code == 403

    res_bad_key = http_client.get(
        f"/api/machines/{machine_id}/lockers",
        headers={"x-api-key": "nieprawidlowy-klucz"},
    )
    assert res_bad_key.status_code == 403

    admin_bad_key = http_client.post(
        f"/api/machines/{machine_id}/service-close",
        headers={"x-api-key": "nieprawidlowy-klucz"},
    )
    assert admin_bad_key.status_code == 403

def test_nginx_rate_limit_login(http_client, rasp_headers):
    """ Weryfikacja ochrony przed brute-force na logowaniu kuriera (limit 1r/s, burst=3) """
    statuses = []
    for _ in range(5):
        res = http_client.post(
            "/api/auth/courier-login",
            json = {"courier_login": "nieistniejacy", "password": "blednehaslo12345!"},
            headers = rasp_headers,
        )
        statuses.append(res.status_code)

    assert 429 in statuses, f"Oczekiwano blokady 429 Too Many Requests, otrzymano: {statuses}"