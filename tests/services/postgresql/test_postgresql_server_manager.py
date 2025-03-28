import pytest
from unittest.mock import patch, MagicMock
from azure.mgmt.rdbms.postgresql_flexibleservers.models import Server

from app.services.postgresql.postgresql_server_manager import PostgreSQLServerManager

@pytest.fixture
def mock_credential():
    return MagicMock()

@pytest.fixture
def mock_client():
    client = MagicMock()
    client.servers = MagicMock()
    return client

@pytest.fixture
def server_manager(mock_credential, mock_client):
    # Reset the singleton instance
    PostgreSQLServerManager._instance = None
    
    with patch('app.services.postgresql.postgresql_server_manager.AzureCliCredential', return_value=mock_credential), \
         patch('app.services.postgresql.postgresql_server_manager.PostgreSQLManagementClient', return_value=mock_client):
        return PostgreSQLServerManager()

def test_init_success(server_manager, mock_credential, mock_client):
    # Verify initialisation
    assert server_manager._resource_group == "TuneTrail"
    assert server_manager._server_name == "tunetrail-postgresql-server"
    assert server_manager._subscription_id == "3ed2f70f-52a1-48f8-bcc7-f0b08214d849"
    assert server_manager._credential == mock_credential
    assert server_manager._client == mock_client

def test_init_failure():
    # Reset the singleton instance
    PostgreSQLServerManager._instance = None
    
    with patch('app.services.postgresql.postgresql_server_manager.AzureCliCredential', side_effect=Exception("Credential error")):
        with pytest.raises(RuntimeError) as exc_info:
            PostgreSQLServerManager()
        assert "Failed to initialise PostgreSQL Manager" in str(exc_info.value)

def test_get_server_status_success(server_manager, mock_client):
    # Mock server response
    mock_server = MagicMock(spec=Server)
    mock_server.state = "Ready"
    mock_client.servers.get.return_value = mock_server
    
    status = server_manager._get_server_status()
    assert status == "Ready"
    mock_client.servers.get.assert_called_once_with("TuneTrail", "tunetrail-postgresql-server")

def test_get_server_status_failure(server_manager, mock_client):
    mock_client.servers.get.side_effect = Exception("API error")
    
    with pytest.raises(RuntimeError) as exc_info:
        server_manager._get_server_status()
    assert "Error checking PostgreSQL server status" in str(exc_info.value)

def test_start_server_already_running(server_manager, mock_client):
    # Mock server already running
    mock_server = MagicMock(spec=Server)
    mock_server.state = "Ready"
    mock_client.servers.get.return_value = mock_server
    
    server_manager.start_server()
    mock_client.servers.begin_start.assert_not_called()

def test_start_server_invalid_state(server_manager, mock_client):
    # Mock server in invalid state
    mock_server = MagicMock(spec=Server)
    mock_server.state = "Stopping"
    mock_client.servers.get.return_value = mock_server
    
    # The method logs an error but doesn't raise an exception
    server_manager.start_server()
    mock_client.servers.begin_start.assert_not_called()

def test_start_server_success(server_manager, mock_client):
    # Mock server stopped
    mock_server = MagicMock(spec=Server)
    mock_server.state = "Stopped"
    mock_client.servers.get.return_value = mock_server
    
    # Mock the start operation
    mock_operation = MagicMock()
    mock_operation.result.return_value = None
    mock_client.servers.begin_start.return_value = mock_operation
    
    # Mock the server state after operation completes
    mock_server_after = MagicMock(spec=Server)
    mock_server_after.state = "Ready"
    mock_client.servers.get.side_effect = [mock_server, mock_server_after]
    
    server_manager.start_server()
    mock_client.servers.begin_start.assert_called_once_with("TuneTrail", "tunetrail-postgresql-server")
    mock_operation.result.assert_called_once()

def test_start_server_failure(server_manager, mock_client):
    # Mock server stopped
    mock_server = MagicMock(spec=Server)
    mock_server.state = "Stopped"
    mock_client.servers.get.return_value = mock_server
    
    # Mock the start operation
    mock_operation = MagicMock()
    mock_operation.result.return_value = None
    mock_client.servers.begin_start.return_value = mock_operation
    
    # Mock the server state after operation completes (failed to start)
    mock_server_after = MagicMock(spec=Server)
    mock_server_after.state = "Failed"
    mock_client.servers.get.side_effect = [mock_server, mock_server_after]
    
    with pytest.raises(RuntimeError) as exc_info:
        server_manager.start_server()
    assert "Error starting PostgreSQL server" in str(exc_info.value)
    mock_client.servers.begin_start.assert_called_once_with("TuneTrail", "tunetrail-postgresql-server")
    mock_operation.result.assert_called_once()

def test_start_server_operation_error(server_manager, mock_client):
    # Mock server stopped
    mock_server = MagicMock(spec=Server)
    mock_server.state = "Stopped"
    mock_client.servers.get.return_value = mock_server
    
    # Mock the start operation to raise an exception
    mock_operation = MagicMock()
    mock_operation.result.side_effect = Exception("Operation failed")
    mock_client.servers.begin_start.return_value = mock_operation
    
    with pytest.raises(RuntimeError) as exc_info:
        server_manager.start_server()
    assert "Error starting PostgreSQL server" in str(exc_info.value)
    mock_client.servers.begin_start.assert_called_once_with("TuneTrail", "tunetrail-postgresql-server")
    mock_operation.result.assert_called_once()

def test_stop_server_already_stopped(server_manager, mock_client):
    # Mock server already stopped
    mock_server = MagicMock(spec=Server)
    mock_server.state = "Stopped"
    mock_client.servers.get.return_value = mock_server
    
    server_manager.stop_server()
    mock_client.servers.begin_stop.assert_not_called()

def test_stop_server_invalid_state(server_manager, mock_client):
    # Mock server in invalid state
    mock_server = MagicMock(spec=Server)
    mock_server.state = "Starting"
    mock_client.servers.get.return_value = mock_server
    
    # The method logs an error but doesn't raise an exception
    server_manager.stop_server()
    mock_client.servers.begin_stop.assert_not_called()

def test_stop_server_success(server_manager, mock_client):
    # Mock server running
    mock_server = MagicMock(spec=Server)
    mock_server.state = "Ready"
    mock_client.servers.get.return_value = mock_server
    
    # Mock the stop operation
    mock_operation = MagicMock()
    mock_operation.result.return_value = None
    mock_client.servers.begin_stop.return_value = mock_operation
    
    # Mock the server state after operation completes
    mock_server_after = MagicMock(spec=Server)
    mock_server_after.state = "Stopped"
    mock_client.servers.get.side_effect = [mock_server, mock_server_after]
    
    server_manager.stop_server()
    mock_client.servers.begin_stop.assert_called_once_with("TuneTrail", "tunetrail-postgresql-server")
    mock_operation.result.assert_called_once()

def test_stop_server_failure(server_manager, mock_client):
    # Mock server running
    mock_server = MagicMock(spec=Server)
    mock_server.state = "Ready"
    mock_client.servers.get.return_value = mock_server
    
    # Mock the stop operation
    mock_operation = MagicMock()
    mock_operation.result.return_value = None
    mock_client.servers.begin_stop.return_value = mock_operation
    
    # Mock the server state after operation completes (failed to stop)
    mock_server_after = MagicMock(spec=Server)
    mock_server_after.state = "Failed"
    mock_client.servers.get.side_effect = [mock_server, mock_server_after]
    
    with pytest.raises(RuntimeError) as exc_info:
        server_manager.stop_server()
    assert "Error starting PostgreSQL server" in str(exc_info.value)
    mock_client.servers.begin_stop.assert_called_once_with("TuneTrail", "tunetrail-postgresql-server")
    mock_operation.result.assert_called_once()

def test_stop_server_operation_error(server_manager, mock_client):
    # Mock server running
    mock_server = MagicMock(spec=Server)
    mock_server.state = "Ready"
    mock_client.servers.get.return_value = mock_server
    
    # Mock the stop operation to raise an exception
    mock_operation = MagicMock()
    mock_operation.result.side_effect = Exception("Operation failed")
    mock_client.servers.begin_stop.return_value = mock_operation
    
    with pytest.raises(RuntimeError) as exc_info:
        server_manager.stop_server()
    assert "Error starting PostgreSQL server" in str(exc_info.value)
    mock_client.servers.begin_stop.assert_called_once_with("TuneTrail", "tunetrail-postgresql-server")
    mock_operation.result.assert_called_once() 