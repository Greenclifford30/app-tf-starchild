import importlib.util
import json
import os
import unittest
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

from botocore.exceptions import ClientError

os.environ.setdefault("PRODUCTS_TABLE", "products-test")
os.environ.setdefault("MEDIA_BUCKET", "media-test")
os.environ.setdefault("MEDIA_BASE_URL", "https://media.example.com")
os.environ.setdefault("ALLOWED_ORIGINS", "https://store.example.com")

SPEC = importlib.util.spec_from_file_location("products_lambda_function", Path(__file__).parents[1] / "src" / "lambda" / "products" / "lambda_function.py")
products_lambda = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(products_lambda)


class FakeTable:
    def __init__(self):
        self.items = {}

    def put_item(self, Item, ConditionExpression=None):
        if ConditionExpression and Item["slug"] in self.items:
            raise ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem")
        self.items[Item["slug"]] = deepcopy(Item)

    def get_item(self, Key, ConsistentRead=True):
        item = self.items.get(Key["slug"])
        return {"Item": deepcopy(item)} if item else {}

    def query(self, **_kwargs):
        return {"Items": [deepcopy(item) for item in self.items.values() if item["catalog_status"] == "ACTIVE"]}

    def scan(self):
        return {"Items": [deepcopy(item) for item in self.items.values()]}

    def update_item(self, Key, ConditionExpression, ExpressionAttributeValues, **_kwargs):
        if Key["slug"] not in self.items:
            raise ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "UpdateItem")
        self.items[Key["slug"]]["catalog_status"] = ExpressionAttributeValues[":archived"]
        self.items[Key["slug"]]["updated_at"] = ExpressionAttributeValues[":updated"]
        return {"Attributes": deepcopy(self.items[Key["slug"]])}


class FakeDynamo:
    def __init__(self, table): self.table = table
    def Table(self, name):
        assert name == "products-test"
        return self.table


class FakeS3:
    def generate_presigned_url(self, *_args, **kwargs):
        return f"https://upload.example.com/{kwargs['Params']['Key']}"


def payload(**overrides):
    result = {
        "slug": "test-tee", "name": "Test Tee", "category": "T-shirt", "homeSummary": "A test product.",
        "story": ["A complete product story."], "priceCents": 3800, "colors": ["White"], "sizes": ["S", "M"],
        "availability": "In stock", "details": [{"label": "Fit", "value": "Relaxed"}], "featured": True,
        "sortOrder": 1, "imageKey": "products/test-tee/front.png", "alt": "White test tee",
    }
    result.update(overrides)
    return result


def event(route, body=None, slug=None, admin=False):
    item = {"routeKey": route, "headers": {"origin": "https://store.example.com"}, "pathParameters": {"slug": slug} if slug else {}}
    if body is not None: item["body"] = json.dumps(body)
    if admin: item["requestContext"] = {"authorizer": {"jwt": {"claims": {"cognito:groups": "starchild-admin"}}}}
    return item


class ProductHandlerTests(unittest.TestCase):
    def setUp(self):
        self.table = FakeTable()
        products_lambda._dynamodb = FakeDynamo(self.table)
        products_lambda._s3 = FakeS3()
        products_lambda.ALLOWED_ORIGINS = {"https://store.example.com"}

    def test_public_reads_only_active_products(self):
        products_lambda.lambda_handler(event("POST /products", payload(), admin=True), None)
        products_lambda.lambda_handler(event("DELETE /products/{slug}", slug="test-tee", admin=True), None)
        response = products_lambda.lambda_handler(event("GET /products"), None)
        self.assertEqual(json.loads(response["body"])["products"], [])

    def test_public_read_serializes_dynamodb_decimal_prices_as_integer_cents(self):
        item = products_lambda._product(payload())
        item["price_cents"] = Decimal("3800")
        item["sort_order"] = Decimal("1")
        self.table.items[item["slug"]] = item

        response = products_lambda.lambda_handler(event("GET /products"), None)

        self.assertEqual(response["statusCode"], 200)
        product = json.loads(response["body"])["products"][0]
        self.assertEqual(product["priceCents"], 3800)
        self.assertIsInstance(product["priceCents"], int)

    def test_admin_required_for_writes(self):
        response = products_lambda.lambda_handler(event("POST /products", payload()), None)
        self.assertEqual(response["statusCode"], 403)

    def test_creates_and_returns_cloudfront_image_url(self):
        response = products_lambda.lambda_handler(event("POST /products", payload(), admin=True), None)
        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 201)
        self.assertEqual(body["product"]["image"], "https://media.example.com/products/test-tee/front.png")

    def test_upload_url_requires_admin_and_valid_content_type(self):
        response = products_lambda.lambda_handler(event("POST /product-images/upload-url", {"contentType": "image/png"}, admin=True), None)
        self.assertEqual(response["statusCode"], 200)
        self.assertIn("uploadUrl", json.loads(response["body"]))


if __name__ == "__main__":
    unittest.main()
