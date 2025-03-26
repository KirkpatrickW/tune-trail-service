import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from httpx import HTTPStatusError, Response, ReadTimeout, ConnectError, RemoteProtocolError
from app.utils.http_helpers import (
    RetryConfig,
    handle_rate_limit,
    handle_retry,
    METHODS,
    METHOD_ARGUMENTS,
    http_client  # Import the singleton instance
)

@pytest.fixture
def mock_sleep():
    with patch('asyncio.sleep', new_callable=AsyncMock) as mock:
        yield mock

@pytest.fixture
def mock_http_client():
    # Store original methods
    original_get = METHODS['GET']
    original_post = METHODS['POST']
    original_put = METHODS['PUT']
    original_delete = METHODS['DELETE']

    # Create mock methods
    get_mock = AsyncMock()
    post_mock = AsyncMock()
    put_mock = AsyncMock()
    delete_mock = AsyncMock()

    # Replace methods in METHODS dictionary
    METHODS['GET'] = get_mock
    METHODS['POST'] = post_mock
    METHODS['PUT'] = put_mock
    METHODS['DELETE'] = delete_mock

    # Create a mock client that properly handles multiple calls
    mock_client = MagicMock(
        get=get_mock,
        post=post_mock,
        put=put_mock,
        delete=delete_mock
    )

    yield mock_client

    # Restore original methods
    METHODS['GET'] = original_get
    METHODS['POST'] = original_post
    METHODS['PUT'] = original_put
    METHODS['DELETE'] = original_delete

@pytest.fixture
def mock_response():
    response = MagicMock(spec=Response)
    response.json.return_value = {"data": "test"}
    response.raise_for_status = MagicMock()
    response.headers = {}
    return response

@pytest.fixture
def rate_limit_event():
    event = asyncio.Event()
    event.set()
    return event

@pytest.mark.asyncio
async def test_handle_rate_limit(rate_limit_event, mock_sleep):
    await handle_rate_limit(rate_limit_event, 1)
    assert rate_limit_event.is_set()
    mock_sleep.assert_called_once_with(1)

@pytest.mark.asyncio
async def test_handle_retry_success(mock_http_client, mock_response, rate_limit_event, mock_sleep):
    mock_http_client.get.return_value = mock_response

    result = await handle_retry(
        RetryConfig(
            rate_limit_event=rate_limit_event,
            max_retries=3,
            retry_after_fallback=5
        ),
        method="GET",
        url="http://test.com"
    )

    assert result == {"data": "test"}
    assert mock_http_client.get.call_args.kwargs == {
        "url": "http://test.com",
        "headers": None,
        "auth": None,
        "params": None
    }
    mock_sleep.assert_not_called()

@pytest.mark.asyncio
async def test_handle_retry_with_post(mock_http_client, mock_response, rate_limit_event, mock_sleep):
    mock_http_client.post.return_value = mock_response

    result = await handle_retry(
        RetryConfig(
            rate_limit_event=rate_limit_event,
            max_retries=3,
            retry_after_fallback=5
        ),
        method="POST",
        url="http://test.com",
        json={"key": "value"}
    )

    assert result == {"data": "test"}
    assert mock_http_client.post.call_args.kwargs == {
        "url": "http://test.com",
        "headers": None,
        "auth": None,
        "params": None,
        "json": {"key": "value"}
    }
    mock_sleep.assert_not_called()

@pytest.mark.asyncio
async def test_handle_retry_with_put(mock_http_client, mock_response, rate_limit_event, mock_sleep):
    mock_http_client.put.return_value = mock_response

    result = await handle_retry(
        RetryConfig(
            rate_limit_event=rate_limit_event,
            max_retries=3,
            retry_after_fallback=5
        ),
        method="PUT",
        url="http://test.com",
        json={"key": "value"}
    )

    assert result == {"data": "test"}
    assert mock_http_client.put.call_args.kwargs == {
        "url": "http://test.com",
        "headers": None,
        "auth": None,
        "params": None,
        "json": {"key": "value"}
    }
    mock_sleep.assert_not_called()

@pytest.mark.asyncio
async def test_handle_retry_with_delete(mock_http_client, mock_response, rate_limit_event, mock_sleep):
    mock_http_client.delete.return_value = mock_response

    result = await handle_retry(
        RetryConfig(
            rate_limit_event=rate_limit_event,
            max_retries=3,
            retry_after_fallback=5
        ),
        method="DELETE",
        url="http://test.com"
    )

    assert result == {"data": "test"}
    assert mock_http_client.delete.call_args.kwargs == {
        "url": "http://test.com",
        "headers": None,
        "auth": None,
        "params": None
    }
    mock_sleep.assert_not_called()

@pytest.mark.asyncio
async def test_handle_retry_rate_limit(mock_http_client, rate_limit_event, mock_sleep):
    # First call raises rate limit
    rate_limit_response = MagicMock(spec=Response)
    rate_limit_response.raise_for_status.side_effect = HTTPStatusError(
        "Rate limit", request=MagicMock(), response=MagicMock(status_code=429, headers={"Retry-After": "2"})
    )
    rate_limit_response.headers = {"Retry-After": "2"}
    
    # Second call succeeds
    success_response = MagicMock(spec=Response)
    success_response.json.return_value = {"data": "success"}
    success_response.raise_for_status.return_value = None
    success_response.headers = {}

    mock_http_client.get.side_effect = [rate_limit_response, success_response]

    result = await handle_retry(
        RetryConfig(
            rate_limit_event=rate_limit_event,
            max_retries=3,
            retry_after_fallback=5
        ),
        method="GET",
        url="http://test.com"
    )

    assert result == {"data": "success"}
    assert mock_http_client.get.call_count == 2
    mock_sleep.assert_called_once_with(2)

@pytest.mark.asyncio
async def test_handle_retry_with_custom_validator(mock_http_client, rate_limit_event, mock_sleep):
    def validate_rate_limit(response):
        return response.get("rate_limited", False)

    # First response indicates rate limit
    rate_limit_response = MagicMock(spec=Response)
    rate_limit_response.json.return_value = {"rate_limited": True}
    rate_limit_response.raise_for_status.return_value = None
    rate_limit_response.headers = {"Retry-After": "2"}

    # Second response succeeds
    success_response = MagicMock(spec=Response)
    success_response.json.return_value = {"data": "success"}
    success_response.raise_for_status.return_value = None
    success_response.headers = {}

    mock_http_client.get.side_effect = [rate_limit_response, success_response]

    result = await handle_retry(
        RetryConfig(
            rate_limit_event=rate_limit_event,
            max_retries=3,
            retry_after_fallback=5,
            validate_rate_limit_body=validate_rate_limit
        ),
        method="GET",
        url="http://test.com"
    )

    assert result == {"data": "success"}
    assert mock_http_client.get.call_count == 2
    mock_sleep.assert_called_once_with(2)

@pytest.mark.asyncio
async def test_handle_retry_invalid_method(mock_http_client, rate_limit_event, mock_sleep):
    with pytest.raises(HTTPException) as exc_info:
        await handle_retry(
            RetryConfig(
                rate_limit_event=rate_limit_event,
                max_retries=3,
                retry_after_fallback=5
            ),
            method="INVALID",
            url="http://test.com"
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Unsupported HTTP method"
    mock_http_client.get.assert_not_called()
    mock_http_client.post.assert_not_called()
    mock_http_client.put.assert_not_called()
    mock_http_client.delete.assert_not_called()
    mock_sleep.assert_not_called()

@pytest.mark.asyncio
async def test_handle_retry_invalid_body(mock_http_client, rate_limit_event, mock_sleep):
    with pytest.raises(HTTPException) as exc_info:
        await handle_retry(
            RetryConfig(
                rate_limit_event=rate_limit_event,
                max_retries=3,
                retry_after_fallback=5
            ),
            method="GET",
            url="http://test.com",
            json={"key": "value"}
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "GET requests cannot have a JSON body"
    mock_http_client.get.assert_not_called()
    mock_sleep.assert_not_called()

@pytest.mark.asyncio
async def test_handle_retry_http_errors(mock_http_client, rate_limit_event, mock_sleep):
    error_response = MagicMock(spec=Response)
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 404
    mock_response.headers = {}  # Add headers to the mock response
    error_response.raise_for_status.side_effect = HTTPStatusError(
        "API rate limit exceeded or unexpected error", request=MagicMock(), response=mock_response
    )
    error_response.headers = {}
    mock_http_client.get.return_value = error_response

    with pytest.raises(HTTPException) as exc_info:
        await handle_retry(
            RetryConfig(
                rate_limit_event=rate_limit_event,
                max_retries=1,  # Only try once
                retry_after_fallback=5
            ),
            method="GET",
            url="http://test.com"
        )

    assert exc_info.value.status_code == 500  # Production code converts all non-rate-limit errors to 500
    assert exc_info.value.detail == "API rate limit exceeded or unexpected error"
    mock_sleep.assert_not_called()

@pytest.mark.asyncio
async def test_handle_retry_network_errors(mock_http_client, rate_limit_event, mock_sleep):
    # First call raises network error
    success_response = MagicMock(spec=Response)
    success_response.json.return_value = {"data": "success"}
    success_response.raise_for_status.return_value = None
    success_response.headers = {}

    mock_http_client.get.side_effect = [
        ReadTimeout("Network timeout"),  # First call fails
        success_response  # Second call succeeds
    ]

    result = await handle_retry(
        RetryConfig(
            rate_limit_event=rate_limit_event,
            max_retries=3,
            retry_after_fallback=5
        ),
        method="GET",
        url="http://test.com"
    )

    assert result == {"data": "success"}
    assert mock_http_client.get.call_count == 2
    mock_sleep.assert_not_called()

@pytest.mark.asyncio
async def test_handle_retry_network_errors_max_retries(mock_http_client, rate_limit_event, mock_sleep):
    # All calls raise network errors
    mock_http_client.get.side_effect = [
        ReadTimeout("Network timeout"),
        ConnectError("Connection error"),
        RemoteProtocolError("Protocol error")
    ]

    with pytest.raises(HTTPException) as exc_info:
        await handle_retry(
            RetryConfig(
                rate_limit_event=rate_limit_event,
                max_retries=3,  # Allow 3 retries to match the number of errors
                retry_after_fallback=5
            ),
            method="GET",
            url="http://test.com"
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "API rate limit exceeded or unexpected error"
    assert mock_http_client.get.call_count == 3  # Initial attempt + 2 retries
    mock_sleep.assert_not_called()

@pytest.mark.asyncio
async def test_handle_retry_max_retries(mock_http_client, rate_limit_event, mock_sleep):
    # First call raises rate limit
    rate_limit_response = MagicMock(spec=Response)
    rate_limit_response.raise_for_status.side_effect = HTTPStatusError(
        "Rate limit", request=MagicMock(), response=MagicMock(status_code=429, headers={"Retry-After": "2"})
    )
    rate_limit_response.headers = {"Retry-After": "2"}
    
    # Second call also raises rate limit
    rate_limit_response2 = MagicMock(spec=Response)
    rate_limit_response2.raise_for_status.side_effect = HTTPStatusError(
        "Rate limit", request=MagicMock(), response=MagicMock(status_code=429, headers={"Retry-After": "2"})
    )
    rate_limit_response2.headers = {"Retry-After": "2"}

    # Configure the mock to return these responses in sequence
    mock_http_client.get.side_effect = [rate_limit_response, rate_limit_response2]

    with pytest.raises(HTTPException) as exc_info:
        await handle_retry(
            RetryConfig(
                rate_limit_event=rate_limit_event,
                max_retries=1,  # Only allow one retry
                retry_after_fallback=5
            ),
            method="GET",
            url="http://test.com"
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "API rate limit exceeded or unexpected error"
    assert mock_http_client.get.call_count == 1  # With max_retries=1, we only try once
    mock_sleep.assert_called_once_with(2)

@pytest.mark.asyncio
async def test_handle_retry_invalid_data(mock_http_client, rate_limit_event, mock_sleep):
    with pytest.raises(HTTPException) as exc_info:
        await handle_retry(
            RetryConfig(
                rate_limit_event=rate_limit_event,
                max_retries=3,
                retry_after_fallback=5
            ),
            method="GET",
            url="http://test.com",
            data={"key": "value"}  # GET requests can't have data
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "GET requests cannot have a body"
    mock_http_client.get.assert_not_called()
    mock_sleep.assert_not_called()

@pytest.mark.asyncio
async def test_handle_retry_with_data(mock_http_client, mock_response, rate_limit_event, mock_sleep):
    mock_http_client.post.return_value = mock_response

    result = await handle_retry(
        RetryConfig(
            rate_limit_event=rate_limit_event,
            max_retries=3,
            retry_after_fallback=5
        ),
        method="POST",
        url="http://test.com",
        data={"key": "value"}  # POST requests can have data
    )

    assert result == {"data": "test"}
    assert mock_http_client.post.call_args.kwargs == {
        "url": "http://test.com",
        "headers": None,
        "auth": None,
        "params": None,
        "data": {"key": "value"}
    }
    mock_sleep.assert_not_called()

@pytest.mark.asyncio
async def test_handle_retry_gateway_timeout(mock_http_client, rate_limit_event, mock_sleep):
    # First call raises gateway timeout
    timeout_response = MagicMock(spec=Response)
    timeout_response.raise_for_status.side_effect = HTTPStatusError(
        "Gateway Timeout", request=MagicMock(), response=MagicMock(status_code=504)
    )
    timeout_response.headers = {}
    
    # Second call succeeds
    success_response = MagicMock(spec=Response)
    success_response.json.return_value = {"data": "success"}
    success_response.raise_for_status.return_value = None
    success_response.headers = {}

    mock_http_client.get.side_effect = [timeout_response, success_response]

    result = await handle_retry(
        RetryConfig(
            rate_limit_event=rate_limit_event,
            max_retries=3,
            retry_after_fallback=5
        ),
        method="GET",
        url="http://test.com"
    )

    assert result == {"data": "success"}
    assert mock_http_client.get.call_count == 2
    mock_sleep.assert_not_called()

@pytest.mark.asyncio
async def test_handle_retry_unexpected_error(mock_http_client, rate_limit_event, mock_sleep):
    # Create a custom exception with a response attribute
    class CustomError(Exception):
        def __init__(self, response):
            self.response = response
            super().__init__("Custom error")

    # Create a mock response with a status_code attribute
    error_response = {"status_code": 503}
    mock_http_client.get.side_effect = CustomError(error_response)

    with pytest.raises(HTTPException) as exc_info:
        await handle_retry(
            RetryConfig(
                rate_limit_event=rate_limit_event,
                max_retries=3,
                retry_after_fallback=5
            ),
            method="GET",
            url="http://test.com"
        )

    assert exc_info.value.status_code == 503  # Uses the status code from the custom error
    assert exc_info.value.detail == "Custom error"
    mock_sleep.assert_not_called()

@pytest.mark.asyncio
async def test_handle_retry_empty_error(mock_http_client, rate_limit_event, mock_sleep):
    # Create an empty exception
    class EmptyError(Exception):
        pass

    # Test case 1: Exception with no message
    mock_http_client.get.side_effect = EmptyError()

    with pytest.raises(HTTPException) as exc_info:
        await handle_retry(
            RetryConfig(
                rate_limit_event=rate_limit_event,
                max_retries=3,
                retry_after_fallback=5
            ),
            method="GET",
            url="http://test.com"
        )

    assert exc_info.value.status_code == 500  # Default status code for empty errors
    assert exc_info.value.detail == ""
    mock_sleep.assert_not_called()

    # Test case 2: Exception with message
    mock_http_client.get.side_effect = EmptyError("Test error message")

    with pytest.raises(HTTPException) as exc_info:
        await handle_retry(
            RetryConfig(
                rate_limit_event=rate_limit_event,
                max_retries=3,
                retry_after_fallback=5
            ),
            method="GET",
            url="http://test.com"
        )

    assert exc_info.value.status_code == 500  # Default status code for empty errors
    assert exc_info.value.detail == "Test error message"
    mock_sleep.assert_not_called() 