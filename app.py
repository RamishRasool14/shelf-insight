"""
Product Shelf Analysis Tool - Streamlit Application
"""

import streamlit as st
import json
from datetime import datetime, timedelta
from PIL import Image
import pandas as pd
from io import BytesIO
import requests
import base64

from config import (
    APP_TITLE, 
    APP_DESCRIPTION, 
    COLORS, 
    MAX_FILE_SIZE_MB,
    ALLOWED_EXTENSIONS
)
from gemini_client import GeminiProductDetector, create_sample_detection_result
from supabase_client import save_osa_run, fetch_runs

# API Configuration
OSA_API_URL = "https://tamimi.impulseglobal.net//ExternalServices/IR_API.asmx/getOSAImage"


def fetch_all_osa_data():
    """Fetch all OSA data without any filters to get available DisplayIDs and dates"""
    try:
        # Fetch data without any Date or DisplayID filters
        params = {
            'Date': '',
            'DisplayID': ''
        }
        
        response = requests.get(OSA_API_URL, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        return data, None
        
    except requests.RequestException as e:
        return None, f"API request failed: {str(e)}"
    except json.JSONDecodeError as e:
        return None, f"Failed to parse API response: {str(e)}"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"


def get_unique_display_ids(api_data):
    """Extract unique DisplayIDs from API response data"""
    if not api_data:
        return []
    
    display_ids = set()
    for item in api_data:
        if 'DisplayID' in item and item['DisplayID']:
            display_ids.add(item['DisplayID'])
    
    return sorted(list(display_ids))


def get_unique_dates(api_data):
    """Extract unique dates from API response data"""
    if not api_data:
        return []
    
    dates = set()
    for item in api_data:
        if 'DOEntry' in item and item['DOEntry']:
            dates.add(item['DOEntry'])
    
    # Convert to list and sort (most recent first)
    sorted_dates = sorted(list(dates), reverse=True)
    
    # Format for display
    formatted_dates = []
    for date_str in sorted_dates:
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            formatted_dates.append({
                'date': date_str,
                'display': date_obj.strftime('%Y-%m-%d (%A)')
            })
        except ValueError:
            # If date parsing fails, use as-is
            formatted_dates.append({
                'date': date_str,
                'display': date_str
            })
    
    return formatted_dates


def get_last_10_days():
    """Get list of last 10 days for date selection (fallback method)"""
    dates = []
    for i in range(10):
        date = datetime.now() - timedelta(days=i)
        dates.append({
            'date': date.strftime('%Y-%m-%d'),
            'display': date.strftime('%Y-%m-%d (%A)')
        })
    return dates


def fetch_osa_images(date, display_id):
    """Fetch OSA images from the API"""
    try:
        # Format date for API (using the date parameter format expected by API)
        formatted_date = date  # API expects YYYY-MM-DD format
        
        params = {
            'Date': formatted_date,
            'DisplayID': display_id
        }
        
        response = requests.get(OSA_API_URL, params=params)
        response.raise_for_status()
        
        data = response.json()
        return data, None
        
    except requests.RequestException as e:
        return None, f"API request failed: {str(e)}"
    except json.JSONDecodeError as e:
        return None, f"Failed to parse API response: {str(e)}"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"


def get_unique_skus_from_api_data(api_data):
    """Extract unique SKUs from API response data"""
    if not api_data:
        return []
    
    unique_skus = set()
    for item in api_data:
        if 'SKU' in item and item['SKU']:
            unique_skus.add(item['SKU'])
    
    return sorted(list(unique_skus))


def get_ground_truth_skus(api_data):
    """Extract ground truth SKUs (OSA=1) from API response data"""
    if not api_data:
        return []
    
    ground_truth_skus = set()
    for item in api_data:
        if 'SKU' in item and item['SKU'] and item.get('OSA') == 1:
            ground_truth_skus.add(item['SKU'])
    
    return sorted(list(ground_truth_skus))


def get_predicted_skus_from_results(detection_results):
    """Extract predicted SKUs supporting minimal and legacy formats"""
    if not detection_results:
        return []
    # Prefer new minimal shape {"sku_names": [...]}
    sku_names = detection_results.get('sku_names')
    if isinstance(sku_names, list):
        return sorted(list({str(s).strip() for s in sku_names if isinstance(s, (str, int, float)) and str(s).strip()}))
    # Fallback to legacy shape {"detected_items": [{"item_name": ...}]}
    detected_items = detection_results.get('detected_items')
    if isinstance(detected_items, list):
        return sorted(list({str(it.get('item_name')).strip() for it in detected_items if isinstance(it, dict) and it.get('item_name')}))
    return []


def get_sku_image_url(sku_name, api_data):
    """Get the image URL for a specific SKU from API data"""
    if not api_data or not sku_name:
        return None
    
    for item in api_data:
        if item.get('SKU') == sku_name:
            if item.get('SKUImage'):
                return item['SKUImage']
            if item.get('SKUimage'):
                return item['SKUimage']
    
    return None


def calculate_accuracy_metrics(ground_truth_skus, predicted_skus):
    """Calculate accuracy metrics comparing ground truth with predictions"""
    if not ground_truth_skus:
        return {
            'accuracy': 0,
            'total_ground_truth': 0,
            'total_predicted': len(predicted_skus),
            'correctly_detected': [],
            'missed_skus': [],
            'false_positives': predicted_skus.copy()
        }
    
    ground_truth_set = set(ground_truth_skus)
    predicted_set = set(predicted_skus)
    
    # Correctly detected SKUs (intersection)
    correctly_detected = list(ground_truth_set.intersection(predicted_set))
    
    # Missed SKUs (in ground truth but not predicted)
    missed_skus = list(ground_truth_set - predicted_set)
    
    # False positives (predicted but not in ground truth)
    false_positives = list(predicted_set - ground_truth_set)
    
    # Calculate accuracy
    accuracy = len(correctly_detected) / len(ground_truth_skus) if ground_truth_skus else 0
    
    return {
        'accuracy': accuracy,
        'total_ground_truth': len(ground_truth_skus),
        'total_predicted': len(predicted_skus),
        'correctly_detected': sorted(correctly_detected),
        'missed_skus': sorted(missed_skus),
        'false_positives': sorted(false_positives)
    }


def display_accuracy_metrics(metrics, api_data=None):
    """Display accuracy metrics with dropdowns for detailed view and images"""
    st.subheader("📊 Accuracy Metrics")
    
    # Main metrics display
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        accuracy_percent = metrics['accuracy'] * 100
        st.metric(
            label="Accuracy", 
            value=f"{accuracy_percent:.1f}%",
            help="Percentage of ground truth SKUs correctly detected"
        )
    
    with col2:
        st.metric(
            label="Ground Truth SKUs", 
            value=metrics['total_ground_truth'],
            help="Total SKUs with OSA=1 in the display"
        )
    
    with col3:
        st.metric(
            label="Predicted SKUs", 
            value=metrics['total_predicted'],
            help="Total SKUs detected by AI"
        )
    
    with col4:
        st.metric(
            label="Correctly Detected", 
            value=len(metrics['correctly_detected']),
            help="SKUs present in both ground truth and predictions"
        )
    
    # Detailed breakdowns with dropdowns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("**✅ Correctly Detected SKUs**")
        if metrics['correctly_detected']:
            with st.expander(f"View {len(metrics['correctly_detected'])} correctly detected SKUs"):
                for i, sku in enumerate(metrics['correctly_detected'], 1):
                    st.write(f"{i}. {sku}")
        else:
            st.info("No SKUs correctly detected")
    
    with col2:
        st.write("**❌ Missed SKUs (False Negatives)**")
        if metrics['missed_skus']:
            with st.expander(f"View {len(metrics['missed_skus'])} missed SKUs"):
                # Create scrollable container using Streamlit's container with height
                with st.container(height=400):
                    for i, sku in enumerate(metrics['missed_skus'], 1):
                        st.write(f"{i}. **{sku}**")
                        
                        # Display SKU image if available
                        if api_data:
                            image_url = get_sku_image_url(sku, api_data)
                            if image_url:
                                try:
                                    st.image(
                                        image_url, 
                                        caption=f"Missed SKU: {sku}", 
                                        width=200
                                    )
                                except Exception as e:
                                    st.error(f"Failed to load image for {sku}: {str(e)}")
                                    st.text(f"Image URL: {image_url}")
                            else:
                                st.info(f"No image available for {sku}")
                        st.write("---")  # Separator between SKUs
        else:
            st.success("No SKUs missed")
    
    with col3:
        st.write("**⚠️ False Positives**")
        if metrics['false_positives']:
            with st.expander(f"View {len(metrics['false_positives'])} false positives"):
                # Create scrollable container using Streamlit's container with height
                with st.container(height=400):
                    for i, sku in enumerate(metrics['false_positives'], 1):
                        st.write(f"{i}. **{sku}**")
                        
                        # Display SKU image if available
                        if api_data:
                            image_url = get_sku_image_url(sku, api_data)
                            if image_url:
                                try:
                                    st.image(
                                        image_url, 
                                        caption=f"False Positive: {sku}", 
                                        width=200
                                    )
                                except Exception as e:
                                    st.error(f"Failed to load image for {sku}: {str(e)}")
                                    st.text(f"Image URL: {image_url}")
                            else:
                                st.info(f"No image available for {sku}")
                        st.write("---")  # Separator between SKUs
        else:
            st.success("No false positives")


def display_osa_images(api_data):
    """Display OSA images with SKU image buttons"""
    if not api_data:
        st.info("No data available for selected date and display ID.")
        return
    
    # Group by unique after images
    image_groups = {}
    for item in api_data:
        after_image = item.get('AfterImagePath', '')
        if after_image:
            if after_image not in image_groups:
                image_groups[after_image] = []
            image_groups[after_image].append(item)
    
    if not image_groups:
        st.info("No display images found for selected date and display ID.")
        return
    
    st.subheader(f"📸 Display Images ({len(image_groups)} images found)")
    
    for i, (after_image_url, items) in enumerate(image_groups.items()):
        with st.expander(f"Display Image {i+1} - {len(items)} SKUs", expanded=True):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                try:
                    st.image(after_image_url, caption=f"Display Image {i+1}", use_container_width=True)
                except Exception as e:
                    st.error(f"Failed to load image: {str(e)}")
                    st.text(f"Image URL: {after_image_url}")
            
            with col2:
                st.write(f"**SKUs in this display:** {len(items)}")
                
                # Create searchable dropdown for SKU selection
                if items:
                    # Prepare SKU options for dropdown
                    sku_options = []
                    sku_data = {}
                    
                    for j, item in enumerate(items):
                        sku_name = item.get('SKU', f'Unknown SKU {j+1}')
                        article = item.get('ArticleNo', 'N/A')
                        upc = item.get('Upccode', 'N/A')
                        osa = item.get('OSA', 'N/A')
                        
                        # Create display text for dropdown
                        display_text = f"{sku_name} (Article: {article})"
                        sku_options.append(display_text)
                        
                        # Store full item data
                        sku_data[display_text] = {
                            'item': item,
                            'sku': sku_name,
                            'article': article,
                            'upc': upc,
                            'osa': osa
                        }
                    
                    # Searchable dropdown
                    st.write("**🔍 Select SKU to view details:**")
                    selected_sku = st.selectbox(
                        "Choose a SKU:",
                        options=["Select a SKU..."] + sku_options,
                        key=f"sku_dropdown_{i}",
                        help="Type to search or scroll to select a SKU"
                    )
                    
                    # Display selected SKU details and image
                    if selected_sku and selected_sku != "Select a SKU...":
                        selected_data = sku_data[selected_sku]
                        
                        st.write("---")
                        st.write(f"**📦 {selected_data['sku']}**")
                        st.write(f"- **Article:** {selected_data['article']}")
                        st.write(f"- **UPC:** {selected_data['upc']}")
                        st.write(f"- **OSA:** {selected_data['osa']}")
                        
                        # Display SKU image if available
                        if selected_data['item'].get('SKUImage'):
                            st.write("**🏷️ SKU Image:**")
                            try:
                                st.image(
                                    selected_data['item']['SKUImage'], 
                                    caption=f"SKU Image: {selected_data['sku']}", 
                                    width=300
                                )
                            except Exception as e:
                                st.error(f"Failed to load SKU image: {str(e)}")
                                st.text(f"Image URL: {selected_data['item']['SKUImage']}")
                        else:
                            st.info("No image available for this SKU")
                else:
                    st.info("No SKU items found in this display")


def setup_page_config():
    """Configure Streamlit page settings"""
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="🛒",
        layout="wide",
        initial_sidebar_state="expanded"
    )


def load_custom_css():
    """Load custom CSS styling"""
    st.markdown(f"""
    <style>
    .main-header {{
        color: {COLORS['text']};
        text-align: center;
        padding: 1rem 0;
        border-bottom: 2px solid {COLORS['primary']};
        margin-bottom: 2rem;
    }}
    
    .upload-section {{
        background-color: {COLORS['background']};
        padding: 2rem;
        border-radius: 10px;
        border: 2px dashed {COLORS['primary']};
        text-align: center;
        margin: 1rem 0;
    }}
    
    .sku-config-section {{
        background-color: white;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid {COLORS['secondary']};
        margin: 1rem 0;
    }}
    
    .results-section {{
        background-color: white;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid {COLORS['success']};
        margin: 1rem 0;
    }}
    
    .metric-card {{
        background-color: {COLORS['background']};
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        margin: 0.5rem 0;
    }}
    
    .download-button {{
        background-color: {COLORS['success']};
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 5px;
        font-weight: bold;
        cursor: pointer;
        width: 100%;
    }}
    
    .error-message {{
        color: {COLORS['accent']};
        background-color: #ffeaea;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid {COLORS['accent']};
    }}
    
    .success-message {{
        color: {COLORS['success']};
        background-color: #e8f5e8;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid {COLORS['success']};
    }}
    </style>
    """, unsafe_allow_html=True)


def validate_uploaded_file(uploaded_file):
    """Validate uploaded file"""
    if uploaded_file is None:
        return False, "No file uploaded"
    
    # Check file size
    if uploaded_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
        return False, f"File too large. Maximum size is {MAX_FILE_SIZE_MB}MB"
    
    # Check file extension
    file_extension = uploaded_file.name.split('.')[-1].lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        return False, f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
    
    return True, "File is valid"


def create_download_button(data, filename):
    """Create a download button for JSON data"""
    json_string = json.dumps(data, indent=2)
    st.download_button(
        label="📥 Download Detection Results (JSON)",
        data=json_string,
        file_name=filename,
        mime="application/json",
        use_container_width=True
    )


def display_detection_results(results):
    """Display detection results in a formatted way"""
    if "error" in results:
        st.markdown(f'<div class="error-message">❌ {results["error"]}</div>', 
                   unsafe_allow_html=True)
        return
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Total Items Detected", 
            results.get("total_items_detected", 0)
        )
    
    with col2:
        st.metric(
            "Analysis Time", 
            results.get("analysis_timestamp", "N/A")[:19].replace("T", " ")
        )
    
    with col3:
        st.metric(
            "Detection Status",
            "✅ Complete" if results.get("detected_items") else "❌ No Items"
        )
    
    # Detailed results
    if results.get("detected_items"):
        st.subheader("📋 Detected Items")
        
        # Create DataFrame for better display
        items_data = []
        for item in results["detected_items"]:
            items_data.append({
                "Item Name": item.get("item_name", "Unknown"),
                "Quantity": item.get("quantity", 0),
                "Location": item.get("location", "Not specified"),
                "Confidence": item.get("confidence", "Unknown"),
                "Notes": item.get("notes", "")
            })
        
        df = pd.DataFrame(items_data)
        st.dataframe(df)
        
        # Individual item cards
        st.subheader("🔍 Item Details")
        for i, item in enumerate(results["detected_items"]):
            with st.expander(f"{item.get('item_name', 'Unknown Item')} - Qty: {item.get('quantity', 0)}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Location:** {item.get('location', 'Not specified')}")
                    st.write(f"**Confidence:** {item.get('confidence', 'Unknown')}")
                with col2:
                    st.write(f"**Notes:** {item.get('notes', 'No additional notes')}")
    else:
        st.info("No items detected in the image.")


def main():
    """Main application function"""
    setup_page_config()
    load_custom_css()
    
    # Header
    st.markdown(f'<h1 class="main-header">{APP_TITLE}</h1>', unsafe_allow_html=True)
    st.markdown(f'<p style="text-align: center; color: {COLORS["text"]}; font-size: 1.1em;">{APP_DESCRIPTION}</p>', 
                unsafe_allow_html=True)
    
    # Initialize session state
    if 'detection_results' not in st.session_state:
        st.session_state.detection_results = None
    if 'uploaded_image' not in st.session_state:
        st.session_state.uploaded_image = None
    if 'osa_data' not in st.session_state:
        st.session_state.osa_data = None
    if 'selected_date' not in st.session_state:
        st.session_state.selected_date = None
    if 'selected_display_id' not in st.session_state:
        st.session_state.selected_display_id = None
    if 'all_osa_data' not in st.session_state:
        st.session_state.all_osa_data = None
    if 'available_display_ids' not in st.session_state:
        st.session_state.available_display_ids = []
    if 'available_dates' not in st.session_state:
        st.session_state.available_dates = []
    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False
    if 'history_runs' not in st.session_state:
        st.session_state.history_runs = []
    if 'history_index' not in st.session_state:
        st.session_state.history_index = 0
    if 'history_loaded_for' not in st.session_state:
        st.session_state.history_loaded_for = None
    if 'last_analyzed_image_url' not in st.session_state:
        st.session_state.last_analyzed_image_url = None
    if 'last_save_signature' not in st.session_state:
        st.session_state.last_save_signature = None
    if 'app_mode' not in st.session_state:
        st.session_state.app_mode = "Perform Analysis"

    # Mode selection
    st.markdown("---")
    st.subheader("Mode")
    st.session_state.app_mode = st.radio(
        "Choose what you want to do:",
        ["Perform Analysis", "View History"],
        horizontal=True,
    )
    
    
    # Load available DisplayIDs and Dates only for analysis mode
    if st.session_state.app_mode == "Perform Analysis":
        if not st.session_state.data_loaded:
            st.info("⏳ Loading available dates and display IDs from API...")
            with st.spinner("Fetching data from API..."):
                all_data, error = fetch_all_osa_data()
                if error:
                    st.error(f"❌ Failed to load data: {error}")
                    st.warning("⚠️ Using fallback data...")
                    # Fallback to default values
                    st.session_state.available_dates = get_last_10_days()
                    st.session_state.available_display_ids = ['ACH187', 'ACH190', 'ACH186', 'ACH191', 'ACH192', 'ACH189', 'ACH188']
                else:
                    st.session_state.all_osa_data = all_data
                    st.session_state.available_display_ids = get_unique_display_ids(all_data)
                    st.session_state.available_dates = get_unique_dates(all_data)
                    st.success(f"✅ Loaded {len(st.session_state.available_display_ids)} display IDs and {len(st.session_state.available_dates)} dates")
                st.session_state.data_loaded = True
                st.rerun()
    
    # If in History mode, render history dashboard and return
    if st.session_state.app_mode == "View History":
        st.subheader("🕘 Analysis History Dashboard")
        st.markdown("Use filters to narrow results, or view all recent runs.")

        filter_col1, filter_col2, filter_col3 = st.columns([2, 2, 1])

        with filter_col1:
            date_filter = st.text_input("Filter by Date (YYYY-MM-DD)", value="")
        with filter_col2:
            display_filter = st.text_input("Filter by Display ID", value="")
        with filter_col3:
            if st.button("📥 Load History", use_container_width=True):
                runs, err = fetch_runs(
                    date_str=(date_filter or None),
                    display_id=(display_filter or None),
                    limit=200,
                )
                if err:
                    st.error(f"Failed to load history: {err}")
                else:
                    st.session_state.history_runs = runs
                    st.session_state.history_index = 0
                    st.session_state.history_loaded_for = (date_filter or None, display_filter or None)

        # Auto-load if nothing loaded yet
        if not st.session_state.history_runs:
            runs, _ = fetch_runs(limit=100)
            st.session_state.history_runs = runs
            st.session_state.history_index = 0
            st.session_state.history_loaded_for = (None, None)

        runs = st.session_state.history_runs or []
        if runs:
            # Build a dataframe-like list
            table_rows = []
            for r in runs:
                gt = r.get("ground_truth_skus") or []
                pred = r.get("predicted_skus") or []
                if not pred and isinstance(r.get("raw_detection"), dict):
                    pred = get_predicted_skus_from_results(r.get("raw_detection") or {})
                metrics_obj = r.get("metrics") or {}
                if isinstance(metrics_obj, dict) and isinstance(metrics_obj.get("false_positives"), list):
                    fp_count = len(metrics_obj.get("false_positives") or [])
                else:
                    fp_count = len(list(set(pred) - set(gt)))
                img_url = r.get("image_url") or ""

                table_rows.append({
                    "Date": r.get("date"),
                    "Display ID": r.get("display_id"),
                    "Accuracy": r.get("accuracy"),
                    "Ground Truth (OSA=1)": len(gt),
                    "Predicted SKUs": len(pred),
                    "False Positives": fp_count,
                    "Image URL": img_url,
                    "Created At": r.get("created_at"),
                })
            df = pd.DataFrame(table_rows)
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Image URL": st.column_config.LinkColumn(
                        "Image URL",
                        help="Open the saved display image in a new tab",
                        display_text="Open Image",
                    )
                },
            )

            st.markdown("---")
            st.subheader("Details")
            nav_cols = st.columns([1, 1, 3])
            with nav_cols[0]:
                prev_disabled = st.session_state.history_index >= len(runs) - 1
                if st.button("⬅️ Previous", disabled=prev_disabled, use_container_width=True):
                    st.session_state.history_index = min(st.session_state.history_index + 1, len(runs) - 1)
            with nav_cols[1]:
                next_disabled = st.session_state.history_index <= 0
                if st.button("Next ➡️", disabled=next_disabled, use_container_width=True):
                    st.session_state.history_index = max(st.session_state.history_index - 1, 0)

            idx = st.session_state.history_index
            cur = runs[idx]
            st.info(f"Showing run {len(runs) - idx} of {len(runs)} (newest first) • {cur.get('created_at','')}")

            run_ground = cur.get("ground_truth_skus") or []
            run_pred = cur.get("predicted_skus") or []
            if not run_pred and isinstance(cur.get("raw_detection"), dict):
                run_pred = get_predicted_skus_from_results(cur.get("raw_detection") or {})
            run_metrics = cur.get("metrics") or calculate_accuracy_metrics(run_ground, run_pred)

            display_accuracy_metrics(run_metrics, st.session_state.osa_data)

            st.subheader("🔍 AI Predictions (from history)")
            if run_pred:
                st.write(f"**Detected {len(run_pred)} SKUs:**")
                for i, sku in enumerate(run_pred, 1):
                    if sku in run_ground:
                        st.success(f"✅ {i}. {sku}")
                    else:
                        st.error(f"❌ {i}. {sku}")
            else:
                st.info("No SKUs detected in this historical run")

            raw_det = cur.get("raw_detection") or {}
            if raw_det:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"osa_analysis_history_{cur.get('date','')}_{cur.get('display_id','')}_{timestamp}.json"
                create_download_button(raw_det, filename)
        else:
            st.info("No history runs found.")

        # Stop further rendering when in history mode
        return
    
    # Show data statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Available Display IDs", len(st.session_state.available_display_ids))
    with col2:
        st.metric("Available Dates", len(st.session_state.available_dates))
    with col3:
        if st.button("🔄 Refresh Data"):
            st.session_state.data_loaded = False
            st.rerun()
    
    st.markdown("---")
    
    # Date and Display ID selection
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        if st.session_state.available_dates:
            date_options = [d['display'] for d in st.session_state.available_dates]
            date_values = [d['date'] for d in st.session_state.available_dates]
            
            selected_date_index = st.selectbox(
                "Select Date:",
                range(len(date_options)),
                format_func=lambda x: date_options[x],
                help=f"Select from {len(date_options)} available dates"
            )
            selected_date = date_values[selected_date_index]
        else:
            st.error("No dates available")
            selected_date = None
    
    with col2:
        if st.session_state.available_display_ids:
            selected_display_id = st.selectbox(
                "Select Display ID:",
                st.session_state.available_display_ids,
                help=f"Select from {len(st.session_state.available_display_ids)} available display IDs"
            )
        else:
            st.error("No display IDs available")
            selected_display_id = None
    
    with col3:
        st.write("")  # Spacer
        st.write("")  # Spacer
        if st.button("🔍 Fetch Images", type="primary", disabled=(not selected_date or not selected_display_id)):
            with st.spinner("Fetching images from API..."):
                data, error = fetch_osa_images(selected_date, selected_display_id)
                if error:
                    st.error(f"❌ {error}")
                    st.session_state.osa_data = None
                else:
                    st.session_state.osa_data = data
                    st.session_state.selected_date = selected_date
                    st.session_state.selected_display_id = selected_display_id
                    st.success(f"✅ Found {len(data)} items for {selected_date} - {selected_display_id}")
    
    # Main analysis interface
    if st.session_state.osa_data:
        st.markdown("---")
        
        # Create two main columns: left for images and data, right for predictions
        left_col, right_col = st.columns([3, 2])
        
        with left_col:
            # Display OSA images
            display_osa_images(st.session_state.osa_data)
            
            # Ground truth and available SKUs section
            st.markdown("---")
            st.subheader("📋 SKU Information")
            
            # Get ground truth and all SKUs
            ground_truth_skus = get_ground_truth_skus(st.session_state.osa_data)
            all_skus = get_unique_skus_from_api_data(st.session_state.osa_data)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Ground Truth SKUs (OSA=1):**")
                st.info(f"Total: {len(ground_truth_skus)} SKUs")
                
                if ground_truth_skus:
                    with st.expander("📋 View Ground Truth SKUs"):
                        for i, sku in enumerate(ground_truth_skus, 1):
                            st.write(f"{i}. {sku}")
                else:
                    st.warning("No ground truth SKUs found (OSA=1)")
            
            with col2:
                st.write("**All Available SKUs:**")
                st.info(f"Total: {len(all_skus)} SKUs")
                
                if all_skus:
                    with st.expander("📋 View All SKUs"):
                        for i, sku in enumerate(all_skus, 1):
                            osa_status = "✅" if sku in ground_truth_skus else "❌"
                            st.write(f"{i}. {sku} {osa_status}")
        
        with right_col:
            st.subheader("🤖 AI Prediction Analysis")
            st.info("ℹ️ AI analysis uses only Ground Truth SKUs (OSA=1) for detection. ShelfNo and FacingTouching are provided as guidance to improve recognition.")
            
            # Analysis button
            if st.button("🔍 Analyze Display Images", type="primary", use_container_width=True):
                if ground_truth_skus:
                    with st.spinner("Analyzing display images... This may take a few moments."):
                        try:
                            # Use the first display image for analysis
                            image_groups = {}
                            for item in st.session_state.osa_data:
                                after_image = item.get('AfterImagePath') or item.get('AfterImagePath'.lower()) or ''
                                if after_image and after_image not in image_groups:
                                    image_groups[after_image] = []
                                if after_image:
                                    image_groups[after_image].append(item)
                            
                            if image_groups:
                                # Get the first image URL and its items
                                first_image_url = list(image_groups.keys())[0]
                                first_image_items = image_groups[first_image_url]
                                
                                # Download and convert image for analysis
                                response = requests.get(first_image_url)
                                response.raise_for_status()
                                image = Image.open(BytesIO(response.content))
                                
                                # Build rich ground truth items for this image only (OSA=1).
                                # Preserve duplicates across shelves/placements.
                                rich_items = []
                                gt_set = set(ground_truth_skus)
                                for it in first_image_items:
                                    sku_name = it.get('SKU')
                                    if sku_name in gt_set:
                                        rich_items.append({
                                            'SKU': sku_name,
                                            'ShelfNo': it.get('ShelfNo') or it.get('shelfno') or it.get('shelfNo'),
                                            'FacingTouching': it.get('FacingTouching') or it.get('facingtouching') or it.get('Facing') or it.get('facing')
                                        })

                                # Fallback 1: if no rich items for the selected image, use all OSA=1 items across the display (preserve duplicates)
                                if not rich_items:
                                    for it in st.session_state.osa_data:
                                        sku_name = it.get('SKU')
                                        if sku_name in gt_set:
                                            rich_items.append({
                                                'SKU': sku_name,
                                                'ShelfNo': it.get('ShelfNo') or it.get('shelfno') or it.get('shelfNo'),
                                                'FacingTouching': it.get('FacingTouching') or it.get('facingtouching') or it.get('Facing') or it.get('facing')
                                            })

                                # Fallback 2: if still empty, send name-only duplicates (preserve occurrences)
                                to_detect = rich_items if rich_items else [it.get('SKU') for it in st.session_state.osa_data if it.get('SKU') in gt_set]

                                detector = GeminiProductDetector()
                                results = detector.detect_products(image, to_detect)
                                st.session_state.detection_results = results
                                st.session_state.last_analyzed_image_url = first_image_url
                                st.success("✅ Analysis complete!")
                            else:
                                st.error("No display images found to analyze")
                        except Exception as e:
                            st.error(f"❌ Analysis failed: {str(e)}")
                else:
                    st.warning("No ground truth SKUs found (OSA=1) to analyze")
            
            # Display prediction results and accuracy metrics
            if st.session_state.detection_results:
                st.markdown("---")
                
                # Get predictions and calculate accuracy
                predicted_skus = get_predicted_skus_from_results(st.session_state.detection_results)
                
                if ground_truth_skus:
                    # Calculate and display accuracy metrics
                    metrics = calculate_accuracy_metrics(ground_truth_skus, predicted_skus)
                    display_accuracy_metrics(metrics, st.session_state.osa_data)
                    # Persist run to Supabase (guard against rerun duplicates)
                    try:
                        import hashlib
                        sig_obj = {
                            "date": st.session_state.selected_date,
                            "display": st.session_state.selected_display_id,
                            "results": st.session_state.detection_results,
                        }
                        sig_str = json.dumps(sig_obj, sort_keys=True, default=str)
                        signature = hashlib.sha256(sig_str.encode("utf-8")).hexdigest()
                        if st.session_state.last_save_signature != signature:
                            ok, err = save_osa_run(
                                date_str=st.session_state.selected_date or "",
                                display_id=st.session_state.selected_display_id or "",
                                ground_truth_skus=ground_truth_skus,
                                predicted_skus=predicted_skus,
                                accuracy_metrics=metrics,
                                raw_detection=st.session_state.detection_results,
                                image_url=st.session_state.last_analyzed_image_url,
                            )
                            if ok:
                                st.session_state.last_save_signature = signature
                                st.caption("💾 Saved analysis to history")
                            else:
                                st.caption(f"⚠️ Could not save to history: {err}")
                    except Exception as e:
                        st.caption(f"⚠️ History save error: {str(e)}")
                    
                    st.markdown("---")
                
                # Display simplified prediction results
                st.subheader("🔍 AI Predictions")
                
                if predicted_skus:
                    st.write(f"**Detected {len(predicted_skus)} SKUs:**")
                    
                    # Color code predictions based on ground truth
                    for i, sku in enumerate(predicted_skus, 1):
                        if sku in ground_truth_skus:
                            st.success(f"✅ {i}. {sku}")
                        else:
                            st.error(f"❌ {i}. {sku}")
                else:
                    st.info("No SKUs detected in the image")
                
                # Download button supports both minimal and legacy shapes
                if st.session_state.detection_results.get("sku_names") or st.session_state.detection_results.get("detected_items"):
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"osa_analysis_{st.session_state.selected_date}_{st.session_state.selected_display_id}_{timestamp}.json"
                    create_download_button(st.session_state.detection_results, filename)

                # History viewer moved to dedicated View History mode
    
    # Footer
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col2:
        st.markdown(
            f'<p style="text-align: center; color: {COLORS["text"]}; font-size: 0.9em;">'
            f'Powered by Google Gemini 2.5 Pro | Built with Streamlit</p>', 
            unsafe_allow_html=True
        )


if __name__ == "__main__":
    main()