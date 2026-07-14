from app.schemas import ParsedPurchase


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_parse_endpoint_stores_transaction(client, mocker):
    mocker.patch(
        "app.service.get_parser",
        return_value=mocker.Mock(
            parse=mocker.Mock(
                return_value=ParsedPurchase(
                    customer_name="Ramesh",
                    action="bought",
                    item="Sugar",
                    quantity=2,
                    unit="kg",
                    confidence=0.95,
                )
            )
        ),
    )

    resp = client.post("/parse", json={"message": "Ramesh bought 2kg Sugar"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["customer_name"] == "Ramesh"
    assert body["item"] == "Sugar"
    assert body["quantity"] == 2
    assert body["status"] == "parsed"


def test_list_transactions_after_insert(client, mocker):
    mocker.patch(
        "app.service.get_parser",
        return_value=mocker.Mock(
            parse=mocker.Mock(
                return_value=ParsedPurchase(
                    customer_name="Sita", action="returned", item="Biscuits",
                    quantity=1, unit="packet", confidence=0.9,
                )
            )
        ),
    )
    client.post("/parse", json={"message": "Sita returned 1 packet biscuits"})

    resp = client.get("/transactions", params={"customer_name": "Sita"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] >= 1
    assert body["results"][0]["customer_name"] == "Sita"


def test_low_confidence_marks_needs_review(client, mocker):
    mocker.patch(
        "app.service.get_parser",
        return_value=mocker.Mock(
            parse=mocker.Mock(
                return_value=ParsedPurchase(
                    customer_name="Unknown", action=None, item="something",
                    quantity=None, unit=None, confidence=0.2,
                )
            )
        ),
    )
    resp = client.post("/parse", json={"message": "hmm not sure what this is"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "needs_review"
