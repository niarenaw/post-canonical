# Post Canonical Systems

A Python implementation of Post Canonical Systems, a formal system for string manipulation and computation.

## Requirements

- Python 3.12 or higher
- uv (for package management)

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/post-canonical.git
cd post-canonical

# Create and activate a virtual environment using uv
uv venv
source .venv/bin/activate  # On Unix/macOS

# Install the package in development mode
uv sync
```

## Usage

The package provides a simple way to create and work with Post Canonical Systems. Here's a basic example:

```python
from post_canonical_system import PostCanonicalSystem, ProductionRule
from alphabet import Alphabet

# Create a simple system that generates binary numbers
binary_alphabet = Alphabet('01')
initial_words = {'0', '1'}
rules = {
    ProductionRule(('x',), 'x0'),  # Append 0
    ProductionRule(('x',), 'x1'),  # Append 1
}

# Create the system
binary_system = PostCanonicalSystem(binary_alphabet, initial_words, rules)

# Generate words
words = binary_system.generate_words(max_steps=3)
print(sorted(words))
```

### MU Puzzle Example

The package includes an implementation of the famous MU puzzle:

```python
from post_canonical_system import create_mu_puzzle

# Create the MU puzzle system
mu_system = create_mu_puzzle()

# Generate words
words = mu_system.generate_words(max_steps=5)
print(sorted(words))
```