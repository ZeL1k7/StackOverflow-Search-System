import math
from functools import lru_cache
import torch
from transformers import AutoTokenizer, AutoModel
from question_answer_index import IQAIndex
from vector_index import IVectorIndex

@lru_cache(1)
def load_model(device: torch.device = "cpu") -> AutoModel:
    model = AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
    model.to(device)
    return model


@lru_cache(1)
def load_tokenizer(*args, **kwargs) -> AutoTokenizer:
    tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
    return tokenizer


def mean_pooling(
    model_output: torch.FloatTensor, attention_mask: torch.BoolTensor
) -> torch.FloatTensor:
    """
    Make sentence embedding averaging word embeddings
    :param model_output:
    :param attention_mask:
    :return:
    """
    token_embeddings = model_output[0]
    input_mask_expanded = (
        attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    )
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(
        input_mask_expanded.sum(1), min=1e-9
    )


def get_sentence_embedding(
    batch: list[str], tokenizer: AutoTokenizer, model: AutoModel
) -> torch.FloatTensor:
    encoded_input = tokenizer(
        batch,
        truncation=True,
        padding=True,
        return_tensors="pt",
    )
    word_embeddings = model(**encoded_input)
    sentence_embedding = mean_pooling(
        model_output=word_embeddings,
        attention_mask=encoded_input["attention_mask"],
    )
    sentence_embedding = sentence_embedding.detach().cpu().numpy()
    return sentence_embedding


def get_answer(
    index: IVectorIndex,
    qa_index: IQAIndex,
    tokenizer: AutoTokenizer,
    model: AutoModel,
    sentence: list[str],
    neighbors: int = 4,
) -> list[str]:
    query = get_sentence_embedding(
        batch=sentence,
        tokenizer=tokenizer,
        model=model,
    )

    distances, question_idxs = index.get(query, neighbors)

    return qa_index.get_items(question_idxs)


def get_n_splits(dataset_size: int, n_splits: int = None) -> int:
    """
    https://github.com/facebookresearch/faiss/wiki/Guidelines-to-choose-an-index
    :param dataset_size:
    :param n_splits:
    :return:
    """
    if n_splits is None:
        n_splits = int(4 * math.sqrt(dataset_size))
    return n_splits


class NotTrainedException(Exception):
    def __init__(self, index):
        self.index_type = type(index).__name__

    def __str__(self):
        return f"{self.index_type} should be trained before adding new vectors"
