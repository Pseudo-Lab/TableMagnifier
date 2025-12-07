"""Agentic flow for generating synthetic tables from images."""

from .flow import build_synthetic_table_graph, run_synthetic_table_flow
from .runner import build_arg_parser, run_flow_for_image, run_with_args

__all__ = [
    "build_synthetic_table_graph",
    "run_synthetic_table_flow",
    "build_arg_parser",
    "run_flow_for_image",
    "run_with_args",
]
