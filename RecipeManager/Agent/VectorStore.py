"""
VectorStore
===========

Shared FAISS‑backed retrieval layer + four concrete stores:

    • IngredientDescriptionVS
    • MealDescriptionVS
    • MealInstructionsVS
    • UserSummaryVS
"""

from __future__ import annotations

import json
from typing import Iterable, List, NamedTuple, Tuple, Type

import faiss                   # pip install faiss-cpu
import numpy as np
from sqlalchemy.orm import Session

from RecipeManager.Agent.OpenAIConnector import OpenAIClient
from RecipeManager.Knowledge import models as db


class Result(NamedTuple):
    id: int
    score: float


class BaseVectorStore:
    """
    Load vectors from SQLAlchemy rows → FAISS index (cosine similarity).

    Sub‑classes must implement `_iter_rows()` yielding `(id, vector_json_str)`
    """

    def __init__(
        self,
        session: Session,
        openai_client: OpenAIClient,
        embedding_model: str = "text-embedding-3-small",
    ) -> None:
        self.session = session
        self.openai_client = openai_client
        self.embedding_model = embedding_model
        self._index: faiss.Index = None          # lazy
        self._ids: list[int] = []
        self.refresh()

    # ------------------------------------------------------------------ loading
    def _iter_rows(self) -> Iterable[Tuple[int, str]]:
        """Override in subclasses."""
        raise NotImplementedError

    def refresh(self) -> None:
        vectors: list[list[float]] = []
        ids: list[int] = []

        for _id, vec_json in self._iter_rows():
            try:
                vec = json.loads(vec_json)
            except Exception:
                continue
            if not vec:
                continue
            ids.append(_id)
            vectors.append(vec)

        if not vectors:
            self._index = None
            self._ids = []
            return

        arr = np.asarray(vectors, dtype="float32")
        # L2‑normalise for cosine ⇒ inner‑product = cosine
        faiss.normalize_L2(arr)
        dim = arr.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(arr)

        self._index = index
        self._ids = ids
        print(f"[VectorStore] built index: {len(ids)} vectors, dim={dim}")

    # ---------------------------------------------------------------- retrieve
    def retrieve(self, query: str, k: int = 5, normalize: bool = True) -> List[Result]:
        """
        Embed `query` with OpenAI, search FAISS, return top‑k ids & scores.
        """
        if self._index is None:
            return []

        qvec = self.openai_client.get_embedding(query, model=self.embedding_model)
        qvec = np.asarray(qvec, dtype="float32").reshape(1, -1)
        if normalize:
            faiss.normalize_L2(qvec)

        scores, idxs = self._index.search(qvec, k)
        return [
            Result(id=self._ids[int(i)], score=float(scores[0][rank]))
            for rank, i in enumerate(idxs[0])
            if i != -1
        ]


# -----------------------------------------------------------------
# Concrete stores
# -----------------------------------------------------------------
class IngredientDescriptionVS(BaseVectorStore):
    def _iter_rows(self):
        q = (
            self.session.query(db.Ingredient.id, db.Ingredient.description_vector)
            .filter(db.Ingredient.description_vector.isnot(None))
        )
        yield from q.all()


class MealDescriptionVS(BaseVectorStore):
    def _iter_rows(self):
        q = (
            self.session.query(db.Meal.id, db.Meal.description_vector)
            .filter(db.Meal.description_vector.isnot(None))
        )
        yield from q.all()


class MealInstructionsVS(BaseVectorStore):
    def _iter_rows(self):
        q = (
            self.session.query(db.Meal.id, db.Meal.instructions_vector)
            .filter(db.Meal.instructions_vector.isnot(None))
        )
        yield from q.all()


class UserSummaryVS(BaseVectorStore):
    def _iter_rows(self):
        q = (
            self.session.query(db.Customer.id, db.Customer.summary_vector)
            .filter(db.Customer.summary_vector.isnot(None))
        )
        yield from q.all()
