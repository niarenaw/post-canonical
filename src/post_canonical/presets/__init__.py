"""Preset alphabets and example systems."""

from .alphabets import (
    BINARY,
    DECIMAL,
    HEXADECIMAL,
    ENGLISH_LOWERCASE,
    ENGLISH_UPPERCASE,
    ENGLISH_LETTERS,
    MIU,
)
from .examples import create_mu_puzzle, create_binary_doubler, create_palindrome_generator

__all__ = [
    # Alphabets
    "BINARY",
    "DECIMAL",
    "HEXADECIMAL",
    "ENGLISH_LOWERCASE",
    "ENGLISH_UPPERCASE",
    "ENGLISH_LETTERS",
    "MIU",
    # Example systems
    "create_mu_puzzle",
    "create_binary_doubler",
    "create_palindrome_generator",
]
