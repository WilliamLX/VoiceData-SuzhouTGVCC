#!/usr/bin/env python3
"""
腾讯云COS增强下载器
支持多线程并发下载、断点续传、文件过滤、进度显示等功能
"""

import argparse
import hashlib
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from qcloud_cos import CosConfig, CosS3Client
from qcloud_cos.cos_exception import CosServiceError
from tqdm import tqdm

from index_manager import IndexManager
from sync_detector import SyncDetector


class EnhancedCOSDownloader:
    """增强版COS下载器"""

    def __init__(self, config_file="config.json", max_workers=5, retry_times=3):
        """
        初始化下载器

        Args:
            config_file: 配置文件路径
            max_workers: 最大并发数
            retry_times: 重试次数

        """
        self.config_file = config_file
        self.max_workers = max_workers
        self.retry_times = retry_times
        self.config = self._load_config()
        print(self.config)
        self.client = self._init_client()
        self.logger = self._setup_logger()
        self.index_manager = IndexManager()
        self.sync_detector = SyncDetector(self.client, self.index_manager)

    def _load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_file, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"配置文件 {self.config_file} 不存在")
            return None
        except json.JSONDecodeError:
            print(f"配置文件 {self.config_file} 格式错误")
            return None

    def _init_client(self):
        """初始化COS客户端"""
        if not self.config:
            return None

        cos_config = self.config["cos_config"]
        client_config = CosConfig(
            Region=cos_config["region"],
            SecretId=cos_config["secret_id"],
            SecretKey=cos_config["secret_key"],
        )
        return CosS3Client(client_config)

    def _setup_logger(self):
        """设置日志记录器"""
        logger = logging.getLogger("EnhancedCOSDownloader")
        logger.setLevel(logging.INFO)

        # 创建日志目录
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)

        # 文件处理器
        log_file = os.path.join(
            log_dir, f"download_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)

        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # 格式化器
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def _calculate_md5(self, file_path):
        """计算文件MD5值"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except (OSError, IOError) as e:
            self.logger.warning(f"计算MD5时发生错误: {e}")
            return None

    def _download_single_file(self, cos_key, local_path, file_size, etag):
        """
        下载单个文件

        Args:
            cos_key: COS对象键
            local_path: 本地文件路径
            file_size: 文件大小（用于进度显示）
            etag: 文件的ETag

        Returns:
            str: 下载结果 ('success', 'skipped', 'failed')

        """
        cos_config = self.config["cos_config"]

        # 检查文件是否已在索引中
        if self.index_manager.file_exists(cos_key, etag):
            self.logger.info(f"文件已索引，跳过: {cos_key}")
            return "skipped"

        # 检查文件是否已存在且大小正确
        if os.path.exists(local_path):
            if file_size and os.path.getsize(local_path) == file_size:
                self.logger.info(f"文件已存在，跳过: {cos_key}")
                return "skipped"

        # 创建目录
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        # 下载文件
        for attempt in range(self.retry_times):
            try:
                self.client.download_file(
                    Bucket=cos_config["bucket_name"],
                    Key=cos_key,
                    DestFilePath=local_path,
                )

                # 下载成功后添加到索引
                md5_hash = self._calculate_md5(local_path)
                last_modified = datetime.fromtimestamp(
                    os.path.getmtime(local_path)
                ).isoformat()
                self.index_manager.add_file(
                    file_path=local_path,
                    file_size=file_size,
                    last_modified=last_modified,
                    md5_hash=md5_hash,
                    cos_key=cos_key,
                    etag=etag,
                )
                self.logger.info(f"下载成功: {cos_key}")
                return "success"

            except (CosServiceError, OSError, IOError) as e:
                self.logger.warning(
                    f"下载失败 (尝试 {attempt + 1}/{self.retry_times}): {cos_key} - {e}"
                )
                if attempt < self.retry_times - 1:
                    time.sleep(2**attempt)  # 指数退避
                else:
                    self.logger.exception(f"下载最终失败: {cos_key}")
                    return "failed"

    def list_objects(self, prefix=None, extensions=None, min_size=None, max_size=None):
        """
        列出COS对象

        Args:
            prefix: 前缀筛选
            extensions: 文件扩展名列表
            min_size: 最小文件大小
            max_size: 最大文件大小

        Returns:
            list: 对象列表

        """
        cos_config = self.config["cos_config"]
        options = self.config.get("options", {})

        if prefix is None:
            prefix = options.get("prefix", "")

        all_objects = []
        marker = ""
        max_keys = options.get("max_keys_per_request", 1000)

        self.logger.info(f"正在获取存储桶 '{cos_config['bucket_name']}' 中的对象...")
        if prefix:
            self.logger.info(f"前缀筛选: {prefix}")

        while True:
            try:
                response = self.client.list_objects(
                    Bucket=cos_config["bucket_name"],
                    Prefix=prefix,
                    Marker=marker,
                    MaxKeys=max_keys,
                )

                if "Contents" in response:
                    objects = response["Contents"]

                    # 应用过滤器
                    filtered_objects = []
                    for obj in objects:
                        # 扩展名过滤
                        if extensions:
                            file_ext = os.path.splitext(obj["Key"])[1].lower()
                            if file_ext not in extensions:
                                continue

                        # 文件大小过滤
                        if min_size and int(obj["Size"]) < min_size:
                            continue
                        if max_size and int(obj["Size"]) > max_size:
                            continue

                        filtered_objects.append(obj)

                    all_objects.extend(filtered_objects)
                    self.logger.info(f"已获取 {len(all_objects)} 个对象...")

                    if response.get("IsTruncated") == "true":
                        marker = response["NextMarker"]
                    else:
                        break
                else:
                    self.logger.info("存储桶为空或没有匹配的对象")
                    break

            except CosServiceError as e:
                self.logger.exception(f"获取对象列表时发生错误: {e}")
                break
            except (OSError, IOError, ValueError) as e:
                self.logger.exception(f"发生未知错误: {e}")
                break

        self.logger.info(f"总共获取到 {len(all_objects)} 个对象")
        return all_objects

    def download_objects(self, objects, output_dir=None, show_progress=True):
        """
        下载对象列表

        Args:
            objects: 对象列表
            output_dir: 输出目录
            show_progress: 是否显示进度条

        Returns:
            dict: 下载结果统计

        """
        if not objects:
            self.logger.warning("没有对象需要下载")
            return {"success": 0, "failed": 0, "skipped": 0}

        options = self.config.get("options", {})
        if output_dir is None:
            output_dir = options.get("download_dir", "downloads")

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        # 准备下载任务
        download_tasks = []
        for obj in objects:
            cos_key = obj["Key"]
            local_path = os.path.join(output_dir, cos_key.replace("/", os.sep))
            download_tasks.append(
                (cos_key, local_path, int(obj["Size"]), obj["ETag"].strip('"'))
            )

        # 统计信息
        success_count = 0
        failed_count = 0
        skipped_count = 0

        self.logger.info(f"开始下载 {len(download_tasks)} 个对象到目录: {output_dir}")

        if show_progress:
            # 使用进度条
            with tqdm(total=len(download_tasks), desc="下载进度") as pbar:
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    # 提交所有任务
                    future_to_task = {
                        executor.submit(self._download_single_file, *task): task
                        for task in download_tasks
                    }

                    # 处理完成的任务
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
                        except (OSError, IOError, ValueError) as e:
                            self.logger.exception(f"任务执行异常: {task[0]} - {e}")
                            failed_count += 1

                        pbar.update(1)
                        pbar.set_postfix(
                            {
                                "成功": success_count,
                                "失败": failed_count,
                                "跳过": skipped_count,
                            }
                        )
        else:
            # 不使用进度条
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
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
                    except (OSError, IOError, ValueError) as e:
                        self.logger.exception(f"任务执行异常: {task[0]} - {e}")
                        failed_count += 1

        # 生成下载报告
        self._generate_download_report(
            success_count, failed_count, skipped_count, output_dir
        )

        return {
            "success": success_count,
            "failed": failed_count,
            "skipped": skipped_count,
        }

    def sync_objects(self, prefix=""):
        """Synchronizes objects from COS to the local directory."""
        cos_config = self.config["cos_config"]
        bucket_name = cos_config["bucket_name"]

        self.logger.info("Starting synchronization...")

        # 1. Get remote and local file lists
        remote_objects = self.sync_detector.list_remote_objects(bucket_name, prefix)
        local_files = self.sync_detector.get_local_files()

        # 2. Compare and find differences
        diff = self.sync_detector.compare_objects(remote_objects, local_files)

        new_files = diff["new"]
        updated_files = diff["updated"]

        self.logger.info(
            f"Found {len(new_files)} new files and {len(updated_files)} updated files."
        )

        # 3. Download new and updated files
        files_to_download = new_files + updated_files
        if files_to_download:
            self.download_objects(files_to_download)
        else:
            self.logger.info("No new or updated files to download.")

        self.logger.info("Synchronization finished.")

    def _generate_download_report(
        self, success_count, failed_count, skipped_count, output_dir
    ):
        """生成下载报告"""
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(log_dir, f"download_report_{timestamp}.json")

        report = {
            "timestamp": datetime.now().isoformat(),
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

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        self.logger.info(f"下载报告已保存到: {report_file}")

    def close(self):
        """关闭资源"""
        if self.index_manager:
            self.index_manager.close()
        self.logger.info("资源已释放")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="腾讯云COS增强下载器")
    parser.add_argument("--config", default="config.json", help="配置文件路径")
    parser.add_argument("--workers", type=int, default=5, help="并发下载数")
    parser.add_argument("--retry", type=int, default=3, help="重试次数")
    parser.add_argument("--prefix", help="对象前缀筛选")
    parser.add_argument("--extensions", nargs="+", help="文件扩展名过滤")
    parser.add_argument("--min-size", type=int, help="最小文件大小（字节）")
    parser.add_argument("--max-size", type=int, help="最大文件大小（字节）")
    parser.add_argument("--output-dir", help="输出目录")
    parser.add_argument("--no-progress", action="store_true", help="禁用进度条")
    parser.add_argument("--no-log-file", action="store_true", help="禁用日志文件")
    parser.add_argument("--sync", action="store_true", help="Enable sync mode")

    args = parser.parse_args()

    # 创建下载器
    downloader = EnhancedCOSDownloader(
        config_file=args.config, max_workers=args.workers, retry_times=args.retry
    )

    if not downloader.client:
        print("初始化COS客户端失败")
        return 1

    try:
        if args.sync:
            downloader.sync_objects(prefix=args.prefix)
        else:
            # 获取对象列表
            objects = downloader.list_objects(
                prefix=args.prefix,
                extensions=args.extensions,
                min_size=args.min_size,
                max_size=args.max_size,
            )

            if not objects:
                print("没有找到匹配的对象")
                return 0

            # 下载对象
            result = downloader.download_objects(
                objects=objects,
                output_dir=args.output_dir,
                show_progress=not args.no_progress,
            )

            # 显示结果
            print("\n下载完成:")
            print(f"  成功: {result['success']}")
            print(f"  失败: {result['failed']}")
            print(f"  跳过: {result['skipped']}")

            if result["failed"] > 0:
                return 1

    except KeyboardInterrupt:
        print("\n用户中断下载")
        return 1
    except (OSError, IOError, ValueError, KeyError) as e:
        print(f"发生错误: {e}")
        return 1
    finally:
        downloader.close()

    return 0


if __name__ == "__main__":
    exit(main())
