import os
import streamlit as st # type: ignore
from weight_calc import process_step_file, MATERIAL_DENSITIES

import pandas as pd
import tempfile
import os
from pathlib import Path
st.set_page_config(page_title="STEP File Volume Calculator", page_icon="📐", layout="wide")
    
st.title("📐 STEP File Volume Calculator")
st.markdown("Upload STEP files to calculate volumes, weights, and dimensions for metal parts")
    
    # File uploader
uploaded_files = st.file_uploader(
        "Upload STEP Files (.step, .stp)",
        type=['step', 'stp'],
        accept_multiple_files=True
    )
    
if uploaded_files:
        st.success(f"✅ {len(uploaded_files)} file(s) uploaded")
        
        # Create material selection for each file
        st.subheader("Configure Material for Each File")
        
        # Initialize session state for densities if not exists
        if 'file_densities' not in st.session_state:
            st.session_state.file_densities = {}
        
        file_configs = []
        
        for idx, uploaded_file in enumerate(uploaded_files):
            with st.expander(f"📄 {uploaded_file.name}", expanded=True):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    material_key = f"material_{idx}_{uploaded_file.name}"
                    material_option = st.selectbox(
                        "Select Material",
                        options=list(MATERIAL_DENSITIES.keys()) + ['custom'],
                        format_func=lambda x: x.replace('_', ' ').title(),
                        key=material_key,
                        index=1  # Default to steel
                    )
                
                with col2:
                    if material_option == 'custom':
                        density_key = f"density_{idx}_{uploaded_file.name}"
                        density = st.number_input(
                            "Density (g/cm³)",
                            min_value=0.1,
                            max_value=25.0,
                            value=7.85,
                            step=0.01,
                            key=density_key
                        )
                    else:
                        density = MATERIAL_DENSITIES[material_option]
                        st.metric("Density (g/cm³)", f"{density}")
                
                file_configs.append({
                    'file': uploaded_file,
                    'density': density,
                    'material': material_option
                })
        
        st.divider()
        
        if st.button("🔄 Process All Files", type="primary"):
            temp_paths = []
            
            # Save uploaded files to temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                for config in file_configs:
                    temp_path = os.path.join(temp_dir, config['file'].name)
                    with open(temp_path, 'wb') as f:
                        f.write(config['file'].getbuffer())
                    temp_paths.append(temp_path)
                
                # Process files with individual densities
                results = []
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for idx, (temp_path, config) in enumerate(zip(temp_paths, file_configs)):
                    status_text.text(f"Processing file {idx + 1}/{len(temp_paths)}: {config['file'].name}")
                    df = process_step_file(temp_path, config['density'])
                    if df is not None:
                        df.insert(0, 'filename', config['file'].name)
                        df['material'] = config['material'] if config['material'] != 'custom' else 'custom'
                        results.append(df)
                    progress_bar.progress((idx + 1) / len(temp_paths))
                
                status_text.empty()
                progress_bar.empty()
                
                if results:
                    results_df = pd.concat(results, ignore_index=True)
                    
                    st.success("✅ Processing complete!")
                    
                    # Display results
                    st.subheader("Results")
                    
                    # Format the dataframe for better display
                    display_df = results_df.copy()
                    for col in ['x', 'y', 'z', 'BV/5000', 'SV', 'SV_weight_kg', 'max_internal_or_weight']:
                        if col in display_df.columns:
                            display_df[col] = display_df[col].round(4)
                    
                    st.dataframe(display_df, use_container_width=True)
                    
                    # Summary statistics
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Files", len(results_df))
                    with col2:
                        st.metric("Total SV (cm³)", f"{results_df['SV'].sum():.2f}")
                    with col3:
                        st.metric("Total Weight (kg)", f"{results_df['SV_weight_kg'].sum():.2f}")
                    with col4:
                        st.metric("Avg Max Value", f"{results_df['max_internal_or_weight'].mean():.4f}")
                    
                    # Download button
                    csv = results_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Results as CSV",
                        data=csv,
                        file_name="step_volume_results.csv",
                        mime="text/csv"
                    )
                else:
                    st.error("❌ No results generated. Please check your files.")
    
else:
        st.info("👆 Please upload STEP files to begin")
        
        # Display material densities reference
        with st.expander("📋 Material Densities Reference"):
            density_df = pd.DataFrame([
                {'Material': k.replace('_', ' ').title(), 'Density (g/cm³)': v}
                for k, v in MATERIAL_DENSITIES.items()
            ])
            st.table(density_df)