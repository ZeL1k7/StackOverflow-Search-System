from pathlib import Path
import torch
import typer
from utils import (
    load_model,
    load_tokenizer,
    get_n_splits,
)
from vector_index import VectorIndexIVFFlat
from datasets import QuestionDataset


def main(question_path: Path, index_save_path: Path, batch_size: int, device: str):
    dataset = QuestionDataset.from_json(question_path)
    dataloader = torch.utils.data.DataLoader(dataset, batch_size)

    tokenizer = load_tokenizer()
    model = load_model(device)
    print("loading finish")
    n_splits = get_n_splits(dataset_size=len(dataset))

    Index = VectorIndexIVFFlat(dim=384, n_splits=n_splits, neighbors=4)
    Index.build()
    print("index build")
    Index.train(
        tokenizer=tokenizer,
        model=model,
        dataset=dataset,
        batch_size=32,
    )
    print("index trained")
    for batch in dataloader:
        Index.update(batch)
    print("index updated")
    Index.save(index_save_path)


if __name__ == "__main__":
    typer.run(main)