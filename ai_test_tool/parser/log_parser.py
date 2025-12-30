"""
智能日志解析器
使用AI进行日志分析，支持任意格式的日志
Python 3.13+ 兼容
"""

import json
import uuid
from typing import Generator, Any, Callable, Self
from dataclasses import dataclass, field, asdict
from pathlib import Path

from ..utils.logger import get_logger


@dataclass
class ParsedRequest:
    """解析后的请求数据结构"""
    request_id: str = ""
    timestamp: str = ""
    method: str = ""
    url: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    body: str | None = None
    query_params: dict[str, str] = field(default_factory=dict)
    http_status: int = 0
    response_time_ms: float = 0
    response_body: str | None = None
    category: str = ""
    has_error: bool = False
    error_message: str = ""
    has_warning: bool = False
    warning_message: str = ""
    curl_command: str = ""
    raw_logs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class LogAnalysisResult:
    """日志分析结果"""
    requests: list[ParsedRequest] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "requests": [r.to_dict() for r in self.requests],
            "errors": self.errors,
            "warnings": self.warnings,
            "observations": self.observations
        }


class LogParser:
    """
    智能日志解析器
    
    使用AI分析日志，无需预定义正则表达式，
    可以处理任意格式的日志文件。
    """
    
    def __init__(self, llm_chain: Any = None, verbose: bool = False) -> None:
        """
        初始化解析器
        
        Args:
            llm_chain: LLM分析链实例
            verbose: 是否显示详细日志
        """
        self.llm_chain = llm_chain
        self.verbose = verbose
        self.logger = get_logger(verbose)
        
        # 配置参数
        self.max_chars_per_batch = 6000  # 每批次最大字符数（考虑模型上下文限制）
        self.max_lines_per_batch = 50    # 每批次最大行数
    
    def parse_file(
        self,
        file_path: str,
        chunk_size: int = 1000,
        max_lines: int | None = None,
        progress_callback: Callable[[int, int], None] | None = None
    ) -> Generator[list[ParsedRequest], None, None]:
        """
        解析日志文件
        
        Args:
            file_path: 日志文件路径
            chunk_size: 每批处理的行数（用于进度显示）
            max_lines: 最大处理行数
            progress_callback: 进度回调函数
            
        Yields:
            解析后的请求列表
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"日志文件不存在: {file_path}")
        
        # 读取并分批处理
        batch_lines: list[str] = []
        batch_chars = 0
        line_count = 0
        batch_count = 0
        total_requests = 0
        
        self.logger.start_step("日志解析")
        
        with open(path, encoding='utf-8', errors='ignore') as f:
            for line in f:
                if max_lines and line_count >= max_lines:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                line_count += 1
                
                # 检查是否需要处理当前批次
                if (len(batch_lines) >= self.max_lines_per_batch or 
                    batch_chars + len(line) > self.max_chars_per_batch):
                    
                    if batch_lines:
                        batch_count += 1
                        self.logger.debug(f"处理批次 #{batch_count} ({len(batch_lines)}行)")
                        
                        requests = self._process_batch(batch_lines, batch_count)
                        total_requests += len(requests)
                        
                        if requests:
                            yield requests
                    
                    batch_lines = []
                    batch_chars = 0
                
                batch_lines.append(line)
                batch_chars += len(line)
                
                if progress_callback and line_count % chunk_size == 0:
                    progress_callback(line_count, max_lines or line_count)
        
        # 处理剩余的批次
        if batch_lines:
            batch_count += 1
            self.logger.debug(f"处理批次 #{batch_count} ({len(batch_lines)}行)")
            
            requests = self._process_batch(batch_lines, batch_count)
            total_requests += len(requests)
            
            if requests:
                yield requests
        
        self.logger.end_step(f"完成，共{batch_count}批次，{total_requests}个请求")
    
    def _process_batch(self, lines: list[str], batch_num: int = 0) -> list[ParsedRequest]:
        """
        处理一批日志行
        
        Args:
            lines: 日志行列表
            batch_num: 批次编号
            
        Returns:
            解析后的请求列表
        """
        if self.llm_chain:
            return self._ai_parse(lines, batch_num)
        else:
            self.logger.warn("未配置LLM Chain，使用规则解析（准确性较低）")
            return self._rule_parse(lines)
    
    def _ai_parse(self, lines: list[str], batch_num: int = 0) -> list[ParsedRequest]:
        """
        使用AI解析日志
        
        Args:
            lines: 日志行列表
            batch_num: 批次编号
            
        Returns:
            解析后的请求列表
        """
        log_content = "\n".join(lines)
        
        try:
            result = self.llm_chain.analyze_logs(log_content)
            
            requests: list[ParsedRequest] = []
            for req_data in result.get("requests", []):
                req = ParsedRequest(
                    request_id=req_data.get("request_id", str(uuid.uuid4())),
                    timestamp=str(req_data.get("timestamp", "")),
                    method=req_data.get("method", "").upper(),
                    url=req_data.get("url", ""),
                    headers=req_data.get("headers", {}),
                    body=req_data.get("body"),
                    http_status=req_data.get("http_status", 0),
                    response_time_ms=req_data.get("response_time_ms", 0),
                    has_error=req_data.get("has_error", False),
                    error_message=req_data.get("error_message", ""),
                    has_warning=req_data.get("has_warning", False),
                    warning_message=req_data.get("warning_message", ""),
                    curl_command=req_data.get("curl_command", ""),
                    raw_logs=lines
                )
                
                # 如果AI没有生成curl命令，自动生成
                if not req.curl_command and req.url:
                    req.curl_command = self._generate_curl(req)
                
                if req.url:  # 只保留有URL的请求
                    requests.append(req)
            
            # 记录错误和警告
            errors = result.get("errors", [])
            warnings = result.get("warnings", [])
            if errors:
                self.logger.debug(f"   发现 {len(errors)} 个错误")
            if warnings:
                self.logger.debug(f"   发现 {len(warnings)} 个警告")
            
            return requests
            
        except Exception as e:
            self.logger.error(f"AI解析失败: {e}")
            self.logger.info("降级使用规则解析")
            return self._rule_parse(lines)
    
    def _rule_parse(self, lines: list[str]) -> list[ParsedRequest]:
        """
        使用规则解析日志（备用方案）
        
        尝试解析常见的日志格式
        """
        requests: list[ParsedRequest] = []
        
        for line in lines:
            req = self._try_parse_line(line)
            if req:
                requests.append(req)
        
        return requests
    
    def _try_parse_line(self, line: str) -> ParsedRequest | None:
        """尝试解析单行日志"""
        # 尝试解析JSON格式
        try:
            data = json.loads(line)
            content = data.get('__CONTENT__', '') or data.get('message', '') or str(data)
            timestamp = data.get('__TIMESTAMP__', '')
            
            # 尝试从content中提取请求信息
            req = self._extract_request_from_content(content, timestamp)
            if req:
                return req
        except json.JSONDecodeError:
            pass
        
        # 尝试从纯文本中提取
        return self._extract_request_from_content(line, "")
    
    def _extract_request_from_content(self, content: str, timestamp: str) -> ParsedRequest | None:
        """从内容中提取请求信息"""
        import re
        
        # 通用HTTP方法匹配
        http_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
        
        for method in http_methods:
            # 匹配各种格式的URL
            patterns = [
                rf'{method}\s+"([^"]+)"',  # GET "/api/xxx"
                rf'{method}\s+(/[^\s]+)',   # GET /api/xxx
                rf'method[=:]\s*{method}.*?url[=:]\s*([^\s|]+)',  # method=GET url=/api/xxx
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    url = match.group(1)
                    
                    # 提取状态码
                    status_match = re.search(r'\|\s*(\d{3})\s*\|', content)
                    http_status = int(status_match.group(1)) if status_match else 0
                    
                    # 提取响应时间
                    time_match = re.search(r'(\d+\.?\d*)\s*(ms|µs|us|s)\s*\|', content)
                    response_time = 0.0
                    if time_match:
                        response_time = float(time_match.group(1))
                        unit = time_match.group(2)
                        if unit == 's':
                            response_time *= 1000
                        elif unit in ['µs', 'us']:
                            response_time /= 1000
                    
                    # 提取请求ID
                    id_match = re.search(r'\[([a-f0-9-]{36})\]', content)
                    request_id = id_match.group(1) if id_match else str(uuid.uuid4())
                    
                    # 提取body
                    body_match = re.search(r'body[=:]\s*(\{.+\})', content)
                    body = body_match.group(1) if body_match else None
                    
                    req = ParsedRequest(
                        request_id=request_id,
                        timestamp=str(timestamp),
                        method=method.upper(),
                        url=url,
                        http_status=http_status,
                        response_time_ms=response_time,
                        body=body,
                        raw_logs=[content]
                    )
                    
                    req.curl_command = self._generate_curl(req)
                    return req
        
        return None
    
    def _generate_curl(self, req: ParsedRequest, base_url: str = "http://localhost:8080") -> str:
        """生成curl命令"""
        parts = ["curl", "-s"]
        
        if req.method != "GET":
            parts.append(f"-X {req.method}")
        
        url = req.url
        if not url.startswith("http"):
            url = f"{base_url.rstrip('/')}{url}"
        parts.append(f'"{url}"')
        
        for key, value in req.headers.items():
            parts.append(f'-H "{key}: {value}"')
        
        if req.body:
            body = req.body
            if isinstance(body, dict):
                body = json.dumps(body, ensure_ascii=False)
            if "Content-Type" not in req.headers:
                parts.append('-H "Content-Type: application/json"')
            escaped_body = body.replace("'", "'\\''")
            parts.append(f"-d '{escaped_body}'")
        
        return " ".join(parts)


def analyze_log_file(
    file_path: str,
    max_lines: int | None = None,
    verbose: bool = False
) -> LogAnalysisResult:
    """
    便捷函数：分析日志文件
    
    Args:
        file_path: 日志文件路径
        max_lines: 最大行数
        verbose: 是否显示详细日志
        
    Returns:
        日志分析结果
    """
    from ..llm.chains import LogAnalysisChain
    
    llm_chain = LogAnalysisChain(verbose=verbose)
    parser = LogParser(llm_chain=llm_chain, verbose=verbose)
    
    all_requests: list[ParsedRequest] = []
    for requests in parser.parse_file(file_path, max_lines=max_lines):
        all_requests.extend(requests)
    
    return LogAnalysisResult(requests=all_requests)
