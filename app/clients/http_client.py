import httpx

class HTTPClient:
    _client: httpx.AsyncClient | None = None

    def __new__(cls):
        if cls._client is None:
            cls._client = httpx.AsyncClient()
        return cls._client
