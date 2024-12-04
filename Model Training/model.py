from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, precision_score, recall_score, 
                             f1_score, confusion_matrix, classification_report, matthews_corrcoef)
from sklearn.model_selection import train_test_split
import m2cgen as m2c

# Train and test the model
def train_model(X_train, y_train, X_test, y_test):
    # Initialize and fit the model
    rf_model = RandomForestClassifier(
        verbose=1,
        n_jobs=-1,
        n_estimators=100, #try 50 # was 100
        # max_depth = 10, #default is none
        # max_features=0.5, # Fewer features per split, less memory
        random_state=42
    )

    rf_model.fit(X_train, y_train)

    # Test predictions
    y_pred = rf_model.predict(X_test)

    # Evaluate model
    metrics_rf = calculate_performance_metrics(y_test, y_pred)
    print_performance_metrics(metrics_rf)
    feature_importance(rf_model, X_train, y_train)

    return rf_model

# Useful values for classification
def calculate_performance_metrics(y_test, y_pred):
    metrics = {}
    metrics['accuracy'] = accuracy_score(y_test, y_pred)
    metrics['precision'] = precision_score(y_test, y_pred, average='weighted')
    metrics['recall'] = recall_score(y_test, y_pred, average='weighted')
    metrics['f1_score'] = f1_score(y_test, y_pred, average='weighted')
    metrics['confusion_matrix'] = confusion_matrix(y_test, y_pred)
    metrics['mcc'] = matthews_corrcoef(y_test, y_pred)
    metrics['classification_report'] = classification_report(y_test, y_pred)
    
    return metrics

# Prints all performance metrics
def print_performance_metrics(metrics):
    print("Accuracy:", metrics.get('accuracy', "Not computed"))
    print("Precision:", metrics.get('precision', "Not computed"))
    print("Recall:", metrics.get('recall', "Not computed"))
    print("F1 Score:", metrics.get('f1_score', "Not computed"))
    print("Confusion Matrix:\n", metrics.get('confusion_matrix', "Not computed"))
    print("Matthews Correlation Coefficient (MCC):", metrics.get('mcc', "Not computed"))
    print("Classification Report:\n", metrics.get('classification_report', "Not computed"))

# Determine the feature importance in the model
def feature_importance(model, X, y_train):
    # Check if y_train is multi-output
    is_multi_output = hasattr(y_train, 'columns')
    outputs = y_train.columns if is_multi_output else ['Output']
    
    # Iterate through outputs (for multi-output models)
    for i, output in enumerate(outputs):
        print(f"Feature Importances for Output {output}:")
        feature_importances = model.feature_importances_  # Single importance vector for classification
        
        # Map feature importance to feature names
        feature_importances_list = [(X.columns[j], importance) for j, importance in enumerate(feature_importances)]
        feature_importances_list_sorted = sorted(feature_importances_list, key=lambda x: x[1], reverse=True)
        
        # Print sorted feature importances
        for feature, importance in feature_importances_list_sorted:
            print(f"{feature}: {importance}")
        print("___________________________________________________________________")

# Runs the model
def run_model_training():
    # REPLACE THIS WITH DATA FROM THE CSV
    X = 0
    y = 0

    # Get test and train
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Run the model
    model = train_model(X_train, X_test, y_train, y_test)
    
    # Send the model to code
    code = m2c.export_to_c(model, function_name="predict")
    file_path = "modelCode.txt"
    with open(file_path, "w") as file:
        file.write(code)


run_model_training()