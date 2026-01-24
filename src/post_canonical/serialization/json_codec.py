"""JSON serialization for Post Canonical Systems."""

import json
from typing import Any

from ..core.alphabet import Alphabet
from ..core.pattern import Pattern
from ..core.rule import ProductionRule
from ..core.variable import Variable, VariableKind
from ..system.pcs import PostCanonicalSystem


class PCSJsonCodec:
    """JSON serialization for Post Canonical Systems.

    Supports round-trip serialization: encode a system to JSON,
    then decode it back to an identical system.

    JSON format:
    {
        "version": "1.0",
        "alphabet": ["M", "I", "U"],
        "variables": [
            {"name": "x", "kind": "ANY"},
            {"name": "y", "kind": "NON_EMPTY"}
        ],
        "axioms": ["MI"],
        "rules": [
            {
                "name": "rule1",
                "priority": 1,
                "antecedents": ["$xI"],
                "consequent": "$xIU"
            }
        ]
    }
    """

    VERSION = "1.0"

    def encode(self, system: PostCanonicalSystem, indent: int = 2) -> str:
        """Serialize PCS to JSON string.

        Args:
            system: The Post Canonical System to serialize
            indent: JSON indentation level (default 2)

        Returns:
            JSON string representation
        """
        data = self._system_to_dict(system)
        return json.dumps(data, indent=indent, sort_keys=True)

    def decode(self, json_str: str) -> PostCanonicalSystem:
        """Deserialize PCS from JSON string.

        Args:
            json_str: JSON representation of a PCS

        Returns:
            Reconstructed PostCanonicalSystem
        """
        data = json.loads(json_str)
        return self._dict_to_system(data)

    def save(self, system: PostCanonicalSystem, path: str) -> None:
        """Save PCS to a JSON file.

        Args:
            system: The system to save
            path: File path to write to
        """
        with open(path, "w") as f:
            f.write(self.encode(system))

    def load(self, path: str) -> PostCanonicalSystem:
        """Load PCS from a JSON file.

        Args:
            path: File path to read from

        Returns:
            Loaded PostCanonicalSystem
        """
        with open(path) as f:
            return self.decode(f.read())

    def _system_to_dict(self, system: PostCanonicalSystem) -> dict[str, Any]:
        """Convert system to dictionary structure."""
        return {
            "version": self.VERSION,
            "alphabet": list(sorted(system.alphabet.symbols)),
            "variables": [
                {
                    "name": v.name,
                    "kind": v.kind.name,
                }
                for v in sorted(system.variables, key=lambda v: v.name)
            ],
            "axioms": list(sorted(system.axioms)),
            "rules": [self._rule_to_dict(r) for r in sorted(system.rules, key=lambda r: (-r.priority, r.name or ""))],
        }

    def _rule_to_dict(self, rule: ProductionRule) -> dict[str, Any]:
        """Convert a rule to dictionary structure."""
        return {
            "name": rule.name,
            "priority": rule.priority,
            "antecedents": [str(p) for p in rule.antecedents],
            "consequent": str(rule.consequent),
        }

    def _dict_to_system(self, data: dict[str, Any]) -> PostCanonicalSystem:
        """Convert dictionary structure to system."""
        # Check version compatibility
        version = data.get("version", "1.0")
        if version != self.VERSION:
            raise ValueError(f"Unsupported version: {version}")

        # Parse variables first (needed for patterns)
        variables: dict[str, Variable] = {}
        for v_data in data["variables"]:
            kind = VariableKind[v_data["kind"]]
            var = Variable(v_data["name"], kind)
            variables[var.name] = var

        # Parse rules
        rules: list[ProductionRule] = []
        for r_data in data["rules"]:
            antecedents = [Pattern.parse(s, variables) for s in r_data["antecedents"]]
            consequent = Pattern.parse(r_data["consequent"], variables)
            rule = ProductionRule(
                antecedents=antecedents,
                consequent=consequent,
                priority=r_data.get("priority", 0),
                name=r_data.get("name"),
            )
            rules.append(rule)

        return PostCanonicalSystem(
            alphabet=Alphabet(data["alphabet"]),
            axioms=frozenset(data["axioms"]),
            rules=frozenset(rules),
            variables=frozenset(variables.values()),
        )
