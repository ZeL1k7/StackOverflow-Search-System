from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import faiss
import numpy as np
import torch
from tqdm import tqdm
from transformers import AutoModel, AutoTokenizer

from datasets import QuestionDataset
from utils import NotTrainedException, get_sentence_embedding


class IVectorIndex(ABC):
    @abstractmethod
    def build(self):
        ...

    @abstractmethod
    def update(self, vector: np.array):
        ...

    @abstractmethod
    def get(self, vector: np.array, neighbors: int):
        ...

    def get_items(self, items: list[int]) -> list[str]:
        return [self.get(idx) for idx in items]


class VectorIndexIVFFlat(IVectorIndex):
    def __init__(
        self,
        dim: int = 768,
        n_splits: int = 1,
        index: Optional[faiss.Index] = None,
    ) -> None:
        self._index = index
        self._dim = dim
        self._n_splits = n_splits

    @classmethod
    def from_pretrained(cls, index_path: Path) -> "VectorIndexIVFFlat":
        index = faiss.read_index(index_path)
        n_splits = index.nlist
        dim = index.d
        return cls(index=index, dim=dim, n_splits=n_splits)

    def build(self) -> None:
        quantizer = faiss.IndexFlatL2(self._dim)
        self._index = faiss.IndexIVFFlat(quantizer, self._dim, self._n_splits)

    def update(self, vector: np.array) -> None:
        self._index.add(vector)

    def get(self, vector: np.array, neighbors: int) -> list[list[float], list[int]]:
        distances, vectors = self._index.search(vector, neighbors)
        return distances[0], vectors[0]

    def train(
        self,
        tokenizer: AutoTokenizer,
        model: AutoModel,
        dataset: QuestionDataset,
        batch_size: int,
    ) -> None:
        if not self._index.is_trained:
            device = "cuda" if torch.cuda.is_available() else "cpu"

            dataloader = torch.utils.data.DataLoader(dataset, batch_size=batch_size)
            index_data = np.zeros((len(dataset), self._dim), dtype=np.float32)

            for idx, batch in tqdm(enumerate(dataloader)):
                sentence_embeddings = get_sentence_embedding(
                    batch=batch,
                    tokenizer=tokenizer,
                    model=model,
                    device=device,
                )

                index_data[
                    batch_size * idx : batch_size * (idx + 1)
                ] = sentence_embeddings

            self._index.train(index_data)
        else:
            raise NotTrainedException(self._index)

    def save(self, index_path: Path) -> None:
        faiss.write_index(self._index, index_path)
