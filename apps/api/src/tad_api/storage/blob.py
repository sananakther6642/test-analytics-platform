"""Raw uploaded file storage — separate from RunStore's parsed data.

Per the plan's architecture: the raw uploaded TRF file goes to Blob,
the parsed structured data goes to Postgres (RunStore). This is a
distinct interface, not a RunStore implementation, because the two
store genuinely different things keyed the same way (run_id), not
interchangeable views of one thing.

NullBlobStore is the default everywhere Blob isn't configured (local
Compose dev, unit tests) — uploads still work, the raw file is just not
retained. This matches RunStore's pattern of always having a working
no-dependency default rather than making Blob a hard requirement to
run the app at all.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class ReportBlobStore(ABC):
    @abstractmethod
    async def save(self, run_id: str, raw: bytes) -> None: ...

    @abstractmethod
    async def get(self, run_id: str) -> bytes | None: ...


class NullBlobStore(ReportBlobStore):
    async def save(self, run_id: str, raw: bytes) -> None:
        return None

    async def get(self, run_id: str) -> bytes | None:
        return None


class AzureBlobStore(ReportBlobStore):
    """Blob-backed store, authenticated via managed identity.

    Uses DefaultAzureCredential rather than a connection string or account
    key — this is the same zero-secrets pattern as Key Vault access and
    ACR pull (D3.3).

    DefaultAzureCredential does NOT automatically pick a user-assigned
    identity when a container has more than one identity or the one it
    has isn't system-assigned — with no client ID it only tries
    system-assigned managed identity and fails with "Unable to load the
    proper Managed Identity" on this project's user-assigned-only setup
    (see ADR 0008 for why user-assigned was deliberately chosen over
    system-assigned). managed_identity_client_id must be passed
    explicitly.

    One blob per run, named "{run_id}.raw" — the parser already
    determined the format when producing the ParsedRun, so no extension
    is needed to know how to re-parse it later.
    """

    def __init__(
        self, account_url: str, container: str, managed_identity_client_id: str | None
    ) -> None:
        # Imported here, not at module level: azure-storage-blob and
        # azure-identity are real dependencies only this class needs.
        # NullBlobStore (the default everywhere else) has no SDK import,
        # so local dev and unit tests never need these packages installed.
        from azure.identity.aio import DefaultAzureCredential
        from azure.storage.blob.aio import ContainerClient

        self._credential = DefaultAzureCredential(
            managed_identity_client_id=managed_identity_client_id
        )
        self._container = ContainerClient(
            account_url=account_url,
            container_name=container,
            credential=self._credential,
        )

    async def save(self, run_id: str, raw: bytes) -> None:
        await self._container.upload_blob(
            name=f"{run_id}.raw", data=raw, overwrite=True
        )

    async def get(self, run_id: str) -> bytes | None:
        blob = self._container.get_blob_client(f"{run_id}.raw")
        if not await blob.exists():
            return None
        stream = await blob.download_blob()
        return await stream.readall()

    async def aclose(self) -> None:
        await self._container.close()
        await self._credential.close()
