from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar

from app.helpers.ddb import dynamodb_client, table_name
from app.helpers.logger import get_logger


# Generic type for models
T = TypeVar("T")

logger = get_logger(__name__)


class BaseRepository(ABC):
    """
    Abstract base repository for DynamoDB operations.

    Provides common patterns for:
    - CRUD operations with PK/SK patterns
    - GSI querying with pagination
    - Soft deletion support
    - DynamoDB item conversion
    """

    def __init__(self):
        self.dynamodb = dynamodb_client
        self.table_name = table_name

    @abstractmethod
    def get_model_class(self) -> Type[T]:
        """Return the model class this repository handles."""

    @abstractmethod
    def get_entity_type(self) -> str:
        """Return the entity type prefix (e.g., 'PRODUCT', 'CATEGORY')."""

    def get_by_id(self, entity_id: str) -> Optional[T]:
        """
        Get an entity by ID using PK/SK pattern.

        Args:
            entity_id: The entity ID

        Returns:
            Model instance or None if not found
        """
        if not entity_id or "../" in entity_id or "\\" in entity_id:
            raise ValueError("Invalid entity ID")

        try:
            pk = f"{self.get_entity_type()}#{entity_id}"
            sk = "METADATA"

            response = self.dynamodb.get_item(
                TableName=self.table_name,
                Key={
                    "PK": {"S": pk},
                    "SK": {"S": sk},
                },
            )

            if "Item" not in response:
                return None

            model_class = self.get_model_class()
            entity = model_class.from_ddb_item(response["Item"])

            # Check if entity is soft deleted
            if hasattr(entity, "deleted_at") and entity.deleted_at:
                return None

            return entity

        except Exception as e:
            logger.error(
                f"Failed to get {self.get_entity_type().lower()} {entity_id}: {e}"
            )
            return None

    def save(self, entity: T) -> bool:
        """
        Save an entity to DynamoDB.

        Args:
            entity: The entity to save

        Returns:
            True if successful, False otherwise
        """
        try:
            self.dynamodb.put_item(
                TableName=self.table_name,
                Item=entity.to_ddb_item(),
            )
            return True

        except Exception as e:
            logger.error(f"Failed to save {self.get_entity_type().lower()}: {e}")
            return False

    def delete_by_id(self, entity_id: str) -> bool:
        """
        Hard delete an entity by ID.

        Args:
            entity_id: The entity ID to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            pk = f"{self.get_entity_type()}#{entity_id}"
            sk = "METADATA"

            self.dynamodb.delete_item(
                TableName=self.table_name,
                Key={
                    "PK": {"S": pk},
                    "SK": {"S": sk},
                },
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to delete {self.get_entity_type().lower()} {entity_id}: {e}"
            )
            return False

    def soft_delete_by_id(self, entity_id: str) -> bool:
        """
        Soft delete an entity by setting deleted_at timestamp.

        Args:
            entity_id: The entity ID to soft delete

        Returns:
            True if successful, False otherwise
        """
        # Get existing entity including deleted ones
        entity = self.get_by_id_including_deleted(entity_id)
        if not entity:
            return False

        # Set deleted_at timestamp
        if hasattr(entity, "deleted_at"):
            entity.deleted_at = datetime.utcnow()
            entity.updated_at = datetime.utcnow()
            return self.save(entity)

        return False

    def get_by_id_including_deleted(self, entity_id: str) -> Optional[T]:
        """
        Get an entity by ID including soft-deleted ones.

        Args:
            entity_id: The entity ID

        Returns:
            Model instance or None if not found
        """
        if not entity_id or "../" in entity_id or "\\" in entity_id:
            raise ValueError("Invalid entity ID")

        try:
            pk = f"{self.get_entity_type()}#{entity_id}"
            sk = "METADATA"

            response = self.dynamodb.get_item(
                TableName=self.table_name,
                Key={
                    "PK": {"S": pk},
                    "SK": {"S": sk},
                },
            )

            if "Item" not in response:
                return None

            model_class = self.get_model_class()
            entity = model_class.from_ddb_item(response["Item"])
            return entity

        except Exception as e:
            logger.error(
                f"Failed to get {self.get_entity_type().lower()} {entity_id}: {e}"
            )
            return None

    def list_by_entity_type(
        self,
        limit: int = 20,
        last_evaluated_key: Optional[dict] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        include_deleted: bool = False,
    ) -> Dict[str, Any]:
        """
        List entities by type using GSI.

        Args:
            limit: Maximum number of items to return
            last_evaluated_key: DynamoDB pagination token
            search: Search term for filtering
            sort_order: Sort order (asc/desc)
            include_deleted: Whether to include soft-deleted items

        Returns:
            Dictionary with items and pagination info
        """
        try:
            # Build query parameters for EntityType GSI
            query_params = {
                "TableName": self.table_name,
                "IndexName": "GSI2",
                "KeyConditionExpression": "EntityType = :entity_type",
                "ExpressionAttributeValues": {
                    ":entity_type": {"S": self.get_entity_type()},
                },
                "Limit": min(limit * 3, 100),  # Scan more to handle filtering
                "ScanIndexForward": sort_order.lower() == "asc",
            }

            # Add soft deletion filter
            if not include_deleted:
                query_params["FilterExpression"] = (
                    "(attribute_not_exists(DeletedAt) OR DeletedAt = :null_str)"
                )
                query_params["ExpressionAttributeValues"][":null_str"] = {"S": "NULL"}

            # Add pagination token if provided
            if last_evaluated_key:
                query_params["ExclusiveStartKey"] = last_evaluated_key

            # Add search filter if provided
            if search:
                filter_expr = query_params.get("FilterExpression", "")
                if filter_expr:
                    filter_expr += " AND "
                filter_expr += "contains(#name, :search)"
                query_params["FilterExpression"] = filter_expr
                if "ExpressionAttributeNames" not in query_params:
                    query_params["ExpressionAttributeNames"] = {}
                query_params["ExpressionAttributeNames"]["#name"] = "Name"
                query_params["ExpressionAttributeValues"][":search"] = {"S": search}

            logger.info(f"Query params: {query_params}")
            response = self.dynamodb.query(**query_params)
            logger.info(f"Query response - Count: {response.get('Count', 0)}")

            # Convert items to models
            model_class = self.get_model_class()
            entities = []
            for item in response.get("Items", []):
                try:
                    entity = model_class.from_ddb_item(item)
                    entities.append(entity)
                    if len(entities) >= limit:
                        break
                except Exception as e:
                    logger.warning(f"Skipping invalid record: {e}")
                    continue

            return {
                "items": entities,
                "last_evaluated_key": response.get("LastEvaluatedKey"),
                "count": len(entities),
            }

        except Exception as e:
            logger.error(f"Failed to list {self.get_entity_type().lower()}s: {e}")
            return {"items": [], "last_evaluated_key": None, "count": 0}

    def batch_get_by_ids(self, entity_ids: List[str]) -> List[T]:
        """
        Batch get entities by IDs.

        Args:
            entity_ids: List of entity IDs

        Returns:
            List of found entities
        """
        if not entity_ids:
            return []

        try:
            # Build batch get request
            keys = []
            for entity_id in entity_ids:
                pk = f"{self.get_entity_type()}#{entity_id}"
                sk = "METADATA"
                keys.append(
                    {
                        "PK": {"S": pk},
                        "SK": {"S": sk},
                    }
                )

            # DynamoDB batch_get_item has a limit of 100 items
            batch_size = 100
            all_entities = []

            for i in range(0, len(keys), batch_size):
                batch_keys = keys[i : i + batch_size]

                response = self.dynamodb.batch_get_item(
                    RequestItems={self.table_name: {"Keys": batch_keys}}
                )

                # Convert items to models
                model_class = self.get_model_class()
                for item in response.get("Responses", {}).get(self.table_name, []):
                    try:
                        entity = model_class.from_ddb_item(item)
                        # Skip soft deleted items
                        if hasattr(entity, "deleted_at") and entity.deleted_at:
                            continue
                        all_entities.append(entity)
                    except Exception as e:
                        logger.warning(
                            f"Failed to parse {self.get_entity_type().lower()} item: {e}"
                        )
                        continue

            return all_entities

        except Exception as e:
            logger.error(f"Failed to batch get {self.get_entity_type().lower()}s: {e}")
            return []

    def exists(self, entity_id: str) -> bool:
        """
        Check if an entity exists by ID.

        Args:
            entity_id: The entity ID to check

        Returns:
            True if exists and not soft deleted, False otherwise
        """
        entity = self.get_by_id(entity_id)
        return entity is not None
