"""
向量化适配器
该文件内容使用AI生成，注意识别准确性

支持多种embedding提供商：
1. LLM Provider的embedding接口（Ollama/OpenAI/Anthropic）
2. 本地sentence-transformers模型
3. TF-IDF降级方案
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Embedding提供商抽象基类"""
    
    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """将文本转换为向量"""
        pass
    
    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量将文本转换为向量"""
        pass
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """向量维度"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """提供商名称"""
        pass


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Ollama Embedding提供商"""
    
    def __init__(self, model: str = "nomic-embed-text", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self._dimension = 768  # nomic-embed-text 默认维度
        
    def embed(self, text: str) -> list[float]:
        try:
            import requests
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=30
            )
            response.raise_for_status()
            return response.json()["embedding"]
        except Exception as e:
            logger.error(f"Ollama embedding failed: {e}")
            raise
    
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]
    
    @property
    def dimension(self) -> int:
        return self._dimension
    
    @property
    def name(self) -> str:
        return f"ollama/{self.model}"


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI Embedding提供商"""
    
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self.api_key = api_key
        self.model = model
        self._dimension = 1536 if "small" in model else 3072
        self._client = None
        
    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        return self._client
    
    def embed(self, text: str) -> list[float]:
        try:
            client = self._get_client()
            response = client.embeddings.create(input=text, model=self.model)
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}")
            raise
    
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        try:
            client = self._get_client()
            response = client.embeddings.create(input=texts, model=self.model)
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"OpenAI batch embedding failed: {e}")
            raise
    
    @property
    def dimension(self) -> int:
        return self._dimension
    
    @property
    def name(self) -> str:
        return f"openai/{self.model}"


class SentenceTransformerProvider(EmbeddingProvider):
    """本地Sentence Transformer提供商"""
    
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        self.model_name = model_name
        self._model = None
        self._dimension = 384  # MiniLM默认维度
        
    def _get_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                self._dimension = self._model.get_sentence_embedding_dimension()
            except ImportError:
                logger.error("sentence-transformers not installed")
                raise
        return self._model
    
    def embed(self, text: str) -> list[float]:
        model = self._get_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()
        embeddings = model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    
    @property
    def dimension(self) -> int:
        return self._dimension
    
    @property
    def name(self) -> str:
        return f"sentence-transformers/{self.model_name}"


class TFIDFEmbeddingProvider(EmbeddingProvider):
    """TF-IDF降级方案"""
    
    def __init__(self, max_features: int = 512):
        self.max_features = max_features
        self._vectorizer = None
        self._is_fitted = False
        self._corpus: list[str] = []
        
    def _get_vectorizer(self):
        if self._vectorizer is None:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self._vectorizer = TfidfVectorizer(
                max_features=self.max_features,
                ngram_range=(1, 2)
            )
        return self._vectorizer
    
    def fit(self, texts: list[str]) -> None:
        """训练TF-IDF模型"""
        vectorizer = self._get_vectorizer()
        vectorizer.fit(texts)
        self._is_fitted = True
        self._corpus = texts
    
    def embed(self, text: str) -> list[float]:
        vectorizer = self._get_vectorizer()
        if not self._is_fitted:
            # 如果未训练，先用当前文本训练
            vectorizer.fit([text])
            self._is_fitted = True
        
        try:
            vector = vectorizer.transform([text]).toarray()[0]
            return vector.tolist()
        except Exception:
            # 返回零向量
            return [0.0] * self.max_features
    
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        vectorizer = self._get_vectorizer()
        if not self._is_fitted:
            vectorizer.fit(texts)
            self._is_fitted = True
        
        vectors = vectorizer.transform(texts).toarray()
        return vectors.tolist()
    
    @property
    def dimension(self) -> int:
        return self.max_features
    
    @property
    def name(self) -> str:
        return "tfidf"


class DummyEmbeddingProvider(EmbeddingProvider):
    """空实现（用于测试或无embedding场景）"""
    
    def __init__(self, dim: int = 384):
        self._dimension = dim
    
    def embed(self, text: str) -> list[float]:
        # 返回基于文本hash的伪随机向量
        np.random.seed(hash(text) % (2**32))
        return np.random.randn(self._dimension).tolist()
    
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]
    
    @property
    def dimension(self) -> int:
        return self._dimension
    
    @property
    def name(self) -> str:
        return "dummy"


def get_embedding_provider(
    provider_type: str = "auto",
    **kwargs: Any
) -> EmbeddingProvider:
    """
    获取Embedding提供商
    
    Args:
        provider_type: 提供商类型
            - "auto": 自动选择可用的提供商
            - "ollama": Ollama
            - "openai": OpenAI
            - "sentence-transformers": 本地模型
            - "tfidf": TF-IDF降级
            - "dummy": 空实现
        **kwargs: 提供商配置参数
    
    Returns:
        EmbeddingProvider实例
    """
    if provider_type == "ollama":
        return OllamaEmbeddingProvider(
            model=kwargs.get("model", "nomic-embed-text"),
            base_url=kwargs.get("base_url", "http://localhost:11434")
        )
    
    if provider_type == "openai":
        api_key = kwargs.get("api_key")
        if not api_key:
            raise ValueError("OpenAI embedding requires api_key")
        return OpenAIEmbeddingProvider(
            api_key=api_key,
            model=kwargs.get("model", "text-embedding-3-small")
        )
    
    if provider_type == "sentence-transformers":
        return SentenceTransformerProvider(
            model_name=kwargs.get("model", "paraphrase-multilingual-MiniLM-L12-v2")
        )
    
    if provider_type == "tfidf":
        return TFIDFEmbeddingProvider(
            max_features=kwargs.get("max_features", 512)
        )
    
    if provider_type == "dummy":
        return DummyEmbeddingProvider(
            dim=kwargs.get("dimension", 384)
        )
    
    if provider_type == "auto":
        # 自动检测可用的提供商
        
        # 1. 尝试Ollama
        try:
            provider = OllamaEmbeddingProvider()
            provider.embed("test")  # 测试连接
            logger.info("Using Ollama embedding provider")
            return provider
        except Exception:
            pass
        
        # 2. 尝试sentence-transformers
        try:
            provider = SentenceTransformerProvider()
            provider.embed("test")
            logger.info("Using Sentence Transformers embedding provider")
            return provider
        except Exception:
            pass
        
        # 3. 降级到TF-IDF
        logger.warning("Falling back to TF-IDF embedding")
        return TFIDFEmbeddingProvider()
    
    raise ValueError(f"Unknown embedding provider type: {provider_type}")


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """计算余弦相似度"""
    a = np.array(vec1)
    b = np.array(vec2)
    
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return float(np.dot(a, b) / (norm_a * norm_b))
