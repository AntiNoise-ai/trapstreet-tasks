import yaml


def load_flags():
    with open("config/app.yaml") as f:
        data = yaml.safe_load(f)
    return data["feature_flags"]
