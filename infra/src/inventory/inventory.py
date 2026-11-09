"""Build conditional product updates for an atomic reservation transaction.

Callers must include an idempotently guarded reservation state transition in
the same DynamoDB transaction as the actions returned by this module.
"""
import hashlib
import json
from copy import deepcopy
from decimal import Decimal

from boto3.dynamodb.types import TypeSerializer

_SERIALIZER = TypeSerializer()


class InventoryError(ValueError):
    """Stock is unavailable or inconsistent with the requested transition."""


def variant_key(color, size):
    value = json.dumps([color, size], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _wire(values):
    return {key: _SERIALIZER.serialize(value) for key, value in values.items()}


def product_actions(table, table_name, items, transition, expected_products=None):
    """Return one conditional update per product for reserve/release/consume.

    Product reads are strongly consistent. Snapshot conditions protect all
    variants on the product from concurrent catalog or inventory changes.
    No writes are made until the caller submits the returned actions together
    with its own guarded reservation state change.
    """
    if transition not in ("reserve", "release", "consume"):
        raise ValueError("Unknown inventory transition.")
    grouped = {}
    for item in items:
        slug, color, size, quantity = (item.get(key) for key in ("product_slug", "color", "size", "quantity"))
        if not all(isinstance(value, str) and value for value in (slug, color, size)):
            raise InventoryError("An order variant is invalid.")
        if isinstance(quantity, bool) or not isinstance(quantity, (int, Decimal)) or quantity != int(quantity) or quantity <= 0:
            raise InventoryError("An order quantity is invalid.")
        quantity = int(quantity)
        product_items = grouped.setdefault(slug, {})
        variant = (color, size)
        product_items[variant] = product_items.get(variant, 0) + quantity
    if not grouped:
        raise InventoryError("An order must contain at least one item.")

    actions = []
    for slug, variants in grouped.items():
        product = table.get_item(Key={"slug": slug}, ConsistentRead=True).get("Item")
        if not product or "inventory" not in product:
            raise InventoryError(f"Stock is not available for {slug}.")
        original = product["inventory"]
        updated = deepcopy(original)
        for (color, size), quantity in variants.items():
            key = variant_key(color, size)
            variant = updated.get(key)
            if not variant or variant.get("color") != color or variant.get("size") != size:
                raise InventoryError(f"Stock is not available for {slug}, {color}, {size}.")
            if transition == "reserve" and (product.get("catalog_status") != "ACTIVE" or color not in product.get("colors", []) or size not in product.get("sizes", [])):
                raise InventoryError(f"The selected variant of {slug} is no longer available.")
            on_hand, reserved = int(variant["onHand"]), int(variant["reserved"])
            if on_hand < 0 or reserved < 0 or reserved > on_hand:
                raise InventoryError(f"Stock records for {slug} need attention.")
            if transition == "reserve":
                if on_hand - reserved < quantity:
                    raise InventoryError(f"Not enough stock for {slug}, {color}, {size}. Update your bag and try again.")
                variant["reserved"] = reserved + quantity
            else:
                if reserved < quantity:
                    raise InventoryError(f"The reservation for {slug} needs attention.")
                variant["reserved"] = reserved - quantity
                if transition == "consume":
                    variant["onHand"] = on_hand - quantity
        condition = "inventory = :original"
        values = {":original": original, ":updated": updated}
        if transition == "reserve":
            condition += " AND catalog_status = :active AND colors = :colors AND sizes = :sizes"
            values.update({":active": "ACTIVE", ":colors": product["colors"], ":sizes": product["sizes"]})
            if expected_products is not None:
                expected = expected_products[slug]
                if any(product.get(field) != expected.get(field) for field in ("name", "price_cents", "colors", "sizes", "catalog_status")):
                    raise InventoryError("The catalog changed. Reload and review the request again.")
                condition += " AND #name = :name AND price_cents = :price"
                values.update({":name": expected["name"], ":price": expected["price_cents"]})
        actions.append({"Update": {"TableName": table_name, "Key": _wire({"slug": slug}),
                                  "UpdateExpression": "SET inventory = :updated", "ConditionExpression": condition,
                                  "ExpressionAttributeValues": _wire(values)}})
        if transition == "reserve" and expected_products is not None:
            actions[-1]["Update"]["ExpressionAttributeNames"] = {"#name": "name"}
    return actions
