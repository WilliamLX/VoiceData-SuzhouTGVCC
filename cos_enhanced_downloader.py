#!/usr/bin/env python3
"""
Provides an enhanced downloader for Tencent Cloud COS.

It supports multi-threaded concurrent downloads, resumable downloads,
file filtering, and progress display.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qcloud_cos import CosConfig, CosS3Client
from qcloud_cos.cos_exception import CosServiceError
from tqdm import tqdm

from index_manager import IndexManager
from sync_detector import SyncDetector


class EnhancedCOSDownloader:
    """An enhanced downloader for COS."""

    def __init__(
        self,
        config_file: str = "config.json",
        max_workers: int = 5,
        retry_times: int = 3,
    ) -> None:
        """
        Initialize the downloader.

        Args:
            config_file: Path to the configuration file.
            max_workers: Maximum number of concurrent workers.
            retry_times: Number of times to retry a failed download.

        """
        self.config_file = Path(config_file)
        self.max_workers = max_workers
        self.retry_times = retry_times
        self.config = self._load_config()
        self.client = self._init_client()
        self.logger = self._setup_logger()
        self.index_manager = IndexManager()
        self.sync_detector = SyncDetector(self.client, self.index_manager)

    def _load_config(self) -> dict[str, Any] | None:
        """Load the configuration file."""
        try:
            with self.config_file.open(encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.exception("Configuration file not found: %s", self.config_file)
            return None
        except json.JSONDecodeError:
            self.logger.exception(
                "Invalid JSON in configuration file: %s", self.config_file
            )
            return None

    def _init_client(self) -> CosS3Client | None:
        """Initialize the COS client."""
        if not self.config:
            return None

        cos_config = self.config["cos_config"]
        client_config = CosConfig(
            Region=cos_config["region"],
            SecretId=cos_config["secret_id"],
            SecretKey=cos_config["secret_key"],
        )
        return CosS3Client(client_config)

    def _setup_logger(self) -> logging.Logger:
        """Set up the logger."""
        logger = logging.getLogger("EnhancedCOSDownloader")
        logger.setLevel(logging.INFO)

        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        log_file = (
            log_dir
            / f"download_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.log"
        )
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def _calculate_md5(self, file_path: Path) -> str | None:
        """Calculate the MD5 hash of a file."""
        hash_md5 = hashlib.new("md5")
        try:
            with file_path.open("rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except OSError:
            self.logger.exception("Error calculating MD5 for %s", file_path)
            return None

    def _download_single_file(
        self, cos_key: str, local_path: Path, file_size: int, etag: str
    ) -> str:
        """
        Download a single file.

        Args:
            cos_key: The COS object key.
            local_path: The local file path.
            file_size: The file size (for progress display).
            etag: The ETag of the file.

        Returns:
            A string indicating the result ('success', 'skipped', 'failed').

        """
        cos_config = self.config["cos_config"]

        if self.index_manager.file_exists(cos_key, etag):
            self.logger.info("File already indexed, skipping: %s", cos_key)
            return "skipped"

        if local_path.exists() and local_path.stat().st_size == file_size:
            self.logger.info("File already exists, skipping: %s", cos_key)
            return "skipped"

        local_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            for attempt in range(self.retry_times):
                try:
                    self.client.download_file(
                        Bucket=cos_config["bucket_name"],
                        Key=cos_key,
                        DestFilePath=str(local_path),
                    )
                    md5_hash = self._calculate_md5(local_path)
                    last_modified = datetime.fromtimestamp(
                        local_path.stat().st_mtime, tz=timezone.utc
                    ).isoformat()
                    self.index_manager.add_file(
                        file_path=str(local_path),
                        file_size=file_size,
                        last_modified=last_modified,
                        md5_hash=md5_hash,
                        cos_key=cos_key,
                        etag=etag,
                    )
                    self.logger.info("Successfully downloaded: %s", cos_key)
                    return "success"
                except (CosServiceError, OSError):
                    self.logger.warning(
                        "Download failed (attempt %d/%d): %s",
                        attempt + 1,
                        self.retry_times,
                        cos_key,
                    )
                    if attempt < self.retry_times - 1:
                        time.sleep(2**attempt)
                    else:
                        raise
        except (CosServiceError, OSError):
            self.logger.exception("Download finally failed: %s", cos_key)
            return "failed"
        return "failed"

    def _list_objects_paginated(
        self, prefix: str, max_keys: int
    ) -> list[dict[str, Any]]:
        """List objects from COS in a paginated manner."""
        all_objects = []
        marker = ""
        cos_config = self.config["cos_config"]
        while True:
            response = self.client.list_objects(
                Bucket=cos_config["bucket_name"],
                Prefix=prefix,
                Marker=marker,
                MaxKeys=max_keys,
            )
            if "Contents" in response:
                all_objects.extend(response["Contents"])
                self.logger.info("Fetched %d objects...", len(all_objects))
            if response.get("IsTruncated") == "true":
                marker = response["NextMarker"]
            else:
                break
        return all_objects

    def list_objects(
        self,
        prefix: str | None = None,
        extensions: list[str] | None = None,
        min_size: int | None = None,
        max_size: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        List objects in COS.

        Args:
            prefix: The prefix to filter by.
            extensions: A list of file extensions to filter by.
            min_size: The minimum file size.
            max_size: The maximum file size.

        Returns:
            A list of objects.

        """
        cos_config = self.config["cos_config"]
        options = self.config.get("options", {})

        if prefix is None:
            prefix = options.get("prefix", "")

        max_keys = options.get("max_keys_per_request", 1000)

        self.logger.info(
            "Fetching objects from bucket '%s'...", cos_config["bucket_name"]
        )
        if prefix:
            self.logger.info("Filtering by prefix: %s", prefix)

        try:
            all_objects = self._list_objects_paginated(prefix, max_keys)
        except (CosServiceError, OSError, ValueError):
            self.logger.exception("Error listing objects")
            return []

        filtered_objects = []
        for obj in all_objects:
            if extensions and Path(obj["Key"]).suffix.lower() not in extensions:
                continue
            if min_size and int(obj["Size"]) < min_size:
                continue
            if max_size and int(obj["Size"]) > max_size:
                continue
            filtered_objects.append(obj)

        self.logger.info("Total objects fetched: %d", len(filtered_objects))
        return filtered_objects

    def download_objects(
        self,
        objects: list[dict[str, Any]],
        output_dir: str | None = None,
        *,
        show_progress: bool = True,
    ) -> dict[str, int]:
        """
        Download a list of objects.

        Args:
            objects: The list of objects to download.
            output_dir: The output directory.
            show_progress: Whether to show a progress bar.

        Returns:
            A dictionary with download statistics.

        """
        if not objects:
            self.logger.warning("No objects to download.")
            return {"success": 0, "failed": 0, "skipped": 0}

        options = self.config.get("options", {})
        if output_dir is None:
            output_dir = options.get("download_dir", "downloads")

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        download_tasks = []
        for obj in objects:
            cos_key = obj["Key"]
            local_path = output_path / cos_key.replace("/", "_")
            download_tasks.append(
                (cos_key, local_path, int(obj["Size"]), obj["ETag"].strip('"'))
            )

        success_count = 0
        failed_count = 0
        skipped_count = 0

        self.logger.info(
            "Starting download of %d objects to: %s",
            len(download_tasks),
            output_path,
        )

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor, tqdm(
            total=len(download_tasks),
            desc="Downloading",
            disable=not show_progress,
        ) as pbar:
            future_to_task = {
                executor.submit(self._download_single_file, *task): task
                for task in download_tasks
            }

            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    if result == "success":
                        success_count += 1
                    elif result == "failed":
                        failed_count += 1
                    elif result == "skipped":
                        skipped_count += 1
                except (OSError, ValueError):
                    self.logger.exception("Task execution error for %s", task[0])
                    failed_count += 1

                pbar.update(1)
                pbar.set_postfix(
                    {
                        "success": success_count,
                        "failed": failed_count,
                        "skipped": skipped_count,
                    }
                )

        self._generate_download_report(
            success_count, failed_count, skipped_count, str(output_path)
        )

        return {
            "success": success_count,
            "failed": failed_count,
            "skipped": skipped_count,
        }

    def sync_objects(self, prefix: str = "") -> None:
        """Synchronize objects from COS to the local directory."""
        cos_config = self.config["cos_config"]
        bucket_name = cos_config["bucket_name"]

        self.logger.info("Starting synchronization...")

        remote_objects = self.sync_detector.list_remote_objects(bucket_name, prefix)
        local_files = self.sync_detector.get_local_files()

        diff = self.sync_detector.compare_objects(remote_objects, local_files)

        new_files = diff["new"]
        updated_files = diff["updated"]

        self.logger.info(
            "Found %d new files and %d updated files.",
            len(new_files),
            len(updated_files),
        )

        files_to_download = new_files + updated_files
        if files_to_download:
            self.download_objects(files_to_download, show_progress=True)
        else:
            self.logger.info("No new or updated files to download.")

        self.logger.info("Synchronization finished.")

    def _generate_download_report(
        self,
        success_count: int,
        failed_count: int,
        skipped_count: int,
        output_dir: str,
    ) -> None:
        """Generate a download report."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        report_file = log_dir / f"download_report_{timestamp}.json"

        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "output_dir": output_dir,
            "statistics": {
                "success": success_count,
                "failed": failed_count,
                "skipped": skipped_count,
                "total": success_count + failed_count + skipped_count,
            },
            "config": {
                "max_workers": self.max_workers,
                "retry_times": self.retry_times,
            },
        }

        with report_file.open("w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        self.logger.info("Download report saved to: %s", report_file)

    def close(self) -> None:
        """Close resources."""
        if self.index_manager:
            self.index_manager.close()
        self.logger.info("Resources released.")


def main() -> int:
    """Run the main program."""
    parser = argparse.ArgumentParser(
        description="Enhanced downloader for Tencent Cloud COS."
    )
    parser.add_argument(
        "--config", default="config.json", help="Path to the configuration file."
    )
    parser.add_argument(
        "--workers", type=int, default=5, help="Number of concurrent workers."
    )
    parser.add_argument(
        "--retry",
        type=int,
        default=3,
        help="Number of times to retry a failed download.",
    )
    parser.add_argument("--prefix", help="Object prefix to filter by.")
    parser.add_argument("--extensions", nargs="+", help="File extensions to filter by.")
    parser.add_argument("--min-size", type=int, help="Minimum file size in bytes.")
    parser.add_argument("--max-size", type=int, help="Maximum file size in bytes.")
    parser.add_argument("--output-dir", help="Output directory.")
    parser.add_argument(
        "--no-progress", action="store_true", help="Disable the progress bar."
    )
    parser.add_argument(
        "--no-log-file", action="store_true", help="Disable logging to a file."
    )
    parser.add_argument("--sync", action="store_true", help="Enable sync mode.")

    args = parser.parse_args()

    downloader = EnhancedCOSDownloader(
        config_file=args.config, max_workers=args.workers, retry_times=args.retry
    )

    if not downloader.client:
        downloader.logger.error("Failed to initialize COS client.")
        return 1

    try:
        if args.sync:
            downloader.sync_objects(prefix=args.prefix)
        else:
            objects = downloader.list_objects(
                prefix=args.prefix,
                extensions=args.extensions,
                min_size=args.min_size,
                max_size=args.max_size,
            )

            if not objects:
                downloader.logger.info("No matching objects found.")
                return 0

            result = downloader.download_objects(
                objects=objects,
                output_dir=args.output_dir,
                show_progress=not args.no_progress,
            )

            downloader.logger.info("Download complete:")
            downloader.logger.info("  Success: %d", result["success"])
            downloader.logger.info("  Failed: %d", result["failed"])
            downloader.logger.info("  Skipped: %d", result["skipped"])

            if result["failed"] > 0:
                return 1

    except KeyboardInterrupt:
        downloader.logger.info("User interrupted the download.")
        return 1
    except (OSError, ValueError, KeyError):
        downloader.logger.exception("An error occurred")
        return 1
    finally:
        downloader.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
