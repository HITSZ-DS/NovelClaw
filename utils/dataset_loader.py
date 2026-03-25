"""
数据集加载工具：从公开数据集加载长故事/创意文本数据
"""
import os
import json
from typing import List, Dict, Optional
from pathlib import Path
from itertools import islice


class DatasetLoader:
    """数据集加载器：支持多种公开数据集"""
    
    # 推荐的数据集
    DATASETS = {
        "storydb": {
            "name": "StoryDB",
            "description": "多语言叙事数据集，42种语言，500+故事",
            "url": "https://github.com/allenai/storydb",
            "format": "json",
            "language": "multilingual"
        },
        "bookcorpus": {
            "name": "BookCorpus",
            "description": "11,038本免费小说，英文",
            "url": "https://github.com/soskek/bookcorpus",
            "format": "txt",
            "language": "english"
        },
        "webnovel_cn": {
            "name": "WebNovel Chinese",
            "description": "约9000本中文网络小说",
            "url": "https://huggingface.co/datasets/wdndev/webnovel-chinese",
            "format": "txt",
            "language": "chinese"
        }
    }
    
    @staticmethod
    def load_from_huggingface(
        dataset_name: str,
        split: str = "train",
        max_samples: Optional[int] = None,
        streaming: Optional[bool] = None
    ) -> List[Dict]:
        """
        从HuggingFace加载数据集
        
        Args:
            dataset_name: 数据集名称（如 "wdndev/webnovel-chinese"）
            split: 数据集分割（train, test等）
            max_samples: 最大加载样本数
        
        Returns:
            数据列表，每个元素包含文本和元数据
        """
        try:
            from datasets import load_dataset
            
            print(f"正在从HuggingFace加载数据集: {dataset_name}")
            
            # 对于超大数据集，优先使用 streaming，避免先下载整片再抽样
            if streaming is None:
                streaming = max_samples is not None
            
            if streaming:
                dataset = load_dataset(dataset_name, split=split, streaming=True)
                iterator = islice(dataset, max_samples) if max_samples else dataset
            else:
                dataset = load_dataset(dataset_name, split=split)
                if max_samples:
                    dataset = dataset.select(range(min(max_samples, len(dataset))))
                iterator = dataset
            
            results = []
            for item in iterator:
                # 根据数据集结构提取文本
                text = item.get("text", item.get("content", ""))
                if text:
                    # 清洗 metadata，避免向量库拒绝列表/复杂对象
                    raw_meta = item if isinstance(item, dict) else {}
                    safe_meta = {}
                    for k, v in raw_meta.items():
                        if isinstance(v, (str, int, float, bool)) or v is None:
                            safe_meta[k] = v
                        else:
                            # 列表/字典等转字符串截断
                            try:
                                safe_meta[k] = str(v)[:500]
                            except Exception:
                                pass
                    results.append({
                        "text": text,
                        "title": item.get("title", "未知"),
                        "author": item.get("author", "未知"),
                        "genre": item.get("genre", "未知"),
                        "metadata": safe_meta
                    })
            
            print(f"成功加载 {len(results)} 条数据")
            return results
            
        except ImportError:
            print("⚠️ 需要安装 datasets 库: pip install datasets")
            return []
        except Exception as e:
            print(f"加载数据集失败: {e}")
            return []
    
    @staticmethod
    def load_from_directory(
        directory_path: str,
        file_pattern: str = "*.txt",
        encoding: str = "utf-8",
        max_files: Optional[int] = None,
        recursive: bool = False,
        file_patterns: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        从目录加载文本文件
        
        Args:
            directory_path: 目录路径
            file_pattern: 文件匹配模式
            encoding: 文件编码
            max_files: 最大文件数
        
        Returns:
            数据列表
        """
        import glob
        
        patterns = file_patterns or [file_pattern]
        files: List[str] = []
        for pat in patterns:
            if recursive:
                files.extend(glob.glob(os.path.join(directory_path, "**", pat), recursive=True))
            else:
                files.extend(glob.glob(os.path.join(directory_path, pat)))

        # 去重 + 排序，便于稳定导入
        files = sorted(set(files))
        
        if max_files:
            files = files[:max_files]
        
        results = []
        for file_path in files:
            try:
                with open(file_path, "r", encoding=encoding, errors="ignore") as f:
                    text = f.read().strip()
                
                if len(text) > 100:  # 只加载有足够内容的文件
                    title = Path(file_path).stem
                    results.append({
                        "text": text,
                        "title": title,
                        "author": "未知",
                        "genre": "未知",
                        "metadata": {"file_path": file_path}
                    })
            except Exception as e:
                print(f"加载文件失败 {file_path}: {e}")
        
        print(f"从目录加载了 {len(results)} 个文件")
        return results
    
    @staticmethod
    def load_from_json(
        json_path: str,
        text_field: str = "text",
        title_field: str = "title"
    ) -> List[Dict]:
        """
        从JSON文件加载数据
        
        Args:
            json_path: JSON文件路径
            text_field: 文本字段名
            title_field: 标题字段名
        
        Returns:
            数据列表
        """
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            results = []
            if isinstance(data, list):
                for item in data:
                    text = item.get(text_field, "")
                    if text:
                        results.append({
                            "text": text,
                            "title": item.get(title_field, "未知"),
                            "author": item.get("author", "未知"),
                            "genre": item.get("genre", "未知"),
                            "metadata": item
                        })
            elif isinstance(data, dict):
                # 如果是字典，尝试找到包含文本的列表
                for key, value in data.items():
                    if isinstance(value, list):
                        for item in value:
                            text = item.get(text_field, "")
                            if text:
                                results.append({
                                    "text": text,
                                    "title": item.get(title_field, "未知"),
                                    "author": item.get("author", "未知"),
                                    "genre": item.get("genre", "未知"),
                                    "metadata": item
                                })
            
            print(f"从JSON加载了 {len(results)} 条数据")
            return results
            
        except Exception as e:
            print(f"加载JSON失败: {e}")
            return []
    
    @staticmethod
    def download_sample_data(output_dir: str = "./sample_data"):
        """
        下载示例数据（如果可用）
        
        Args:
            output_dir: 输出目录
        """
        os.makedirs(output_dir, exist_ok=True)
        print(f"示例数据将保存到: {output_dir}")
        print("\n推荐的数据集下载方式：")
        print("1. HuggingFace: 使用 load_from_huggingface()")
        print("2. 手动下载后使用 load_from_directory()")
        print("\n推荐的中文数据集：")
        print("- wdndev/webnovel-chinese (HuggingFace)")
        print("- qgyd2021/h_novel (HuggingFace)")
        print("\n推荐的英文数据集：")
        print("- BookCorpus")
        print("- StoryDB")


def quick_load_chinese_novels(max_samples: int = 100) -> List[Dict]:
    """
    快速加载中文小说数据（从HuggingFace）
    
    Args:
        max_samples: 最大样本数
    
    Returns:
        数据列表
    """
    # 尝试加载中文网络小说数据集
    datasets_to_try = [
        "wdndev/webnovel-chinese",
        "qgyd2021/h_novel",
    ]
    
    for dataset_name in datasets_to_try:
        try:
            data = DatasetLoader.load_from_huggingface(
                dataset_name,
                max_samples=max_samples
            )
            if data:
                return data
        except:
            continue
    
    print("⚠️ 无法从HuggingFace加载数据，请手动下载数据集")
    return []


def quick_load_english_novels(max_samples: int = 100) -> List[Dict]:
    """
    快速加载英文小说数据
    
    Args:
        max_samples: 最大样本数
    
    Returns:
        数据列表
    """
    # BookCorpus通常需要从GitHub下载
    print("⚠️ 英文数据集需要手动下载")
    print("推荐: BookCorpus (https://github.com/soskek/bookcorpus)")
    return []

