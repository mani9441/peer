# PEER Studio: Prompt Engineering Evaluation & Research Workbench

PEER Studio is a scientific workbench and Python framework tailored for prompt engineers and researchers to run rigorous, empirical evaluations. PEER (Prompt Engineering Evaluation & Research) enables users to design prompt variations as experimental parameters, execute them across various language models in the background, and systematically evaluate outputs against standardized ground-truth benchmarks.

---

## 🚀 Key Features

*   **Multi-Provider & Model Catalog**: Out-of-the-box integration with Google Gemini (via the `google-genai` SDK), OpenAI, OpenRouter, and local Ollama instances. Features live connection health checks and automatic catalog syncing.
*   **Empirical Experiments Engine**: Executes multi-run evaluations sequentially in background daemon threads, preventing UI lockups. Supports configuration of parameters like temperature, top-p, random seeds, and max sample limits.
*   **Prompt Templating & Versioning**: Complete Jinja2 templating environment with variable extraction, tag associations, and full version history tracking.
*   **Prompt Strategy Configurations**: Fine-grained prompt configuration including system prompt placement, format constraints (Plain Text, JSON, XML, etc.), reasoning style (e.g., Chain-of-Thought), and few-shot details.
*   **Few-Shot Demonstration Engineering**: Selection of demonstrations from dataset training splits using Random Sampling, Semantic Similarity (via FAISS vector indexes and Sentence-Transformers embeddings), and Diversity Filtering.
*   **Dataset Management & Validation**: Supports `classification` and `qa` (Question Answering) tasks. Features automated column mapping detection, dataset version splits stored in Parquet format, label mapping validation, and dataset imbalance stats calculation.
*   **Interactive Analytics & Visual Comparison**: Side-by-side run comparisons with metrics (accuracy, F1, exact match, average latency, token counts, and estimated cost tracking) mapped through Plotly-based analytics charts.

---

## 📁 Repository Structure

```text
PEER/
├── app.py                     # Streamlit application entry point & page navigation router
├── requirements.txt           # Python dependency specifications
├── assets/                    # Static image assets and favicons
├── config/                    # Default folder for SQLite storage (peer.db)
├── datasets/                  # Local storage folder for Parquet splits and vector indexes
│   ├── versions/              # Saved Parquet files of registered dataset versions
│   └── cache/                 # Temporary workspace caches
├── exports/                   # Excel/CSV export targets for runs and configurations
├── backend/                   # Core Python backend package
│   ├── database/              # SQLite configurations and table initialization (db.py)
│   ├── datasets/              # Dataset models, loader, sampler, stats, and validators
│   ├── prompts/               # Prompt version control, renderer, and library manager
│   ├── strategies/            # Optimization strategies and parameter schemas
│   ├── fewshot/               # FAISS vector retriever, embeddings, and diversity filter
│   ├── providers/             # Inference service APIs, retry logic, tokenizers, and pricing
│   └── experiments/           # Background execution pipeline, metrics, and evaluator
├── peer_studio/               # Streamlit pages and dashboard views
│   ├── landing.py             # App welcome screen
│   ├── home.py                # Main Dashboard & Guided Experiment Journey
│   ├── utils/                 # Custom UI styles and header render components
│   └── pages/
│       ├── experiments/       # Create, monitor running, and browse completed experiments
│       ├── results/           # View run details, compare configurations, and view analytics
│       ├── resources/         # Datasets registry, prompt templates, and model catalog
│       └── settings.py        # System health metrics and database utilities
└── tests/                     # Unit test suites
    ├── test_experiments.py    # Pipeline execution tests
    ├── test_labels.py         # Numeric label mapping and parser tests
    └── test_providers.py      # Provider API and mock network tests
```

---

## 🛠️ Installation & Setup

### 1. Prerequisites
Ensure you have **Python 3.9+** and `pip` installed.

### 2. Install Dependencies
Clone the repository and install the required dependencies:
```bash
pip install -r requirements.txt
```

### 3. Configure API Credentials
Configure the API keys for the providers you intend to use. You can export them in your active shell or place them inside a `.env` file in the project's root directory:
```bash
export GEMINI_API_KEY="your-gemini-api-key"
export OPENAI_API_KEY="your-openai-api-key"
export OPENROUTER_API_KEY="your-openrouter-api-key"
```
*Note: For local model execution via Ollama, make sure you have the Ollama server running locally (`ollama serve`).*

---

## 💻 Running the Application

Launch the Streamlit interface using:
```bash
streamlit run app.py
```
Upon opening, the application will initialize a local SQLite database at `config/peer.db` and seed default provider configurations automatically.

---

## 🧪 Running the Test Suite

Run the unit tests to verify database migrations, mock provider connections, and run evaluation pipelines:
```bash
python3 -m unittest discover tests
```
*(Or install `pytest` and execute `pytest tests/`)*

---

## 📖 Guided Workflow Guide

1.  **Register a Dataset**: Navigate to **Resources > Datasets** to upload a CSV/JSON file or import a dataset from Hugging Face. The system will auto-detect columns, separate train/test splits, compute stats, and map classification/QA targets.
2.  **Define a Prompt Template**: Under **Resources > Prompt Templates**, design a prompt template using Jinja2 variables (e.g., `{{ text }}` or `{{ context }}`).
3.  **Sync Model Catalog**: Under **Resources > Models**, check the health of enabled providers and sync the list of available active LLMs.
4.  **Create an Experiment**: Go to **Experiments > Create Experiment** to define an experiment configuration: select a model, prompt template, strategy (zero-shot vs. few-shot selection criteria), and parameters.
5.  **Monitor Run**: Monitor progress via **Experiments > Running Experiments**. Since executions are multi-threaded, they run safely in the background.
6.  **Analyze & Export**: Review findings in **Results > Experiment Results** or compare runs side-by-side using **Results > Compare Experiments**. Export evaluations to CSV/Excel from the dashboard.
