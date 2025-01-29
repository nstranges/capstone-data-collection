from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, precision_score, recall_score, 
                             f1_score, confusion_matrix, classification_report, matthews_corrcoef)
from sklearn.model_selection import train_test_split
import m2cgen as m2c
import pandas as pd

# Train and test the model
def train_model(X_train, y_train, X_test, y_test, feature_names):
    # Initialize and fit the model
    rf_model = RandomForestClassifier(
        verbose=1,
        n_jobs=-1,
        n_estimators=10, #try 50 # was 100
        # max_depth = 10, #default is none
        max_features=0.5, # Fewer features per split, less memory
        random_state=42
    )

    rf_model.fit(X_train, y_train)

    # Test predictions
    y_pred = rf_model.predict(X_test)

    # Evaluate model
    metrics_rf = calculate_performance_metrics(y_test, y_pred)
    print_performance_metrics(metrics_rf)
    feature_importance(rf_model, X_train, feature_names)

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
def feature_importance(model, X, feature_names):
    feature_importances = model.feature_importances_
    feature_importances_list = [(feature_names[j], importance) for j, importance in enumerate(feature_importances)]
    feature_importances_list.sort(key=lambda x: x[1], reverse=True)

    print("Feature Importances:")
    for feature, importance in feature_importances_list:
        print(f"{feature}: {importance}")

# Formatting the variable drops
def makeDropList(appender):
    xa = 'xaccel_' + appender
    ya = 'yaccel_' + appender
    za = 'zaccel_' + appender
    xr = 'xrot_' + appender
    yr = 'yrot_' + appender
    zr = 'zrot_' + appender

    return [xa, ya, za, xr, yr, zr]

# Formatting the variable drops
def secondDropList(appender):
    emg1 = 'emg1_' + appender
    emg2 = 'emg2_' + appender
    emg3 = 'emg3_' + appender
    pulse = 'pulse_' + appender

    return [emg1, emg2, emg3, pulse]

# Runs the model
def run_model_training():
    # Load the data
    processed_data = pd.read_csv('processed_data.csv')

    # Dropping accelerometers
    for num in range(1, 16):
        i = str(num)
        cur_drops = makeDropList(appender=i)
        processed_data = processed_data.drop(columns=cur_drops)

        cur_drops = secondDropList(appender=i)
        processed_data = processed_data.drop(columns=cur_drops)

    # Dropping avg and var
    processed_data = processed_data.drop(columns=makeDropList('avg'))
    processed_data = processed_data.drop(columns=makeDropList('var'))
    processed_data = processed_data.drop(columns=makeDropList('rms'))
    processed_data = processed_data.drop(columns=secondDropList('rms'))
    processed_data = processed_data.drop(columns=makeDropList('first_derivative'))
    processed_data = processed_data.drop(columns=makeDropList('second_derivative'))
    processed_data = processed_data.drop(columns=secondDropList('first_derivative'))
    processed_data = processed_data.drop(columns=secondDropList('second_derivative'))

    # Separate data
    X = processed_data.drop(columns=['Position']).values
    y = processed_data['Position'].values

    feature_names = processed_data.columns[:-1].tolist()

    # Get test and train
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print('Read the data')
    # Run the model
    model = train_model(X_train, y_train, X_test, y_test, feature_names)
    
    #Send the model to code
    # code = m2c.export_to_c(model, function_name="predict")
    # file_path = "modelCode.txt"
    # with open(file_path, "w") as file:
    #     file.write(code)


run_model_training()