import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, classification_report
import joblib
import numpy as np

# Updated: Categorize all symptoms from your list
NON_SEVERE_SYMPTOMS = [
    'fever', 'headache', 'nausea', 'fatigue', 'joint pain', 'rashes',
    'back pain', 'eye pain', 'vomiting', 'abdominal pain',
    'bleeding gums', 'vomiting blood', 'blood in stool', 'rapid pulse',
    'low blood pressure', 'cold extremities', 'breathing difficulty',
    'severe abdominal pain', 'persistent vomiting', 'drowsiness',
]

HIGH_RISK_SYMPTOMS = [
    'bleeding gums', 'vomiting blood', 'blood in stool', 'rapid pulse',
    'low blood pressure', 'cold extremities', 'breathing difficulty',
    'severe abdominal pain', 'persistent vomiting', 'drowsiness',
]

def create_and_train_model():
    """
    Creates a more sophisticated synthetic dataset to train a Random Forest model.
    The model is now explicitly trained on the count of non-severe symptoms.
    """
    print("Creating enhanced synthetic dataset...")

    num_samples = 2000

    data = {}
    data['age'] = np.random.randint(20, 60, num_samples)
    data['days_with_symptoms'] = np.random.randint(1, 15, num_samples)
    
    # Feature for presence of fever
    data['has_fever'] = np.random.choice([0, 1], num_samples, p=[0.2, 0.8])
    
    # Feature for the count of non-severe symptoms
    # This is a new feature that will help the model detect cumulative risk
    data['non_severe_symptom_count'] = np.random.randint(0, 10, num_samples)
    
    # Initialize all high-risk symptom features to 0
    for symptom in HIGH_RISK_SYMPTOMS:
        data[f'has_{symptom.replace(" ", "_")}'] = np.zeros(num_samples, dtype=int)
        
    outcome = np.zeros(num_samples, dtype=int)

    # Rule 1: A patient with a high-risk symptom almost always has a severe outcome
    num_high_risk = int(0.15 * num_samples)
    high_risk_indices = np.random.choice(num_samples, num_high_risk, replace=False)
    for i in high_risk_indices:
        random_symptom = np.random.choice(HIGH_RISK_SYMPTOMS)
        data[f'has_{random_symptom.replace(" ", "_")}'][i] = 1
        outcome[i] = np.random.choice([0, 1], p=[0.05, 0.95]) # 95% chance of severe outcome
        
    # Rule 2: A high number of non-severe symptoms can also lead to a severe outcome
    non_high_risk_indices = np.setdiff1d(np.arange(num_samples), high_risk_indices)
    for i in non_high_risk_indices:
        # A severe outcome is possible if there's a high symptom count and long duration
        if data['has_fever'][i] == 1 and data['non_severe_symptom_count'][i] > 5 and data['days_with_symptoms'][i] > 7:
            outcome[i] = np.random.choice([0, 1], p=[0.5, 0.5]) # 50% chance of severe outcome
    
    data['outcome'] = outcome
    df = pd.DataFrame(data)

    print(f"Generated a dataset with {len(df)} records. Severe cases: {df['outcome'].sum()}")

    # 2. Define features (X) and target (y)
    X = df.drop('outcome', axis=1)
    y = df['outcome']

    # 3. Split data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # 4. Train the model
    print("Training the Random Forest model...")
    model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
    model.fit(X_train, y_train)
    
    # 5. Evaluate the model on the test set
    y_pred = model.predict(X_test)
    
    print("\n--- Model Evaluation ---")
    print(f"Accuracy: {accuracy_score(y_test, y_pred):.2f}")
    print(f"Precision: {precision_score(y_test, y_pred, zero_division=0):.2f}")
    print(f"Recall: {recall_score(y_test, y_pred, zero_division=0):.2f}")
    print(f"F1-Score: {f1_score(y_test, y_pred, zero_division=0):.2f}")
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, zero_division=0))

    # 6. Save the trained model and features
    joblib.dump(model, 'ml_model/risk_model.pkl')
    joblib.dump(list(X.columns), 'ml_model/features.pkl')
    print("\nModel and features saved successfully.")

if __name__ == '__main__':
    create_and_train_model()