"""Tests for training dataset generation."""

import json
import os
import tempfile

import pytest

from tf_avm_agent.lightning.dataset import TerraformTrainingDataset, TrainingExample


class TestTrainingExample:
    """Tests for TrainingExample dataclass."""

    def test_creation(self):
        example = TrainingExample(
            task_id="test_0",
            input_prompt="Create a VM",
            expected_services=["virtual_machine"],
            expected_modules=["virtual_machine"],
        )
        assert example.task_id == "test_0"
        assert example.ground_truth_code is None
        assert example.metadata is None


class TestTrainingDataset:
    """Tests for TerraformTrainingDataset."""

    @pytest.fixture
    def dataset(self):
        return TerraformTrainingDataset()

    def test_has_architecture_patterns(self, dataset):
        """Dataset should have predefined architecture patterns."""
        assert len(dataset.ARCHITECTURE_PATTERNS) >= 4

    def test_generate_examples(self, dataset):
        """Should generate examples from architecture patterns."""
        examples = list(dataset.generate_examples())
        assert len(examples) > 0
        assert all(isinstance(e, TrainingExample) for e in examples)

    def test_example_has_required_fields(self, dataset):
        """Each example should have all required fields."""
        examples = list(dataset.generate_examples())
        for example in examples:
            assert example.task_id
            assert example.input_prompt
            assert isinstance(example.expected_services, list)
            assert isinstance(example.expected_modules, list)

    def test_generate_module_lookup_examples(self, dataset):
        """Should generate lookup examples from AVM_MODULES."""
        examples = list(dataset.generate_module_lookup_examples())
        assert len(examples) > 0

    def test_lookup_example_has_module(self, dataset):
        """Lookup examples should reference a module."""
        examples = list(dataset.generate_module_lookup_examples())
        for example in examples:
            assert len(example.expected_modules) == 1
            assert example.metadata is not None
            assert "module" in example.metadata

    def test_save_to_jsonl(self, dataset):
        """Should save dataset to JSONL file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f:
            path = f.name

        try:
            count = dataset.save_to_jsonl(path)
            assert count > 0

            with open(path) as f:
                lines = f.readlines()

            assert len(lines) == count

            # Verify JSONL format
            first = json.loads(lines[0])
            assert "task_id" in first
            assert "input" in first
            assert "expected_services" in first
            assert "expected_modules" in first
        finally:
            os.unlink(path)

    def test_save_creates_parent_dirs(self, dataset):
        """save_to_jsonl should create parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "subdir", "data.jsonl")
            count = dataset.save_to_jsonl(path)
            assert count > 0
            assert os.path.exists(path)
