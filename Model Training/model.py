from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, precision_score, recall_score, 
                             f1_score, confusion_matrix, classification_report, matthews_corrcoef)
from sklearn.model_selection import train_test_split
import m2cgen as m2c
import pandas as pd
import re
from sklearn.neural_network import MLPClassifier

# Train and test the model
def train_model(X_train, y_train, X_test, y_test, feature_names):
    # Initialize and fit the model
    # rf_model = RandomForestClassifier(
    #     verbose=1,
    #     n_jobs=-1,
    #     n_estimators=25, #try 50 # was 100
    #     #max_depth = 10, #default is none
    #     #max_features=3, # Fewer features per split, less memory
    #     random_state=42
    # )

    rf_model = MLPClassifier(hidden_layer_sizes=(1028, 512, 32),  # Two hidden layers with 16 neurons each
                    activation='relu',            # ReLU activation
                    solver='adam',                # Adam optimizer
                    max_iter=500,                 # Increase iterations for convergence
                    random_state=42)

    rf_model.fit(X_train, y_train)

    # Test predictions
    y_pred = rf_model.predict(X_test)

    # Evaluate model
    metrics_rf = calculate_performance_metrics(y_test, y_pred)
    print_performance_metrics(metrics_rf)
    #feature_importance(rf_model, X_train, feature_names)

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

def split_deep_ifs(code_lines, max_depth=3):
    refactored_lines = []
    extracted_functions = []
    stack = []
    if_block = []
    inside_block = False
    function_count = 0

    # Track variables used in each if block (e.g., var2, var49) plus 'output'
    used_variables = set()

    for line in code_lines:
        indent_level = len(line) - len(line.lstrip())

        # detect if statement
        if re.match(r'\s*(?:else\s+)?if\s*\(|\s*else\s*\{', line):
            stack.append(line)
            if len(stack) > max_depth:
                inside_block = True
                if_block.append(line)
                # find var usage
                used_variables.update(re.findall(r'var(\d+)', line))
                # also capture usage of 'output'
                if 'output' in line:
                    used_variables.add('output')
            else:
                refactored_lines.append(line)
        else:
            if inside_block:
                if_block.append(line)
                used_variables.update(re.findall(r'var(\d+)', line))
                if 'output' in line:
                    used_variables.add('output')

                # close block when a '}' is found, reduce stack
                if '}' in line:
                    stack.pop()
                    # if we are back at max_depth, finalize
                    if len(stack) == max_depth:
                        inside_block = False
                        fn_name = f"split_func_{function_count}"
                        function_count += 1
                        # copy block lines
                        block_copy = if_block[:]

                        # Insert call in the main code
                        # pass all varN used in that block + output
                        if used_variables:
                            # separate numeric from 'output'
                            numeric_vars = sorted([v for v in used_variables if v.isdigit()])
                            has_output = ('output' in used_variables)

                            # build the parameter call
                            param_call_parts = []
                            for v in numeric_vars:
                                param_call_parts.append(f"var{v}")
                            if has_output:
                                param_call_parts.append("output")

                            if param_call_parts:
                                call_line = (" " * indent_level 
                                             + f"{fn_name}(input, "
                                             + ", ".join(param_call_parts) 
                                             + ");\n")
                            else:
                                call_line = (" " * indent_level 
                                             + f"{fn_name}(input);\n")
                        else:
                            call_line = (" " * indent_level 
                                         + f"{fn_name}(input);\n")

                        refactored_lines.append(call_line)

                        extracted_functions.append((fn_name, block_copy[:], used_variables.copy()))

                        # clear for next block
                        if_block.clear()
                        used_variables.clear()
            else:
                refactored_lines.append(line)

    return refactored_lines, extracted_functions


def generate_function_definitions(function_data):
    """
    Build function definitions for each extracted if block.
    Each function receives 'double *input' plus all needed 'double *varX',
    plus 'double *output' if used.
    """
    defs = []
    for fn_name, block_lines, var_usage in function_data:
        numeric_vars = sorted([v for v in var_usage if v.isdigit()])
        has_output = ('output' in var_usage)

        # build param list
        param_list_parts = []
        for v in numeric_vars:
            param_list_parts.append(f"double *var{v}")
        if has_output:
            param_list_parts.append("double *output")

        if param_list_parts:
            full_param_list = ", ".join(param_list_parts)
            signature = f"void {fn_name}(double *input, {full_param_list}) {{\n"
        else:
            signature = f"void {fn_name}(double *input) {{\n"

        fn_code = [signature]

        fn_code_body = []
        for line in block_lines:
            fn_code_body.append("    " + line.strip() + "\n")

        body_text = "".join(fn_code_body)
        open_braces = sum(l.count("{") for l in block_lines)
        close_braces = sum(l.count("}") for l in block_lines)
        while close_braces < open_braces:
            body_text += "}\n"
            close_braces += 1

        fn_code.append(body_text)
        fn_code.append("}\n\n")
        defs.append("".join(fn_code))

    return defs


def create_proper_code(
    file_path,
    replacements,
    output_file,
    text_to_insert,
    max_depth=3
):
    # 1) read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        original_lines = f.readlines()

    # 2) do replacements
    content = "".join(original_lines)
    for old_val, new_val in replacements.items():
        content = content.replace(old_val, new_val)

    # 3) split deep ifs
    updated_lines = []
    lines = content.splitlines(keepends=True)
    for line in lines:
        updated_lines.append(line)

    refactored, extracted = split_deep_ifs(updated_lines, max_depth)

    # 4) generate separate function definitions
    func_defs = generate_function_definitions(extracted)

    # 5) assemble final code
    final_code = "".join(func_defs)
    final_code += "".join(refactored)

    # 6) Place #include lines at top
    includes = '#include "helpers.h"\n#include <cstring>\n#include <string.h>\n' + text_to_insert
    final_code = includes + final_code

    # 7) write
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(final_code)


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

    # print("Model code created")
    # output_file = "adjustedModelCode.txt"

    # replacements = {
    #     "(double[]){1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0}": "defaultValues1",
    #     "(double[]){0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0}": "defaultValues2",
    #     "(double[]){0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0}": "defaultValues3",
    #     "(double[]){0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0}": "defaultValues4",
    #     "(double[]){0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0}": "defaultValues5",
    #     "(double[]){0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0}": "defaultValues6",
    #     "(double[]){0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0}": "defaultValues7",
    #     "(double[]){0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0}": "defaultValues8",
    #     "#include <string.h>": "",
    # }

    # text_to_insert = ("double defaultValues1[8] = {1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};"+
    #                 "\ndouble defaultValues2[8] = {0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};"+
    #                 "\ndouble defaultValues3[8] = {0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0};"+
    #                 "\ndouble defaultValues4[8] = {0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0};"+
    #                 "\ndouble defaultValues5[8] = {0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0};"+
    #                 "\ndouble defaultValues6[8] = {0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0};"+
    #                 "\ndouble defaultValues7[8] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0};"+
    #                 "\ndouble defaultValues8[8] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0};\n")

    # create_proper_code(file_path, replacements, output_file, text_to_insert)
    # print("Model code adjusted")


run_model_training()