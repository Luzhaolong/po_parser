"""
Streamlit App for STEP File Volume Calculator
Upload STEP files and calculate volumes and weights
"""

import streamlit as st
import pandas as pd
import tempfile
import os
from pathlib import Path

from OCP.STEPControl import STEPControl_Reader
from OCP.IFSelect import IFSelect_ReturnStatus
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib


def calculate_volume_from_step(step_file_path):
    """Calculate the volume of a 3D model from a STEP file."""
    step_file_path = str(step_file_path)
    
    if not os.path.exists(step_file_path):
        raise FileNotFoundError(f"STEP file not found: {step_file_path}")
    
    reader = STEPControl_Reader()
    status = reader.ReadFile(step_file_path)
    
    if status != IFSelect_ReturnStatus.IFSelect_RetDone:
        raise ValueError(f"Error reading STEP file: {step_file_path}")
    
    reader.TransferRoots()
    shape = reader.OneShape()
    
    if shape.IsNull():
        raise ValueError("No valid shape found in STEP file")
    
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, props)
    
    return props.Mass()


def calculate_bounding_box_volume_from_step(step_file_path):
    """Calculate the bounding box volume (x × y × z) from a STEP file."""
    step_file_path = str(step_file_path)
    
    if not os.path.exists(step_file_path):
        raise FileNotFoundError(f"STEP file not found: {step_file_path}")
    
    reader = STEPControl_Reader()
    status = reader.ReadFile(step_file_path)
    
    if status != IFSelect_ReturnStatus.IFSelect_RetDone:
        raise ValueError(f"Error reading STEP file: {step_file_path}")
    
    reader.TransferRoots()
    shape = reader.OneShape()
    
    if shape.IsNull():
        raise ValueError("No valid shape found in STEP file")
    
    bbox = Bnd_Box()
    BRepBndLib.Add_s(shape, bbox)
    
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
    
    x_dimension = xmax - xmin
    y_dimension = ymax - ymin
    z_dimension = zmax - zmin
    
    bbox_volume = x_dimension * y_dimension * z_dimension
    
    return {
        'x_dimension': x_dimension,
        'y_dimension': y_dimension,
        'z_dimension': z_dimension,
        'bounding_box_volume': bbox_volume
    }


# Common material densities (g/cm³)
MATERIAL_DENSITIES = {
    'aluminum': 2.70,
    'steel': 7.85,
    'stainless_steel': 8.00,
    'brass': 8.50,
    'copper': 8.96,
    'titanium': 4.51,
    'cast_iron': 7.20,
    'bronze': 8.80,
    'zinc': 7.14,
    'magnesium': 1.74,
}


def process_step_file(step_file_path, material='steel'):
    """
    Complete workflow: Read STEP file and calculate volumes.
    Returns a pandas DataFrame with columns: x, y, z, BV/5000, SV, density, max_internal_or_weight
    """
    try:
        step_file_path = str(step_file_path)
        
        # Calculate actual volume (SV - Solid Volume)
        actual_volume_mm3 = calculate_volume_from_step(step_file_path)
        sv_cm3 = actual_volume_mm3 / 1000.0  # Convert to cm³
        
        # Calculate bounding box volume
        bbox_info = calculate_bounding_box_volume_from_step(step_file_path)
        bbox_volume_mm3 = bbox_info['bounding_box_volume']
        
        # Get dimensions
        x = bbox_info['x_dimension']
        y = bbox_info['y_dimension']
        z = bbox_info['z_dimension']
        
        # Calculate BV/5000 (internal box volume)
        bv_5000 = bbox_volume_mm3 / 5000000  # Convert to cm³ and divide by 5000
        
        # Get material density
        if isinstance(material, str):
            density = MATERIAL_DENSITIES.get(material.lower(), MATERIAL_DENSITIES['steel'])
        else:
            density = material
        
        # Calculate actual weight in kg (SV * density)
        actual_weight_kg = sv_cm3 * density / 1000.0
        
        # Calculate max(internal_box_v, actual_weight_kg)
        max_value = max(bv_5000, actual_weight_kg)
        
        # Create DataFrame
        df = pd.DataFrame({
            'x': [x],
            'y': [y],
            'z': [z],
            'BV/5000': [bv_5000],
            'SV': [sv_cm3],
            'density': [density],
            'SV_weight_kg': [actual_weight_kg],
            'max_internal_or_weight': [max_value]
        })
        
        return df
    
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None


def process_multiple_step_files(step_file_paths, material='steel'):
    """Process multiple STEP files and combine results into a single table."""
    results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, file_path in enumerate(step_file_paths):
        status_text.text(f"Processing file {idx + 1}/{len(step_file_paths)}: {Path(file_path).name}")
        df = process_step_file(file_path, material)
        if df is not None:
            df.insert(0, 'filename', Path(file_path).name)
            results.append(df)
        progress_bar.progress((idx + 1) / len(step_file_paths))
    
    status_text.empty()
    progress_bar.empty()
    
    if results:
        return pd.concat(results, ignore_index=True)
    else:
        return pd.DataFrame(columns=['filename', 'x', 'y', 'z', 'BV/5000', 'SV', 'density', 'SV_weight_kg', 'max_internal_or_weight'])

