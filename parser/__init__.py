"""
Job Description Parser
======================
Offline, deterministic JD → structured-JSON parser powered by Qwen 2.5 7B
running on a local Ollama daemon.

Quick start
-----------
>>> from parser import parse_job_description
>>> result = parse_job_description(open("jd.txt").read())
>>> result["job_title"]
'Senior Data Engineer'

For a long-lived application (e.g. Streamlit) instantiate once:

>>> from parser import JDParser
>>> parser = JDParser(model="qwen2.5:7b-instruct")
>>> result = parser.parse(jd_text)

Public surface
--------------
* :func:`parse_job_description`     — one-shot helper
* :class:`JDParser`                 — stateful pipeline (reuse the client)
* :class:`JobDescription`           — Pydantic schema for the parsed result
* :exc:`OllamaError`                — raised when the local Ollama is down
"""

from .jd_parser import JDParser, OllamaError, parse_job_description
from .models import Experience, JobDescription, Skills

__all__ = [
    "parse_job_description",
    "JDParser",
    "OllamaError",
    "JobDescription",
    "Experience",
    "Skills",
]

__version__ = "0.1.0"
