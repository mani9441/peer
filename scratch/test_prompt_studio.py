import os
import sys

# Add workspace path to python import lookup
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from backend.database.db import get_db, init_db
from backend.prompts.prompt_manager import PromptManager
from backend.prompts.models import PromptTemplate, PromptVersion, PromptTag

def run_tests():
    print("=== STARTING PEER PROMPT STUDIO VERIFICATION ===")
    
    # Initialize DB
    init_db()
    
    # Initialize Manager
    manager = PromptManager(export_dir="exports/test_exports")

    # 1. Test Validator
    print("\n1. Testing template validator compiler...")
    # Good Jinja
    good_template = "Classify sentiment.\nInput: {{input}}\nAnswer: {{label}}"
    good_val = manager.validate_prompt(good_template, "classification")
    assert good_val["status"] == "PASS"
    assert "input" in good_val["placeholders"]
    assert "label" in good_val["placeholders"]
    
    # Bad Jinja syntax
    bad_template = "Classify sentiment.\nInput: {{input"
    bad_val = manager.validate_prompt(bad_template, "classification")
    assert bad_val["status"] == "FAIL"
    assert len(bad_val["errors"]) > 0
    print("Jinja compiler syntax checks PASSED!")

    # 2. Test CRUD & library creation
    print("\n2. Testing prompt registration CRUD...")
    with get_db() as db:
        # Check clean slate
        # Delete if exists from previous runs
        existing = db.query(PromptTemplate).filter(PromptTemplate.name == "test_dummy_sentiment_prompt").first()
        if existing:
            manager.delete_prompt(db, existing.id)
            
        prompt = manager.create_prompt(
            db=db,
            name="test_dummy_sentiment_prompt",
            template_body=good_template,
            task_type="classification",
            strategy="Instruction",
            format="Plain Text",
            instruction_style="Simple",
            reasoning_style="None",
            description="Testing prompt creation",
            language="English",
            tags=["sentiment", "test"]
        )
        print(f"Created Prompt ID: {prompt.id}")
        assert prompt.name == "test_dummy_sentiment_prompt"
        assert prompt.current_version == "1"
        
        # Verify first version created
        ver = db.query(PromptVersion).filter(PromptVersion.prompt_id == prompt.id).first()
        assert ver is not None
        assert ver.version == "1"
        assert ver.template_body == good_template
        
        # Verify tags
        tags = db.query(PromptTag).filter(PromptTag.prompt_id == prompt.id).all()
        assert len(tags) == 2
        print("Template, Version 1, and Tags successfully written to DB!")

    # 3. Test Version Increment & Diffs
    print("\n3. Testing version management & diff visualizer...")
    with get_db() as db:
        p_template = db.query(PromptTemplate).filter(PromptTemplate.name == "test_dummy_sentiment_prompt").first()
        
        # Increment version: 1 -> 2
        next_ver = manager.get_next_version_name(p_template.current_version)
        assert next_ver == "2"
        
        # Create version 2 body
        v2_body = "Classify review sentiment.\nReview: {{input}}\nClass: {{label}}\nAdditional Instruction: Step-by-Step"
        v2_rec = manager.create_new_version(
            db=db,
            prompt_id=p_template.id,
            version_name=next_ver,
            template_body=v2_body,
            change_notes="Add detailed formatting constraints."
        )
        
        # Check parent updated
        assert p_template.current_version == "2"
        
        # Generate Diff
        diff_text = manager.get_diff(good_template, v2_body)
        print("Diff generated: \n" + diff_text)
        assert len(diff_text) > 0
        print("Version lineage and visual diff PASSED!")

    # 4. Test Rendering Preview
    print("\n4. Testing Jinja2 renderer...")
    placeholders = {"input": "Excellent codebase layout!", "label": "positive"}
    rendered = manager.render_prompt(v2_body, placeholders)
    print("Rendered Output: \n" + rendered)
    assert "Excellent codebase layout!" in rendered
    assert "positive" in rendered
    
    # Verify metrics
    metrics = manager.get_prompt_metrics(rendered)
    assert metrics["char_count"] > 0
    assert metrics["word_count"] > 0
    assert metrics["token_estimate"] > 0
    print("Placeholder rendering and metrics computation PASSED!")

    # 5. Test Exporter
    print("\n5. Testing Exporter...")
    with get_db() as db:
        p_template = db.query(PromptTemplate).filter(PromptTemplate.name == "test_dummy_sentiment_prompt").first()
        export_path = manager.export_prompt(
            db=db,
            prompt_id=p_template.id,
            version="2",
            filename="test_dummy_sentiment_prompt_v2",
            format="md"
        )
        assert os.path.exists(export_path)
        print(f"Template successfully exported to Markdown: {export_path}")

    # 6. Test Deletion
    print("\n6. Testing Deletion cascading...")
    with get_db() as db:
        p_template = db.query(PromptTemplate).filter(PromptTemplate.name == "test_dummy_sentiment_prompt").first()
        prompt_id = p_template.id
        manager.delete_prompt(db, prompt_id)
        
        # Check template deleted
        assert db.query(PromptTemplate).filter(PromptTemplate.id == prompt_id).first() is None
        # Check versions deleted
        assert db.query(PromptVersion).filter(PromptVersion.prompt_id == prompt_id).all() == []
        # Check tags deleted
        assert db.query(PromptTag).filter(PromptTag.prompt_id == prompt_id).all() == []
        print("Deletion cascading cleaned up template, versions, and tags from database!")

    # Cleanup test files
    print("\nCleaning up test files...")
    import shutil
    if os.path.exists("exports/test_exports"):
        shutil.rmtree("exports/test_exports")
        
    print("\n=== ALL TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_tests()
