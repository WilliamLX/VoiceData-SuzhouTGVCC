#!/usr/bin/env python3
"""A tool for fetching objects from Tencent Cloud COS."""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

from qcloud_cos import CosConfig, CosS3Client
from qcloud_cos.cos_exception import CosServiceError


class COSObjectDownloader:
    """A tool for downloading objects from COS."""

    def __init__(
        self, secret_id: str, secret_key: str, region: str, bucket_name: str
    ) -> None:
        """
        Initialize the COS client.

        Args:
            secret_id: The Tencent Cloud SecretId.
            secret_key: The Tencent Cloud SecretKey.
            region: The COS region, e.g., ap-beijing-1.
            bucket_name: The name of the bucket.
        """
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.region = region
        self.bucket_name = bucket_name

        config = CosConfig(
            Region=self.region, SecretId=self.secret_id, SecretKey=self.secret_key
        )
        self.client = CosS3Client(config)
        self.logger = logging.getLogger("COSObjectDownloader")

    def list_all_objects(
        self, prefix: str = "", max_keys: int = 1000
    ) -> list[dict[str, Any]]:
        """
        Get all objects in the bucket.

        Args:
            prefix: The object prefix to filter by.
            max_keys: The maximum number of objects to return per request.

        Returns:
            A list of all objects.
        """
        all_objects = []
        marker = ""

        self.logger.info("Fetching objects from bucket '%s'...", self.bucket_name)
        self.logger.info("Prefix filter: %s", prefix if prefix else "All objects")

        start_time = time.time()

        while True:
            try:
                response = self.client.list_objects(
                    Bucket=self.bucket_name,
                    Prefix=prefix,
                    Marker=marker,
                    MaxKeys=max_keys,
                )

                if "Contents" in response:
                    objects = response["Contents"]
                    all_objects.extend(objects)
                    self.logger.info("Fetched %d objects...", len(all_objects))

                    if response.get("IsTruncated") == "true":
                        marker = response["NextMarker"]
                    else:
                        break
                else:
                    self.logger.info("Bucket is empty or no matching objects found.")
                    break

            except CosServiceError:
                self.logger.exception("Error listing objects")
                break
            except (OSError, ValueError):
                self.logger.exception("An unknown error occurred")
                break

        elapsed_time = time.time() - start_time
        self.logger.info(
            "Total objects fetched: %d, time taken: %.2f seconds",
            len(all_objects),
            elapsed_time,
        )
        return all_objects

    def get_object_info(self, objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Get detailed information for objects.

        Args:
            objects: A list of objects.

        Returns:
            A list of detailed object information.
        """
        object_info_list = []
        start_time = time.time()

        for obj in objects:
            last_modified = obj["LastModified"]
            if hasattr(last_modified, "isoformat"):
                last_modified_str = last_modified.isoformat()
            else:
                last_modified_str = str(last_modified)
            info = {
                "key": obj["Key"],
                "size": obj["Size"],
                "last_modified": last_modified_str,
                "etag": obj["ETag"].strip('"'),
                "storage_class": obj.get("StorageClass", "STANDARD"),
            }
            object_info_list.append(info)

        elapsed_time = time.time() - start_time
        self.logger.info("Time taken to get object info: %.2f seconds", elapsed_time)
        return object_info_list

    def save_objects_to_file(
        self, objects: list[dict[str, Any]], filename: str = "cos_objects.json"
    ) -> None:
        """
        Save object information to a JSON file.

        Args:
            objects: A list of objects.
            filename: The output filename.
        """
        start_time = time.time()
        object_info = self.get_object_info(objects)
        output_path = Path(filename)

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(object_info, f, ensure_ascii=False, indent=2)

        elapsed_time = time.time() - start_time
        self.logger.info(
            "Object information saved to %s, time taken: %.2f seconds",
            output_path,
            elapsed_time,
        )

    def download_objects(
        self,
        objects: list[dict[str, Any]],
        local_dir: str = "downloads",
        prefix_filter: str = "",
    ) -> None:
        """
        Download objects to a local directory.

        Args:
            objects: The list of objects to download.
            local_dir: The local download directory.
            prefix_filter: A prefix to filter by.
        """
        local_path = Path(local_dir)
        local_path.mkdir(exist_ok=True)

        downloaded_count = 0
        total_count = len(objects)

        self.logger.info(
            "Starting download of %d objects to %s...", total_count, local_path
        )
        start_time = time.time()

        for obj in objects:
            key = obj["Key"]
            if prefix_filter and not key.startswith(prefix_filter):
                continue

            try:
                dest_path = local_path / key
                dest_path.parent.mkdir(parents=True, exist_ok=True)

                response = self.client.get_object(Bucket=self.bucket_name, Key=key)
                with dest_path.open("wb") as f:
                    f.write(response["Body"].read())

                downloaded_count += 1
                self.logger.info(
                    "Downloaded (%d/%d): %s", downloaded_count, total_count, key
                )

            except (OSError, ValueError):
                self.logger.exception("Error downloading %s", key)

        elapsed_time = time.time() - start_time
        self.logger.info(
            "Download complete! Successfully downloaded %d objects, total time: %.2f seconds",
            downloaded_count,
            elapsed_time,
        )


def get_user_input(prompt: str, default: str | None = None) -> str:
    """
    Get user input with a prompt and a default value.

    Args:
        prompt: The prompt to display to the user.
        default: The default value to use if the user enters nothing.

    Returns:
        The user's input or the default value.
    """
    response = input(prompt).strip()
    if not response and default is not None:
        return default
    return response


def main() -> None:
    """Run the main program."""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("Main")
    logger.info("Tencent Cloud COS Object Fetcher")
    logger.info("=" * 50)

    start_time = time.time()

    try:
        with Path("config.json").open(encoding="utf-8") as f:
            config = json.load(f)
            cos_config = config["cos_config"]
            secret_id = cos_config["secret_id"]
            secret_key = cos_config["secret_key"]
            region = cos_config["region"]
            bucket_name = cos_config["bucket_name"]
    except FileNotFoundError:
        logger.exception("Error: config.json not found.")
        sys.exit(1)
    except KeyError:
        logger.exception("Error: Missing required field in config file.")
        sys.exit(1)
    except json.JSONDecodeError:
        logger.exception("Error: config.json is not well-formed.")
        sys.exit(1)

    if not all([secret_id, secret_key, region, bucket_name]):
        logger.error("Error: All fields in the config are required.")
        sys.exit(1)

    try:
        downloader = COSObjectDownloader(secret_id, secret_key, region, bucket_name)
        prefix = config.get("options", {}).get("prefix", "")
        objects = downloader.list_all_objects(prefix=prefix)

        if not objects:
            logger.info("No objects found.")
            return

        total_size = sum(
            int(obj["Size"]) for obj in objects if isinstance(obj["Size"], (int, str))
        )
        logger.info("\nObject Statistics:")
        logger.info("  Total count: %d", len(objects))
        logger.info("  Total size: %.2f MB", total_size / (1024 * 1024))

        if (
            get_user_input("\nSave object info to JSON file? (y/n): ", "n").lower()
            == "y"
        ):
            filename = get_user_input(
                "Enter filename (default: cos_objects.json): ", "cos_objects.json"
            )
            downloader.save_objects_to_file(objects, filename)

        if (
            get_user_input("\nDownload all objects locally? (y/n): ", "n").lower()
            == "y"
        ):
            local_dir = get_user_input(
                "Enter local directory (default: downloads): ", "downloads"
            )
            downloader.download_objects(objects, local_dir, prefix)

        total_time = time.time() - start_time
        logger.info("\nOperation complete! Total time: %.2f seconds", total_time)

    except (OSError, ValueError, KeyError):
        logger.exception("An error occurred")
        sys.exit(1)


if __name__ == "__main__":
    main()
