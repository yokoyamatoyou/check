"""
パフォーマンス監視とメトリクス収集モジュール
"""
import time
import logging
import json
import os
from typing import Dict, Any, Optional, Callable
from functools import wraps
from datetime import datetime, timedelta
import threading
from collections import defaultdict, deque

class PerformanceMonitor:
    """パフォーマンス監視クラス"""
    
    def __init__(self, enable_metrics: bool = True):
        self.logger = logging.getLogger(__name__)
        self.enable_metrics = enable_metrics
        self.metrics = defaultdict(lambda: deque(maxlen=1000))
        self.lock = threading.Lock()
        
        # メトリクス収集間隔
        self.collection_interval = 60  # 秒
        
        if enable_metrics:
            self._start_metrics_collection()
    
    def _start_metrics_collection(self):
        """メトリクス収集の開始"""
        def collect_metrics():
            while True:
                try:
                    self._collect_system_metrics()
                    time.sleep(self.collection_interval)
                except Exception as e:
                    self.logger.error(f"Metrics collection failed: {e}")
        
        thread = threading.Thread(target=collect_metrics, daemon=True)
        thread.start()
    
    def _collect_system_metrics(self):
        """システムメトリクスの収集"""
        try:
            import psutil
            
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            self.record_metric("system.cpu_percent", cpu_percent)
            
            # メモリ使用率
            memory = psutil.virtual_memory()
            self.record_metric("system.memory_percent", memory.percent)
            self.record_metric("system.memory_available", memory.available)
            
            # ディスク使用率
            disk = psutil.disk_usage('/')
            self.record_metric("system.disk_percent", disk.percent)
            
        except ImportError:
            self.logger.warning("psutil not available, skipping system metrics")
    
    def record_metric(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """メトリクスの記録"""
        if not self.enable_metrics:
            return
        
        with self.lock:
            metric_data = {
                "timestamp": datetime.now().isoformat(),
                "value": value,
                "tags": tags or {}
            }
            self.metrics[metric_name].append(metric_data)
    
    def get_metric_stats(self, metric_name: str, window_minutes: int = 5) -> Dict[str, Any]:
        """メトリクスの統計情報を取得"""
        if not self.enable_metrics:
            return {}
        
        with self.lock:
            if metric_name not in self.metrics:
                return {}
            
            # 指定時間内のデータをフィルタ
            cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
            recent_data = [
                item for item in self.metrics[metric_name]
                if datetime.fromisoformat(item["timestamp"]) > cutoff_time
            ]
            
            if not recent_data:
                return {}
            
            values = [item["value"] for item in recent_data]
            
            return {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "latest": values[-1] if values else None
            }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """全メトリクスの取得"""
        if not self.enable_metrics:
            return {}
        
        with self.lock:
            return {
                metric_name: list(metric_data)
                for metric_name, metric_data in self.metrics.items()
            }

class PerformanceDecorator:
    """パフォーマンス計測デコレータ"""
    
    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor
    
    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                success = True
            except Exception as e:
                success = False
                raise
            finally:
                execution_time = time.time() - start_time
                
                # メトリクスを記録
                metric_name = f"function.{func.__module__}.{func.__name__}"
                self.monitor.record_metric(
                    f"{metric_name}.execution_time",
                    execution_time,
                    {"success": str(success)}
                )
                
                # ログ出力
                if execution_time > 1.0:  # 1秒以上かかった場合
                    self.monitor.logger.warning(
                        f"Slow execution detected: {func.__name__} took {execution_time:.2f}s"
                    )
            
            return result
        
        return wrapper

class CacheMonitor:
    """キャッシュ監視クラス"""
    
    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor
        self.cache_hits = 0
        self.cache_misses = 0
        self.lock = threading.Lock()
    
    def record_cache_hit(self, cache_name: str):
        """キャッシュヒットの記録"""
        with self.lock:
            self.cache_hits += 1
        
        self.monitor.record_metric(
            f"cache.{cache_name}.hits",
            1,
            {"cache_name": cache_name}
        )
    
    def record_cache_miss(self, cache_name: str):
        """キャッシュミスの記録"""
        with self.lock:
            self.cache_misses += 1
        
        self.monitor.record_metric(
            f"cache.{cache_name}.misses",
            1,
            {"cache_name": cache_name}
        )
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """キャッシュ統計の取得"""
        with self.lock:
            total_requests = self.cache_hits + self.cache_misses
            hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "hits": self.cache_hits,
                "misses": self.cache_misses,
                "total_requests": total_requests,
                "hit_rate": hit_rate
            }

# グローバルインスタンス
performance_monitor = PerformanceMonitor(enable_metrics=True)
cache_monitor = CacheMonitor(performance_monitor)

def monitor_performance(func: Callable) -> Callable:
    """パフォーマンス監視デコレータ"""
    return PerformanceDecorator(performance_monitor)(func)

def log_performance_metrics():
    """パフォーマンスメトリクスのログ出力"""
    if not performance_monitor.enable_metrics:
        return
    
    # システムメトリクス
    cpu_stats = performance_monitor.get_metric_stats("system.cpu_percent")
    memory_stats = performance_monitor.get_metric_stats("system.memory_percent")
    
    # キャッシュ統計
    cache_stats = cache_monitor.get_cache_stats()
    
    # ログ出力
    performance_monitor.logger.info(
        f"Performance metrics - CPU: {cpu_stats.get('avg', 0):.1f}%, "
        f"Memory: {memory_stats.get('avg', 0):.1f}%, "
        f"Cache hit rate: {cache_stats.get('hit_rate', 0):.1f}%"
    )
