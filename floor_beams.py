import streamlit as st
import numpy as np
from utils.calculations import (
    convert_to_kn, calculate_moment, calculate_shear_force,
    calculate_deflection, select_optimal_section
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
    page_title="Structo 🏗 - Floor Beam Design",
    page_icon="🏗",
    layout="wide"
)

# Initialize session state variables if they don't exist
if 'additional_loads' not in st.session_state:
    st.session_state.additional_loads = []
if 'calculate_clicked' not in st.session_state:
    st.session_state.calculate_clicked = False
if 'design_results' not in st.session_state:
    st.session_state.design_results = {}
if 'load_diagrams' not in st.session_state:
    st.session_state.load_diagrams = {}

# Function to add a new additional load
def add_load():
    st.session_state.additional_loads.append({
        'value': 0.0,
        'unit': 'kN',
        'case': 'Case A'
    })

# Function to remove a load
def remove_load(index):
    st.session_state.additional_loads.pop(index)

# Function to calculate results
def calculate_results():
    st.session_state.calculate_clicked = True
    
    # Get input values
    span = st.session_state.span
    dead_load = st.session_state.dead_load
    floor_cover_load = st.session_state.floor_cover_load
    live_load = st.session_state.live_load
    is_accessible = st.session_state.is_accessible
    chord_angle = st.session_state.chord_angle  # Using single chord angle parameter
    steel_grade = st.session_state.steel_grade
    design_code = st.session_state.design_code
    supported_beam_reaction = st.session_state.supported_beam_reaction
    additional_loads = st.session_state.additional_loads
    
    # Calculate total load
    # For simplicity, we'll convert floor cover and live loads to linear loads
    # In a real app, this would involve more detailed load distribution calculations
    beam_width = 1.0  # Assuming 1m tributary width for demonstration
    total_dead_load = dead_load  # kN/m (already linear)
    total_floor_cover_load = floor_cover_load * beam_width  # kN/m^2 -> kN/m
    total_live_load = live_load * beam_width  # kN/m^2 -> kN/m
    
    # Add supported beam reaction if provided
    if supported_beam_reaction > 0:
        # Convert to an equivalent uniform load for simplified calculation
        # In reality, this would be a point load in the analysis
        equivalent_reaction_load = supported_beam_reaction / span  # kN -> kN/m
        total_dead_load += equivalent_reaction_load
    
    # Process additional loads
    additional_load_total = 0
    for load in additional_loads:
        # Convert all loads to kN/m for simplicity
        # In a real app, this would handle different load types more precisely
        load_value = convert_to_kn(load['value'], load['unit'])
        if 'm' not in load['unit'].lower():
            # If it's not already a linear load, distribute it over the span
            load_value = load_value / span
        additional_load_total += load_value
    
    # Total uniform load for simple beam calculation
    total_load = total_dead_load + total_floor_cover_load + total_live_load + additional_load_total
    
    # Calculate moment and shear
    max_moment = calculate_moment(span, total_load, "uniform")
    max_shear = calculate_shear_force(span, total_load, "uniform")
    
    # Select optimal section
    results = select_optimal_section(
        moment=max_moment,
        span=span,
        load_type="uniform",
        steel_grade=steel_grade,
        code=design_code.lower(),
        section_type="I-Beam"
    )
    
    # Create diagrams
    moment_diagram = plot_moment_diagram(span, max_moment, "uniform")
    shear_diagram = plot_shear_force_diagram(span, max_shear, "uniform")
    deflection_diagram = plot_deflection_diagram(span, results['deflection'], "uniform")
    section_profile = plot_section_profile(results['section_properties'])
    
    # Store results in session state
    st.session_state.design_results = {
        'design_type': 'Floor Beam',
        'span': span,
        'dead_load': dead_load,
        'floor_cover_load': floor_cover_load,
        'live_load': live_load,
        'is_accessible': is_accessible,
        'chord_angle': chord_angle,
        'steel_grade': steel_grade,
        'code': design_code,
        'supported_beam_reaction': supported_beam_reaction,
        'additional_loads': additional_loads,
        'total_load': total_load,
        'moment': max_moment,
        'shear': max_shear,
        'results': results
    }
    
    # Store diagrams in session state
    st.session_state.load_diagrams = {
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
    st.title("Structo 🏗 - Floor Beam Design")
with col3:
    st.write("")  # Empty column for balance

# Main content
st.write("Design floor beams according to Egyptian and American codes.")

# Input section
st.header("Design Inputs")

# Design code selection
design_code = st.radio(
    "Select Design Code",
    ["Egyptian Code", "American Code"],
    horizontal=True,
    key="design_code"
)

# Basic inputs
col1, col2 = st.columns(2)
with col1:
    span = st.number_input("Span (m)", value=5.0, step=0.5, key="span")
    
    st.write("### Loads")
    dead_load = st.number_input("Dead Load (kN/m)", value=1.0, step=0.1, key="dead_load", 
                               help="Own weight of the beam (typically)")
    floor_cover_load = st.number_input("Floor Cover Load (kN/m²)", value=1.5, step=0.1, key="floor_cover_load")
    live_load = st.number_input("Live Load (kN/m²)", value=2.5, step=0.1, key="live_load")
    is_accessible = st.radio("Live Load Accessibility", ["Accessible", "Inaccessible"], index=0, key="is_accessible",
                           format_func=lambda x: x) == "Accessible"

with col2:
    st.write("### Structural Parameters")
    chord_angle = st.number_input("Chord Angle (degrees)", value=0.0, step=1.0, key="chord_angle")
    
    # Steel grade selection based on code
    steel_grade_options = EGYPTIAN_STEEL_GRADES if design_code == "Egyptian Code" else AMERICAN_STEEL_GRADES
    steel_grade = st.selectbox("Steel Grade", steel_grade_options, key="steel_grade")
    
    supported_beam_reaction = st.number_input("Reaction from Supported Beam (kN) (Optional)", value=0.0, step=1.0, key="supported_beam_reaction")

# Additional loads section
st.subheader("Additional Loads (Optional)")
st.write("Add any additional loads that should be considered in the design calculation.")

# Container for additional loads
load_container = st.container()

# Add existing loads
for i, load in enumerate(st.session_state.additional_loads):
    with load_container:
        cols = st.columns([3, 2, 2, 1])
        with cols[0]:
            st.session_state.additional_loads[i]['value'] = st.number_input(
                f"Load {i+1} Value", 
                value=load['value'],
                key=f"load_value_{i}"
            )
        with cols[1]:
            st.session_state.additional_loads[i]['unit'] = st.selectbox(
                f"Unit {i+1}",
                ["kN", "kN/m", "kN/m²", "kg", "kg/m", "kg/m²"],
                index=["kN", "kN/m", "kN/m²", "kg", "kg/m", "kg/m²"].index(load['unit']),
                key=f"load_unit_{i}"
            )
        with cols[2]:
            st.session_state.additional_loads[i]['case'] = st.selectbox(
                f"Case {i+1}",
                ["Case A", "Case B"],
                index=["Case A", "Case B"].index(load['case']),
                key=f"load_case_{i}"
            )
        with cols[3]:
            if st.button("✖", key=f"remove_load_{i}"):
                remove_load(i)
                st.rerun()

# Add load button
if st.button("Add Load", key="add_load"):
    add_load()
    st.rerun()

# Calculate button
if st.button("Calculate", type="primary", key="calculate_button"):
    with st.spinner("Performing calculations..."):
        calculate_results()

# Results section
if st.session_state.calculate_clicked:
    st.header("Design Results")
    
    results = st.session_state.design_results.get('results', {})
    diagrams = st.session_state.load_diagrams
    
    # Display overall design status with color
    status = results.get('overall_status', 'Unknown')
    status_color = "green" if status == "Safe" else "red"
    st.markdown(f"### Overall Design Status: <span style='color: {status_color};'>{status}</span>", unsafe_allow_html=True)
    
    # Section for moment and shear diagrams
    st.subheader("Structural Analysis")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Moment Diagram")
        st.markdown(f"Maximum Moment: **{st.session_state.design_results.get('moment', 0):.2f} kNm**")
        st.image(f"data:image/png;base64,{diagrams.get('moment_diagram', '')}", use_container_width=True)
    
    with col2:
        st.markdown("#### Shear Force Diagram")
        st.markdown(f"Maximum Shear Force: **{st.session_state.design_results.get('shear', 0):.2f} kN**")
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
        
        st.markdown(f"**Deflection Ratio Limit:** {deflection_check.get('limit_ratio', 'L/360')}")
        
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
        st.markdown(f"**Applied Moment:** {st.session_state.design_results.get('moment', 0):.2f} kNm")
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
            st.session_state.design_results, 
            "structo_floor_beam_design"
        )
        st.markdown(excel_link, unsafe_allow_html=True)
    
    with col2:
        pdf_link = create_pdf_download_link(
            st.session_state.design_results,
            st.session_state.load_diagrams,
            "structo_floor_beam_design"
        )
        st.markdown(pdf_link, unsafe_allow_html=True)
