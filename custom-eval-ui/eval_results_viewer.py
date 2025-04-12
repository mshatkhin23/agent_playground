import streamlit as st
import json
import pandas as pd
import plotly.express as px
from typing import List, Dict
from difflib import Differ
import yaml

# Set page config for wide layout
st.set_page_config(layout="wide")

def load_eval_results():
    with open('eval_results.json', 'r') as f:
        return json.load(f)

def create_summary_table(eval_results):
    summary_data = []
    for result in eval_results:
        # Extract key metrics
        metrics_dict = {metric["name"]: metric["value"] for metric in result["aggregate-metrics"]}
        
        # Get predictor info
        predictor = result["evaluation-config"]["predictor"]
        predictor_str = f"{predictor['module']} ({predictor['args']['model_version']})"
        
        summary_data.append({
            "Run Name": result["evaluation-run-name"],
            "Dataset": result["evaluation-config"]["dataset"]["bri"],
            "Predictor": predictor_str,
            **metrics_dict
        })
    
    return pd.DataFrame(summary_data)

def create_metric_charts(selected_results: List[Dict], metric_names: List[str]):
    """Create bar charts for each metric comparing selected runs."""
    charts = []
    for metric_name in metric_names:
        # Prepare data for the chart
        chart_data = []
        for result in selected_results:
            # Find the metric value
            metric_value = next(
                (m["value"] for m in result["aggregate-metrics"] if m["name"] == metric_name),
                None
            )
            if metric_value is not None:
                chart_data.append({
                    "Run ID": result["evaluation-run-id"],
                    "Value": metric_value,
                    "Metric": metric_name
                })
        
        if chart_data:
            df = pd.DataFrame(chart_data)
            fig = px.bar(
                df,
                x="Run ID",
                y="Value",
                title=metric_name,
                color="Run ID",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            charts.append(fig)
    
    return charts

def create_comparison_table(selected_results: List[Dict], selected_metric: str = None) -> pd.DataFrame:
    """Create a table comparing instance outputs across selected runs."""
    # Get all unique instance IDs
    instance_ids = set()
    inputs = {}
    reference_outputs = {}
    for result in selected_results:
        for instance in result["instance-metrics"]:
            instance_id = instance.get("instance-id", instance["input"])
            instance_ids.add(instance_id)
            inputs[instance_id] = instance["input"]
            reference_outputs[instance_id] = instance["reference-output"]
    
    # Create comparison data
    comparison_data = []
    for instance_id in sorted(instance_ids):
        row = {
            "Instance ID": instance_id,
            "Input": inputs.get(instance_id, ""),
            "Expected Classes": json.dumps(reference_outputs.get(instance_id, {}))
        }
        
        # Store metric values for comparison
        metric_values = {}
        for result in selected_results:
            # Find the matching instance
            instance = next(
                (i for i in result["instance-metrics"] 
                 if i.get("instance-id", i["input"]) == instance_id),
                None
            )
            if instance:
                row[result["evaluation-run-id"]] = instance["output"]
                # Add the selected metric value if specified
                if selected_metric and "metrics" in instance:
                    metric_value = next(
                        (m["value"] for m in instance["metrics"] if m["name"] == selected_metric),
                        None
                    )
                    if metric_value is not None:
                        metric_values[result["evaluation-run-id"]] = metric_value
                        # Format float values to 3 decimal places
                        if isinstance(metric_value, float):
                            metric_value = f"{metric_value:.3f}"
                        row[f"{result['evaluation-run-id']} - {selected_metric}"] = metric_value
        
        comparison_data.append(row)
    
    df = pd.DataFrame(comparison_data)
    
    # Reorder columns to put metric columns next to each other on the right
    if selected_metric and len(selected_results) == 2:
        # Get the base columns (non-metric columns)
        base_columns = [col for col in df.columns if not col.endswith(f" - {selected_metric}")]
        
        # Get the metric columns in the same order as their corresponding output columns
        metric_columns = []
        for col in base_columns:
            if col in [result["evaluation-run-id"] for result in selected_results]:
                metric_columns.append(f"{col} - {selected_metric}")
        
        # Reorder columns: base columns first, then metric columns
        df = df[base_columns + metric_columns]
    
    # Apply styling if we have metric values to compare
    if selected_metric and len(selected_results) == 2:
        run_ids = [result["evaluation-run-id"] for result in selected_results]
        metric_columns = [f"{run_id} - {selected_metric}" for run_id in run_ids]
        
        def highlight_metrics(row):
            styles = [""] * len(df.columns)
            for i, col in enumerate(df.columns):
                if col in metric_columns:
                    # Convert values to float, handling both string and numeric types
                    v1 = float(str(row[metric_columns[0]]).replace(',', ''))
                    v2 = float(str(row[metric_columns[1]]).replace(',', ''))
                    if v1 > v2 and col == metric_columns[0]:
                        styles[i] = "color: #2b8a3e"
                    elif v2 > v1 and col == metric_columns[1]:
                        styles[i] = "color: #2b8a3e"
                    elif v1 < v2 and col == metric_columns[0]:
                        styles[i] = "color: #c92a2a"
                    elif v2 < v1 and col == metric_columns[1]:
                        styles[i] = "color: #c92a2a"
            return styles
        
        df = df.style.apply(highlight_metrics, axis=1)
    
    return df

def get_common_instance_metrics(selected_results: List[Dict]) -> List[str]:
    """Get a list of instance metrics that are common across all selected runs."""
    if not selected_results:
        return []
    
    # Get all metric names from the first run
    first_run_metrics = set()
    for instance in selected_results[0]["instance-metrics"]:
        if "metrics" in instance:
            first_run_metrics.update(m["name"] for m in instance["metrics"])
    
    # Find intersection with other runs
    common_metrics = first_run_metrics
    for result in selected_results[1:]:
        run_metrics = set()
        for instance in result["instance-metrics"]:
            if "metrics" in instance:
                run_metrics.update(m["name"] for m in instance["metrics"])
        common_metrics &= run_metrics
    
    return sorted(common_metrics)

def get_diff_lines(config1: Dict, config2: Dict) -> tuple[List[str], List[str]]:
    """Get the diff lines for two configs by comparing dictionaries directly."""
    def format_value(value, indent: int = 0) -> str:
        """Format a value for display with proper indentation in YAML format."""
        if isinstance(value, dict):
            if not value:  # Empty dict
                return "{}"
            lines = []
            for k, v in sorted(value.items()):
                if isinstance(v, dict) and v:
                    lines.append(f"{'  ' * indent}{k}:")
                    lines.append(format_value(v, indent + 1))
                else:
                    lines.append(f"{'  ' * indent}{k}: {format_value(v, indent)}")
            return "\n".join(lines)
        elif isinstance(value, list):
            if not value:  # Empty list
                return "[]"
            lines = []
            for item in value:
                if isinstance(item, (dict, list)) and item:
                    lines.append(f"{'  ' * indent}-")
                    lines.append(format_value(item, indent + 1))
                else:
                    lines.append(f"{'  ' * indent}- {format_value(item, indent)}")
            return "\n".join(lines)
        else:
            return str(value)

    def compare_dicts(d1: Dict, d2: Dict, indent: int = 0) -> tuple[List[str], List[str]]:
        """Compare two dictionaries and return formatted diff lines."""
        left_lines = []
        right_lines = []
        
        # Get all unique keys
        all_keys = sorted(set(d1.keys()) | set(d2.keys()))
        
        for key in all_keys:
            if key not in d1:
                # Key only in right dict
                right_lines.append(f'<span style="color: #51cf66; background-color: #ebfbee">{key}:</span>')
                right_lines.extend(format_value(d2[key], indent + 1).split('\n'))
                left_lines.append('')
                left_lines.extend([''] * len(format_value(d2[key], indent + 1).split('\n')))
            elif key not in d2:
                # Key only in left dict
                left_lines.append(f'<span style="color: #ff6b6b; background-color: #fff5f5">{key}:</span>')
                left_lines.extend(format_value(d1[key], indent + 1).split('\n'))
                right_lines.append('')
                right_lines.extend([''] * len(format_value(d1[key], indent + 1).split('\n')))
            else:
                # Key in both dicts
                v1, v2 = d1[key], d2[key]
                
                if isinstance(v1, dict) and isinstance(v2, dict):
                    # Both values are dicts, recurse
                    left_lines.append(f'<span style="color: #333">{key}:</span>')
                    right_lines.append(f'<span style="color: #333">{key}:</span>')
                    sub_left, sub_right = compare_dicts(v1, v2, indent + 1)
                    left_lines.extend(sub_left)
                    right_lines.extend(sub_right)
                elif v1 != v2:
                    # Values are different
                    left_lines.append(f'<span style="color: #ff6b6b; background-color: #fff5f5">{key}:</span>')
                    left_lines.extend(format_value(v1, indent + 1).split('\n'))
                    right_lines.append(f'<span style="color: #51cf66; background-color: #ebfbee">{key}:</span>')
                    right_lines.extend(format_value(v2, indent + 1).split('\n'))
                else:
                    # Values are the same
                    left_lines.append(f'<span style="color: #333">{key}:</span>')
                    left_lines.extend(format_value(v1, indent + 1).split('\n'))
                    right_lines.append(f'<span style="color: #333">{key}:</span>')
                    right_lines.extend(format_value(v2, indent + 1).split('\n'))
        
        return left_lines, right_lines

    # Start the comparison
    left_lines, right_lines = compare_dicts(config1, config2)
    
    return left_lines, right_lines

def show_comparison_details(selected_results: List[Dict]):
    st.title("Evaluation Runs Comparison")
    
    # Show evaluation configs comparison
    st.subheader("Evaluation Configurations")
    if len(selected_results) == 2:
        # If exactly two runs are selected, show side-by-side configs
        st.markdown(f"**{selected_results[0]['evaluation-run-name']}** vs **{selected_results[1]['evaluation-run-name']}**")
        
        # Create two columns for side-by-side display
        col1, col2 = st.columns(2)
        
        with col1:
            st.json(selected_results[0]["evaluation-config"])
        
        with col2:
            st.json(selected_results[1]["evaluation-config"])
    else:
        # If more or fewer runs are selected, just show the configs
        for result in selected_results:
            st.markdown(f"**{result['evaluation-run-name']}**")
            st.json(result["evaluation-config"])
    
    # Get common metric names
    metric_names = set()
    for result in selected_results:
        metric_names.update(m["name"] for m in result["aggregate-metrics"])
    metric_names = sorted(metric_names)
    
    # Create and display metric charts in a horizontal layout
    st.subheader("Aggregate Metrics Comparison")
    charts = create_metric_charts(selected_results, metric_names)
    
    # Create columns for horizontal layout
    cols = st.columns(len(charts))
    for col, chart in zip(cols, charts):
        with col:
            st.plotly_chart(chart, use_container_width=True)
    
    # Create and display comparison table
    st.subheader("Instance Outputs Comparison")
    
    # Add dropdown for common instance metrics
    common_metrics = get_common_instance_metrics(selected_results)
    if common_metrics:
        selected_metric = st.selectbox(
            "Select Instance Metric to Compare",
            options=common_metrics,
            index=0
        )
    else:
        selected_metric = None
    
    comparison_df = create_comparison_table(selected_results, selected_metric)
    if isinstance(comparison_df, pd.io.formats.style.Styler):
        st.dataframe(comparison_df, hide_index=True)
    else:
        st.dataframe(comparison_df, hide_index=True)

def main():
    # Initialize session state
    if 'selected_runs' not in st.session_state:
        st.session_state.selected_runs = []
    if 'show_comparison' not in st.session_state:
        st.session_state.show_comparison = False
    if 'selected_indices' not in st.session_state:
        st.session_state.selected_indices = []
    
    # Debug information
    st.sidebar.title("Debug Info")
    st.sidebar.write("Session State:")
    st.sidebar.json({
        "show_comparison": st.session_state.show_comparison,
        "selected_runs_count": len(st.session_state.selected_runs),
        "selected_indices": st.session_state.selected_indices
    })
    
    # Load the evaluation results
    eval_results = load_eval_results()
    
    # Home page - Summary Table
    if not st.session_state.show_comparison:
        st.title("Evaluation Runs Summary")
        summary_df = create_summary_table(eval_results)
        
        # Display the table with multi-row selection
        selected_df = st.dataframe(
            summary_df,
            hide_index=True,
            on_select="rerun",
            selection_mode="multi-row"
        )
        
        # Get the selection from the dataframe component
        if selected_df is not None and hasattr(selected_df, 'selection'):
            st.session_state.selected_indices = selected_df.selection.rows
            st.sidebar.write("Current Selection:")
            st.sidebar.json({"selected_rows": st.session_state.selected_indices})
        
        # Add a button to view selected runs
        if st.button("View Selected Runs"):
            if st.session_state.selected_indices:
                st.sidebar.write(f"Selected indices: {st.session_state.selected_indices}")
                
                st.session_state.selected_runs = [eval_results[i] for i in st.session_state.selected_indices]
                st.session_state.show_comparison = True
                st.sidebar.write("Transitioning to comparison view...")
                st.rerun()
            else:
                st.sidebar.write("No rows selected!")
    
    # Comparison page
    else:
        # Add a back button
        if st.button("← Back to Summary"):
            st.session_state.show_comparison = False
            st.session_state.selected_runs = []
            st.session_state.selected_indices = []
            st.sidebar.write("Returning to summary view...")
            st.rerun()
        
        # Show the comparison
        show_comparison_details(st.session_state.selected_runs)

if __name__ == "__main__":
    main() 