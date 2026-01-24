"""Preset alphabets and example systems."""

from .alphabets import (
    BINARY,
    DECIMAL,
    ENGLISH_LETTERS,
    ENGLISH_LOWERCASE,
    ENGLISH_UPPERCASE,
    HEXADECIMAL,
    MIU,
)
from .examples import create_binary_doubler, create_mu_puzzle, create_palindrome_generator

__all__ = [
    # Alphabets
    "BINARY",
    "DECIMAL",
    "ENGLISH_LETTERS",
    "ENGLISH_LOWERCASE",
    "ENGLISH_UPPERCASE",
    "HEXADECIMAL",
    "MIU",
    "create_binary_doubler",
    # Example systems
    "create_mu_puzzle",
    "create_palindrome_generator",
]
