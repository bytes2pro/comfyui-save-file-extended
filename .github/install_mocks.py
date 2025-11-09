"""Install ComfyUI mocks as sitecustomize.py so they're available to all Python processes."""
import os
import site

# Get site-packages directory
site_packages = site.getsitepackages()[0] if site.getsitepackages() else site.getusersitepackages()

# Ensure directory exists
os.makedirs(site_packages, exist_ok=True)

# Copy the mock setup script to sitecustomize.py
mock_script_path = os.path.join(os.path.dirname(__file__), "setup_comfyui_mocks.py")
sitecustomize_path = os.path.join(site_packages, "sitecustomize.py")

with open(mock_script_path, "r") as src, open(sitecustomize_path, "w") as dst:
    dst.write(src.read())

print(f"Installed ComfyUI mocks to {sitecustomize_path}")

