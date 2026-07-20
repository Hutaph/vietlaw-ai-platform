"""
Backward-compatible entry point.
Chay: python main.py HOAC uvicorn app.main:app --reload
File nay ton tai de giu kha nang chay bang `python main.py` nhu cu.
Logic thuc te nam trong package app/
"""
import uvicorn
from app.main import app  # noqa: F401 - import de uvicorn tim duoc


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
