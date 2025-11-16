import pytest


@pytest.mark.django_db
def test_docs_and_schema_available(client):
    resp_schema = client.get("/api/v1/schema/")
    resp_docs = client.get("/api/v1/docs/")

    assert resp_schema.status_code in (200, 403)  # 403 if auth-protected
    assert resp_docs.status_code in (200, 403)
