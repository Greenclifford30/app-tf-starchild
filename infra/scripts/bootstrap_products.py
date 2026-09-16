#!/usr/bin/env python3
"""Upload local product media and seed catalog records from a JSON file.

The manifest is a JSON array using the public POST /products fields plus
``sourceImages``: a mapping from imageKey to a path relative to --media-dir.
Run after Terraform apply with AWS credentials for the deployed account.
"""
import argparse
import json
import mimetypes
from pathlib import Path

import boto3


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--media-dir", required=True, type=Path)
    args = parser.parse_args()
    products = json.loads(args.manifest.read_text())
    if not isinstance(products, list):
        raise SystemExit("The manifest must contain a JSON array.")

    s3 = boto3.client("s3")
    table = boto3.resource("dynamodb").Table(args.table)
    for product in products:
        source_images = product.pop("sourceImages")
        for key, source in source_images.items():
            source_path = args.media_dir / source
            content_type = mimetypes.guess_type(source_path.name)[0] or "application/octet-stream"
            print(f"Uploading {source_path} -> {key}")
            s3.upload_file(str(source_path), args.bucket, key, ExtraArgs={"ContentType": content_type})
        item = {
            "slug": product["slug"], "name": product["name"], "category": product["category"],
            "home_summary": product["homeSummary"], "story": product["story"], "price_cents": product["priceCents"],
            "colors": product["colors"], "sizes": product["sizes"], "availability": product["availability"],
            "details": product["details"], "featured": product["featured"], "sort_order": product["sortOrder"],
            "catalog_status": "ACTIVE", "catalog_sort": f"{product['sortOrder']:07d}#{product['slug']}",
            "image_key": product["imageKey"], "alternate_image_key": product.get("alternateImageKey"), "alt": product["alt"],
            "created_at": product["createdAt"], "updated_at": product["createdAt"],
        }
        print(f"Seeding {item['slug']}")
        table.put_item(Item=item, ConditionExpression="attribute_not_exists(slug)")


if __name__ == "__main__":
    main()
