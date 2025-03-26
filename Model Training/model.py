from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, precision_score, recall_score, 
                             f1_score, confusion_matrix, classification_report, matthews_corrcoef)
from sklearn.model_selection import train_test_split
import m2cgen as m2c
import pandas as pd
import re

# Train and test the model
def train_model(X_train, y_train, X_test, y_test, feature_names):
    # Initialize and fit the model
    rf_model = RandomForestClassifier(
        verbose=1,
        n_jobs=-1,
        n_estimators=100, #try 50 # was 100
        #max_depth = 10, #default is none
        #max_features=3, # Fewer features per split, less memory
        random_state=42
    )

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

def split_deep_if_else(code_lines, max_depth=3):
    """
    Scans through 'code_lines' from m2cgen, extracting entire if/else
    blocks that exceed 'max_depth'.
    Returns:
      refactored_lines: code with deep blocks replaced by function calls
      extracted_functions: list of (fn_name, block_lines, used_vars)
    """
    refactored_lines = []
    extracted_functions = []
    i = 0
    function_count = 0
    
    # Tracks our current brace "depth" across the entire file
    brace_depth = 0

    # Helper to find all var usage in some lines
    def find_used_vars(lines):
        found = set()
        for ln in lines:
            found.update(re.findall(r'var(\d+)', ln))
            if 'output' in ln:
                found.add('output')
        return found

    while i < len(code_lines):
        line = code_lines[i]
        
        # If this line starts an if(...) block
        if re.match(r'\s*(?:else\s+)?if\s*\(', line):
            # We'll parse the *entire* if/else structure (including nested else if, else)
            block_lines, end_index = parse_full_if_else_structure(code_lines, i)

            # measure how many braces are in the lines prior
            local_depth = brace_depth

            # Count the max additional nested braces inside this block
            # to see how deep it goes
            block_brace_diff = compute_local_depth(block_lines)
            # The final depth of this block is local_depth + block_brace_diff
            # If that's more than max_depth, we extract
            if local_depth + block_brace_diff > max_depth:
                # Make a function
                fn_name = f"split_func_{function_count}"
                function_count += 1
                
                # Find used variables
                used_vars = find_used_vars(block_lines)
                
                # Insert a call in the main code
                indent_level = len(line) - len(line.lstrip())
                
                numeric_vars = sorted([v for v in used_vars if v.isdigit()])
                has_output = ('output' in used_vars)

                if numeric_vars or has_output:
                    param_call_parts = [f"var{v}" for v in numeric_vars]
                    if has_output:
                        param_call_parts.append("output")
                    call_line = (
                        " " * indent_level
                        + f"{fn_name}(input, {', '.join(param_call_parts)});\n"
                    )
                else:
                    call_line = (
                        " " * indent_level + f"{fn_name}(input);\n"
                    )

                refactored_lines.append(call_line)
                
                extracted_functions.append((fn_name, block_lines, used_vars))
                
            else:
                # block is shallow enough → keep it inline
                refactored_lines.extend(block_lines)
            
            # we've consumed lines up to end_index
            # update brace_depth by scanning the block for net +/-
            brace_depth += net_braces_in_block(block_lines)
            i = end_index + 1

        else:
            # normal line, just keep it
            # update brace depth
            brace_depth += line.count("{")
            brace_depth -= line.count("}")
            refactored_lines.append(line)
            i += 1

    return refactored_lines, extracted_functions


def parse_full_if_else_structure(lines, start_index):
    """
    Reads from 'lines[start_index]' which should be an 'if(...) {'
    (or 'else if(...)') until the entire matching if/else chain is complete.
    
    Returns:
      block_lines: list of lines that constitute *all* of:
        if(...) { ... } [ else if(...) { ... } ]* [ else { ... } ]?
      end_index: the last index we used in 'lines'
    """
    block_lines = []
    brace_count = 0
    i = start_index
    started = False
    
    while i < len(lines):
        line = lines[i]
        block_lines.append(line)
        # check braces
        opens = line.count("{")
        closes = line.count("}")
        brace_count += opens
        brace_count -= closes

        # once we see the first '{', we mark started
        if opens > 0 and not started:
            started = True

        # if we've closed all braces
        if started and brace_count <= 0:
            # but we might see an immediate else or else if
            # so let's peek next line, if it's "else {..." or "else if(...){"
            # we keep going
            if i + 1 < len(lines):
                next_line = lines[i+1]
                if re.match(r'\s*else\s*(?:if\s*\(|\{)', next_line):
                    i += 1
                    continue
            
            return block_lines, i
        i += 1

    # if we run out of lines, return what we have
    return block_lines, i

def compute_local_depth(block_lines):
    """
    Return how many net braces are in block_lines
    (the maximum depth relative to block start, or a simpler measure).
    For a more accurate approach, track the maximum running brace_count.
    """
    brace_count = 0
    max_depth_in_block = 0
    for ln in block_lines:
        opens = ln.count("{")
        closes = ln.count("}")
        # increment first
        for _ in range(opens):
            brace_count += 1
            max_depth_in_block = max(max_depth_in_block, brace_count)
        # then decrement
        for _ in range(closes):
            brace_count -= 1
    return max_depth_in_block

def net_braces_in_block(block_lines):
    """
    Return net open braces minus close braces in entire block.
    """
    opens = sum(ln.count("{") for ln in block_lines)
    closes = sum(ln.count("}") for ln in block_lines)
    return opens - closes

def generate_function_definitions(function_data):
    """
    Build function definitions for each extracted if block,
    removing empty 'else { }' blocks in the process.
    """
    # This regex looks for '} else { }' with only optional whitespace/newlines
    # in between, and replaces it with a single '}' (thus removing the empty else).
    empty_else_pattern = re.compile(r"\}\s*else\s*\{\s*\}", re.MULTILINE)

    defs = []
    for fn_name, block_lines, var_usage in function_data:
        # Determine which var indices we need to pass to the function
        numeric_vars = sorted([v for v in var_usage if v.isdigit()])
        has_output = ('output' in var_usage)

        # Build function signature
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

        # Indent the block lines inside the function
        fn_code_body = []
        for line in block_lines:
            fn_code_body.append("    " + line.strip() + "\n")

        # Join all lines of function body
        body_text = "".join(fn_code_body)

        # 1) Remove any empty 'else { }' blocks
        body_text = empty_else_pattern.sub("}", body_text)

        # 2) If there's a mismatch in braces, add closing braces
        open_braces = sum(l.count("{") for l in block_lines)
        close_braces = sum(l.count("}") for l in block_lines)
        while close_braces < open_braces:
            body_text += "}\n"
            close_braces += 1

        # Assemble final function text
        fn_code.append(body_text)
        fn_code.append("}\n\n")

        # Add to overall definitions
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

    refactored, extracted = split_deep_if_else(updated_lines, max_depth)

    # 4) generate separate function definitions
    func_defs = generate_function_definitions(extracted)

    # 5) assemble final code
    final_code = "".join(func_defs)
    final_code += "".join(refactored)

    # 6) Place #include lines at top
    includes = '#include "helpers.h"\n#include <cstring>\n#include <string.h>\n' + text_to_insert
    final_code = includes + final_code

    # 7) Changing the variable names
    final_code = final_code.replace('input', 'modelInput')
    final_code = final_code.replace('output', 'modelOutput')

    # 8) write
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

# Trains the model
def create_model():
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
    #processed_data = processed_data.drop(columns=secondDropList('first_derivative'))
    #processed_data = processed_data.drop(columns=secondDropList('second_derivative'))

    # Separate data
    X = processed_data.drop(columns=['Position']).values
    y = processed_data['Position'].values

    feature_names = processed_data.columns[:-1].tolist()

    # Get test and train
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print('Read the data')
    # Run the model
    model = train_model(X_train, y_train, X_test, y_test, feature_names)

    return model

# Formats the code correctly
def create_model_code(model):
    #Send the model to code
    code = m2c.export_to_c(model, function_name="predict")
    file_path = "modelCode.txt"
    with open(file_path, "w") as file:
        file.write(code)

    print("Model code created")
    output_file = "adjustedModelCode.txt"

    replacements = {
        "(double[]){1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0}": "defaultValues1",
        "(double[]){0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0}": "defaultValues2",
        "(double[]){0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0}": "defaultValues3",
        "(double[]){0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0}": "defaultValues4",
        "(double[]){0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0}": "defaultValues5",
        "(double[]){0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0}": "defaultValues6",
        "(double[]){0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0}": "defaultValues7",
        "(double[]){0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0}": "defaultValues8",
        "#include <string.h>": "",
    }

    text_to_insert = ("double defaultValues1[8] = {1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};"+
                    "\ndouble defaultValues2[8] = {0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};"+
                    "\ndouble defaultValues3[8] = {0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0};"+
                    "\ndouble defaultValues4[8] = {0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0};"+
                    "\ndouble defaultValues5[8] = {0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0};"+
                    "\ndouble defaultValues6[8] = {0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0};"+
                    "\ndouble defaultValues7[8] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0};"+
                    "\ndouble defaultValues8[8] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0};\n")

    create_proper_code(file_path, replacements, output_file, text_to_insert)
    print("Model code adjusted")

# Runs the model
def run_model_training():
    # Train the model
    model = create_model()

    # Make the code
    create_model_code(model)

run_model_training()