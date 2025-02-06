import httpx

client = httpx.AsyncClient()

def get_client() -> httpx.AsyncClient:
    return client
