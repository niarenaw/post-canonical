"""Tests for derivation tracking classes."""

import pytest

from post_canonical import Pattern, ProductionRule, Variable
from post_canonical.matching.binding import Binding
from post_canonical.system.derivation import Derivation, DerivationStep, DerivedWord


class TestDerivationStep:
    """Tests for DerivationStep class."""

    def test_create_step(self) -> None:
        """DerivationStep can be created with all fields."""
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x, "I"])], Pattern([x, "I", "U"]), name="add_U")
        binding = Binding({"x": "M"})

        step = DerivationStep(
            inputs=("MI",),
            rule=rule,
            binding=binding,
            output="MIU",
        )

        assert step.inputs == ("MI",)
        assert step.rule == rule
        assert step.binding == binding
        assert step.output == "MIU"

    def test_step_multiple_inputs(self) -> None:
        """DerivationStep can have multiple inputs."""
        x = Variable.any("x")
        y = Variable.any("y")
        rule = ProductionRule(
            [Pattern([x]), Pattern([y])],
            Pattern([x, y]),
            name="concat",
        )
        binding = Binding({"x": "0", "y": "1"})

        step = DerivationStep(
            inputs=("0", "1"),
            rule=rule,
            binding=binding,
            output="01",
        )

        assert len(step.inputs) == 2
        assert step.inputs[0] == "0"
        assert step.inputs[1] == "1"

    def test_step_str(self) -> None:
        """String representation of step."""
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern([x, x]), name="double")
        binding = Binding({"x": "0"})

        step = DerivationStep(
            inputs=("0",),
            rule=rule,
            binding=binding,
            output="00",
        )

        s = str(step)
        assert "'0'" in s
        assert "double" in s
        assert "'00'" in s

    def test_step_repr(self) -> None:
        """Repr of step."""
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern([x]))
        step = DerivationStep(
            inputs=("A",),
            rule=rule,
            binding=Binding.empty(),
            output="A",
        )
        assert "DerivationStep" in repr(step)

    def test_step_immutability(self) -> None:
        """DerivationStep is immutable."""
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern([x]))
        step = DerivationStep(
            inputs=("A",),
            rule=rule,
            binding=Binding.empty(),
            output="A",
        )
        with pytest.raises(AttributeError):
            step.output = "B"  # type: ignore


class TestDerivation:
    """Tests for Derivation class."""

    def test_create_empty_derivation(self) -> None:
        """Empty derivation (for axioms) can be created."""
        deriv = Derivation()
        assert len(deriv.steps) == 0
        assert deriv.is_axiom is True

    def test_create_from_steps(self) -> None:
        """Derivation can be created from steps."""
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern([x, x]), name="double")
        step = DerivationStep(
            inputs=("0",),
            rule=rule,
            binding=Binding({"x": "0"}),
            output="00",
        )

        deriv = Derivation([step])
        assert deriv.length == 1
        assert deriv.is_axiom is False

    def test_final_word_property(self) -> None:
        """final_word returns output of last step."""
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern([x, x]), name="double")

        step1 = DerivationStep(
            inputs=("0",),
            rule=rule,
            binding=Binding({"x": "0"}),
            output="00",
        )
        step2 = DerivationStep(
            inputs=("00",),
            rule=rule,
            binding=Binding({"x": "00"}),
            output="0000",
        )

        deriv = Derivation([step1, step2])
        assert deriv.final_word == "0000"

    def test_final_word_empty_derivation(self) -> None:
        """final_word is None for empty derivation."""
        deriv = Derivation()
        assert deriv.final_word is None

    def test_extend_derivation(self) -> None:
        """extend() adds a new step."""
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern([x, x]), name="double")

        step1 = DerivationStep(
            inputs=("0",),
            rule=rule,
            binding=Binding({"x": "0"}),
            output="00",
        )
        deriv1 = Derivation([step1])

        step2 = DerivationStep(
            inputs=("00",),
            rule=rule,
            binding=Binding({"x": "00"}),
            output="0000",
        )
        deriv2 = deriv1.extend(step2)

        assert deriv1.length == 1  # Original unchanged
        assert deriv2.length == 2
        assert deriv2.final_word == "0000"

    def test_rules_used(self) -> None:
        """rules_used returns list of rule names."""
        x = Variable.any("x")
        rule1 = ProductionRule([Pattern([x])], Pattern([x, x]), name="double")
        rule2 = ProductionRule([Pattern([x])], Pattern(["0", x]), name="prepend")

        step1 = DerivationStep(
            inputs=("1",),
            rule=rule1,
            binding=Binding({"x": "1"}),
            output="11",
        )
        step2 = DerivationStep(
            inputs=("11",),
            rule=rule2,
            binding=Binding({"x": "11"}),
            output="011",
        )

        deriv = Derivation([step1, step2])
        rules = deriv.rules_used()

        assert rules == ["double", "prepend"]

    def test_str_empty_derivation(self) -> None:
        """String representation of empty derivation."""
        deriv = Derivation()
        assert "axiom" in str(deriv).lower()

    def test_str_with_steps(self) -> None:
        """String representation with steps."""
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern([x, x]), name="double")
        step = DerivationStep(
            inputs=("0",),
            rule=rule,
            binding=Binding({"x": "0"}),
            output="00",
        )

        deriv = Derivation([step])
        s = str(deriv)
        assert "=>" in s or "->" in s

    def test_to_trace(self) -> None:
        """to_trace provides detailed multi-line output."""
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern([x, x]), name="double")
        step = DerivationStep(
            inputs=("0",),
            rule=rule,
            binding=Binding({"x": "0"}),
            output="00",
        )

        deriv = Derivation([step])
        trace = deriv.to_trace()

        assert "double" in trace
        assert "00" in trace
        assert "bindings" in trace.lower()

    def test_to_trace_empty(self) -> None:
        """to_trace for empty derivation."""
        deriv = Derivation()
        trace = deriv.to_trace()
        assert "axiom" in trace.lower()


class TestDerivedWord:
    """Tests for DerivedWord class."""

    def test_create_axiom(self) -> None:
        """DerivedWord.axiom creates an axiom."""
        dw = DerivedWord.axiom("MI")
        assert dw.word == "MI"
        assert dw.is_axiom is True
        assert dw.derivation.is_axiom is True

    def test_create_with_derivation(self) -> None:
        """DerivedWord can be created with derivation."""
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern([x, x]), name="double")
        step = DerivationStep(
            inputs=("0",),
            rule=rule,
            binding=Binding({"x": "0"}),
            output="00",
        )
        deriv = Derivation([step])

        dw = DerivedWord(word="00", derivation=deriv)
        assert dw.word == "00"
        assert dw.is_axiom is False

    def test_str(self) -> None:
        """String representation of DerivedWord."""
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern([x, x]))
        step = DerivationStep(
            inputs=("0",),
            rule=rule,
            binding=Binding({"x": "0"}),
            output="00",
        )
        deriv = Derivation([step])

        dw = DerivedWord(word="00", derivation=deriv)
        s = str(dw)

        assert "00" in s
        assert "step" in s.lower()

    def test_repr(self) -> None:
        """Repr of DerivedWord."""
        dw = DerivedWord.axiom("X")
        assert "DerivedWord" in repr(dw)

    def test_trace(self) -> None:
        """trace() provides full derivation trace."""
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern([x, x]), name="double")
        step = DerivationStep(
            inputs=("0",),
            rule=rule,
            binding=Binding({"x": "0"}),
            output="00",
        )
        deriv = Derivation([step])

        dw = DerivedWord(word="00", derivation=deriv)
        trace = dw.trace()

        assert "Word: '00'" in trace
        assert "double" in trace

    def test_trace_axiom(self) -> None:
        """trace() for axiom shows axiom status."""
        dw = DerivedWord.axiom("MI")
        trace = dw.trace()

        assert "MI" in trace
        assert "axiom" in trace.lower()

    def test_derived_word_immutability(self) -> None:
        """DerivedWord is immutable."""
        dw = DerivedWord.axiom("X")
        with pytest.raises(AttributeError):
            dw.word = "Y"  # type: ignore


class TestDerivationEdgeCases:
    """Edge case tests for derivation classes."""

    def test_long_derivation(self) -> None:
        """Long derivation chains work correctly."""
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern([x, x]), name="double")

        steps = []
        word = "0"
        for _ in range(10):
            step = DerivationStep(
                inputs=(word,),
                rule=rule,
                binding=Binding({"x": word}),
                output=word + word,
            )
            steps.append(step)
            word = word + word

        deriv = Derivation(steps)
        assert deriv.length == 10
        assert deriv.final_word == "0" * 1024  # 2^10

    def test_empty_word_axiom(self) -> None:
        """Empty string can be an axiom."""
        dw = DerivedWord.axiom("")
        assert dw.word == ""
        assert dw.is_axiom is True

    def test_derivation_with_unnamed_rule(self) -> None:
        """Derivation works with unnamed rules."""
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern([x, x]))  # No name
        step = DerivationStep(
            inputs=("0",),
            rule=rule,
            binding=Binding({"x": "0"}),
            output="00",
        )

        deriv = Derivation([step])
        rules = deriv.rules_used()

        # Should use fallback name
        assert len(rules) == 1
        assert "rule" in rules[0].lower()
