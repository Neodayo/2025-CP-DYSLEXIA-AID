# ml/train_model.py
import pandas as pd
import glob
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
import joblib
import os

# Path to your extracted CSV files
DATA_PATH = "data_extracted/data"

def load_data():
    files = glob.glob(os.path.join(DATA_PATH, "*_metrics.csv"))
    dfs = [pd.read_csv(f) for f in files]
    df = pd.concat(dfs, ignore_index=True)

    # ✅ Select features (add more if needed)
    features = ["n_fix_trial", "mean_fix_dur_trial", "n_sacc_trial", "n_regress_trial"]

    # ⚠️ Fake labels (replace later with real dyslexia types if available)
    labels = ["Phonological", "Surface", "Visual", "Rapid Naming"] * (len(df) // 4 + 1)
    df["label"] = labels[:len(df)]  # ✅ ensures same length

    return df, features

def train_model():
    df, features = load_data()
    X = df[features]
    y = df["label"]

    # Split train/test
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Train model
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    print("Model Performance:\n", classification_report(y_test, y_pred))

    # Save model
    joblib.dump(model, "ml/dyslexia_model.pkl")
    print("✅ Model saved to ml/dyslexia_model.pkl")

if __name__ == "__main__":
    train_model()
