"""Common predefined alphabets."""

from ..core.alphabet import Alphabet

# Binary digits
BINARY = Alphabet("01")

# Decimal digits
DECIMAL = Alphabet("0123456789")

# Hexadecimal digits
HEXADECIMAL = Alphabet("0123456789ABCDEF")

# English letters
ENGLISH_LOWERCASE = Alphabet("abcdefghijklmnopqrstuvwxyz")
ENGLISH_UPPERCASE = Alphabet("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
ENGLISH_LETTERS = Alphabet("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")

# MIU puzzle alphabet
MIU = Alphabet("MIU")
