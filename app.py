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
    DEFAULT_SKU_ITEMS,
    MAX_FILE_SIZE_MB,
    ALLOWED_EXTENSIONS
)
from gemini_client import GeminiProductDetector, create_sample_detection_result

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
    """Extract predicted SKUs from Gemini detection results"""
    if not detection_results or 'detected_items' not in detection_results:
        return []
    
    predicted_skus = set()
    for item in detection_results['detected_items']:
        if 'item_name' in item and item['item_name']:
            predicted_skus.add(item['item_name'])
    
    return sorted(list(predicted_skus))


def get_sku_image_url(sku_name, api_data):
    """Get the image URL for a specific SKU from API data"""
    if not api_data or not sku_name:
        return None
    
    for item in api_data:
        if item.get('SKU') == sku_name and item.get('SKUImage'):
            return item['SKUImage']
    
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


def initialize_sku_session_state():
    """Initialize session state for SKU management"""
    if 'custom_sku_items' not in st.session_state:
        st.session_state.custom_sku_items = DEFAULT_SKU_ITEMS.copy()
    if 'sku_edit_mode' not in st.session_state:
        st.session_state.sku_edit_mode = False
    if 'sku_edit_index' not in st.session_state:
        st.session_state.sku_edit_index = None


def add_sku_item(new_item):
    """Add a new SKU item to the list"""
    if new_item.strip() and new_item.strip() not in st.session_state.custom_sku_items:
        st.session_state.custom_sku_items.append(new_item.strip())
        return True
    return False


def edit_sku_item(index, updated_item):
    """Edit an existing SKU item"""
    if 0 <= index < len(st.session_state.custom_sku_items) and updated_item.strip():
        st.session_state.custom_sku_items[index] = updated_item.strip()
        return True
    return False


def delete_sku_item(index):
    """Delete a SKU item from the list"""
    if 0 <= index < len(st.session_state.custom_sku_items):
        del st.session_state.custom_sku_items[index]
        return True
    return False


def export_sku_list():
    """Export SKU list as JSON"""
    sku_data = {
        "sku_items": st.session_state.custom_sku_items,
        "total_items": len(st.session_state.custom_sku_items),
        "export_timestamp": datetime.now().isoformat()
    }
    return json.dumps(sku_data, indent=2)


def import_sku_list(uploaded_file):
    """Import SKU list from JSON file"""
    try:
        sku_data = json.load(uploaded_file)
        if "sku_items" in sku_data and isinstance(sku_data["sku_items"], list):
            st.session_state.custom_sku_items = sku_data["sku_items"]
            return True, f"Successfully imported {len(sku_data['sku_items'])} SKU items"
        else:
            return False, "Invalid JSON format. Expected 'sku_items' key with list of items."
    except json.JSONDecodeError:
        return False, "Invalid JSON file format."
    except Exception as e:
        return False, f"Error importing file: {str(e)}"


def render_sku_management():
    """Render the SKU management interface"""
    st.subheader("📦 SKU Items Management")
    
    # Tab selection
    tab1, tab2, tab3 = st.tabs(["📋 View & Edit", "➕ Add Items", "📁 Import/Export"])
    
    with tab1:
        st.write("**Current SKU Items:**")
        
        if not st.session_state.custom_sku_items:
            st.info("No SKU items configured. Add some items to get started!")
        else:
            # Search functionality
            search_term = st.text_input("🔍 Search SKU items:", placeholder="Type to filter items...")
            
            # Filter items based on search
            filtered_items = []
            for i, item in enumerate(st.session_state.custom_sku_items):
                if not search_term or search_term.lower() in item.lower():
                    filtered_items.append((i, item))
            
            st.write(f"Showing {len(filtered_items)} of {len(st.session_state.custom_sku_items)} items")
            
            # Display items with edit/delete options
            for original_index, item in filtered_items:
                col1, col2, col3, col4 = st.columns([6, 1, 1, 1])
                
                with col1:
                    if st.session_state.sku_edit_mode and st.session_state.sku_edit_index == original_index:
                        # Edit mode
                        edited_item = st.text_input(
                            f"Edit item {original_index + 1}:",
                            value=item,
                            key=f"edit_item_{original_index}",
                            label_visibility="collapsed"
                        )
                    else:
                        # Display mode
                        st.write(f"{original_index + 1}. {item}")
                
                with col2:
                    if st.session_state.sku_edit_mode and st.session_state.sku_edit_index == original_index:
                        # Save button
                        if st.button("💾", key=f"save_{original_index}", help="Save changes"):
                            edited_item = st.session_state[f"edit_item_{original_index}"]
                            if edit_sku_item(original_index, edited_item):
                                st.session_state.sku_edit_mode = False
                                st.session_state.sku_edit_index = None
                                st.success("Item updated!")
                                st.rerun()
                            else:
                                st.error("Failed to update item!")
                    else:
                        # Edit button
                        if st.button("✏️", key=f"edit_{original_index}", help="Edit item"):
                            st.session_state.sku_edit_mode = True
                            st.session_state.sku_edit_index = original_index
                            st.rerun()
                
                with col3:
                    if st.session_state.sku_edit_mode and st.session_state.sku_edit_index == original_index:
                        # Cancel button
                        if st.button("❌", key=f"cancel_{original_index}", help="Cancel editing"):
                            st.session_state.sku_edit_mode = False
                            st.session_state.sku_edit_index = None
                            st.rerun()
                    else:
                        # Delete button
                        if st.button("🗑️", key=f"delete_{original_index}", help="Delete item"):
                            if delete_sku_item(original_index):
                                st.success("Item deleted!")
                                st.rerun()
                            else:
                                st.error("Failed to delete item!")
            
            # Bulk operations
            st.write("**Bulk Operations:**")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🔄 Reset to Default", help="Reset to default SKU items"):
                    st.session_state.custom_sku_items = DEFAULT_SKU_ITEMS.copy()
                    st.session_state.sku_edit_mode = False
                    st.session_state.sku_edit_index = None
                    st.success("Reset to default SKU items!")
                    st.rerun()
            
            with col2:
                if st.button("🗑️ Clear All", help="Remove all SKU items"):
                    st.session_state.custom_sku_items = []
                    st.session_state.sku_edit_mode = False
                    st.session_state.sku_edit_index = None
                    st.success("All items cleared!")
                    st.rerun()
            
            with col3:
                if st.button("🔀 Sort A-Z", help="Sort items alphabetically"):
                    st.session_state.custom_sku_items.sort()
                    st.success("Items sorted alphabetically!")
                    st.rerun()
    
    with tab2:
        st.write("**Add New SKU Items:**")
        
        # Single item addition
        new_item = st.text_input("Enter new SKU item:", placeholder="Type SKU item name...")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ Add Item", type="primary", use_container_width=True):
                if add_sku_item(new_item):
                    st.success(f"Added: {new_item}")
                    st.rerun()
                elif not new_item.strip():
                    st.error("Please enter a valid SKU item!")
                else:
                    st.error("Item already exists!")
        
        with col2:
            if st.button("➕ Add & Clear", use_container_width=True):
                if add_sku_item(new_item):
                    st.success(f"Added: {new_item}")
                    # Clear the input by rerunning
                    st.rerun()
                elif not new_item.strip():
                    st.error("Please enter a valid SKU item!")
                else:
                    st.error("Item already exists!")
        
        st.divider()
        
        # Bulk addition
        st.write("**Bulk Add Items:**")
        bulk_items = st.text_area(
            "Enter multiple SKU items (one per line):",
            height=150,
            placeholder="Item 1\nItem 2\nItem 3\n..."
        )
        
        if st.button("➕ Add All Items", type="primary"):
            if bulk_items.strip():
                items_to_add = [item.strip() for item in bulk_items.split('\n') if item.strip()]
                added_count = 0
                duplicate_count = 0
                
                for item in items_to_add:
                    if add_sku_item(item):
                        added_count += 1
                    else:
                        duplicate_count += 1
                
                if added_count > 0:
                    st.success(f"Added {added_count} new items!")
                if duplicate_count > 0:
                    st.warning(f"{duplicate_count} items were duplicates and skipped.")
                
                if added_count > 0:
                    st.rerun()
            else:
                st.error("Please enter at least one item!")
    
    with tab3:
        st.write("**Export SKU List:**")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total SKU Items", len(st.session_state.custom_sku_items))
        with col2:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sku_items_{timestamp}.json"
            st.download_button(
                label="📥 Download SKU List",
                data=export_sku_list(),
                file_name=filename,
                mime="application/json",
                use_container_width=True
            )
        
        st.divider()
        
        st.write("**Import SKU List:**")
        uploaded_sku_file = st.file_uploader(
            "Choose a JSON file with SKU items:",
            type=['json'],
            help="Upload a JSON file containing SKU items"
        )
        
        if uploaded_sku_file is not None:
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📁 Replace Current List", type="primary"):
                    success, message = import_sku_list(uploaded_sku_file)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
            
            with col2:
                if st.button("📁 Merge with Current List"):
                    # Save current list
                    current_items = st.session_state.custom_sku_items.copy()
                    
                    success, message = import_sku_list(uploaded_sku_file)
                    if success:
                        # Merge with existing items (avoid duplicates)
                        imported_items = st.session_state.custom_sku_items.copy()
                        st.session_state.custom_sku_items = current_items
                        
                        added_count = 0
                        for item in imported_items:
                            if add_sku_item(item):
                                added_count += 1
                        
                        st.success(f"Merged {added_count} new items with existing list!")
                        st.rerun()
                    else:
                        st.error(message)
        
        # Show sample JSON format
        with st.expander("📋 View Sample JSON Format"):
            sample_json = {
                "sku_items": [
                    "Sample Item 1",
                    "Sample Item 2", 
                    "Sample Item 3"
                ],
                "total_items": 3,
                "export_timestamp": "2024-01-01T12:00:00"
            }
            st.code(json.dumps(sample_json, indent=2), language="json")


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
        st.info("No items detected in the image. Try adjusting your SKU list or upload a different image.")


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
    
    # Initialize SKU management session state
    initialize_sku_session_state()
    
    # Load available DisplayIDs and Dates
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
    
    # OSA Image Analysis Interface
    st.subheader("📅 Select Date and Display ID")
    
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
            st.info("ℹ️ AI analysis uses only Ground Truth SKUs (OSA=1) for detection")
            
            # Analysis button
            if st.button("🔍 Analyze Display Images", type="primary", use_container_width=True):
                if ground_truth_skus:
                    with st.spinner("Analyzing display images... This may take a few moments."):
                        try:
                            # Use the first display image for analysis
                            image_groups = {}
                            for item in st.session_state.osa_data:
                                after_image = item.get('AfterImagePath', '')
                                if after_image and after_image not in image_groups:
                                    image_groups[after_image] = True
                                    break
                            
                            if image_groups:
                                # Get the first image URL
                                first_image_url = list(image_groups.keys())[0]
                                
                                # Download and convert image for analysis
                                response = requests.get(first_image_url)
                                response.raise_for_status()
                                image = Image.open(BytesIO(response.content))
                                
                                # Use only ground truth SKUs (OSA=1) for detection
                                detector = GeminiProductDetector()
                                results = detector.detect_products(image, ground_truth_skus)
                                st.session_state.detection_results = results
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
                
                # Download button
                if st.session_state.detection_results.get("detected_items"):
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"osa_analysis_{st.session_state.selected_date}_{st.session_state.selected_display_id}_{timestamp}.json"
                    create_download_button(st.session_state.detection_results, filename)
    
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