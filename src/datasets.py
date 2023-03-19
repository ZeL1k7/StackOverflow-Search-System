from typing import List
from pathlib import Path
from pydantic import BaseModel, Field
import torch


class Question(BaseModel):
    id: int = Field(..., description="Unique identifier")
    title: str = Field(..., description="Title of the question")


class Questions(BaseModel):
    items: List[Question]


class QuestionDataset(torch.utils.data.Dataset):
    def __init__(self, questions: Questions) -> None:
        super().__init__()
        self.questions = questions

    @classmethod
    def from_json(cls, path: Path):
        questions = Questions.parse_file(path)
        return cls(questions=questions)

    def __getitem__(self, idx):
        return self.questions.items[idx].title

    def __len__(self):
        return len(self.questions.items)


class Answer(BaseModel):
    id: int = Field(..., description="Id of answer")
    parent_id: int = Field(..., description="Id of parent question")
    text: str = Field(..., description="Text of the answer")
    score: int = Field(..., description="Score of the answer")


class Answers(BaseModel):
    items: List[Answer]


class AnswerDataset:
    def __init__(self, answers: Answers) -> None:
        self.answers = answers

    @classmethod
    def from_json(cls, path: Path):
        answers = Answers.parse_file(path)
        return cls(answers=answers)

    def __getitem__(self, idx):
        item = self.answers.items[idx]
        return item.id, item.parent_id, item.title, item.score

    def __len__(self):
        return len(self.answers.items)