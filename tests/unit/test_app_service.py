from unittest.mock import MagicMock, patch

import pytest

from app.services.app import AppService


class DummyTable:
    def __init__(self):
        self.storage = {}

    def update_item(
        self, Key, UpdateExpression, ExpressionAttributeValues, ReturnValues
    ):
        self.storage[Key["Key"]] = ExpressionAttributeValues[":val"]
        return {"Attributes": {"Attr_Data": ExpressionAttributeValues[":val"]}}

    def get_item(self, Key):
        val = self.storage.get(Key["Key"])
        if val:
            return {"Item": {"Attr_Data": val}}
        return {"Item": {}}

    def delete_item(self, Key):
        val = self.storage.pop(Key["Key"], None)
        return {"Attributes": {"Attr_Data": val}}


@patch("app.services.app.boto3")
def test_app_service_set_get_remove(mock_boto3):
    dummy_table = DummyTable()
    dummy_resource = MagicMock()
    dummy_resource.Table.return_value = dummy_table
    mock_boto3.resource.return_value = dummy_resource
    svc = AppService()
    # set
    result = svc.set_state("k", {"x": 1})
    assert result is not None
    # get
    out = svc.get_state("k")
    assert out == {"x": 1}
    # remove
    removed = svc.remove_state("k")
    assert removed is not None
    # get after remove
    assert svc.get_state("k") is None


@patch("app.services.app.boto3")
def test_app_service_error_handling(mock_boto3):
    dummy_table = DummyTable()
    dummy_resource = MagicMock()
    dummy_resource.Table.return_value = dummy_table
    mock_boto3.resource.return_value = dummy_resource
    svc = AppService()
    # Patch table to raise
    svc.table.update_item = MagicMock(side_effect=Exception("fail"))
    with pytest.raises(Exception):
        svc.set_state("k", {"x": 1})
    svc.table.get_item = MagicMock(side_effect=Exception("fail"))
    with pytest.raises(Exception):
        svc.get_state("k")
    svc.table.delete_item = MagicMock(side_effect=Exception("fail"))
    with pytest.raises(Exception):
        svc.remove_state("k")
