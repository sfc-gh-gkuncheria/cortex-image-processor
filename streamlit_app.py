import streamlit as st
from snowflake.snowpark.context import get_active_session
import tempfile
import os

# Page configuration
st.set_page_config(layout="wide", page_title="Image Analysis Dashboard")

# Enhanced Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stForm {
        padding: 2rem;
        background-color: #f8f9fa;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .upload-header {
        text-align: center;
        padding: 2rem;
        background: linear-gradient(120deg, #1e3799, #0c2461);
        color: white;
        border-radius: 15px;
        margin-bottom: 2rem;
    }
    .file-container {
        background-color: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        margin-bottom: 1rem;
    }
    .stAlert {
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

session = get_active_session()

# Header section with gradient background
st.markdown("""
    <div class='upload-header'>
        <h1>🖼️ Property Damage Analysis</h1>
        <p style='font-size: 1.2rem; opacity: 0.9;'>Upload images to analyze storm damage and get instant cost estimates</p>
    </div>
""", unsafe_allow_html=True)

# Main content in three columns
col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    st.info("""
    ### 📋 Guidelines
    1. Upload one or more images
    2. Review the previews
    3. Click analyze for AI insights
    """)

with col2:
    uploaded_files = st.file_uploader(
        "Drag and drop your images here",
        accept_multiple_files=True,
        type=['png', 'jpg', 'jpeg'],
        help="Multiple images can be analyzed simultaneously"
    )

with col3:
    st.success("""
    ### 📁 Supported Formats
    - PNG
    - JPG/JPEG
    
    Max size: 200MB per file
    """)

if uploaded_files:
    with st.form("upload_form", clear_on_submit=False):
        st.markdown("### 📸 Selected Images")
        
        # Create a grid for image previews
        cols = st.columns(3)
        for idx, file in enumerate(uploaded_files):
            with cols[idx % 3]:
                st.markdown(f"""
                    <div class='file-container'>
                        <p style='text-align: center; color: #666;'>{file.name}</p>
                    </div>
                """, unsafe_allow_html=True)
                st.image(file, use_container_width=True)
        
        # Define the submit buttons first
        col1, col2, col3, col4 = st.columns([1, 2, 2, 1])
        with col2:
            analyze_button = st.form_submit_button(
                "🔍 Analyze Images",
                use_container_width=True,
                help="Click to analyze individual images"
            )
        with col3:
            compare_button = st.form_submit_button(
                "🔄 Post-Repair Reimbursement",
                use_container_width=True,
                help="Click to compare before/after images"
            )

        
        if analyze_button or compare_button:
            try:
                session.sql("CREATE STAGE IF NOT EXISTS input_stage").collect()
                
                if analyze_button:
                    progress_bar = st.progress(0)
                    with tempfile.TemporaryDirectory() as temp_dir:
                        for idx, file in enumerate(uploaded_files):
                            progress = (idx + 1) / len(uploaded_files)
                            progress_bar.progress(progress)
                            
                            with st.expander(f"📊 Analysis Results: {file.name}", expanded=True):
                                temp_path = os.path.join(temp_dir, file.name)
                                with open(temp_path, "wb") as f:
                                    f.write(file.getbuffer())
                                
                                session.file.put(temp_path, "@input_stage", auto_compress=False)
                                
                                with st.spinner("AI is analyzing your image..."):
                                    analysis_query = f"""
                                    SELECT SNOWFLAKE.CORTEX.COMPLETE(
                                        'claude-3-5-sonnet',
                                        'Summarize the storm damage from this image in 100 words and then provide an estimate for how much it would cost to fix it',
                                        TO_FILE('@input_stage', '{file.name}')
                                    )
                                    """
                                    result = session.sql(analysis_query).collect()
                                    
                                    st.markdown("""
                                        <div style='background-color: white; padding: 1.5rem; border-radius: 10px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);'>
                                            <h4>Analysis Results</h4>
                                        </div>
                                    """, unsafe_allow_html=True)
                                    st.write(result[0][0])
                    
                    st.success("✅ Analysis complete!")
                
                elif compare_button:
                    if len(uploaded_files) != 2:
                        st.error("Please upload exactly 2 images for comparison (before and after)")
                    else:
                        with tempfile.TemporaryDirectory() as temp_dir:
                            # Upload both files to stage
                            file_paths = []
                            for file in uploaded_files:
                                temp_path = os.path.join(temp_dir, file.name)
                                with open(temp_path, "wb") as f:
                                    f.write(file.getbuffer())
                                session.file.put(temp_path, "@input_stage", auto_compress=False)
                                file_paths.append(file.name)
                            
                            with st.spinner("Comparing images..."):
                                comparison_query = f"""
                                SELECT SNOWFLAKE.CORTEX.COMPLETE(
                                    'claude-3-5-sonnet',
                                    PROMPT('Compare this image {{0}} to this image {{1}} and describe the repairs that have been performed, along with a cost estimate',
                                    TO_FILE('@input_stage', '{file_paths[0]}'),
                                    TO_FILE('@input_stage', '{file_paths[1]}')
                                ))
                                """
                                result = session.sql(comparison_query).collect()
                                
                                st.markdown("""
                                    <div style='background-color: white; padding: 1.5rem; border-radius: 10px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);'>
                                        <h4>Comparison Results</h4>
                                    </div>
                                """, unsafe_allow_html=True)
                                st.write(result[0][0])
                        
                        st.success("✅ Comparison complete!")
                        
            except Exception as e:
                st.error(f"❌ An error occurred: {str(e)}")
