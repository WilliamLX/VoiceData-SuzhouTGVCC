"""Sync detector for comparing remote and local files."""

import logging
from typing import Any

from qcloud_cos import CosS3Client

from index_manager import IndexManager


class SyncDetector:
    """Detect differences between remote COS objects and the local index."""

    def __init__(self, cos_client: CosS3Client, index_manager: IndexManager) -> None:
        """
        Initialize the SyncDetector.

        Args:
            cos_client: An instance of the COS client.
            index_manager: An instance of the IndexManager.

        """
        self.cos_client = cos_client
        self.index_manager = index_manager
        self.logger = logging.getLogger("SyncDetector")

    def list_remote_objects(
        self, bucket_name: str, prefix: str = ""
    ) -> list[dict[str, Any]]:
        """
        List all objects in the COS bucket.

        Args:
            bucket_name: The name of the COS bucket.
            prefix: An optional prefix to filter objects.

        Returns:
            A list of object dictionaries from COS.

        """
        all_objects = []
        marker = ""

        while True:
            try:
                response = self.cos_client.list_objects(
                    Bucket=bucket_name, Prefix=prefix, Marker=marker, MaxKeys=1000
                )

                if "Contents" in response:
                    all_objects.extend(response["Contents"])

                if response.get("IsTruncated") == "true":
                    marker = response["NextMarker"]
                else:
                    break

            except (OSError, ValueError):
                self.logger.exception("Error listing objects")
                break

        return all_objects

    def get_local_files(self) -> list[dict[str, Any]]:
        """
        Get all file records from the local index.

        Returns:
            A list of file records from the IndexManager.

        """
        return self.index_manager.get_all_files()

    def compare_objects(
        self,
        remote_objects: list[dict[str, Any]],
        local_files: list[dict[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Compare remote objects with local files to find differences.

        Args:
            remote_objects: A list of object dictionaries from COS.
            local_files: A list of file records from the local index.

        Returns:
            A dictionary containing lists of new, updated, and deleted files.

        """
        remote_map = {obj["Key"]: obj for obj in remote_objects}
        local_map = {f["cos_key"]: f for f in local_files}

        new_files = [
            remote_obj for key, remote_obj in remote_map.items() if key not in local_map
        ]
        updated_files = [
            remote_obj
            for key, remote_obj in remote_map.items()
            if key in local_map
            and local_map[key]["etag"] != remote_obj["ETag"].strip('"')
        ]
        deleted_files = [local_map[key] for key in local_map if key not in remote_map]

        return {"new": new_files, "updated": updated_files, "deleted": deleted_files}
