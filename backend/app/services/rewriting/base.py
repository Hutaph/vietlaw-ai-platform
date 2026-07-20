from abc import ABC, abstractmethod
from typing import List, Tuple
from pydantic import BaseModel, Field

class RewriteResult(BaseModel):
    domain: str = Field(description="Domain of the query, either 'legal' or 'chitchat'")
    queries: List[str] = Field(description="List of search queries. Empty if domain is chitchat.")

class BaseRewriter(ABC):
    """
    Abstract base class for Query Rewriters.
    """
    @abstractmethod
    def rewrite(self, query: str, history: str = None, runtime_config=None) -> Tuple[str, List[str]]:
        """
        Rewrite the query and return the domain and a list of queries.
        
        Args:
            query (str): The original user query.
            history (str, optional): Recent conversation history for context resolution.
            
        Returns:
            Tuple[str, List[str]]: A tuple containing the domain ("legal" or "chitchat") and a list of rewritten queries.
        """
        pass
