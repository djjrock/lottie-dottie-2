import streamlit as st
import json
import requests
from PIL import Image
import io
import base64

# Ensure streamlit-lottie is installed
try:
    from streamlit_lottie import st_lottie
except ImportError:
    st.error("streamlit-lottie is not installed. Installing now...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit-lottie"])
    from streamlit_lottie import st_lottie

st.set_page_config(page_title="Advanced Lottie Animation Editor", layout="wide")

# Set dark theme
st.markdown("""
<style>
    .reportview-container {
        background: #1E1E1E;
        color: white;
    }
    .sidebar .sidebar-content {
        background: #2E2E2E;
    }
    .Widget>label {
        color: white;
    }
    .stTextInput>div>div>input {
        color: white;
    }
</style>
""", unsafe_allow_html=True)

def load_lottieurl(url: str):
    try:
        r = requests.get(url)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Error loading Lottie from URL: {e}")
    return None

def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255))

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return [int(hex_color[i:i+2], 16)/255 for i in (0, 2, 4)]

def edit_shape_colors(shape, prefix):
    if 'it' in shape:
        for i, item in enumerate(shape['it']):
            if item.get('ty') == 'fl':  # Fill
                st.subheader(f"{prefix} Fill Color")
                current_color = rgb_to_hex(item['c']['k'][:3])
                new_color = st.color_picker("Choose color", current_color)
                item['c']['k'] = hex_to_rgb(new_color) + [item['c']['k'][3]]  # Preserve alpha
            elif item.get('ty') == 'st':  # Stroke
                st.subheader(f"{prefix} Stroke Color")
                current_color = rgb_to_hex(item['c']['k'][:3])
                new_color = st.color_picker("Choose color", current_color)
                item['c']['k'] = hex_to_rgb(new_color) + [item['c']['k'][3]]  # Preserve alpha
            elif item.get('ty') == 'gr':  # Group
                edit_shape_colors(item, f"{prefix} Group {i}")

def main():
    st.title("Advanced Lottie Animation Editor")
    st.markdown("""
    This advanced Lottie editor allows you to:
    - Load animations from file or URL
    - Edit layer properties (position, scale, rotation)
    - Modify shape colors
    - Adjust animation speed and direction
    - Trim animation
    - Export as JSON or GIF
    """)

    # Sidebar for file upload and URL input
    with st.sidebar:
        st.header("Load Animation")
        uploaded_file = st.file_uploader("Choose a Lottie JSON file", type="json")
        lottie_url = st.text_input("Or enter a Lottie animation URL")

        if uploaded_file is not None:
            try:
                lottie_json = json.load(uploaded_file)
            except json.JSONDecodeError:
                st.error("Invalid JSON file. Please upload a valid Lottie JSON.")
                return
        elif lottie_url:
            lottie_json = load_lottieurl(lottie_url)
            if lottie_json is None:
                return
        else:
            # Load a default animation if no file or URL is provided
            default_url = "https://assets5.lottiefiles.com/packages/lf20_V9t630.json"
            lottie_json = load_lottieurl(default_url)
            if lottie_json is None:
                st.error(f"Failed to load default animation")
                return

    # Main content area
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("Animation Preview")
        
        # Animation controls
        speed = st.slider("Animation Speed", 0.1, 3.0, 1.0, 0.1)
        direction = st.radio("Animation Direction", ["Forward", "Reverse"])
        loop = st.checkbox("Loop Animation", value=True)

        # Trim animation
        st.subheader("Trim Animation")
        total_frames = lottie_json['op'] - lottie_json['ip']
        trim_start, trim_end = st.slider("Trim Frames", 0, total_frames, (0, total_frames), 1)
        lottie_json['ip'] = trim_start
        lottie_json['op'] = trim_end

        # Display the Lottie animation
        lottie_container = st_lottie(
            lottie_json,
            speed=speed,
            reverse=direction == "Reverse",
            loop=loop,
            quality="low",
            height=400,
            key="lottie",
        )

    with col2:
        st.header("Edit Animation")
        
        # Layer editing
        st.subheader("Layer Editor")
        if 'layers' in lottie_json:
            selected_layer = st.selectbox("Select Layer", range(len(lottie_json['layers'])))
            layer = lottie_json['layers'][selected_layer]
            
            # Edit layer properties
            layer_name = st.text_input("Layer Name", layer.get('nm', f"Layer {selected_layer}"))
            layer['nm'] = layer_name

            if 'ks' in layer:
                st.subheader("Transform Properties")
                if 'p' in layer['ks']:  # Position
                    pos_x, pos_y = layer['ks']['p'].get('k', [0, 0])[:2]
                    new_pos_x = st.number_input("X Position", value=float(pos_x))
                    new_pos_y = st.number_input("Y Position", value=float(pos_y))
                    layer['ks']['p']['k'] = [new_pos_x, new_pos_y] + layer['ks']['p'].get('k', [0])[2:]

                if 's' in layer['ks']:  # Scale
                    scale_x, scale_y = layer['ks']['s'].get('k', [100, 100])[:2]
                    new_scale_x = st.number_input("X Scale (%)", value=float(scale_x))
                    new_scale_y = st.number_input("Y Scale (%)", value=float(scale_y))
                    layer['ks']['s']['k'] = [new_scale_x, new_scale_y] + layer['ks']['s'].get('k', [100])[2:]

                if 'r' in layer['ks']:  # Rotation
                    rotation = layer['ks']['r'].get('k', 0)
                    new_rotation = st.number_input("Rotation (degrees)", value=float(rotation))
                    layer['ks']['r']['k'] = new_rotation

            # Color editing for shape layers
            if layer.get('ty') == 4:  # Shape layer
                st.subheader("Shape Properties")
                for i, shape in enumerate(layer.get('shapes', [])):
                    st.markdown(f"**Shape {i+1}**")
                    edit_shape_colors(shape, f"Layer {selected_layer} Shape {i}")

        # Animation properties
        st.subheader("Animation Properties")
        lottie_json['fr'] = st.number_input("Frame Rate", value=lottie_json.get('fr', 60))

    # Download buttons
    col1, col2 = st.columns(2)
    with col1:
        if lottie_json:
            st.download_button(
                label="Download Edited Lottie JSON",
                data=json.dumps(lottie_json, indent=2),
                file_name="edited_lottie_animation.json",
                mime="application/json",
            )

    # Export as GIF
    with col2:
        st.subheader("Export as GIF")
        gif_frames = st.number_input("Number of frames for GIF", min_value=10, max_value=100, value=30)
        if st.button("Generate GIF"):
            gif_data = lottie_container.to_gif(duration=gif_frames/lottie_json['fr'])
            st.image(gif_data, caption="Generated GIF")
            
            # Provide download link for GIF
            buffered = io.BytesIO()
            Image.open(io.BytesIO(gif_data)).save(buffered, format="GIF")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            href = f'<a href="data:image/gif;base64,{img_str}" download="lottie_animation.gif">Download GIF</a>'
            st.markdown(href, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
