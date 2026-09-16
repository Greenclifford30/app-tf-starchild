"""Product catalog API handler for the Starchild storefront."""
import base64
import json
import os
import re
import secrets
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

PRODUCTS_TABLE = os.environ.get("PRODUCTS_TABLE", "")
MEDIA_BUCKET = os.environ.get("MEDIA_BUCKET", "")
MEDIA_BASE_URL = os.environ.get("MEDIA_BASE_URL", "").rstrip("/")
ALLOWED_ORIGINS = {origin.strip() for origin in os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if origin.strip()}
ADMIN_GROUP = "starchild-admin"
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
IMAGE_KEY_PATTERN = re.compile(r"^products/[a-z0-9][a-z0-9/_-]*\.(?:jpg|jpeg|png|webp|avif)$")
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/avif"}

_dynamodb = None
_s3 = None


class RequestError(ValueError):
    pass


def _table():
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb")
    return _dynamodb.Table(PRODUCTS_TABLE)


def _s3_client():
    global _s3
    if _s3 is None:
        _s3 = boto3.client("s3")
    return _s3


def _response(status, payload, origin=None):
    headers = {"content-type": "application/json", "cache-control": "no-store"}
    if origin in ALLOWED_ORIGINS:
        headers.update({"access-control-allow-origin": origin, "vary": "Origin"})
    return {"statusCode": status, "headers": headers, "body": json.dumps(payload, default=_json_default)}


def _json_default(value):
    """Convert DynamoDB numeric values to their native JSON equivalents."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _origin(event):
    headers = event.get("headers") or {}
    return headers.get("origin") or headers.get("Origin")


def _is_admin(event):
    claims = ((event.get("requestContext") or {}).get("authorizer") or {}).get("jwt", {}).get("claims", {})
    groups = claims.get("cognito:groups", "")
    if isinstance(groups, (list, tuple, set)):
        return ADMIN_GROUP in groups
    if isinstance(groups, str):
        # HTTP API JWT claims are commonly strings, including JSON-encoded
        # arrays such as '["starchild-admin"]' for Cognito group claims.
        try:
            parsed_groups = json.loads(groups)
        except json.JSONDecodeError:
            parsed_groups = None
        if isinstance(parsed_groups, list):
            return ADMIN_GROUP in parsed_groups
        return ADMIN_GROUP in (group.strip() for group in groups.split(","))
    return False


def _body(event):
    value = event.get("body") or ""
    if event.get("isBase64Encoded"):
        value = base64.b64decode(value, validate=True).decode("utf-8")
    try:
        decoded = json.loads(value)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        raise RequestError("The request body must be valid JSON.") from exc
    if not isinstance(decoded, dict):
        raise RequestError("The request body must be a JSON object.")
    return decoded


def _text(value, field, maximum, required=True):
    if value is None and not required:
        return ""
    if not isinstance(value, str) or not value.strip():
        raise RequestError(f"{field} is required.")
    value = value.strip()
    if len(value) > maximum:
        raise RequestError(f"{field} is too long.")
    return value


def _text_list(value, field, maximum_items=20, maximum_length=100):
    if not isinstance(value, list) or not value or len(value) > maximum_items:
        raise RequestError(f"{field} must contain between 1 and {maximum_items} values.")
    return [_text(item, field, maximum_length) for item in value]


def _image_key(value, field):
    if value is None:
        return None
    if not isinstance(value, str) or not IMAGE_KEY_PATTERN.fullmatch(value):
        raise RequestError(f"{field} must be an uploaded product image key.")
    return value


def _product(payload, slug=None):
    requested_slug = _text(payload.get("slug"), "slug", 100)
    if not SLUG_PATTERN.fullmatch(requested_slug):
        raise RequestError("slug must use lowercase letters, numbers, and hyphens.")
    if slug and requested_slug != slug:
        raise RequestError("slug cannot be changed.")
    price_cents = payload.get("priceCents")
    if isinstance(price_cents, bool) or not isinstance(price_cents, int) or not 1 <= price_cents <= 1_000_000:
        raise RequestError("priceCents must be a whole number between 1 and 1000000.")
    availability = payload.get("availability")
    if availability not in {"In stock", "Limited availability"}:
        raise RequestError("availability must be In stock or Limited availability.")
    sort_order = payload.get("sortOrder", 0)
    if isinstance(sort_order, bool) or not isinstance(sort_order, int) or not 0 <= sort_order <= 1_000_000:
        raise RequestError("sortOrder must be a whole number between 0 and 1000000.")
    if not isinstance(payload.get("featured"), bool):
        raise RequestError("featured must be true or false.")
    details = payload.get("details")
    if not isinstance(details, list) or not details or len(details) > 12:
        raise RequestError("details must contain between 1 and 12 entries.")
    normalized_details = []
    for detail in details:
        if not isinstance(detail, dict):
            raise RequestError("Each detail must be an object.")
        normalized_details.append({"label": _text(detail.get("label"), "detail label", 60), "value": _text(detail.get("value"), "detail value", 240)})
    alternate_key = _image_key(payload.get("alternateImageKey"), "alternateImageKey")
    return {
        "slug": requested_slug, "name": _text(payload.get("name"), "name", 160), "category": _text(payload.get("category"), "category", 80),
        "home_summary": _text(payload.get("homeSummary"), "homeSummary", 300), "story": _text_list(payload.get("story"), "story", 8, 1500),
        "price_cents": price_cents, "colors": _text_list(payload.get("colors"), "colors"), "sizes": _text_list(payload.get("sizes"), "sizes"),
        "availability": availability, "details": normalized_details, "featured": payload["featured"], "sort_order": sort_order,
        "catalog_status": "ACTIVE", "catalog_sort": f"{sort_order:07d}#{requested_slug}",
        "image_key": _image_key(payload.get("imageKey"), "imageKey"), "alternate_image_key": alternate_key,
        "alt": _text(payload.get("alt"), "alt", 500),
    }


def _public_product(item):
    output = {"slug": item["slug"], "name": item["name"], "category": item["category"], "homeSummary": item["home_summary"], "story": item["story"], "priceCents": item["price_cents"], "colors": item["colors"], "sizes": item["sizes"], "availability": item["availability"], "details": item["details"], "featured": item["featured"], "sortOrder": item["sort_order"], "alt": item["alt"]}
    output["image"] = f"{MEDIA_BASE_URL}/{item['image_key']}"
    if item.get("alternate_image_key"):
        output["alternateImage"] = f"{MEDIA_BASE_URL}/{item['alternate_image_key']}"
    return output


def _admin_product(item):
    output = _public_product(item)
    output.update({"status": item["catalog_status"], "imageKey": item["image_key"], "alternateImageKey": item.get("alternate_image_key"), "createdAt": item.get("created_at"), "updatedAt": item.get("updated_at")})
    return output


def _route(event):
    return event.get("routeKey", ""), (event.get("pathParameters") or {}).get("slug")


def _upload_url(payload):
    content_type = payload.get("contentType")
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise RequestError("contentType must be a supported image MIME type.")
    extension = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/avif": "avif"}[content_type]
    key = f"products/uploads/{secrets.token_hex(16)}.{extension}"
    url = _s3_client().generate_presigned_url("put_object", Params={"Bucket": MEDIA_BUCKET, "Key": key, "ContentType": content_type}, ExpiresIn=900, HttpMethod="PUT")
    return {"key": key, "uploadUrl": url, "imageUrl": f"{MEDIA_BASE_URL}/{key}", "expiresIn": 900}


def lambda_handler(event, _context):
    origin = _origin(event)
    if origin and origin not in ALLOWED_ORIGINS:
        return _response(403, {"message": "This origin is not allowed."})
    route, slug = _route(event)
    admin_route = route.startswith("GET /admin") or route.startswith("POST ") or route.startswith("PUT ") or route.startswith("DELETE ")
    if admin_route and not _is_admin(event):
        return _response(403, {"message": "Administrator access is required."}, origin)
    table = _table()
    try:
        if route == "GET /products":
            result = table.query(IndexName="catalog", KeyConditionExpression=Key("catalog_status").eq("ACTIVE"))
            return _response(200, {"products": [_public_product(item) for item in result.get("Items", [])]}, origin)
        if route == "GET /products/{slug}":
            item = table.get_item(Key={"slug": slug}, ConsistentRead=True).get("Item")
            if not item or item["catalog_status"] != "ACTIVE":
                return _response(404, {"message": "Product not found."}, origin)
            return _response(200, {"product": _public_product(item)}, origin)
        if route == "GET /admin/products":
            result = table.scan()
            return _response(200, {"products": [_admin_product(item) for item in sorted(result.get("Items", []), key=lambda item: (item["catalog_status"], item["catalog_sort"]))]}, origin)
        if route == "POST /product-images/upload-url":
            return _response(200, _upload_url(_body(event)), origin)
        if route == "POST /products":
            item = _product(_body(event))
            now = datetime.now(timezone.utc).isoformat()
            item.update({"created_at": now, "updated_at": now})
            table.put_item(Item=item, ConditionExpression="attribute_not_exists(slug)")
            return _response(201, {"product": _admin_product(item)}, origin)
        if route == "PUT /products/{slug}":
            existing = table.get_item(Key={"slug": slug}, ConsistentRead=True).get("Item")
            if not existing:
                return _response(404, {"message": "Product not found."}, origin)
            item = _product(_body(event), slug)
            item.update({"created_at": existing["created_at"], "updated_at": datetime.now(timezone.utc).isoformat()})
            table.put_item(Item=item)
            return _response(200, {"product": _admin_product(item)}, origin)
        if route == "DELETE /products/{slug}":
            result = table.update_item(Key={"slug": slug}, UpdateExpression="SET catalog_status = :archived, updated_at = :updated", ConditionExpression="attribute_exists(slug)", ExpressionAttributeValues={":archived": "ARCHIVED", ":updated": datetime.now(timezone.utc).isoformat()}, ReturnValues="ALL_NEW")
            return _response(200, {"product": _admin_product(result["Attributes"])}, origin)
    except RequestError as exc:
        return _response(400, {"message": str(exc)}, origin)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            return _response(409, {"message": "A product with that slug already exists."}, origin)
        raise
    return _response(404, {"message": "Route not found."}, origin)
