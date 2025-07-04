"""Sync detector for comparing remote and local files."""

from typing import Any, Dict, List


class SyncDetector:
    """Detect differences between remote COS objects and the local index."""

    def __init__(self, cos_client: Any, index_manager: Any) -> None:
        """
        Initialize the SyncDetector.

        Args:
            cos_client: An instance of the COS client.
            index_manager: An instance of the IndexManager.
        """
        self.cos_client = cos_client
        self.index_manager = index_manager

    def list_remote_objects(
        self, bucket_name: str, prefix: str = ""
    ) -> List[Dict[str, Any]]:
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

                # Check if there are more objects
                if response.get("IsTruncated", False):
                    marker = response["Contents"][-1]["Key"]
                else:
                    break

            except (OSError, IOError, ValueError) as e:
                print(f"Error listing objects: {e}")
                break

        return all_objects

    def get_local_files(self) -> List[Dict[str, Any]]:
        """
        Get all file records from the local index.

        Returns:
            A list of file records from the IndexManager.
        """
        return self.index_manager.get_all_files()

    def compare_objects(
        self, remote_objects: List[Dict[str, Any]], local_files: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
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

        new_files = []
        updated_files = []
        deleted_files = []

        # Find new and updated files
        for key, remote_obj in remote_map.items():
            if key not in local_map:
                new_files.append(remote_obj)
            elif local_map[key]["etag"] != remote_obj["ETag"].strip('"'):
                updated_files.append(remote_obj)

        # Find deleted files (files that exist locally but not remotely)
        for key in local_map:
            if key not in remote_map:
                deleted_files.append(local_map[key])

        return {"new": new_files, "updated": updated_files, "deleted": deleted_files}
