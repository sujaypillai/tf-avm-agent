"""Training script for Agent Lightning integration."""

import argparse
import json
import sys
from pathlib import Path

from tf_avm_agent.lightning import LIGHTNING_AVAILABLE


def create_training_config(
    model_name: str = "gpt-4",
    batch_size: int = 32,
    epochs: int = 3,
    learning_rate: float = 1e-5,
) -> dict:
    """Create training configuration.

    Returns a dict when agentlightning is not available,
    or a TrainingConfig object when it is.
    """
    config = {
        "algorithm": "grpo",
        "model_name": model_name,
        "batch_size": batch_size,
        "epochs": epochs,
        "learning_rate": learning_rate,
        "reward_normalization": True,
        "discount_factor": 0.99,
        "clip_ratio": 0.2,
        "max_trajectory_length": 10,
        "trajectory_level_aggregation": True,
        "checkpoint_interval": 100,
        "checkpoint_dir": "./checkpoints",
    }

    if LIGHTNING_AVAILABLE:
        from agentlightning import TrainingConfig  # type: ignore[import-untyped]

        return TrainingConfig(**config)

    return config


def run_training(
    dataset_path: str,
    output_dir: str,
    config: dict,
) -> dict:
    """Run the training loop.

    Args:
        dataset_path: Path to JSONL training dataset.
        output_dir: Directory to save trained model.
        config: Training configuration.

    Returns:
        Training metrics dictionary.
    """
    if not LIGHTNING_AVAILABLE:
        raise RuntimeError(
            "agentlightning package is not installed. "
            "Install with: pip install tf-avm-agent[lightning]"
        )

    from agentlightning import Trainer  # type: ignore[import-untyped]

    from tf_avm_agent.lightning.config import get_lightning_store
    from tf_avm_agent.lightning.rewards import TerraformRewardCalculator

    store = get_lightning_store()
    reward_calculator = TerraformRewardCalculator()

    # Load dataset
    examples = []
    with open(dataset_path, "r") as f:
        for line in f:
            examples.append(json.loads(line))

    print(f"Loaded {len(examples)} training examples")

    # Create trainer
    trainer = Trainer(
        config=config,
        store=store,
        reward_fn=lambda output: reward_calculator.calculate_reward(
            output
        ).total_reward,
    )

    # Training loop
    metrics = trainer.train(
        examples=examples,
        validation_split=0.1,
    )

    # Save final model
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    trainer.save(output_dir)

    return metrics


def main() -> None:
    """Main entry point for training."""
    if not LIGHTNING_AVAILABLE:
        print("Error: agentlightning package is not installed.")
        print("Install with: pip install tf-avm-agent[lightning]")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Train TF-AVM-Agent with Agent Lightning"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="./data/training.jsonl",
        help="Path to training dataset",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./models/tf-avm-agent-rl",
        help="Output directory for trained model",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4",
        help="Base model to fine-tune",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=3,
        help="Number of training epochs",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Training batch size",
    )
    parser.add_argument(
        "--generate-dataset",
        action="store_true",
        help="Generate training dataset before training",
    )

    args = parser.parse_args()

    # Generate dataset if requested
    if args.generate_dataset:
        from tf_avm_agent.lightning.dataset import TerraformTrainingDataset

        print("Generating training dataset...")
        dataset = TerraformTrainingDataset()
        count = dataset.save_to_jsonl(args.dataset)
        print(f"Generated {count} examples to {args.dataset}")

    # Create training config
    config = create_training_config(
        model_name=args.model,
        batch_size=args.batch_size,
        epochs=args.epochs,
    )

    # Run training
    print(f"Starting training with {args.model}...")
    metrics = run_training(args.dataset, args.output, config)

    print("Training complete!")
    print(f"Final metrics: {metrics}")


if __name__ == "__main__":
    main()
