import json
from typing import Callable, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.helpers.environment import env


class BaseHandlerConfig(BaseModel):
    """
    BaseHandlerConfig is a configuration class for logging handlers.

    Attributes:
        model_config (ConfigDict): Configuration dictionary for the model,
        allowing attributes to be set from the dictionary.
        class_ (str): The class name of the logging handler.
        formatter (str): The formatter to be used by the logging handler.
    """

    model_config = ConfigDict(from_attributes=True)
    class_: str
    formatter: str


class ConsoleHandlerConfig(BaseHandlerConfig):
    """
    ConsoleHandlerConfig is a configuration class for console logging handlers.

    Attributes:
        name (str): The name of the console handler.
        level (str): The logging level for the console handler.
    """

    name: str
    level: str


class FileHandlerConfig(BaseHandlerConfig):
    """
    Configuration for a file handler.

    Attributes:
        name (str): The name of the handler.
        level (str): The logging level for the handler.
        path (str): The file path where logs will be written.
        json_deserializer (Optional[Callable]): A callable for deserializing JSON data.
        Defaults to `json.loads`. This attribute is excluded from certain operations.
    """

    name: str
    level: str
    path: str
    json_deserializer: Optional[Callable] = Field(default=json.loads, exclude=True)


class TcpHandlerConfig(BaseHandlerConfig):
    """
    TcpHandlerConfig is a configuration class for TCP handlers.

    Attributes:
        name (str): The name of the handler.
        level (str): The logging level for the handler.
        host (str): The host address for the TCP connection.
        port (int): The port number for the TCP connection. Must be between 0 and 65535.

    Methods:
        validate_port(cls, v):
            Validates that the port number is within the valid range (0-65535).
            Raises:
                ValueError: If the port number is not within the valid range.
    """

    name: str
    level: str
    host: str
    port: int

    @field_validator("port")
    def validate_port(cls, v):
        if not (0 <= v <= 65535):
            raise ValueError("Port must be between 0 and 65535")
        return v


class Handlers:
    """
    Singleton class to manage logging handlers.

    This class ensures that only one instance of logging handlers is created and
    provides access to different types of logging handlers (console, file, tcp).

    Methods
    -------
    __new__(cls)
        Creates a new instance of the Handlers class if one does not already exist.

    _initialize_handlers()
        Initializes the logging handlers based on environment variables.

    get_handler(handler_type)
        Returns the specified logging handler.

    Attributes
    ----------
    handlers : dict
        A dictionary containing the logging handlers.
    """

    _instance = None

    def __new__(cls):
        """
        Create a new instance of the Handlers class if one does not already exist.

        This method ensures that only one instance of the Handlers class is created
        (singleton pattern). If an instance already exists, it returns the existing instance.
        Otherwise, it creates a new instance and initializes the handlers.

        Returns:
            Handlers: The singleton instance of the Handlers class.
        """
        if cls._instance is None:
            cls._instance = super(Handlers, cls).__new__(cls)
            cls._instance._initialize_handlers()
        return cls._instance

    def _initialize_handlers(self):
        """
        Initializes the logging handlers for the application.

        This method sets up three types of logging handlers:
        - ConsoleHandlerConfig: Logs messages to the console.
        - FileHandlerConfig: Logs messages to a file.
        - TcpHandlerConfig: Logs messages to a TCP socket.

        The configuration for each handler is retrieved from environment variables:
        - APP_NAME: The name of the application.
        - LOG_LEVEL: The logging level (e.g., DEBUG, INFO, WARNING, ERROR, CRITICAL).
        - LOG_FILE: The file path for the file handler.

        The handlers are configured with a JSON formatter and are stored in the
        `self.handlers` dictionary.
        """
        app_name = env().APP_NAME
        log_level = env().LOG_LEVEL
        log_file = env().LOG_FILE

        self.handlers = {
            "console": ConsoleHandlerConfig(
                class_="logging.StreamHandler",
                name=app_name,
                level=log_level,
                formatter="json",
            ),
            "file": FileHandlerConfig(
                class_="logging.FileHandler",
                name=app_name,
                level=log_level,
                formatter="json",
                path=log_file,
            ),
            "tcp": TcpHandlerConfig(
                class_="logging.handlers.SocketHandler",
                name=app_name,
                level=log_level,
                host="localhost",
                port=9999,
                formatter="json",
            ),
        }

    def get_handler(self, handler_type):
        """
        Retrieve a logging handler by its type.

        Args:
            handler_type (str): The type of the handler to retrieve.

        Returns:
            logging.Handler: The logging handler associated with the given type,
                             or None if no handler is found.
        """
        return self.handlers.get(handler_type)


handlers = Handlers()


def handler(handler_type):
    """
    Retrieve a logging handler based on the specified handler type.

    Args:
        handler_type (str): The type of handler to retrieve.

    Returns:
        logging.Handler: The logging handler corresponding to the specified type.
    """
    return handlers.get_handler(handler_type)
