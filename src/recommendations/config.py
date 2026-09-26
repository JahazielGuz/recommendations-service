import os

from dotenv import load_dotenv

load_dotenv()

def require(name: str) -> str:
  """The value of an environment variable, or a written error naming the one that is missing."""
  value = os.environ.get(name)

  if not value:
    raise RuntimeError(f"{name} is not set")
  
  return value
