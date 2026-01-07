from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, ConfigDict


class DDBModel(BaseModel, ABC):
    """
    Base class for DynamoDB models.

    This class provides the interface that all DynamoDB models must implement
    to work with the DynamoDB service layer.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    @abstractmethod
    def pk(self) -> str:
        """Return the partition key for this item"""

    @abstractmethod
    def sk(self) -> str:
        """Return the sort key for this item"""

    def to_ddb_item(self) -> Dict[str, Any]:
        """
        Convert the model to a DynamoDB item format.

        This method should handle the conversion from the Pydantic model
        to the format expected by DynamoDB, including proper type mapping.
        """
        item = {}

        # Add the partition and sort keys
        item["PK"] = {"S": self.pk()}
        item["SK"] = {"S": self.sk()}

        # Convert model fields to DynamoDB format
        model_dict = self.model_dump()

        for key, value in model_dict.items():
            if value is not None:
                if isinstance(value, str):
                    item[key] = {"S": value}
                elif isinstance(value, bool):
                    item[key] = {"BOOL": value}
                elif isinstance(value, (int, float)):
                    item[key] = {"N": str(value)}
                elif isinstance(value, datetime):
                    item[key] = {"S": value.isoformat()}
                elif isinstance(value, list):
                    item[key] = {"L": [{"S": str(v)} for v in value]}
                elif isinstance(value, dict):
                    item[key] = {"M": {k: {"S": str(v)} for k, v in value.items()}}
                else:
                    item[key] = {"S": str(value)}

        return item

    @classmethod
    @abstractmethod
    def from_ddb_item(cls, item: Dict[str, Any]) -> "DDBModel":
        """
        Create a model instance from a DynamoDB item.

        This method should handle the conversion from DynamoDB item format
        back to the Pydantic model, including proper type conversion.
        """

    def get_entity_type(self) -> str:
        """Return the entity type for GSI queries"""
        return self.__class__.__name__.upper()
