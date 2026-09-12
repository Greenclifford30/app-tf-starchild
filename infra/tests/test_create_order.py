import json
import os
import sys
import unittest
from copy import deepcopy
from pathlib import Path

from botocore.exceptions import ClientError

os.environ.setdefault("ORDERS_TABLE", "orders-test")
os.environ.setdefault("NOTIFICATION_TOPIC_ARN", "arn:aws:sns:us-east-1:123456789012:orders-test")
os.environ.setdefault("ALLOWED_ORIGINS", "https://main.example.amplifyapp.com,http://localhost:3000")
sys.path.insert(0, str(Path(__file__).parents[1] / "src" / "lambda" / "create_order"))

import lambda_function


class FakeTable:
    def __init__(self):
        self.items = {}

    def put_item(self, Item, ConditionExpression):
        assert ConditionExpression == "attribute_not_exists(submission_id)"
        key = Item["submission_id"]
        if key in self.items:
            raise ClientError(
                {"Error": {"Code": "ConditionalCheckFailedException", "Message": "duplicate"}},
                "PutItem",
            )
        self.items[key] = deepcopy(Item)
        return {}

    def get_item(self, Key, ConsistentRead):
        assert ConsistentRead is True
        item = self.items.get(Key["submission_id"])
        return {"Item": deepcopy(item)} if item else {}

    def update_item(self, Key, UpdateExpression, ExpressionAttributeValues):
        item = self.items[Key["submission_id"]]
        item["notification_status"] = ExpressionAttributeValues[":status"]
        if ":message_id" in ExpressionAttributeValues:
            item["notification_message_id"] = ExpressionAttributeValues[":message_id"]
        return {}


class FakeDynamoDB:
    def __init__(self, table):
        self.table = table

    def Table(self, name):
        assert name == "orders-test"
        return self.table


class FakeSns:
    def __init__(self):
        self.messages = []

    def publish(self, **message):
        self.messages.append(message)
        return {"MessageId": f"message-{len(self.messages)}"}


class FlakySns(FakeSns):
    def __init__(self):
        super().__init__()
        self.failures_remaining = 1

    def publish(self, **message):
        if self.failures_remaining:
            self.failures_remaining -= 1
            raise ClientError(
                {"Error": {"Code": "ServiceUnavailable", "Message": "try again"}},
                "Publish",
            )
        return super().publish(**message)


def valid_event(**payload_overrides):
    payload = {
        "submissionId": "83fa7913-ec2e-4aef-9ee3-480c3df2a502",
        "website": "",
        "customer": {
            "email": "customer@example.com",
            "firstName": "Jordan",
            "lastName": "Brooks",
            "phone": "555-555-0100",
            "address": "123 Main Street",
            "addressLine2": "",
            "city": "Chicago",
            "state": "IL",
            "postalCode": "60601",
            "country": "US",
            "notes": "Please confirm pickup options.",
        },
        "items": [
            {
                "productSlug": "love-in-motion",
                "color": "Espresso",
                "size": "M",
                "quantity": 2,
            }
        ],
    }
    payload.update(payload_overrides)
    return {
        "headers": {"origin": "https://main.example.amplifyapp.com"},
        "body": json.dumps(payload),
        "isBase64Encoded": False,
    }


class OrderHandlerTests(unittest.TestCase):
    def setUp(self):
        self.table = FakeTable()
        self.sns = FakeSns()
        lambda_function._DYNAMODB = FakeDynamoDB(self.table)
        lambda_function._SNS = self.sns

    def test_valid_order_is_repriced_stored_and_notified(self):
        response = lambda_function.lambda_handler(valid_event(), None)
        body = json.loads(response["body"])

        self.assertEqual(response["statusCode"], 200)
        self.assertRegex(body["orderReference"], r"^SC-\d{8}-[A-F0-9]{4}$")
        self.assertEqual(body["subtotal"], 136.0)
        self.assertEqual(body["shipping"], 0.0)
        self.assertEqual(body["total"], 136.0)
        stored = next(iter(self.table.items.values()))
        self.assertEqual(stored["items"][0]["unit_price_cents"], 6800)
        self.assertEqual(stored["notification_status"], "PUBLISHED")
        self.assertEqual(len(self.sns.messages), 1)

    def test_duplicate_submission_returns_original_reference_without_second_email(self):
        first = lambda_function.lambda_handler(valid_event(), None)
        second = lambda_function.lambda_handler(valid_event(), None)

        self.assertEqual(json.loads(first["body"])["orderReference"], json.loads(second["body"])["orderReference"])
        self.assertEqual(len(self.sns.messages), 1)

    def test_invalid_variant_is_rejected(self):
        event = valid_event(items=[{
            "productSlug": "love-in-motion",
            "color": "Espresso",
            "size": "NOT-A-SIZE",
            "quantity": 1,
        }])
        response = lambda_function.lambda_handler(event, None)

        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(self.table.items, {})

    def test_retry_completes_a_delayed_notification_without_a_second_order(self):
        self.sns = FlakySns()
        lambda_function._SNS = self.sns

        with self.assertLogs(lambda_function.LOGGER, level="ERROR"):
            first = lambda_function.lambda_handler(valid_event(), None)
        original = next(iter(self.table.items.values()))["order_reference"]
        second = lambda_function.lambda_handler(valid_event(), None)

        self.assertEqual(first["statusCode"], 503)
        self.assertEqual(second["statusCode"], 200)
        self.assertEqual(json.loads(second["body"])["orderReference"], original)
        self.assertEqual(len(self.table.items), 1)
        self.assertEqual(len(self.sns.messages), 1)

    def test_unapproved_browser_origin_is_rejected(self):
        event = valid_event()
        event["headers"]["origin"] = "https://example.invalid"
        response = lambda_function.lambda_handler(event, None)

        self.assertEqual(response["statusCode"], 403)
        self.assertEqual(self.table.items, {})


if __name__ == "__main__":
    unittest.main()
