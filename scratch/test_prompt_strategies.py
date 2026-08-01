import os
import sys

# Add workspace path to python import lookup
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from backend.database.db import get_db, init_db
from backend.strategies.models import PromptStrategy, StrategyVersion
from backend.strategies.strategy_manager import StrategyManager

def run_tests():
    print("=== STARTING PEER PROMPT STRATEGY VERIFICATION ===")
    
    # Initialize DB
    init_db()
    
    # Initialize Manager
    manager = StrategyManager()

    # 1. Test Validator
    print("\n1. Testing strategy variables validator...")
    # Valid Instruction Config (0 examples)
    good_instruction = {
        "name": "test_instruction_only",
        "structure": "Instruction",
        "format": "Plain Text",
        "prompt_length": "Short",
        "instruction_style": "Simple",
        "reasoning_style": "None",
        "example_count": 0,
        "selection_strategy": "None",
        "ordering_strategy": "None",
        "output_constraints": ["label_only"]
    }
    val1 = manager.validate_strategy(good_instruction)
    assert val1["status"] == "PASS"

    # Invalid Instruction Config (3 examples) -> should FAIL
    bad_instruction = good_instruction.copy()
    bad_instruction["example_count"] = 3
    val2 = manager.validate_strategy(bad_instruction)
    assert val2["status"] == "FAIL"
    assert "cannot contain few-shot examples" in val2["errors"][0]
    
    # Invalid Mixed Config (0 examples) -> should FAIL
    bad_mixed = {
        "name": "test_bad_mixed",
        "structure": "Mixed",
        "format": "Markdown",
        "prompt_length": "Medium",
        "instruction_style": "Detailed",
        "reasoning_style": "None",
        "example_count": 0,
        "selection_strategy": "Random",
        "ordering_strategy": "Original",
        "output_constraints": []
    }
    val3 = manager.validate_strategy(bad_mixed)
    assert val3["status"] == "FAIL"
    assert "require at least 1 demonstration example" in val3["errors"][0]
    print("Strategy validation logic PASSED!")

    # 2. Test CRUD & library creation
    print("\n2. Testing strategy registry CRUD...")
    with get_db() as db:
        # Delete if exists from previous runs
        existing = db.query(PromptStrategy).filter(PromptStrategy.name == "test_mixed_strategy").first()
        if existing:
            manager.delete_strategy(db, existing.id)

        strategy = manager.create_strategy(
            db=db,
            name="test_mixed_strategy",
            structure="Mixed",
            format="Markdown",
            instruction_style="Detailed",
            reasoning_style="Chain-of-Thought",
            prompt_length="Medium",
            example_count=3,
            selection_strategy="Semantic",
            ordering_strategy="Similarity",
            output_constraints=["label_only", "no_explanation"],
            description="Testing mixed strategy creation"
        )
        print(f"Created Strategy ID: {strategy.id}")
        assert strategy.name == "test_mixed_strategy"
        assert strategy.version == "1"
        assert strategy.example_count == 3
        
        # Verify first version created
        ver = db.query(StrategyVersion).filter(StrategyVersion.strategy_id == strategy.id).first()
        assert ver is not None
        assert ver.version == "1"
        
        # Verify deserialization
        config_dict = manager.get_strategy_version_config(db, strategy.id, "1")
        assert config_dict["format"] == "Markdown"
        print("Strategy registry and version serialization PASSED!")

    # 3. Test Version Increment
    print("\n3. Testing strategy version control...")
    with get_db() as db:
        strat = db.query(PromptStrategy).filter(PromptStrategy.name == "test_mixed_strategy").first()
        next_ver = manager.get_next_version_name(strat.version)
        assert next_ver == "2"
        
        # Modify config (change count to 5)
        new_config = manager.get_strategy_version_config(db, strat.id, "1")
        new_config["example_count"] = 5
        
        ver_rec = manager.create_new_version(
            db=db,
            strategy_id=strat.id,
            version_name=next_ver,
            config_dict=new_config
        )
        
        # Check parent updated
        assert strat.version == "2"
        assert strat.example_count == 5
        print("Strategy version control lineage update PASSED!")

    # 4. Test Complexity Estimator
    print("\n4. Testing Complexity Estimator heuristics...")
    config_est = {
        "instruction_style": "Step-by-Step",  # 60
        "format": "JSON",                    # 30
        "reasoning_style": "Chain-of-Thought",# 25
        "example_count": 3,                  # 3 * 150 = 450
        "output_constraints": ["label_only", "no_explanation"] # 2 * 8 = 16
    }
    # Expected: 60 + 30 + 25 + 16 + 450 = 581 expected prompt tokens
    est = manager.estimate_complexity(config_est)
    print(f"Token Breakdown Metrics: {est}")
    assert est["expected_prompt_size"] == 581
    assert est["complexity_rating"] == "Medium"
    print("Complexity heuristics match analytical calculations!")

    # 5. Test Cloning
    print("\n5. Testing Cloning...")
    with get_db() as db:
        strat = db.query(PromptStrategy).filter(PromptStrategy.name == "test_mixed_strategy").first()
        cloned = manager.clone_strategy(db, strat.id, "test_mixed_strategy_cloned")
        assert cloned.name == "test_mixed_strategy_cloned"
        assert cloned.version == "1"
        assert cloned.example_count == 5  # cloned from latest version configuration
        print(f"Strategy cloned successfully as '{cloned.name}'!")

    # 6. Test Deletion
    print("\n6. Testing Deletion cascading...")
    with get_db() as db:
        strat = db.query(PromptStrategy).filter(PromptStrategy.name == "test_mixed_strategy").first()
        cloned = db.query(PromptStrategy).filter(PromptStrategy.name == "test_mixed_strategy_cloned").first()
        
        strat_id = strat.id
        clone_id = cloned.id
        
        manager.delete_strategy(db, strat_id)
        manager.delete_strategy(db, clone_id)
        
        # Assert deleted
        assert db.query(PromptStrategy).filter(PromptStrategy.id == strat_id).first() is None
        assert db.query(StrategyVersion).filter(StrategyVersion.strategy_id == strat_id).all() == []
        assert db.query(PromptStrategy).filter(PromptStrategy.id == clone_id).first() is None
        assert db.query(StrategyVersion).filter(StrategyVersion.strategy_id == clone_id).all() == []
        print("Deletion cascading cleaned up databases successfully!")

    print("\n=== ALL TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_tests()
