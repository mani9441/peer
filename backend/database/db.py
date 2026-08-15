import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from contextlib import contextmanager

# Ensure config directory exists
os.makedirs("config", exist_ok=True)
os.makedirs("datasets", exist_ok=True)
os.makedirs("exports", exist_ok=True)

DATABASE_URL = "sqlite:///config/peer.db"

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def self_heal_dataset_labels():
    from backend.datasets.models import Dataset, DatasetLabel
    db = SessionLocal()
    try:
        # Fetch all classification datasets
        datasets = db.query(Dataset).filter(Dataset.task == "classification").all()
        for d in datasets:
            db_labels = db.query(DatasetLabel).filter(DatasetLabel.dataset_id == d.id).all()
            
            # Check if labels are missing OR if existing labels are dummy self-mappings like 0='0', 1='1'
            is_dummy = False
            if db_labels:
                is_dummy = all(str(lbl.label_id).strip() == str(lbl.label_name).strip() for lbl in db_labels)
                
            if not db_labels or is_dummy:
                if db_labels:
                    db.query(DatasetLabel).filter(DatasetLabel.dataset_id == d.id).delete()
                    db.flush()

                label_mapping = {}
                d_name_lower = d.name.lower()
                if "emotion" in d_name_lower:
                    label_mapping = {
                        0: "sadness",
                        1: "joy",
                        2: "love",
                        3: "anger",
                        4: "fear",
                        5: "surprise"
                    }
                elif "sst" in d_name_lower or "rotten" in d_name_lower:
                    label_mapping = {
                        0: "negative",
                        1: "positive"
                    }
                elif "ag_news" in d_name_lower or "agnews" in d_name_lower:
                    label_mapping = {
                        0: "World",
                        1: "Sports",
                        2: "Business",
                        3: "Sci/Tech"
                    }
                elif "dbpedia" in d_name_lower:
                    label_mapping = {
                        0: "Company",
                        1: "EducationalInstitution",
                        2: "Artist",
                        3: "Athlete",
                        4: "OfficeHolder",
                        5: "MeanOfTransportation",
                        6: "Building",
                        7: "NaturalPlace",
                        8: "Village",
                        9: "Animal",
                        10: "Plant",
                        11: "Album",
                        12: "Film",
                        13: "WrittenWork"
                    }
                else:
                    try:
                        from backend.datasets.dataset_manager import DatasetManager
                        mgr = DatasetManager()
                        df_dict = mgr.get_dataset_version_data(db, d.id, d.version)
                        pref_split = "train" if "train" in df_dict else list(df_dict.keys())[0]
                        df = df_dict[pref_split]
                        from backend.datasets.dataset_validator import DatasetValidator
                        val_report = DatasetValidator.detect_and_normalize_columns(df, "classification")
                        mapping = val_report.get("column_mapping", {})
                        label_col = mapping.get("label")
                        if label_col and label_col in df.columns:
                            unique_labels = df[label_col].dropna().unique().tolist()
                            try:
                                numeric_vals = sorted([int(val) for val in unique_labels])
                                label_mapping = {val: f"Class {val}" for val in numeric_vals}
                            except ValueError:
                                string_vals = sorted([str(val).strip() for val in unique_labels])
                                label_mapping = {i: val for i, val in enumerate(string_vals)}
                    except Exception as e:
                        print(f"Failed to auto-heal generic label mapping for {d.id}: {e}")
                
                if label_mapping:
                    print(f"Self-healing label mappings for dataset '{d.id}': {label_mapping}")
                    for lbl_id, lbl_name in label_mapping.items():
                        db_lbl = DatasetLabel(
                            dataset_id=d.id,
                            label_id=int(lbl_id),
                            label_name=str(lbl_name)
                        )
                        db.add(db_lbl)
                    db.commit()
    except Exception as err:
        print(f"Error during self-healing: {err}")
        db.rollback()
    finally:
        db.close()

def self_heal_response_columns():
    db = SessionLocal()
    try:
        from sqlalchemy import inspect
        inspector = inspect(engine)
        columns = [col["name"] for col in inspector.get_columns("responses")]
        new_cols = {
            "status": "VARCHAR",
            "error_type": "VARCHAR",
            "error_message": "TEXT",
            "can_retry": "BOOLEAN",
            "provider": "VARCHAR",
            "model": "VARCHAR"
        }
        for col_name, col_type in new_cols.items():
            if col_name not in columns:
                print(f"Self-healing: Adding column '{col_name}' to 'responses' table...")
                # Use raw SQL connection to perform execute
                db.execute(text(f"ALTER TABLE responses ADD COLUMN {col_name} {col_type}"))
        db.commit()
    except Exception as err:
        print(f"Error during responses columns self-healing: {err}")
        db.rollback()
    finally:
        db.close()

def init_db():
    # Import models so they are registered with the declarative Base
    import backend.datasets.models
    import backend.prompts.models
    import backend.strategies.models
    import backend.fewshot.models
    import backend.providers.models
    import backend.experiments.models
    Base.metadata.create_all(bind=engine)
    self_heal_dataset_labels()
    self_heal_response_columns()
