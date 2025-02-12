import logging
from azure.identity import AzureCliCredential
from azure.mgmt.rdbms.postgresql_flexibleservers import PostgreSQLManagementClient

logger = logging.getLogger("uvicorn")

class PostgreSQLServerManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(PostgreSQLServerManager, cls).__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.resource_group = "TuneTrail"
        self.server_name = "tunetrail-postgresql-server"
        self.subscription_id = "3ed2f70f-52a1-48f8-bcc7-f0b08214d849"

        try:
            self.credential = AzureCliCredential()
            self.client = PostgreSQLManagementClient(credential=self.credential, subscription_id=self.subscription_id)
        except Exception as e:
            raise RuntimeError("Failed to initialise PostgreSQL Manager due to client or credential failure.") from e


    def _get_server_status(self):
        try:
            server = self.client.servers.get(self.resource_group, self.server_name)
            return server.state
        except Exception as e:
            raise RuntimeError("Error checking PostgreSQL server status.") from e
        

    def start_server(self):
        inital_status = self._get_server_status()

        if inital_status in ["Ready", "Starting"]:
            logger.info(f"PostgreSQL server '{self.server_name}' is already running or starting.")
            return
        
        if inital_status in ["Stopping", "Failed"]:
            logger.error(f"PostgreSQL server '{self.server_name}' is in an invalid state to start: {inital_status}.")
            return

        try:
            logger.info(f"Starting PostgreSQL server '{self.server_name}'...")
            start_operation = self.client.servers.begin_start(self.resource_group, self.server_name)
            start_operation.result()

            status = self._get_server_status()
            if status != "Ready":
                raise RuntimeError(f"PostgreSQL server '{self.server_name}' failed to start. Current state: {status}")

            logger.info(f"PostgreSQL server '{self.server_name}' is now ready.")
        except Exception as e:
            raise RuntimeError("Error starting PostgreSQL server") from e


    def stop_server(self):
        inital_status = self._get_server_status()

        if inital_status in ["Stopped", "Stopping"]:
            logger.info(f"PostgreSQL server '{self.server_name}' is already stopped or stopping.")
            return
        
        if inital_status in ["Starting", "Failed"]:
            logger.error(f"PostgreSQL server '{self.server_name}' is in an invalid state to stop: {inital_status}.")
            return
        
        try:
            logger.info(f"Stopping PostgreSQL server '{self.server_name}'...")
            stop_operation = self.client.servers.begin_stop(self.resource_group, self.server_name)
            stop_operation.result()

            status = self._get_server_status()
            if status != "Stopped":
                raise RuntimeError(f"PostgreSQL server '{self.server_name}' failed to stop. Current state: {status}")

            logger.info(f"PostgreSQL server '{self.server_name}' is now stopped.")
        except Exception as e:
            raise RuntimeError("Error starting PostgreSQL server") from e