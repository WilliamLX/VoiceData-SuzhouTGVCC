#!/usr/bin/env python3
"""
腾讯云COS对象获取工具
用于获取指定存储桶中的所有对象
"""

import json
import os
import sys
import time

from qcloud_cos import CosConfig, CosS3Client
from qcloud_cos.cos_exception import CosServiceError


class COSObjectDownloader:
    def __init__(self, secret_id, secret_key, region, bucket_name):
        """
        初始化COS客户端

        Args:
            secret_id (str): 腾讯云SecretId
            secret_key (str): 腾讯云SecretKey
            region (str): COS地域，如ap-beijing-1
            bucket_name (str): 存储桶名称

        """
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.region = region
        self.bucket_name = bucket_name

        # 配置COS客户端
        config = CosConfig(
            Region=self.region, SecretId=self.secret_id, SecretKey=self.secret_key
        )
        self.client = CosS3Client(config)

    def list_all_objects(self, prefix="", max_keys=1000):
        """
        获取存储桶中的所有对象

        Args:
            prefix (str): 对象前缀，用于筛选特定目录下的对象
            max_keys (int): 每次请求返回的最大对象数量

        Returns:
            list: 所有对象的列表

        """
        all_objects = []
        marker = ""

        print(f"正在获取存储桶 '{self.bucket_name}' 中的对象...")
        print(f"前缀筛选: {prefix if prefix else '所有对象'}")

        start_time = time.time()

        while True:
            try:
                # 获取对象列表
                response = self.client.list_objects(
                    Bucket=self.bucket_name,
                    Prefix=prefix,
                    Marker=marker,
                    MaxKeys=max_keys,
                )

                # 检查是否有内容
                if "Contents" in response:
                    objects = response["Contents"]
                    all_objects.extend(objects)
                    print(f"已获取 {len(all_objects)} 个对象...")

                    # 检查是否还有更多对象
                    if response["IsTruncated"]:
                        marker = objects[-1]["Key"]
                    else:
                        break
                else:
                    print("存储桶为空或没有匹配的对象")
                    break

            except CosServiceError as e:
                print(f"获取对象列表时发生错误: {e}")
                break
            except (OSError, IOError, ValueError) as e:
                print(f"发生未知错误: {e}")
                break

        elapsed_time = time.time() - start_time
        print(f"总共获取到 {len(all_objects)} 个对象，耗时 {elapsed_time:.2f} 秒")
        return all_objects

    def get_object_info(self, objects):
        """
        获取对象的详细信息

        Args:
            objects (list): 对象列表

        Returns:
            list: 包含对象详细信息的列表

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
        print(f"获取对象详细信息耗时 {elapsed_time:.2f} 秒")
        return object_info_list

    def save_objects_to_file(self, objects, filename="cos_objects.json"):
        """
        将对象信息保存到JSON文件

        Args:
            objects (list): 对象列表
            filename (str): 输出文件名

        """
        start_time = time.time()

        object_info = self.get_object_info(objects)

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(object_info, f, ensure_ascii=False, indent=2)

        elapsed_time = time.time() - start_time
        print(f"对象信息已保存到 {filename}，耗时 {elapsed_time:.2f} 秒")

    def download_objects(self, objects, local_dir="downloads", prefix_filter=""):
        """
        下载对象到本地目录

        Args:
            objects (list): 要下载的对象列表
            local_dir (str): 本地下载目录
            prefix_filter (str): 前缀过滤器

        """
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)

        downloaded_count = 0
        total_count = len(objects)

        print(f"开始下载 {total_count} 个对象到 {local_dir}...")

        start_time = time.time()

        for obj in objects:
            key = obj["Key"]

            # 如果设置了前缀过滤器，跳过不匹配的对象
            if prefix_filter and not key.startswith(prefix_filter):
                continue

            try:
                # 创建本地文件路径
                local_path = os.path.join(local_dir, key)
                local_dir_path = os.path.dirname(local_path)

                # 创建目录
                if local_dir_path and not os.path.exists(local_dir_path):
                    os.makedirs(local_dir_path)

                # 下载对象
                response = self.client.get_object(Bucket=self.bucket_name, Key=key)

                with open(local_path, "wb") as f:
                    f.write(response["Body"].read())

                downloaded_count += 1
                print(f"已下载 ({downloaded_count}/{total_count}): {key}")

            except (OSError, IOError, ValueError) as e:
                print(f"下载 {key} 时发生错误: {e}")

        elapsed_time = time.time() - start_time
        print(
            f"下载完成！成功下载 {downloaded_count} 个对象，总耗时 {elapsed_time:.2f} 秒"
        )


def main():
    """主函数"""
    print("腾讯云COS对象获取工具")
    print("=" * 50)

    start_time = time.time()

    # 获取用户输入
    # 从配置文件读取COS配置
    try:
        with open("config.json") as f:
            config = json.load(f)
            cos_config = config["cos_config"]
            secret_id = cos_config["secret_id"]
            secret_key = cos_config["secret_key"]
            region = cos_config["region"]
            bucket_name = cos_config["bucket_name"]
    except FileNotFoundError:
        print("错误: 未找到config.json配置文件")
        sys.exit(1)
    except KeyError as e:
        print(f"错误: 配置文件缺少必要的字段: {e}")
        sys.exit(1)
    except json.JSONDecodeError:
        print("错误: config.json格式不正确")
        sys.exit(1)

    # 验证输入
    if not all([secret_id, secret_key, region, bucket_name]):
        print("错误：所有字段都是必填的！")
        sys.exit(1)

    try:
        # 创建下载器实例
        downloader = COSObjectDownloader(secret_id, secret_key, region, bucket_name)

        # 询问是否要筛选特定前缀
        prefix = (
            config["options"]["prefix"]
            if "options" in config and "prefix" in config["options"]
            else ""
        )

        # 获取所有对象
        objects = downloader.list_all_objects(prefix=prefix)

        if not objects:
            print("没有找到任何对象")
            return

        # 显示对象统计信息
        total_size = sum(
            int(obj["Size"]) for obj in objects if isinstance(obj["Size"], (int, str))
        )
        print(f"\n对象统计:")
        print(f"总数量: {len(objects)}")
        print(f"总大小: {total_size / (1024 * 1024):.2f} MB")

        # 询问是否保存对象信息到文件
        save_to_file = input("\n是否保存对象信息到JSON文件? (y/n): ").strip().lower()
        if save_to_file == "y":
            filename = input("请输入文件名 (默认: cos_objects.json): ").strip()
            if not filename:
                filename = "cos_objects.json"
            downloader.save_objects_to_file(objects, filename)

        # 询问是否下载对象
        download_objects = input("\n是否下载所有对象到本地? (y/n): ").strip().lower()
        if download_objects == "y":
            local_dir = input("请输入本地下载目录 (默认: downloads): ").strip()
            if not local_dir:
                local_dir = "downloads"
            downloader.download_objects(objects, local_dir, prefix)

        total_time = time.time() - start_time
        print(f"\n操作完成！总耗时 {total_time:.2f} 秒")

    except (OSError, IOError, ValueError, KeyError) as e:
        print(f"发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
