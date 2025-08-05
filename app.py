"""
Product Shelf Analysis Tool - Streamlit Application
"""

import streamlit as st
import json
from datetime import datetime
from PIL import Image
import pandas as pd
from io import BytesIO

from config import (
    APP_TITLE, 
    APP_DESCRIPTION, 
    COLORS, 
    DEFAULT_SKU_ITEMS,
    MAX_FILE_SIZE_MB,
    ALLOWED_EXTENSIONS
)
from gemini_client import GeminiProductDetector, create_sample_detection_result


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
    
    # Initialize SKU management session state
    initialize_sku_session_state()
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # SKU Items Configuration with Management
        sku_mode = st.radio(
            "📦 SKU Configuration Mode:",
            ["🎯 Quick Detection", "⚙️ Manage SKU Items"],
            help="Quick Detection: Use current list for detection\nManage SKU Items: Add, edit, delete SKU items"
        )
        
        if sku_mode == "🎯 Quick Detection":
            # Quick detection mode - show current list and allow usage
            st.write(f"**Current SKU Items:** {len(st.session_state.custom_sku_items)} items")
            
            # Quick preview of items
            with st.expander("📋 View Current SKU Items"):
                if st.session_state.custom_sku_items:
                    # Show first 10 items and count
                    display_items = st.session_state.custom_sku_items[:10]
                    for i, item in enumerate(display_items, 1):
                        st.write(f"{i}. {item}")
                    
                    if len(st.session_state.custom_sku_items) > 10:
                        st.write(f"... and {len(st.session_state.custom_sku_items) - 10} more items")
                else:
                    st.info("No SKU items configured. Switch to 'Manage SKU Items' to add some!")
            
            # Use session state SKU items for detection
            sku_items = st.session_state.custom_sku_items.copy()
            
            # Quick actions
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📥 Load Default"):
                    st.session_state.custom_sku_items = DEFAULT_SKU_ITEMS.copy()
                    st.success("Loaded default SKU items!")
                    st.rerun()
            with col2:
                if st.button("🔄 Refresh"):
                    st.rerun()
        
        else:
            # Management mode - full SKU management interface
            render_sku_management()
            sku_items = st.session_state.custom_sku_items.copy()
        
        # Additional options
        st.subheader("🔧 Detection Options")
        demo_mode = st.checkbox("Demo Mode (Use Sample Results)", value=False, 
                               help="Use sample detection results for testing")
    
    # Main content area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown('<div class="upload-section">', unsafe_allow_html=True)
        st.subheader("📸 Upload Product Shelf Image")
        
        uploaded_file = st.file_uploader(
            "Choose an image file",
            type=ALLOWED_EXTENSIONS,
            help=f"Maximum file size: {MAX_FILE_SIZE_MB}MB. Supported formats: {', '.join(ALLOWED_EXTENSIONS)}"
        )
        
        if uploaded_file is not None:
            # Validate file
            is_valid, message = validate_uploaded_file(uploaded_file)
            
            if is_valid:
                # Display uploaded image
                image = Image.open(uploaded_file)
                st.image(image, caption="Uploaded Image", width=600)
                st.session_state.uploaded_image = image
                
                # Analyze button
                if st.button("🔍 Analyze Product Shelf", type="primary", use_container_width=True):
                    with st.spinner("Analyzing image... This may take a few moments."):
                        if demo_mode:
                            # Use sample results for demo
                            st.session_state.detection_results = create_sample_detection_result()
                            st.success("✅ Analysis complete (Demo Mode)")
                        else:
                            try:
                                detector = GeminiProductDetector()
                                results = detector.detect_products(image, sku_items)
                                st.session_state.detection_results = results
                                st.success("✅ Analysis complete!")
                            except Exception as e:
                                st.error(f"❌ Analysis failed: {str(e)}")
            else:
                st.error(f"❌ {message}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        if st.session_state.detection_results:
            st.markdown('<div class="results-section">', unsafe_allow_html=True)
            st.subheader("📊 Detection Results")
            
            # Display results
            display_detection_results(st.session_state.detection_results)
            
            # Download button
            if st.session_state.detection_results.get("detected_items"):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"shelf_analysis_{timestamp}.json"
                create_download_button(st.session_state.detection_results, filename)
            
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("👆 Upload an image and click 'Analyze Product Shelf' to see results here.")
    
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