import streamlit as st
import json
import requests
from PIL import Image
import io
import base64
import copy

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

@st.cache_data
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

def safe_get(obj, key, default=0):
    if isinstance(obj, dict):
        value = obj.get(key, default)
    elif isinstance(obj, (list, tuple)) and isinstance(key, int):
        value = obj[key] if 0 <= key < len(obj) else default
    else:
        value = default
    
    try:
        return float(value)
    except (ValueError, TypeError):
        return float(default)

def find_colors(item, colors, path):
    if isinstance(item, dict):
        if 'ty' in item:
            if item['ty'] == 'fl' and 'c' in item and 'k' in item['c']:  # Fill
                colors.append((path + ['Fill'], item['c']['k']))
            elif item['ty'] == 'st' and 'c' in item and 'k' in item['c']:  # Stroke
                colors.append((path + ['Stroke'], item['c']['k']))
        for key, value in item.items():
            find_colors(value, colors, path + [key])
    elif isinstance(item, list):
        for i, value in enumerate(item):
            find_colors(value, colors, path + [str(i)])

def edit_shape_colors(shape, prefix):
    colors = []
    find_colors(shape, colors, [prefix])
    
    color_changes = {}
    for i, (path, color) in enumerate(colors):
        color_name = ' > '.join(path)
        st.write(f"**{color_name}**")
        current_color = rgb_to_hex(color[:3])
        new_color = st.color_picker("Choose color", current_color, key=f"{prefix}_color_{i}")
        new_rgb = hex_to_rgb(new_color) + [color[3]]  # Preserve alpha
        
        if new_rgb[:3] != color[:3]:
            color_changes[tuple(path)] = new_rgb

    return color_changes

def apply_color_changes(shape, color_changes):
    for path, new_rgb in color_changes.items():
        target = shape
        for p in path[1:-1]:
            if isinstance(target, dict) and p in target:
                target = target[p]
            elif isinstance(target, list) and p.isdigit() and int(p) < len(target):
                target = target[int(p)]
            else:
                st.warning(f"Could not update color for {' > '.join(path)}. Path not found in Lottie structure.")
                break
        else:
            if isinstance(target, dict) and 'c' in target and 'k' in target['c']:
                target['c']['k'] = new_rgb
            else:
                st.warning(f"Could not update color for {' > '.join(path)}. Unexpected Lottie structure.")

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

    if 'lottie_json' not in st.session_state:
        st.session_state.lottie_json = None

    with st.sidebar:
        st.header("Load Animation")
        uploaded_file = st.file_uploader("Choose a Lottie JSON file", type="json")
        lottie_url = st.text_input("Or enter a Lottie animation URL")

        if uploaded_file is not None:
            try:
                st.session_state.lottie_json = json.load(uploaded_file)
            except json.JSONDecodeError:
                st.error("Invalid JSON file. Please upload a valid Lottie JSON.")
        elif lottie_url:
            st.session_state.lottie_json = load_lottieurl(lottie_url)
        elif st.session_state.lottie_json is None:
            default_url = "https://assets5.lottiefiles.com/packages/lf20_V9t630.json"
            st.session_state.lottie_json = load_lottieurl(default_url)

        if st.session_state.lottie_json is None:
            st.error("Failed to load animation")
            return

    lottie_json = copy.deepcopy(st.session_state.lottie_json)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("Animation Preview")
        speed = st.slider("Animation Speed", 0.1, 3.0, 1.0, 0.1)
        direction = st.radio("Animation Direction", ["Forward", "Reverse"])
        loop = st.checkbox("Loop Animation", value=True)

        st.subheader("Trim Animation")
        total_frames = max(1, int(safe_get(lottie_json, 'op', 60) - safe_get(lottie_json, 'ip', 0)))
        trim_start, trim_end = st.slider("Trim Frames", 0, total_frames, (0, total_frames), 1)
        lottie_json['ip'] = float(trim_start)
        lottie_json['op'] = float(trim_end)

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
        st.subheader("Layer Editor")
        if isinstance(lottie_json, dict) and 'layers' in lottie_json and isinstance(lottie_json['layers'], list):
            selected_layer = st.selectbox("Select Layer", range(len(lottie_json['layers'])))
            layer = lottie_json['layers'][selected_layer]
            
            layer_name = st.text_input("Layer Name", layer.get('nm', f"Layer {selected_layer}"))
            layer['nm'] = layer_name

            if isinstance(layer, dict) and 'ks' in layer:
                st.subheader("Transform Properties")
                ks = layer['ks']
                if isinstance(ks, dict):
                    if 'p' in ks:
                        pos = ks['p'].get('k', [0, 0]) if isinstance(ks['p'], dict) else ks['p']
                        new_pos_x = st.number_input("X Position", value=safe_get(pos, 0))
                        new_pos_y = st.number_input("Y Position", value=safe_get(pos, 1))
                        if isinstance(ks['p'], dict):
                            ks['p']['k'] = [new_pos_x, new_pos_y] + pos[2:]
                        else:
                            ks['p'] = [new_pos_x, new_pos_y] + pos[2:]

                    if 's' in ks:
                        scale = ks['s'].get('k', [100, 100]) if isinstance(ks['s'], dict) else ks['s']
                        new_scale_x = st.number_input("X Scale (%)", value=safe_get(scale, 0, 100))
                        new_scale_y = st.number_input("Y Scale (%)", value=safe_get(scale, 1, 100))
                        if isinstance(ks['s'], dict):
                            ks['s']['k'] = [new_scale_x, new_scale_y] + scale[2:]
                        else:
                            ks['s'] = [new_scale_x, new_scale_y] + scale[2:]

                    if 'r' in ks:
                        rotation = ks['r'].get('k', 0) if isinstance(ks['r'], dict) else ks['r']
                        new_rotation = st.number_input("Rotation (degrees)", value=safe_get(rotation, 0))
                        if isinstance(ks['r'], dict):
                            ks['r']['k'] = new_rotation
                        else:
                            ks['r'] = new_rotation

            st.subheader("Color Properties")
            if isinstance(layer, dict):
                color_changes = edit_shape_colors(layer, f"Layer_{selected_layer}")
                if color_changes:
                    apply_color_changes(layer, color_changes)
            else:
                st.warning("This layer does not contain editable color properties.")

        st.subheader("Animation Properties")
        lottie_json['fr'] = st.number_input("Frame Rate", value=safe_get(lottie_json, 'fr', 60))

    col1, col2 = st.columns(2)
    with col1:
        if lottie_json:
            st.download_button(
                label="Download Edited Lottie JSON",
                data=json.dumps(lottie_json, indent=2),
                file_name="edited_lottie_animation.json",
                mime="application/json",
            )

    with col2:
        st.subheader("Export as GIF")
        gif_frames = st.number_input("Number of frames for GIF", min_value=10, max_value=100, value=30)
        if st.button("Generate GIF"):
            gif_data = lottie_container.to_gif(duration=gif_frames/safe_get(lottie_json, 'fr', 60))
            st.image(gif_data, caption="Generated GIF")
            
            buffered = io.BytesIO()
            Image.open(io.BytesIO(gif_data)).save(buffered, format="GIF")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            href = f'<a href="data:image/gif;base64,{img_str}" download="lottie_animation.gif">Download GIF</a>'
            st.markdown(href, unsafe_allow_html=True)

    # Update the session state with the modified Lottie JSON
    st.session_state.lottie_json = lottie_json

if __name__ == "__main__":
    main()
