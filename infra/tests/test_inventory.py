import importlib.util
import unittest
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

from boto3.dynamodb.types import TypeDeserializer

SPEC = importlib.util.spec_from_file_location("inventory", Path(__file__).parents[1] / "src" / "inventory" / "inventory.py")
inventory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inventory)
DESERIALIZER = TypeDeserializer()


class Table:
    def __init__(self, products):
        self.products = products

    def get_item(self, Key, ConsistentRead):
        assert ConsistentRead
        item = self.products.get(Key["slug"])
        return {"Item": deepcopy(item)} if item else {}


def item(quantity=1):
    return {"product_slug": "tee", "color": "White", "size": "M", "quantity": quantity}


def product(on_hand=5, reserved=0):
    return {"slug": "tee", "catalog_status": "ACTIVE", "colors": ["White"], "sizes": ["M"],
            "inventory": {inventory.variant_key("White", "M"): {"color": "White", "size": "M", "onHand": on_hand, "reserved": reserved}}}


def values(action):
    return {key: DESERIALIZER.deserialize(value) for key, value in action["Update"]["ExpressionAttributeValues"].items()}


class InventoryTests(unittest.TestCase):
    def test_reserves_combined_quantities_with_snapshot_condition(self):
        original = product()
        actions = inventory.product_actions(Table({"tee": original}), "products", [item(2), item(Decimal(1))], "reserve")
        self.assertEqual(len(actions), 1)
        snapshot = values(actions[0])
        self.assertEqual(next(iter(snapshot[":updated"].values()))["reserved"], 3)
        self.assertEqual(snapshot[":original"], original["inventory"])
        self.assertIn("catalog_status = :active", actions[0]["Update"]["ConditionExpression"])
        self.assertEqual(next(iter(original["inventory"].values()))["reserved"], 0)

    def test_rejects_untracked_or_insufficient_stock(self):
        for source in ({}, {"tee": product(1)}):
            with self.subTest(source=source), self.assertRaises(inventory.InventoryError):
                inventory.product_actions(Table(source), "products", [item(2)], "reserve")

    def test_release_and_consume_keep_physical_counts_correct(self):
        for transition, expected_on_hand in (("release", 5), ("consume", 3)):
            action = inventory.product_actions(Table({"tee": product(5, 3)}), "products", [item(2)], transition)[0]
            variant = next(iter(values(action)[":updated"].values()))
            self.assertEqual((variant["onHand"], variant["reserved"]), (expected_on_hand, 1))

    def test_rejects_release_larger_than_reservation(self):
        with self.assertRaises(inventory.InventoryError):
            inventory.product_actions(Table({"tee": product(5, 1)}), "products", [item(2)], "release")

    def test_archived_product_releases_existing_reservations_but_cannot_reserve(self):
        archived = product(5, 1)
        archived["catalog_status"] = "ARCHIVED"
        self.assertEqual(len(inventory.product_actions(Table({"tee": archived}), "products", [item()], "release")), 1)
        with self.assertRaises(inventory.InventoryError):
            inventory.product_actions(Table({"tee": archived}), "products", [item()], "reserve")

    def test_items_for_same_product_share_one_transaction_update(self):
        tracked = product()
        tracked["sizes"].append("L")
        tracked["inventory"][inventory.variant_key("White", "L")] = {"color": "White", "size": "L", "onHand": 2, "reserved": 0}
        other = {**item(), "size": "L"}
        actions = inventory.product_actions(Table({"tee": tracked}), "products", [item(), other], "reserve")
        self.assertEqual(len(actions), 1)
        self.assertEqual([entry["reserved"] for entry in values(actions[0])[":updated"].values()], [1, 1])


if __name__ == "__main__":
    unittest.main()
