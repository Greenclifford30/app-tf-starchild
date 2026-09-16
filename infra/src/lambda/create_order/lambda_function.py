import base64
import json
import logging
import os
import re
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import boto3
from botocore.exceptions import BotoCoreError, ClientError

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

ORDERS_TABLE = os.environ.get("ORDERS_TABLE", "")
PRODUCTS_TABLE = os.environ.get("PRODUCTS_TABLE", "")
NOTIFICATION_TOPIC_ARN = os.environ.get("NOTIFICATION_TOPIC_ARN", "")
ALLOWED_ORIGINS = {
    origin.strip()
    for origin in os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
}

MAX_BODY_BYTES = 32_000
MAX_ITEMS = 20
MAX_QUANTITY = 10
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_DYNAMODB = None
_SNS = None


class RequestError(ValueError):
    pass


def _orders_table():
    global _DYNAMODB
    if _DYNAMODB is None:
        _DYNAMODB = boto3.resource("dynamodb")
    return _DYNAMODB.Table(ORDERS_TABLE)


def _products_table():
    global _DYNAMODB
    if _DYNAMODB is None:
        _DYNAMODB = boto3.resource("dynamodb")
    return _DYNAMODB.Table(PRODUCTS_TABLE)


def _sns_client():
    global _SNS
    if _SNS is None:
        _SNS = boto3.client("sns")
    return _SNS


def _response(status_code, payload, origin=None):
    headers = {
        "content-type": "application/json",
        "cache-control": "no-store",
    }
    if origin in ALLOWED_ORIGINS:
        headers["access-control-allow-origin"] = origin
        headers["vary"] = "Origin"
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(payload),
    }


def _parse_body(event):
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        try:
            body = base64.b64decode(body, validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise RequestError("The request body is not valid.") from exc

    if len(body.encode("utf-8")) > MAX_BODY_BYTES:
        raise RequestError("The order request is too large.")

    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, TypeError) as exc:
        raise RequestError("The request body must be valid JSON.") from exc

    if not isinstance(payload, dict):
        raise RequestError("The request body must be a JSON object.")
    return payload


def _required_text(source, name, max_length):
    value = source.get(name)
    if not isinstance(value, str) or not value.strip():
        raise RequestError(f"{name} is required.")
    value = value.strip()
    if len(value) > max_length:
        raise RequestError(f"{name} is too long.")
    return value


def _optional_text(source, name, max_length):
    value = source.get(name, "")
    if not isinstance(value, str):
        raise RequestError(f"{name} must be text.")
    value = value.strip()
    if len(value) > max_length:
        raise RequestError(f"{name} is too long.")
    return value


def _validate_submission_id(value):
    if not isinstance(value, str):
        raise RequestError("submissionId is required.")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as exc:
        raise RequestError("submissionId must be a UUID.") from exc
    return str(parsed)


def _validate_customer(payload):
    customer = payload.get("customer")
    if not isinstance(customer, dict):
        raise RequestError("Customer information is required.")

    email = _required_text(customer, "email", 254).lower()
    if not EMAIL_PATTERN.fullmatch(email):
        raise RequestError("A valid email address is required.")

    country = _required_text(customer, "country", 2).upper()
    if country not in {"US", "CA"}:
        raise RequestError("Orders are currently limited to the United States and Canada.")

    return {
        "email": email,
        "first_name": _required_text(customer, "firstName", 80),
        "last_name": _required_text(customer, "lastName", 80),
        "phone": _required_text(customer, "phone", 30),
        "address": _required_text(customer, "address", 160),
        "address_line_2": _optional_text(customer, "addressLine2", 100),
        "city": _required_text(customer, "city", 80),
        "state": _required_text(customer, "state", 80),
        "postal_code": _required_text(customer, "postalCode", 20),
        "country": country,
        "notes": _optional_text(customer, "notes", 500),
    }


def _validate_items(payload):
    requested_items = payload.get("items")
    if not isinstance(requested_items, list) or not requested_items:
        raise RequestError("At least one item is required.")
    if len(requested_items) > MAX_ITEMS:
        raise RequestError("The order contains too many items.")

    combined = {}
    products = {}
    table = _products_table()
    for requested in requested_items:
        if not isinstance(requested, dict):
            raise RequestError("Each item must be an object.")

        slug = requested.get("productSlug")
        color = requested.get("color")
        size = requested.get("size")
        quantity = requested.get("quantity")
        if not isinstance(slug, str):
            raise RequestError("An item in your bag is no longer available.")
        product = products.get(slug)
        if product is None:
            product = table.get_item(Key={"slug": slug}, ConsistentRead=True).get("Item")
            products[slug] = product

        if product is None or product.get("catalog_status") != "ACTIVE":
            raise RequestError("An item in your bag is no longer available.")
        if color not in product["colors"] or size not in product["sizes"]:
            raise RequestError(f"The selected {product['name']} variant is unavailable.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= MAX_QUANTITY:
            raise RequestError("Item quantities must be between 1 and 10.")

        key = (slug, color, size)
        combined[key] = combined.get(key, 0) + quantity
        if combined[key] > MAX_QUANTITY:
            raise RequestError("A product variant cannot have a quantity greater than 10.")

    items = []
    for (slug, color, size), quantity in combined.items():
        product = products[slug]
        unit_price_cents = product["price_cents"]
        items.append(
            {
                "product_slug": slug,
                "name": product["name"],
                "color": color,
                "size": size,
                "quantity": quantity,
                "unit_price_cents": unit_price_cents,
                "line_total_cents": unit_price_cents * quantity,
            }
        )
    return items


def _notification_message(order):
    customer = order["customer"]
    item_lines = [
        f"- {item['quantity']} x {item['name']} / {item['color']} / {item['size']} "
        f"(${item['line_total_cents'] / 100:.2f})"
        for item in order["items"]
    ]
    address_lines = [customer["address"]]
    if customer["address_line_2"]:
        address_lines.append(customer["address_line_2"])
    address_lines.append(
        f"{customer['city']}, {customer['state']} {customer['postal_code']} {customer['country']}"
    )
    notes = customer["notes"] or "None"
    return "\n".join(
        [
            f"New Starchild order request: {order['order_reference']}",
            "",
            f"Customer: {customer['first_name']} {customer['last_name']}",
            f"Email: {customer['email']}",
            f"Phone: {customer['phone']}",
            "Delivery:",
            *address_lines,
            "",
            "Items:",
            *item_lines,
            "",
            f"Subtotal: ${order['subtotal_cents'] / 100:.2f}",
            f"Estimated shipping: ${order['shipping_cents'] / 100:.2f}",
            f"Estimated total: ${order['total_cents'] / 100:.2f}",
            f"Notes: {notes}",
            "",
            "No payment has been collected. Confirm availability, payment, and fulfillment with the customer.",
        ]
    )


def _publish_notification(table, order):
    try:
        result = _sns_client().publish(
            TopicArn=NOTIFICATION_TOPIC_ARN,
            Subject=f"Starchild order request {order['order_reference']}",
            Message=_notification_message(order),
        )
        table.update_item(
            Key={"submission_id": order["submission_id"]},
            UpdateExpression="SET notification_status = :status, notification_message_id = :message_id",
            ExpressionAttributeValues={
                ":status": "PUBLISHED",
                ":message_id": result["MessageId"],
            },
        )
        return True
    except (BotoCoreError, ClientError):
        LOGGER.exception("Failed to publish order notification", extra={"order_reference": order["order_reference"]})
        table.update_item(
            Key={"submission_id": order["submission_id"]},
            UpdateExpression="SET notification_status = :status",
            ExpressionAttributeValues={":status": "FAILED"},
        )
        return False


def lambda_handler(event, _context):
    headers = event.get("headers") or {}
    origin = headers.get("origin") or headers.get("Origin")
    if origin and origin not in ALLOWED_ORIGINS:
        return _response(403, {"message": "This origin is not allowed."})

    try:
        payload = _parse_body(event)
        if payload.get("website"):
            fake_reference = f"SC-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(2).upper()}"
            return _response(201, {"orderReference": fake_reference}, origin)

        submission_id = _validate_submission_id(payload.get("submissionId"))
        customer = _validate_customer(payload)
        items = _validate_items(payload)
    except RequestError as exc:
        return _response(400, {"message": str(exc)}, origin)

    now = datetime.now(timezone.utc)
    subtotal_cents = sum(item["line_total_cents"] for item in items)
    shipping_cents = 0 if subtotal_cents >= 10_000 else 800
    order = {
        "submission_id": submission_id,
        "order_reference": f"SC-{now:%Y%m%d}-{secrets.token_hex(2).upper()}",
        "status": "REQUESTED",
        "notification_status": "PENDING",
        "created_at": now.isoformat(),
        "customer": customer,
        "items": items,
        "subtotal_cents": subtotal_cents,
        "shipping_cents": shipping_cents,
        "total_cents": subtotal_cents + shipping_cents,
        "currency": "USD",
    }

    table = _orders_table()
    try:
        table.put_item(
            Item=order,
            ConditionExpression="attribute_not_exists(submission_id)",
        )
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
            LOGGER.exception("Failed to store order request")
            return _response(503, {"message": "We could not save your order request. Please try again."}, origin)

        existing = table.get_item(
            Key={"submission_id": submission_id},
            ConsistentRead=True,
        ).get("Item")
        if not existing:
            return _response(503, {"message": "We could not verify your order request. Please try again."}, origin)
        order = existing

    if order.get("notification_status") != "PUBLISHED" and not _publish_notification(table, order):
        return _response(
            503,
            {"message": "Your request was saved, but notification is delayed. Please retry to complete it."},
            origin,
        )

    return _response(
        200,
        {
            "orderReference": order["order_reference"],
            "subtotal": float(Decimal(order["subtotal_cents"]) / 100),
            "shipping": float(Decimal(order["shipping_cents"]) / 100),
            "total": float(Decimal(order["total_cents"]) / 100),
        },
        origin,
    )
