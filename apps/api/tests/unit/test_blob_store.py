"""NullBlobStore is the only variant exercised in unit tests — AzureBlobStore
needs a real (or mocked) Azure SDK client, which belongs in an integration
test if one is ever added, not here. This just confirms the no-op contract
upload_report's error paths rely on: save/get never raise, get always
returns None.
"""

from tad_api.storage.blob import NullBlobStore


async def test_null_blob_store_save_is_a_noop():
    store = NullBlobStore()
    await store.save("run-1", b"raw bytes")  # must not raise


async def test_null_blob_store_get_always_returns_none():
    store = NullBlobStore()
    await store.save("run-1", b"raw bytes")
    assert await store.get("run-1") is None
    assert await store.get("nonexistent") is None
