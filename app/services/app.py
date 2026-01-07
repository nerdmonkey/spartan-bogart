import boto3
import jsonpickle


class AppService:
    """
    A service class to interact with an AWS DynamoDB table.
    Provides methods to set, get, and remove a state in a DynamoDB table.
    """

    def __init__(self):
        """
        Initializes the AppService class.
        Sets up the DynamoDB resource and table.
        """
        self.dynamodb_resource, self.table = self._setup_dynamodb()

    @staticmethod
    def _load_config():
        """Load configuration from environment variables.

        This function retrieves the table name and region name from environment variables.
        If the environment variables are not set, default values are used.

        Returns:
            tuple: A tuple containing the table name and region name.
        """
        table_name = "GSM_TABLE"
        region_name = "ap-southeast-1"
        return table_name, region_name

    @staticmethod
    def _setup_dynamodb():
        """Set up the DynamoDB resource and table.

        This function initializes the DynamoDB resource and table based on the configuration
        loaded from the app's configuration file. It uses the `boto3` library to create the
        DynamoDB resource and retrieve the specified table.

        Returns:
            tuple: A tuple containing the DynamoDB resource and the table object.

        """
        table_name, region_name = AppService._load_config()
        dynamodb_resource = boto3.resource("dynamodb", region_name=region_name)
        table = dynamodb_resource.Table(table_name)
        return dynamodb_resource, table

    @staticmethod
    def _serialize(value):
        """Serialize a Python object to JSON.

        Args:
            value: The Python object to be serialized.

        Returns:
            str: The JSON representation of the serialized object.
        """
        return jsonpickle.encode(value)

    @staticmethod
    def _deserialize(value):
        """
        Deserialize a JSON string to a Python object.

        Parameters:
        value (str): The JSON string to be deserialized.

        Returns:
        object: The deserialized Python object.
        """
        return jsonpickle.decode(value)

    def _handle_dynamodb_error(self, error, action):
        """
        Handle DynamoDB errors.

        This method is responsible for handling errors that occur during DynamoDB operations.
        It logs the error message and raises the error.

        Args:
            error (Exception): The error that occurred during the DynamoDB operation.
            action (str): The action being performed when the error occurred.

        Raises:
            Exception: The original error that occurred during the DynamoDB operation.

        """
        raise error

    def set_state(self, key, value):
        """
        Sets or updates a state in the DynamoDB table.

        Args:
            key (str): The key of the state to be set or updated.
            value (Any): The value of the state to be set or updated.

        Returns:
            Any: The updated value of the state.

        Raises:
            boto3.exceptions.Boto3Error: If there is an error while setting or updating the state.
        """
        try:
            value_json = self._serialize(value)
            response = self.table.update_item(
                Key={"Key": key},
                UpdateExpression="SET Attr_Data = :val",
                ExpressionAttributeValues={":val": value_json},
                ReturnValues="UPDATED_NEW",
            )
            return response["Attributes"]["Attr_Data"]
        except boto3.exceptions.Boto3Error as e:
            self._handle_dynamodb_error(e, "setting")

    def get_state(self, key):
        """
        Retrieves a state from the DynamoDB table.

        Args:
            key (str): The key used to retrieve the state.

        Returns:
            dict or None: The deserialized state if found, None otherwise.
        """
        try:
            response = self.table.get_item(Key={"Key": key})
            item = response.get("Item", {})
            return self._deserialize(item["Attr_Data"]) if "Attr_Data" in item else None
        except boto3.exceptions.Boto3Error as e:
            self._handle_dynamodb_error(e, "getting")

    def remove_state(self, key):
        """
        Removes a state from the DynamoDB table.

        Args:
            key (str): The key of the state to be removed.

        Returns:
            str: The attribute data of the removed state.

        Raises:
            boto3.exceptions.Boto3Error: If there is an error while removing the state.
        """
        try:
            response = self.table.delete_item(Key={"Key": key})
            return response.get("Attributes", {}).get("Attr_Data")
        except boto3.exceptions.Boto3Error as e:
            self._handle_dynamodb_error(e, "removing")
