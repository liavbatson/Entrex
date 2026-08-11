
import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox
from loguru import logger

# Add the project root to the path so we can import our modules
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


def setup_styles():
    """Setup custom styles for better appearance"""
    style = ttk.Style()

    # Configure theme
    style.theme_use('clam')

    # Configure custom styles
    style.configure('Title.TLabel', font=('Segoe UI', 16, 'bold'), foreground='#2c3e50')
    style.configure('Subtitle.TLabel', font=('Segoe UI', 10), foreground='#7f8c8d')
    style.configure('Custom.TButton', font=('Segoe UI', 10, 'bold'), padding=6)
    style.configure('Status.TLabel', font=('Segoe UI', 9))
    style.configure('Requirements.TLabel', font=('Segoe UI', 9), foreground='#2c3e50')

    # Configure progress bar
    style.configure('Custom.Horizontal.TProgressbar', thickness=20)


class FolderUploaderUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Uploader")
        self.root.geometry("650x450")
        self.root.minsize(550, 400)

        # Configure styles
        setup_styles()

        # Variables to store folder path
        self.folder_path = tk.StringVar()

        # Create the UI components
        self.create_widgets()

    def create_widgets(self):
        # Main container frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights for main frame - make it responsive
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # Configure rows to allow proper expansion
        for i in range(10):  # Configure enough rows
            main_frame.rowconfigure(i, weight=0)
        main_frame.rowconfigure(2, weight=0)  # Folder selection
        main_frame.rowconfigure(3, weight=1)  # Progress section
        main_frame.rowconfigure(4, weight=0)  # Button row

        # Title
        title_label = ttk.Label(main_frame, text="Image Uploader", style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))

        subtitle_label = ttk.Label(main_frame, text="Upload images and metadata to Azure Storage",
                                   style='Subtitle.TLabel')
        subtitle_label.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))

        # Requirements text
        requirements_label = ttk.Label(main_frame,
                                      text="Folder must contain exactly one metadata file (json) and one image (jpg, jpeg, png, tiff, tif, bmp)",
                                      style='Requirements.TLabel',
                                      wraplength=550)
        requirements_label.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(0, 15))

        # Folder selection frame
        folder_frame = ttk.LabelFrame(main_frame, text="Folder Selection", padding="15")
        folder_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        folder_frame.columnconfigure(1, weight=1)

        # Folder path
        ttk.Label(folder_frame, text="Select Folder:").grid(row=0, column=0, sticky=tk.W, pady=5)
        folder_entry = ttk.Entry(folder_frame, textvariable=self.folder_path, width=60)
        folder_entry.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5, padx=(0, 10))
        browse_btn = ttk.Button(folder_frame, text="Browse...", command=self.browse_folder, style='Custom.TButton')
        browse_btn.grid(row=1, column=2, sticky=tk.W, pady=5)

        # Progress section
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        progress_frame.columnconfigure(0, weight=1)

        # Progress bar
        self.progress = ttk.Progressbar(progress_frame, mode='indeterminate', style='Custom.Horizontal.TProgressbar')
        self.progress.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Status label
        self.status_label = ttk.Label(progress_frame, text="Ready to upload", style='Status.TLabel')
        self.status_label.grid(row=1, column=0, sticky=tk.W)

        # Run button
        self.run_button = ttk.Button(main_frame, text="Upload Folder", command=self.run_upload, style='Custom.TButton')
        self.run_button.grid(row=5, column=1, pady=20, sticky=tk.E)

        # Make sure the main frame expands properly
        main_frame.columnconfigure(1, weight=1)

    def browse_folder(self):
        folder_selected = filedialog.askdirectory(title="Select Folder with Image and Metadata")
        if folder_selected:
            self.folder_path.set(folder_selected)

    def get_image_suffix_from_folder(self, folder_path):
        """Extract image suffix from the folder contents"""
        folder = Path(folder_path)

        # Look for image files (common formats)
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.tiff', '*.tif', '*.bmp']

        for ext in image_extensions:
            image_files = list(folder.glob(ext))
            if image_files:
                # Return the extension without the dot
                return image_files[0].suffix[1:].lower()

        # If no image found, raise an error
        raise ValueError("No image file found in folder")

    def run_upload(self):
        folder = self.folder_path.get()

        if not folder:
            messagebox.showerror("Error", "Please select a folder")
            return

        try:
            # Automatically detect image suffix from folder contents
            image_suffix = self.get_image_suffix_from_folder(folder)

            # Disable the button and show progress
            self.run_button.config(state='disabled')
            self.status_label.config(text="Processing...", foreground="#3498db")
            self.progress.start()

            # Run the upload in a separate thread to avoid freezing the UI
            thread = threading.Thread(target=self.upload_folder, args=(folder, image_suffix))
            thread.daemon = True
            thread.start()

        except ValueError as e:
            messagebox.showerror("Error", str(e))
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}")

    def upload_folder(self, folder_path, image_suffix):
        try:
            # Import your existing modules (you'll need to adjust these paths)
            sys.path.insert(0, str(Path(folder_path).parent))

            # Import your existing ImageUploader class
            from hazut_hakol.apio.data_storage.data_storage_azure import DataStorageAzureNode
            from hazut_hakol.apio.interfaces.azure_storage_interface import AzureStorageInterface
            from hazut_hakol.apio.knowledge_center.knowledge_center import KnowledgeCenter
            from hazut_hakol.core.classes.barak import Sweep
            from hazut_hakol.core.utils import Environment

            # Import ImageUploader
            from hazut_hakol.image_uploader.upload_image_to_azure_and_mongo import ImageUploader

            # Create the ImageUploader instance
            image_uploader = ImageUploader(
                mode=Environment.DEVELOPMENT,
                input_folder=folder_path,
                image_suffix=image_suffix
            )

            # Perform the upload
            image_uploader.upload_image()

            # Update UI with success message
            self.root.after(0, lambda: self.update_status("Upload completed successfully!", "green"))

        except Exception as e:
            logger.error(f"Error during upload: {str(e)}")
            self.root.after(0, lambda: self.update_status(f"Error: {str(e)}", "red"))

    def update_status(self, message, color):
        self.status_label.config(text=message, foreground=color)
        self.progress.stop()
        self.run_button.config(state='normal')


def main():
    root = tk.Tk()
    app = FolderUploaderUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()