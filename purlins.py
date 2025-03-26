import streamlit as st
import numpy as np
from utils.calculations import (
    convert_to_kn, calculate_moment, calculate_shear_force,
    calculate_deflection, select_optimal_section, calculate_wind_load, 
    calculate_critical_moment, KG_TO_KN
)
from utils.visualization import (
    plot_moment_diagram, plot_shear_force_diagram,
    plot_deflection_diagram, plot_section_profile,
    create_interactive_moment_diagram, create_interactive_results_chart
)
from utils.export import create_excel_download_link, create_pdf_download_link
from utils.constants import EGYPTIAN_STEEL_GRADES, AMERICAN_STEEL_GRADES, KG_TO_KN

# Set page configuration
st.set_page_config(
    page_title="Structo 🏗 - Purlin Design",
    page_icon="🏗",
    layout="wide"
)

# Initialize session state variables if they don't exist
if 'purlin_additional_loads' not in st.session_state:
    st.session_state.purlin_additional_loads = []
if 'purlin_calculate_clicked' not in st.session_state:
    st.session_state.purlin_calculate_clicked = False
if 'purlin_design_results' not in st.session_state:
    st.session_state.purlin_design_results = {}
if 'purlin_load_diagrams' not in st.session_state:
    st.session_state.purlin_load_diagrams = {}

# Function to add a new additional load
def add_load():
    st.session_state.purlin_additional_loads.append({
        'value': 0.0,
        'unit': 'kN',
        'case': 'Case A'
    })

# Function to remove a load
def remove_load(index):
    st.session_state.purlin_additional_loads.pop(index)

# Function to calculate results
def calculate_results():
    st.session_state.purlin_calculate_clicked = True
    
    # Get input values
    span = st.session_state.purlin_span
    dead_load = st.session_state.purlin_dead_load
    live_load = st.session_state.purlin_live_load
    is_accessible = st.session_state.purlin_is_accessible
    maintenance_load_kg = st.session_state.purlin_maintenance_load
    wind_load = st.session_state.purlin_wind_load
    chord_angle = st.session_state.purlin_chord_angle  # Using single chord angle parameter
    steel_grade = st.session_state.purlin_steel_grade
    design_code = st.session_state.purlin_design_code
    additional_loads = st.session_state.purlin_additional_loads
    
    # Convert maintenance load from kg to kN
    maintenance_load_kn = maintenance_load_kg * KG_TO_KN
    
    # Purlin spacing (assumed for calculation, in a real app this would be an input)
    purlin_spacing = 1.5  # meters
    
    # Calculate total loads (in kN/m)
    total_dead_load = dead_load  # kN/m (already linear)
    total_live_load = live_load  # kN/m (already linear)
    total_wind_load = calculate_wind_load(span, wind_load, purlin_spacing)  # kN/m
    
    # Note: Supported beam reaction feature was removed as requested
    
    # Process additional loads
    additional_load_total = 0
    for load in additional_loads:
        # Convert all loads to kN/m for simplicity
        load_value = convert_to_kn(load['value'], load['unit'])
        if 'm' not in load['unit'].lower():
            # If it's not already a linear load, distribute it over the span
            load_value = load_value / span
        additional_load_total += load_value
    
    # Combine loads for critical moment calculation
    loads = {
        "dead": total_dead_load,
        "live": total_live_load,
        "wind": total_wind_load,
        "maintenance": maintenance_load_kn,  # This will be considered as point load in calculations
        "additional": additional_load_total
    }
    
    # Calculate critical moment and critical load case
    moment_results = calculate_critical_moment(loads, span)
    max_moment = moment_results['critical_moment']
    critical_case = moment_results['critical_case']
    
    # Calculate maximum shear (simplified, based on critical case)
    # In a real application, this would consider different load combinations
    if critical_case == "Maintenance (point load)":
        # For point load at center
        max_shear = maintenance_load_kn / 2
        load_type = "point_center"
    else:
        # For uniformly distributed loads (simplification)
        total_uniform_load = 0
        # Check which loads are included in the critical case
        critical_case_str = str(critical_case)  # Convert to string to ensure 'in' operator works
        if "Dead + Live" in critical_case_str:
            total_uniform_load += total_dead_load + total_live_load
        if "Maintenance" in critical_case_str and "point" not in critical_case_str:
            # If maintenance is distributed (simplified)
            total_uniform_load += maintenance_load_kn / span
        if "Wind" in critical_case_str:
            total_uniform_load += total_wind_load
        total_uniform_load += additional_load_total
        
        max_shear = calculate_shear_force(span, total_uniform_load, "uniform")
        load_type = "uniform"
    
    # Select optimal section
    results = select_optimal_section(
        moment=max_moment,
        span=span,
        load_type=load_type,
        steel_grade=steel_grade,
        code=design_code.lower(),
        section_type="Channel"  # Purlins are often channel sections
    )
    
    # Create diagrams
    moment_diagram = plot_moment_diagram(span, max_moment, load_type)
    shear_diagram = plot_shear_force_diagram(span, max_shear, load_type)
    deflection_diagram = plot_deflection_diagram(span, results['deflection'], load_type)
    section_profile = plot_section_profile(results['section_properties'])
    
    # Store results in session state
    st.session_state.purlin_design_results = {
        'design_type': 'Purlin',
        'span': span,
        'dead_load': dead_load,
        'live_load': live_load,
        'is_accessible': is_accessible,
        'maintenance_load': maintenance_load_kg,
        'wind_load': wind_load,
        'chord_angle': chord_angle,
        'steel_grade': steel_grade,
        'code': design_code,
        'additional_loads': additional_loads,
        'moment': max_moment,
        'shear': max_shear,
        'critical_case': critical_case,
        'load_type': load_type,
        'results': results
    }
    
    # Store diagrams in session state
    st.session_state.purlin_load_diagrams = {
        'moment_diagram': moment_diagram,
        'shear_diagram': shear_diagram,
        'deflection_diagram': deflection_diagram,
        'section_profile': section_profile
    }

# App header with back button
col1, col2, col3 = st.columns([1, 3, 1])
with col1:
    if st.button("← Back to Home"):
        st.switch_page("app.py")
with col2:
    st.title("Structo 🏗 - Purlin Design")
with col3:
    st.write("")  # Empty column for balance

# Main content
st.write("Design purlins according to Egyptian and American codes.")

# Input section
st.header("Design Inputs")

# Design code selection
design_code = st.radio(
    "Select Design Code",
    ["Egyptian Code", "American Code"],
    horizontal=True,
    key="purlin_design_code"
)

# Basic inputs
col1, col2 = st.columns(2)
with col1:
    span = st.number_input("Span (m)", value=6.0, step=0.5, key="purlin_span")
    
    st.write("### Loads")
    dead_load = st.number_input("Dead Load (kN/m)", value=0.5, step=0.1, key="purlin_dead_load", 
                               help="Own weight of the purlin (typically)")
    live_load = st.number_input("Live Load (kN/m)", value=1.0, step=0.1, key="purlin_live_load")
    is_accessible = st.radio("Live Load Accessibility", ["Accessible", "Inaccessible"], index=1, key="purlin_is_accessible",
                           format_func=lambda x: x) == "Accessible"
    maintenance_load = st.number_input("Maintenance Load (kg)", value=100.0, step=10.0, key="purlin_maintenance_load",
                                     help="Typically 100kg for maintenance personnel")
    wind_load = st.number_input("Wind Load (kN/m²)", value=0.7, step=0.1, key="purlin_wind_load")

with col2:
    st.write("### Structural Parameters")
    chord_angle = st.number_input("Chord Angle (degrees)", value=15.0, step=1.0, key="purlin_chord_angle")
    
    # Steel grade selection based on code
    steel_grade_options = EGYPTIAN_STEEL_GRADES if design_code == "Egyptian Code" else AMERICAN_STEEL_GRADES
    steel_grade = st.selectbox("Steel Grade", steel_grade_options, key="purlin_steel_grade")

# Additional loads section
st.subheader("Additional Loads (Optional)")
st.write("Add any additional loads that should be considered in the design calculation.")

# Container for additional loads
load_container = st.container()

# Add existing loads
for i, load in enumerate(st.session_state.purlin_additional_loads):
    with load_container:
        cols = st.columns([3, 2, 2, 1])
        with cols[0]:
            st.session_state.purlin_additional_loads[i]['value'] = st.number_input(
                f"Load {i+1} Value", 
                value=load['value'],
                key=f"purlin_load_value_{i}"
            )
        with cols[1]:
            st.session_state.purlin_additional_loads[i]['unit'] = st.selectbox(
                f"Unit {i+1}",
                ["kN", "kN/m", "kN/m²", "kg", "kg/m", "kg/m²"],
                index=["kN", "kN/m", "kN/m²", "kg", "kg/m", "kg/m²"].index(load['unit']),
                key=f"purlin_load_unit_{i}"
            )
        with cols[2]:
            st.session_state.purlin_additional_loads[i]['case'] = st.selectbox(
                f"Case {i+1}",
                ["Case A", "Case B"],
                index=["Case A", "Case B"].index(load['case']),
                key=f"purlin_load_case_{i}"
            )
        with cols[3]:
            if st.button("✖", key=f"purlin_remove_load_{i}"):
                remove_load(i)
                st.rerun()

# Add load button
if st.button("Add Load", key="purlin_add_load"):
    add_load()
    st.rerun()

# Calculate button
if st.button("Calculate", type="primary", key="purlin_calculate_button"):
    with st.spinner("Performing calculations..."):
        calculate_results()

# Results section
if st.session_state.purlin_calculate_clicked:
    st.header("Design Results")
    
    results = st.session_state.purlin_design_results.get('results', {})
    diagrams = st.session_state.purlin_load_diagrams
    
    # Display overall design status with color
    status = results.get('overall_status', 'Unknown')
    status_color = "green" if status == "Safe" else "red"
    st.markdown(f"### Overall Design Status: <span style='color: {status_color};'>{status}</span>", unsafe_allow_html=True)
    
    # Critical load case
    st.markdown(f"**Critical Load Case:** {st.session_state.purlin_design_results.get('critical_case', 'Unknown')}")
    
    # Section for moment and shear diagrams
    st.subheader("Structural Analysis")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Moment Diagram")
        st.markdown(f"Maximum Moment: **{st.session_state.purlin_design_results.get('moment', 0):.2f} kNm**")
        st.image(f"data:image/png;base64,{diagrams.get('moment_diagram', '')}", use_container_width=True)
    
    with col2:
        st.markdown("#### Shear Force Diagram")
        st.markdown(f"Maximum Shear Force: **{st.session_state.purlin_design_results.get('shear', 0):.2f} kN**")
        st.image(f"data:image/png;base64,{diagrams.get('shear_diagram', '')}", use_container_width=True)
    
    # Section profile and properties
    st.subheader("Section Details")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Section Profile")
        section_props = results.get('section_properties', {})
        st.image(f"data:image/png;base64,{diagrams.get('section_profile', '')}", use_container_width=True)
    
    with col2:
        st.markdown("#### Section Properties")
        if section_props:
            st.markdown(f"**Selected Section:** {section_props.get('name', 'Unknown')}")
            st.markdown(f"**Height:** {section_props.get('height', 0)} mm")
            st.markdown(f"**Width:** {section_props.get('width', 0)} mm")
            st.markdown(f"**Web Thickness:** {section_props.get('web_thickness', 0)} mm")
            st.markdown(f"**Flange Thickness:** {section_props.get('flange_thickness', 0)} mm")
            st.markdown(f"**Cross-sectional Area:** {section_props.get('area', 0):.1f} mm²")
            st.markdown(f"**Moment of Inertia (Ix):** {section_props.get('Ix', 0):.3e} mm⁴")
            st.markdown(f"**Section Modulus (Zx):** {section_props.get('Zx', 0):.3e} mm³")
    
    # Deflection analysis
    st.subheader("Deflection Analysis")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Deflection Diagram")
        st.image(f"data:image/png;base64,{diagrams.get('deflection_diagram', '')}", use_container_width=True)
    
    with col2:
        st.markdown("#### Deflection Check")
        deflection = results.get('deflection', 0)
        deflection_check = results.get('deflection_check', {})
        
        st.markdown(f"**Maximum Deflection:** {deflection:.2f} mm")
        st.markdown(f"**Allowable Deflection:** {deflection_check.get('allowable_deflection', 0):.2f} mm")
        
        status = deflection_check.get('status', 'Unknown')
        status_color = "green" if status == "Safe" else "red"
        st.markdown(f"**Status:** <span style='color: {status_color};'>{status}</span>", unsafe_allow_html=True)
        
        st.markdown(f"**Deflection Ratio Limit:** {deflection_check.get('limit_ratio', 'L/240')}")
        
        # Utilization bar
        utilization = deflection_check.get('utilization', 0)
        st.progress(min(utilization, 1.0), text=f"Utilization: {utilization:.2f}")
    
    # Design checks
    st.subheader("Design Checks")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Stress Check")
        capacity_check = results.get('capacity_check', {})
        status = capacity_check.get('status', 'Unknown')
        status_color = "green" if status == "Safe" else "red"
        
        st.markdown(f"**Status:** <span style='color: {status_color};'>{status}</span>", unsafe_allow_html=True)
        st.markdown(f"**Moment Capacity:** {capacity_check.get('moment_capacity', 0):.2f} kNm")
        st.markdown(f"**Applied Moment:** {st.session_state.purlin_design_results.get('moment', 0):.2f} kNm")
        st.markdown(f"**Safety Factor:** {capacity_check.get('safety_factor', 0):.2f}")
        
        # Utilization bar
        utilization = capacity_check.get('utilization', 0)
        st.progress(min(utilization, 1.0), text=f"Utilization: {utilization:.2f}")
    
    with col2:
        st.markdown("#### Compactness Check")
        compactness_check = results.get('compactness_check', {})
        classification = compactness_check.get('classification', 'Unknown')
        class_color = "green" if classification == "Compact" else "orange"
        
        st.markdown(f"**Classification:** <span style='color: {class_color};'>{classification}</span>", unsafe_allow_html=True)
        st.markdown(f"**Flange:**")
        st.markdown(f"- Width-to-Thickness Ratio: {compactness_check.get('flange_ratio', 0):.2f}")
        st.markdown(f"- Compact Limit: {compactness_check.get('flange_compact_limit', 0):.2f}")
        st.markdown(f"- Status: {compactness_check.get('flange_status', 'Unknown')}")
        
        st.markdown(f"**Web:**")
        st.markdown(f"- Height-to-Thickness Ratio: {compactness_check.get('web_ratio', 0):.2f}")
        st.markdown(f"- Compact Limit: {compactness_check.get('web_compact_limit', 0):.2f}")
        st.markdown(f"- Status: {compactness_check.get('web_status', 'Unknown')}")
    
    # Lateral torsional buckling check
    st.markdown("#### Lateral Torsional Buckling Check")
    ltb_check = results.get('ltb_check', {})
    
    if ltb_check.get('status') == "Cannot determine - missing section properties":
        st.markdown("Detailed section properties required for complete LTB check.")
    else:
        status = ltb_check.get('status', 'Unknown')
        status_color = "green" if status == "Safe" else "red"
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Status:** <span style='color: {status_color};'>{status}</span>", unsafe_allow_html=True)
            st.markdown(f"**Critical Moment:** {ltb_check.get('critical_moment', 0):.2f} kNm")
            st.markdown(f"**Design Capacity:** {ltb_check.get('design_capacity', 0):.2f} kNm")
        
        with col2:
            # Utilization bar
            utilization = ltb_check.get('utilization', 0)
            if utilization:
                st.progress(min(utilization, 1.0), text=f"Utilization: {utilization:.2f}")
    
    # Export section
    st.header("Export Results")
    col1, col2 = st.columns(2)
    
    with col1:
        excel_link = create_excel_download_link(
            st.session_state.purlin_design_results, 
            "structo_purlin_design"
        )
        st.markdown(excel_link, unsafe_allow_html=True)
    
    with col2:
        pdf_link = create_pdf_download_link(
            st.session_state.purlin_design_results,
            st.session_state.purlin_load_diagrams,
            "structo_purlin_design"
        )
        st.markdown(pdf_link, unsafe_allow_html=True)
