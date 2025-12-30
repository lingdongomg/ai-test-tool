"""
请求分析器
对解析后的请求进行智能分析和分类
Python 3.13+ 兼容
"""

import re
from typing import Any
from collections import defaultdict

from ..parser.log_parser import ParsedRequest
from ..llm.chains import LogAnalysisChain
from ..utils.logger import get_logger


class RequestAnalyzer:
    """请求分析器"""
    
    def __init__(self, llm_chain: LogAnalysisChain | None = None, verbose: bool = False) -> None:
        self.llm_chain = llm_chain
        self.verbose = verbose
        self.logger = get_logger(verbose)
        
        # 分类规则（可扩展）
        self.category_rules: list[tuple[str, str, str | None]] = [
            # (模式, 分类, 子分类)
            (r'/product[s_]?manage', '商品管理', None),
            (r'/product[s]?/', '商品管理', None),
            (r'/shop[s]?/', '店铺管理', None),
            (r'/order[s]?/', '订单管理', None),
            (r'/user[s]?/', '用户管理', None),
            (r'/auth/', '认证授权', None),
            (r'/login', '认证授权', '登录'),
            (r'/logout', '认证授权', '登出'),
            (r'/register', '认证授权', '注册'),
            (r'/config/', '配置管理', None),
            (r'/setting[s]?/', '配置管理', None),
            (r'/upload/', '文件管理', '上传'),
            (r'/download/', '文件管理', '下载'),
            (r'/file[s]?/', '文件管理', None),
            (r'/report[s]?/', '报表统计', None),
            (r'/statistic[s]?/', '报表统计', None),
            (r'/analytics/', '报表统计', None),
            (r'/payment[s]?/', '支付管理', None),
            (r'/pay/', '支付管理', None),
            (r'/notification[s]?/', '消息通知', None),
            (r'/message[s]?/', '消息通知', None),
            (r'/search/', '搜索服务', None),
            (r'/cos/', '对象存储', None),
            (r'/oss/', '对象存储', None),
            (r'/session[s]?', '会话管理', None),
        ]
        
        # 编译规则
        self._compiled_rules: list[tuple[re.Pattern[str], str, str | None]] = [
            (re.compile(pattern, re.IGNORECASE), cat, sub)
            for pattern, cat, sub in self.category_rules
        ]
    
    def analyze_requests(self, requests: list[ParsedRequest]) -> dict[str, Any]:
        """分析请求列表"""
        if not requests:
            return {"total": 0, "requests": []}
        
        self.logger.start_step("请求分析")
        
        # 分类请求
        categorized = self._categorize_requests(requests)
        
        # 统计分析
        stats = self._compute_statistics(requests)
        
        # 识别问题
        issues = self._identify_issues(requests)
        
        # 性能分析
        performance = self._analyze_performance(requests)
        
        self.logger.end_step(f"分析完成，{len(requests)}个请求")
        
        return {
            "total": len(requests),
            "requests": [r.to_dict() for r in requests],
            "categorized": categorized,
            "statistics": stats,
            "issues": issues,
            "performance": performance
        }
    
    def _categorize_requests(self, requests: list[ParsedRequest]) -> dict[str, list[dict[str, Any]]]:
        """对请求进行分类"""
        categories: dict[str, list[dict[str, Any]]] = defaultdict(list)
        
        for req in requests:
            category = self._get_category(req.url)
            req.category = category
            categories[category].append({
                "url": req.url,
                "method": req.method,
                "http_status": req.http_status
            })
        
        # 使用LLM进行智能分类增强
        if self.llm_chain:
            self._enhance_categorization_with_llm(requests, categories)
        
        return dict(categories)
    
    def _get_category(self, url: str) -> str:
        """根据URL获取分类"""
        path = url.split('?')[0]
        
        for pattern, category, sub_category in self._compiled_rules:
            if pattern.search(path):
                if sub_category:
                    return f"{category}-{sub_category}"
                return category
        
        # 尝试从路径提取模块名
        parts = path.strip('/').split('/')
        if len(parts) >= 3:
            return parts[2] or '其他'
        elif len(parts) >= 2:
            return parts[1] or '其他'
        
        return '其他'
    
    def _enhance_categorization_with_llm(
        self,
        requests: list[ParsedRequest],
        categories: dict[str, list[dict[str, Any]]]
    ) -> None:
        """使用LLM增强分类"""
        # 找出"其他"分类的请求
        uncategorized = [r for r in requests if r.category == '其他']
        
        if uncategorized and len(uncategorized) <= 50:
            try:
                self.logger.ai_start("分类增强", f"{len(uncategorized)}个未分类请求")
                
                requests_data = [{"url": r.url, "method": r.method} for r in uncategorized]
                result = self.llm_chain.categorize_requests(requests_data)
                
                # 更新分类
                for item in result.get("categorized_requests", []):
                    url = item.get("url")
                    new_category = item.get("category", "其他")
                    
                    for req in uncategorized:
                        if req.url == url:
                            req.category = new_category
                            # 更新分类字典
                            if "其他" in categories:
                                categories["其他"] = [
                                    r for r in categories["其他"] if r["url"] != url
                                ]
                            if new_category not in categories:
                                categories[new_category] = []
                            categories[new_category].append({
                                "url": url,
                                "method": req.method,
                                "http_status": req.http_status
                            })
                
                self.logger.ai_end()
            except Exception as e:
                self.logger.error(f"LLM分类增强失败: {e}")
    
    def _compute_statistics(self, requests: list[ParsedRequest]) -> dict[str, Any]:
        """计算统计数据"""
        total = len(requests)
        
        # 状态统计
        success_count = sum(1 for r in requests if 200 <= r.http_status < 400)
        client_error_count = sum(1 for r in requests if 400 <= r.http_status < 500)
        server_error_count = sum(1 for r in requests if r.http_status >= 500)
        unknown_status_count = sum(1 for r in requests if r.http_status == 0)
        
        # 方法统计
        method_stats: dict[str, int] = defaultdict(int)
        for r in requests:
            method_stats[r.method] += 1
        
        # 分类统计
        category_stats: dict[str, int] = defaultdict(int)
        for r in requests:
            category_stats[r.category] += 1
        
        # 错误和警告统计
        error_count = sum(1 for r in requests if r.has_error)
        warning_count = sum(1 for r in requests if r.has_warning)
        
        return {
            "total_requests": total,
            "success_count": success_count,
            "success_rate": f"{success_count/total*100:.2f}%" if total > 0 else "0%",
            "client_error_count": client_error_count,
            "server_error_count": server_error_count,
            "unknown_status_count": unknown_status_count,
            "error_count": error_count,
            "warning_count": warning_count,
            "method_distribution": dict(method_stats),
            "category_distribution": dict(category_stats)
        }
    
    def _identify_issues(self, requests: list[ParsedRequest]) -> dict[str, list[dict[str, Any]]]:
        """识别问题"""
        issues: dict[str, list[dict[str, Any]]] = {
            "errors": [],
            "warnings": [],
            "slow_requests": [],
            "failed_requests": []
        }
        
        for req in requests:
            # 收集错误
            if req.has_error:
                issues["errors"].append({
                    "url": req.url,
                    "method": req.method,
                    "message": req.error_message[:200] if req.error_message else ""
                })
            
            # 收集警告
            if req.has_warning:
                issues["warnings"].append({
                    "url": req.url,
                    "method": req.method,
                    "message": req.warning_message[:200] if req.warning_message else ""
                })
            
            # 慢请求（超过1秒）
            if req.response_time_ms > 1000:
                issues["slow_requests"].append({
                    "url": req.url,
                    "method": req.method,
                    "response_time_ms": req.response_time_ms
                })
            
            # 失败请求
            if req.http_status >= 400:
                issues["failed_requests"].append({
                    "url": req.url,
                    "method": req.method,
                    "http_status": req.http_status
                })
        
        return issues
    
    def _analyze_performance(self, requests: list[ParsedRequest]) -> dict[str, Any]:
        """分析性能"""
        response_times = [r.response_time_ms for r in requests if r.response_time_ms > 0]
        
        if not response_times:
            return {"no_data": True}
        
        response_times.sort()
        n = len(response_times)
        
        return {
            "total_requests_with_timing": n,
            "avg_response_time_ms": round(sum(response_times) / n, 2),
            "min_response_time_ms": round(min(response_times), 2),
            "max_response_time_ms": round(max(response_times), 2),
            "p50_response_time_ms": round(response_times[n // 2], 2),
            "p90_response_time_ms": round(response_times[int(n * 0.9)], 2),
            "p99_response_time_ms": round(response_times[int(n * 0.99)], 2) if n >= 100 else None,
            "slow_request_count": sum(1 for t in response_times if t > 1000),
            "very_slow_request_count": sum(1 for t in response_times if t > 3000)
        }
    
    def add_category_rule(self, pattern: str, category: str, sub_category: str | None = None) -> None:
        """添加自定义分类规则"""
        self.category_rules.append((pattern, category, sub_category))
        self._compiled_rules.append(
            (re.compile(pattern, re.IGNORECASE), category, sub_category)
        )
