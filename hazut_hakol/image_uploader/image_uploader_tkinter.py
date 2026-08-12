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
        self.root_path = tk.StringVar()

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
                                       text="Select a directory containing folders with image and metadata files",
                                       style='Requirements.TLabel',
                                       wraplength=550)
        requirements_label.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(0, 15))

        # Folder selection frame
        folder_frame = ttk.LabelFrame(main_frame, text="Directory Selection", padding="15")
        folder_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        folder_frame.columnconfigure(1, weight=1)

        # Folder path
        ttk.Label(folder_frame, text="Select Directory:").grid(row=0, column=0, sticky=tk.W, pady=5)
        folder_entry = ttk.Entry(folder_frame, textvariable=self.root_path, width=60)
        folder_entry.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5, padx=(0, 10))
        browse_btn = ttk.Button(folder_frame, text="Browse...", command=self.browse_directory, style='Custom.TButton')
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
        self.run_button = ttk.Button(main_frame, text="Upload Directory", command=self.run_upload,
                                     style='Custom.TButton')
        self.run_button.grid(row=5, column=1, pady=20, sticky=tk.E)

        # Make sure the main frame expands properly
        main_frame.columnconfigure(1, weight=1)

    def browse_directory(self):
        directory_selected = filedialog.askdirectory(title="Select Directory Containing Folders")
        if directory_selected:
            self.root_path.set(directory_selected)

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
        directory = self.root_path.get()

        if not directory:
            messagebox.showerror("Error", "Please select a directory")
            return

        try:
            # Disable the button and show progress
            self.run_button.config(state='disabled')
            self.status_label.config(text="Processing...", foreground="#3498db")
            self.progress.start()

            # Run the upload in a separate thread to avoid freezing the UI
            thread = threading.Thread(target=self.upload_directory, args=(directory,))
            thread.daemon = True
            thread.start()

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}")

    def upload_directory(self, directory):
        try:
            dir_path = Path(directory)

            # Check if this is a folder with image and json (single folder case)
            # or a parent directory containing multiple folders
            subfolders = [f for f in dir_path.iterdir() if f.is_dir()]

            # If there are no subdirectories, treat the current directory as containing one folder
            if not subfolders:
                # Check if the current directory has both image and json files
                image_files = list(dir_path.glob("*.jpg")) + list(dir_path.glob("*.jpeg")) + \
                              list(dir_path.glob("*.png")) + list(dir_path.glob("*.tiff")) + \
                              list(dir_path.glob("*.tif")) + list(dir_path.glob("*.bmp"))

                json_files = list(dir_path.glob("*.json"))

                if len(image_files) == 1 and len(json_files) == 1:
                    # This is a single folder with image and metadata - process it directly
                    folders_to_process = [dir_path]
                else:
                    messagebox.showerror("Error",
                                         "Directory must contain either:\n1. Multiple subfolders each with image and metadata\n2. A single folder with one image and one json file")
                    self.root.after(0, lambda: self.update_status("Invalid directory structure", "red"))
                    return
            else:
                # Process all subdirectories
                folders_to_process = subfolders

            # Process each folder
            for i, folder in enumerate(folders_to_process):
                try:
                    # Automatically detect image suffix from folder contents
                    image_suffix = self.get_image_suffix_from_folder(folder)

                    # Import your existing modules (you'll need to adjust these paths)
                    sys.path.insert(0, str(Path(folder).parent))

                    # Import your existing ImageUploader class and related modules
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
                        input_folder=str(folder),
                        image_suffix=image_suffix
                    )

                    # Perform the upload
                    image_uploader.upload_image()

                    # Update UI with progress
                    self.root.after(0, lambda msg=f"Processed folder {i + 1}/{len(folders_to_process)}: {folder.name}":
                    self.update_status(msg, "black"))

                except Exception as e:
                    logger.error(f"Error processing folder {folder}: {str(e)}")
                    self.root.after(0, lambda msg=f"Error in folder {folder.name}: {str(e)}":
                    self.update_status(msg, "red"))
                    continue

            # Update UI with success message
            self.root.after(0, lambda: self.update_status("All folders processed successfully!", "green"))

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