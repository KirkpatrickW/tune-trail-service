import pytest
from fastapi import Request
from unittest.mock import AsyncMock, MagicMock
import asyncio

from app.decorators.handle_client_disconnect import handle_client_disconnect, disconnect_poller

@pytest.fixture
def mock_request():
    request = AsyncMock(spec=Request)
    request.state = MagicMock()
    request.state.is_disconnected = AsyncMock(return_value=False)
    request.method = "GET"
    request.url = "http://test.com"
    return request

@pytest.mark.asyncio
async def test_disconnect_poller(mock_request):
    # Simulate client disconnection after a short delay
    async def simulate_disconnect():
        await asyncio.sleep(0.1)
        mock_request.state.is_disconnected.return_value = True
    
    # Start the disconnect simulation
    disconnect_task = asyncio.create_task(simulate_disconnect())
    
    # Run the poller
    await disconnect_poller(mock_request)
    
    # Clean up
    disconnect_task.cancel()
    try:
        await disconnect_task
    except asyncio.CancelledError:
        pass

@pytest.mark.asyncio
async def test_handle_client_disconnect_normal_completion(mock_request):
    # Create a mock handler that completes successfully
    async def mock_handler(request, *args, **kwargs):
        await asyncio.sleep(0.1)
        return "success"
    
    decorated_handler = handle_client_disconnect(mock_handler)
    result = await decorated_handler(mock_request)
    
    assert result == "success"
    mock_request.state.is_disconnected.assert_called()

@pytest.mark.asyncio
async def test_handle_client_disconnect_client_disconnects(mock_request):
    # Create a mock handler that takes longer to complete
    async def mock_handler(request, *args, **kwargs):
        await asyncio.sleep(0.5)
        return "success"
    
    # Simulate client disconnection after a short delay
    async def simulate_disconnect():
        await asyncio.sleep(0.1)
        mock_request.state.is_disconnected.return_value = True
    
    # Start the disconnect simulation
    disconnect_task = asyncio.create_task(simulate_disconnect())
    
    # Run the decorated handler
    decorated_handler = handle_client_disconnect(mock_handler)
    result = await decorated_handler(mock_request)
    
    # Clean up
    disconnect_task.cancel()
    try:
        await disconnect_task
    except asyncio.CancelledError:
        pass
    
    # Verify the handler was cancelled
    assert result is None

@pytest.mark.asyncio
async def test_handle_client_disconnect_handler_error(mock_request):
    # Create a mock handler that raises an exception
    async def mock_handler(request, *args, **kwargs):
        await asyncio.sleep(0.1)
        raise ValueError("Test error")
    
    decorated_handler = handle_client_disconnect(mock_handler)
    
    with pytest.raises(ValueError) as exc_info:
        await decorated_handler(mock_request)
    
    assert str(exc_info.value) == "Test error"
    mock_request.state.is_disconnected.assert_called()

@pytest.mark.asyncio
async def test_handle_client_disconnect_cleanup(mock_request):
    # Create a mock handler that takes longer to complete
    async def mock_handler(request, *args, **kwargs):
        await asyncio.sleep(0.5)
        return "success"
    
    # Simulate client disconnection after a short delay
    async def simulate_disconnect():
        await asyncio.sleep(0.1)
        mock_request.state.is_disconnected.return_value = True
    
    # Start the disconnect simulation
    disconnect_task = asyncio.create_task(simulate_disconnect())
    
    # Run the decorated handler
    decorated_handler = handle_client_disconnect(mock_handler)
    await decorated_handler(mock_request)
    
    # Clean up
    disconnect_task.cancel()
    try:
        await disconnect_task
    except asyncio.CancelledError:
        pass
    
    # Give tasks time to clean up
    await asyncio.sleep(0.1)
    
    # Verify all tasks are cleaned up
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    assert len(tasks) == 0 