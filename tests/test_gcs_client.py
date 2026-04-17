from unittest.mock import MagicMock

import pytest

from src.services.gcs import client as gcs_client


def test_parse_gcs_uri_ok():
    assert gcs_client.parse_gcs_uri("gs://bucket/foo/bar.pdf") == (
        "bucket",
        "foo/bar.pdf",
    )


def test_parse_gcs_uri_rejects_bad():
    with pytest.raises(ValueError):
        gcs_client.parse_gcs_uri("https://bucket/foo")
    with pytest.raises(ValueError):
        gcs_client.parse_gcs_uri("gs://bucket")


def test_upload_bytes(monkeypatch):
    fake_blob = MagicMock()
    fake_bucket = MagicMock()
    fake_bucket.blob.return_value = fake_blob
    fake_storage_client = MagicMock()
    fake_storage_client.bucket.return_value = fake_bucket
    monkeypatch.setattr(gcs_client, "get_client", lambda: fake_storage_client)

    uri = gcs_client.upload_bytes("gtm-uploads/abc/x.pdf", b"data", "application/pdf")
    assert uri == "gs://test-bucket/gtm-uploads/abc/x.pdf"
    fake_storage_client.bucket.assert_called_once_with("test-bucket")
    fake_bucket.blob.assert_called_once_with("gtm-uploads/abc/x.pdf")
    fake_blob.upload_from_string.assert_called_once_with(
        b"data", content_type="application/pdf"
    )


def test_download_bytes(monkeypatch):
    fake_blob = MagicMock()
    fake_blob.download_as_bytes.return_value = b"hello"
    fake_bucket = MagicMock()
    fake_bucket.blob.return_value = fake_blob
    fake_storage_client = MagicMock()
    fake_storage_client.bucket.return_value = fake_bucket
    monkeypatch.setattr(gcs_client, "get_client", lambda: fake_storage_client)

    out = gcs_client.download_bytes("gs://test-bucket/foo/bar.pdf")
    assert out == b"hello"


def test_delete_object_swallows_errors(monkeypatch):
    fake_storage_client = MagicMock()
    fake_storage_client.bucket.side_effect = RuntimeError("boom")
    monkeypatch.setattr(gcs_client, "get_client", lambda: fake_storage_client)
    # should not raise
    gcs_client.delete_object("gs://test-bucket/foo.pdf")
