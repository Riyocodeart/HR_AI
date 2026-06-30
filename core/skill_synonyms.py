SKILL_SYNONYMS = {

    # Programming Languages
    "python": ["python3", "py"],
    "java": ["core java", "java se"],
    "javascript": ["js", "ecmascript"],
    "typescript": ["ts"],
    "c++": ["cpp"],
    "c#": ["csharp", ".net"],
    "r": ["r language"],
    "go": ["golang"],
    "scala": [],
    "kotlin": [],
    "swift": [],
    "php": [],

    # Data Science
    "machine learning": ["ml", "machine-learning"],
    "deep learning": ["dl", "deep-learning"],
    "artificial intelligence": ["ai"],
    "data science": ["data scientist"],
    "statistics": ["statistical analysis"],
    "data analysis": ["analytics", "analytical"],
    "predictive modeling": ["predictive analytics"],

    # NLP
    "natural language processing": ["nlp"],
    "large language models": ["llm", "llms"],
    "bert": [],
    "gpt": ["chatgpt"],
    "transformers": ["huggingface transformers"],

    # Computer Vision
    "computer vision": ["cv"],
    "image classification": [],
    "object detection": [],
    "opencv": [],

    # Frameworks
    "tensorflow": ["tf"],
    "pytorch": ["torch"],
    "keras": [],
    "scikit-learn": ["sklearn"],
    "xgboost": [],
    "lightgbm": [],
    "catboost": [],

    # Data Engineering
    "apache spark": ["spark", "pyspark"],
    "apache airflow": ["airflow"],
    "apache kafka": ["kafka"],
    "hadoop": [],
    "dbt": [],
    "snowflake": [],
    "databricks": [],

    # Databases
    "mysql": [],
    "postgresql": ["postgres", "postgres db"],
    "mongodb": ["mongo"],
    "oracle": [],
    "sqlite": [],
    "redis": [],
    "elasticsearch": [],

    # Cloud
    "amazon web services": ["aws"],
    "google cloud platform": ["gcp", "google cloud"],
    "microsoft azure": ["azure"],

    # DevOps
    "docker": [],
    "kubernetes": ["k8s"],
    "jenkins": [],
    "github actions": [],
    "terraform": [],

    # Backend
    "django": [],
    "flask": [],
    "fastapi": [],
    "spring boot": [],
    "node.js": ["nodejs", "node"],

    # Frontend
    "react": ["reactjs"],
    "angular": [],
    "vue.js": ["vue"],
    "tailwind css": ["tailwind"],
    "html": ["html5"],
    "css": ["css3"],

    # BI
    "power bi": ["powerbi"],
    "tableau": [],
    "excel": ["microsoft excel"],

    # Version Control
    "git": [],
    "github": [],
    "gitlab": [],

    # MLOps
    "mlflow": [],
    "weights & biases": ["wandb"],
    "bentoml": [],
    "faiss": [],
    "onnx": [],
    "lora": [],
    "langchain": [],
    "llamaindex": []
}

def normalize_skill(skill):

    skill = skill.strip().lower()

    for canonical, aliases in SKILL_SYNONYMS.items():

        if skill == canonical:
            return canonical

        if skill in aliases:
            return canonical

    return skill
