import time

def test_01_get_machine_lockers(http_client, rasp_headers, seed_data):
    """ GET /api/machines/KR001/lockers - pobieranie stanu skrytek """
    machine_id = seed_data["machine_id"]
    response = http_client.get(f"/api/machines/{machine_id}/lockers", headers=rasp_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["machine_id"] == "KR001"
    assert len(body["lockers"]) == 5

def test_02_sender_create_package(http_client, rasp_headers, seed_data):
    """ POST /api/machines/KR001/sender/create-package - nadanie nowej paczki """
    machine_id = seed_data["machine_id"]
    payload = {
        "recipient_phone": seed_data["new_pkg_phone"],
        "target_machine_id": machine_id,
    }

    response = http_client.post(f"/api/machines/{machine_id}/sender/create-package", json=payload, headers=rasp_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True

def test_03_courier_login(http_client, rasp_headers, seed_data, secure_state):
    """ POST /api/auth/courier-login - logowanie kuriera i zapis tokenu w keyring """
    time.sleep(1.5)
    payload = {
        "courier_login": seed_data["courier_login"],
        "password": seed_data["courier_pass"],
    }

    response = http_client.post("/api/auth/courier-login", json=payload, headers=rasp_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is True
    secure_state.set("courier_token", body["token_session"])

def test_04_get__courier_pickups(http_client, rasp_headers, seed_data, secure_state):
    """ GET /api/machines/KR001/courier/pickups - lista paczek do odbioru przez kuriera """
    token = secure_state.get("courier_token")
    assert token is not None, "Brak tokenu w keyring, uruchom najpierw test_03"

    machine_id = seed_data["machine_id"]
    headers = {**rasp_headers, "Authorization": f"Bearer {token}"}
    response = http_client.get(f"/api/machines/{machine_id}/courier/pickups", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True

def test_05_confirm_courier_pickups(http_client, rasp_headers, seed_data, secure_state):
    """ POST /api/machines/KR001/courier/confirm-pickups - potwierdzenie odbioru paczek """
    token = secure_state.get("courier_token")
    assert token is not None, "Brak tokenu w keyring, uruchom najpierw test_03 i test_04"

    machine_id = seed_data["machine_id"]
    headers = {**rasp_headers, "Authorization": f"Bearer {token}"}
    response = http_client.post(f"/api/machines/{machine_id}/courier/confirm-pickups", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True

def test_06_courier_deliver(http_client, rasp_headers, seed_data, secure_state):
    """ POST /api/machines/KR001/courier/deliver - umieszczenie paczki w maszynie """
    token = secure_state.get("courier_token")
    assert token is not None, "Brak tokenu w keyring, uruchom najpierw test_03"

    machine_id = seed_data["machine_id"]
    headers = {**rasp_headers, "Authorization": f"Bearer {token}"}
    payload = {"package_number": seed_data["courier_pkg"]}

    response = http_client.post(f"/api/machines/{machine_id}/courier/deliver", json=payload, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True    

def test_07_recipient_pickup(http_client, rasp_headers, seed_data):
    """ POST /api/machines/KR001/recipient/pickup - odbior pacczki """
    machine_id = seed_data["machine_id"]
    payload = {
        "recipient_phone": seed_data["pickup_phone"],
        "pin_code": seed_data["pickup_pin"],
    }

    response = http_client.post(f"/api/machines/{machine_id}/recipient/pickup", json=payload, headers=rasp_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True 
    assert body["locker_id"] == "KR001_POX2"

def test_08_tech_verify_and_service_close(http_client, admin_headers, seed_data):
    """ POST /api/auth/technician-verify i /api/machines/KR001/service-close - cykl serwisowy"""
    machine_id = seed_data["machine_id"]
    payload ={
        "machine_id": machine_id, 
        "full_name": seed_data["technician_name"]
    }

    res_verify = http_client.post("/api/auth/technician-verify", json=payload, headers=admin_headers)
    assert res_verify.status_code == 200
    body = res_verify.json()
    assert body["access_granted"] is True
    assert body["service_locker"] == "KR001_SRV1"

    res_close = http_client.post(f"/api/machines/{machine_id}/service-close", headers=admin_headers)
    assert res_close.status_code == 200
    body2 = res_close.json()
    assert body2["success"] is True

def test_09_courier_logout(http_client, rasp_headers, seed_data, secure_state):
    """ POST /api/auth/courier-logout - wylogowanie i usuniecie tokenu z sejfu"""
    token = secure_state.get("courier_token")
    assert token is not None, "Brak tokenu w keyring"

    headers = {**rasp_headers, "Authorization": f"Bearer {token}"}
    res_logout = http_client.post("/api/auth/courier-logout", headers=headers)
    assert res_logout.status_code == 200
    body = res_logout.json()
    assert body["success"] is True

    secure_state.delete("courier_token")

    # Weryfikacja ze odrzucony token zwraca 401
    machine_id = seed_data["machine_id"]
    res_after = http_client.get(f"/api/machines/{machine_id}/courier/pickups", headers=headers)
    assert res_after.status_code == 401
