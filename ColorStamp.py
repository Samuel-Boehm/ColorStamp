from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime
import cv2
import numpy as np
import exifread
from sklearn.mixture import GaussianMixture

class MetadataPaletteGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("Metadata and Palette Generator")
        self.root.geometry("1200x800")
        
        self.image_path = None
        self.image = None
        self.display_image = None
        self.palette_colors = []
        self.selected_colors = []
        self.shadow_var = tk.BooleanVar(value=True)
        self.font_var = tk.StringVar(value="default")
        self.font_size_var = tk.IntVar(value=24)  # Default font size is 24

        # Create frames
        self.top_frame = tk.Frame(root)
        self.top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.image_frame = tk.Frame(root)
        self.image_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.color_selection_frame = tk.Frame(root)
        self.color_selection_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.selected_colors_frame = tk.Frame(root)
        self.selected_colors_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.options_frame = tk.Frame(root)
        self.options_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.bottom_frame = tk.Frame(root)
        self.bottom_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Setup frames
        self.setup_top_frame()
        self.setup_image_frame()
        self.setup_color_selection_frame()
        self.setup_selected_colors_frame()
        self.setup_options_frame()
        self.setup_bottom_frame()

        
        # Detect available fonts
        self.available_fonts = self.get_available_fonts()
        self.update_font_dropdown()


    
    def setup_top_frame(self):
        self.open_button = tk.Button(self.top_frame, text="Open Image", command=self.open_image)
        self.open_button.pack(side=tk.LEFT, padx=5)
        
        self.extract_button = tk.Button(self.top_frame, text="Preview Result", command=self.preview_result)
        self.extract_button.pack(side=tk.LEFT, padx=5)

        self.pipette_button = tk.Button(self.top_frame, text="Use Pipette Tool", command=self.activate_pipette_tool)
        self.pipette_button.pack(side=tk.LEFT, padx=5)

        self.color_preview_label = tk.Label(self.top_frame, text="Hover Color: None", bg="white", width=20)
        self.color_preview_label.pack(side=tk.LEFT, padx=5)

        self.rectangle_tool_button = tk.Button(self.top_frame, text="Rectangle Tool", command=self.activate_rectangle_tool)
        self.rectangle_tool_button.pack(side=tk.LEFT, padx=5)

    def activate_rectangle_tool(self):
        """Activate the rectangle tool for selecting regions"""
        if not self.image_path:
            messagebox.showwarning("Warning", "Please open an image first.")
            return
        
        # Initialize rectangle variables
        self.start_x = None
        self.start_y = None
        self.current_rectangle = None
        
        # Bind mouse events for drawing the rectangle
        self.canvas.bind("<Button-1>", self.start_rectangle)
        self.canvas.bind("<B1-Motion>", self.update_rectangle)
        self.canvas.bind("<ButtonRelease-1>", self.finish_rectangle)

    def start_rectangle(self, event):
        """Start drawing a rectangle"""
        # Convert canvas coordinates to image coordinates
        img_x, img_y = self.canvas_to_image_coords(event.x, event.y)
        
        # Only create rectangle if click is within the image
        if img_x is not None and img_y is not None:
            self.start_x = event.x
            self.start_y = event.y
            self.current_rectangle = self.canvas.create_rectangle(
                self.start_x, self.start_y, event.x, event.y, 
                outline="red", width=2
            )

    def update_rectangle(self, event):
        """Update the rectangle as the user drags the mouse"""
        if self.current_rectangle and self.start_x is not None and self.start_y is not None:
            self.canvas.coords(
                self.current_rectangle,
                self.start_x, self.start_y, event.x, event.y
            )

    def finish_rectangle(self, event):
        """Finish drawing the rectangle and calculate the average color"""
        if not self.current_rectangle or self.start_x is None or self.start_y is None:
            return
            
        # Get the rectangle coordinates on canvas
        rect_coords = self.canvas.coords(self.current_rectangle)
        x1, y1, x2, y2 = map(int, rect_coords)
        
        # Ensure coordinates are ordered correctly
        if x1 > x2:
            x1, x2 = x2, x1
        if y1 > y2:
            y1, y2 = y2, y1
        
        # Convert rectangle corners to image coordinates
        img_x1, img_y1 = self.canvas_to_image_coords(x1, y1)
        img_x2, img_y2 = self.canvas_to_image_coords(x2, y2)
        
        # Process only if at least part of the rectangle is within the image
        if img_x1 is not None or img_x2 is not None or img_y1 is not None or img_y2 is not None:
            # Adjust coordinates to ensure they're within image bounds
            img_width, img_height = self.display_image.size
            
            img_x1 = max(0, img_x1) if img_x1 is not None else 0
            img_y1 = max(0, img_y1) if img_y1 is not None else 0
            img_x2 = min(img_width, img_x2) if img_x2 is not None else img_width
            img_y2 = min(img_height, img_y2) if img_y2 is not None else img_height
            
            # Only proceed if we have a valid rectangle
            if img_x1 < img_x2 and img_y1 < img_y2:
                try:
                    # Crop the region from the displayed image
                    cropped_region = self.display_image.crop((img_x1, img_y1, img_x2, img_y2))
                    
                    # Calculate the average color of the cropped region
                    pixels = np.array(cropped_region)
                    if pixels.size > 0:  # Make sure there are pixels to analyze
                        avg_color = tuple(np.mean(pixels, axis=(0, 1)).astype(int))
                        
                        # Add the average color to the selected colors
                        self.select_color(avg_color)
                except Exception as e:
                    print(f"Error in rectangle selection: {e}")
        
        # Remove the rectangle from the canvas
        self.canvas.delete(self.current_rectangle)
        
        # Reset rectangle variables
        self.start_x = None
        self.start_y = None
        self.current_rectangle = None

    def show_hover_color(self, event):
        """Show the color under the cursor as the user hovers over the image"""
        if not self.display_image:
            return
            
        # Convert canvas coordinates to image coordinates
        img_x, img_y = self.canvas_to_image_coords(event.x, event.y)
        
        # Only process if cursor is within the image
        if img_x is not None and img_y is not None:
            # Define the range for multi-pixel averaging
            range_size = 5  # Adjust this value for a larger or smaller range
            x_start = max(0, img_x - range_size)
            x_end = min(self.display_image.width, img_x + range_size)
            y_start = max(0, img_y - range_size)
            y_end = min(self.display_image.height, img_y + range_size)
            
            # Crop the region around the cursor
            cropped_region = self.display_image.crop((x_start, y_start, x_end, y_end))
            
            # Calculate the average color of the cropped region
            pixels = np.array(cropped_region)
            avg_color = tuple(np.mean(pixels, axis=(0, 1)).astype(int))
            
            # Update the color preview label
            hex_color = f'#{avg_color[0]:02x}{avg_color[1]:02x}{avg_color[2]:02x}'
            self.color_preview_label.config(text=f"Hover Color: {hex_color}", bg=hex_color)
        else:
            # Reset the label if the cursor is outside the image
            self.color_preview_label.config(text="Hover Color: None", bg="white")

    def activate_pipette_tool(self):
        """Activate the pipette tool for selecting colors"""
        if not self.image_path:
            messagebox.showwarning("Warning", "Please open an image first.")
            return

        # Bind mouse click event to the canvas
        self.canvas.bind("<Button-1>", self.pick_color_with_pipette)
    
    def select_color(self, color):
        """Add a color to the selected colors list"""
        if color not in self.selected_colors:
            self.selected_colors.append(color)
            self.update_selected_colors_display()

    def pick_color_with_pipette(self, event):
        """Pick a color from the image using the pipette tool"""
        if not self.display_image:
            return
            
        # Convert canvas coordinates to image coordinates
        img_x, img_y = self.canvas_to_image_coords(event.x, event.y)
        
        # Only pick color if cursor is within the image
        if img_x is not None and img_y is not None:
            # Define the range for multi-pixel averaging
            range_size = 5  # Adjust this value for a larger or smaller range
            x_start = max(0, img_x - range_size)
            x_end = min(self.display_image.width, img_x + range_size)
            y_start = max(0, img_y - range_size)
            y_end = min(self.display_image.height, img_y + range_size)
            
            # Crop the region around the clicked point
            cropped_region = self.display_image.crop((x_start, y_start, x_end, y_end))
            
            # Calculate the average color of the cropped region
            pixels = np.array(cropped_region)
            avg_color = tuple(np.mean(pixels, axis=(0, 1)).astype(int))
            
            # Add the picked color to the selected colors
            self.select_color(avg_color)
            
        # Unbind the pipette tool after picking a color
        self.canvas.unbind("<Button-1>")
    
    def setup_image_frame(self):
        self.canvas = tk.Canvas(self.image_frame, bg="gray")
        self.canvas.pack(fill=tk.BOTH, expand=True)
    
    def setup_color_selection_frame(self):
        self.color_selection_label = tk.Label(self.color_selection_frame, text="Available Colors:")
        self.color_selection_label.pack(anchor=tk.W)
        
        self.color_boxes_frame = tk.Frame(self.color_selection_frame)
        self.color_boxes_frame.pack(fill=tk.X, pady=5)
    
    def setup_selected_colors_frame(self):
        self.selected_colors_label = tk.Label(self.selected_colors_frame, text="Selected Colors:")
        self.selected_colors_label.pack(anchor=tk.W)
        
        self.selected_color_boxes_frame = tk.Frame(self.selected_colors_frame)
        self.selected_color_boxes_frame.pack(fill=tk.X, pady=5)
    
    def setup_options_frame(self):
        self.shadow_check = tk.Checkbutton(self.options_frame, text="Add Shadow", variable=self.shadow_var)
        self.shadow_check.pack(side=tk.LEFT, padx=5)
        
        # Font selection
        self.font_label = tk.Label(self.options_frame, text="Font:")
        self.font_label.pack(side=tk.LEFT, padx=5)
        
        self.font_dropdown = ttk.Combobox(self.options_frame, textvariable=self.font_var)
        self.font_dropdown.pack(side=tk.LEFT, padx=5)

        self.font_size_label = tk.Label(self.options_frame, text="Font Size:")
        self.font_size_label.pack(side=tk.LEFT, padx=5)

        self.font_size_spinbox = tk.Spinbox(self.options_frame, from_=8, to=72, textvariable=self.font_size_var, width=5)
        self.font_size_spinbox.pack(side=tk.LEFT, padx=5)
    
    def setup_bottom_frame(self):
        self.save_button = tk.Button(self.bottom_frame, text="Save Image", command=self.save_image)
        self.save_button.pack(side=tk.RIGHT, padx=5)
        
        self.clear_selected_button = tk.Button(self.bottom_frame, text="Clear Selected", command=self.clear_selected_colors)
        self.clear_selected_button.pack(side=tk.RIGHT, padx=5)
    
    def get_available_fonts(self):
        """Detect available fonts on the system"""
        fonts = ["default"]
        
        # Common font directories
        font_dirs = [
            # Windows
            r"C:\Windows\Fonts",
            # MacOS
            "/Library/Fonts",
            "/System/Library/Fonts",
            os.path.expanduser("~/Library/Fonts"),
            # Linux
            "/usr/share/fonts",
            "/usr/local/share/fonts",
            os.path.expanduser("~/.fonts")
        ]
        
        # Look for common font file extensions
        font_extensions = ['.ttf', '.otf', '.ttc']
        
        for font_dir in font_dirs:
            if os.path.exists(font_dir):
                for root, dirs, files in os.walk(font_dir):
                    for file in files:
                        if any(file.lower().endswith(ext) for ext in font_extensions):
                            fonts.append(os.path.join(root, file))
        
        return fonts
    
    def update_font_dropdown(self):
        """Update font dropdown with available fonts"""
        self.font_dropdown['values'] = ["default"] + [os.path.basename(f) for f in self.available_fonts if f != "default"]
        self.font_dropdown.current(0)
    
    def open_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.tif *.tiff *.bmp *.gif"),
                ("JPEG files", "*.jpg *.jpeg"),
                ("PNG files", "*.png"),
                ("TIFF files", "*.tif *.tiff"),
                ("Bitmap files", "*.bmp"),
                ("GIF files", "*.gif"),
                ("All files", "*.*")
            ]
        )
        if file_path:
            self.image_path = file_path
            self.load_image()
            self.extract_colors()
        
    def load_image(self):
        try:
            self.image = Image.open(self.image_path)
            self.resize_image_for_display()
            self.display_image_on_canvas()

            # Automatically enable live color preview
            self.canvas.bind("<Motion>", self.show_hover_color)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open image: {str(e)}")
    
    def resize_image_for_display(self):
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            # Canvas not ready yet, use default size
            canvas_width = 800
            canvas_height = 600
        
        img_width, img_height = self.image.size
        
        # Calculate new dimensions
        ratio = min(canvas_width / img_width, canvas_height / img_height)
        new_width = int(img_width * ratio)
        new_height = int(img_height * ratio)
        
        self.display_image = self.image.resize((new_width, new_height), Image.LANCZOS)
    
    def display_image_on_canvas(self):
        if self.display_image:
            # Convert to PhotoImage
            self.tk_image = tk.PhotoImage(data=self.pil_to_data(self.display_image))
            
            # Clear canvas
            self.canvas.delete("all")
            
            # Calculate position to center the image
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if canvas_width <= 1 or canvas_height <= 1:
                # Canvas not ready yet, use default size
                canvas_width = 800
                canvas_height = 600
            
            x = (canvas_width - self.display_image.width) // 2
            y = (canvas_height - self.display_image.height) // 2
            
            # Save these offsets for coordinate translation
            self.image_x_offset = x
            self.image_y_offset = y
            
            # Add image to canvas with a specific tag
            self.canvas_image_id = self.canvas.create_image(
                x, y, anchor=tk.NW, image=self.tk_image, tags="displayed_image"
            )

    def canvas_to_image_coords(self, canvas_x, canvas_y):
        """Convert canvas coordinates to image coordinates"""
        if not hasattr(self, 'image_x_offset') or not hasattr(self, 'image_y_offset'):
            return None, None
            
        # Calculate image coordinates
        img_x = canvas_x - self.image_x_offset
        img_y = canvas_y - self.image_y_offset
        
        # Check if coordinates are within the image bounds
        if 0 <= img_x < self.display_image.width and 0 <= img_y < self.display_image.height:
            return img_x, img_y
        else:
            return None, None
        
    def pil_to_data(self, image):
        """Convert PIL image to format suitable for tkinter PhotoImage"""
        # Save image to a temporary file
        temp_file = "temp_image.png"
        image.save(temp_file)
        
        # Read the file data
        with open(temp_file, "rb") as file:
            data = file.read()
        
        # Clean up
        try:
            os.remove(temp_file)
        except:
            pass
        
        return data
    
    def extract_colors(self):
        """Extract dominant colors using Gaussian Mixture Models"""
        if self.image_path:
            num_colors = 10  # Fixed number of colors
            
            # Read image with OpenCV
            img = cv2.imread(self.image_path)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Reshape the image to be a list of pixels
            pixels = img.reshape(-1, 3)
            
            # Reduce the size of the pixel list for faster processing
            sample_size = min(10000, len(pixels))
            indices = np.random.choice(len(pixels), size=sample_size, replace=False)
            sample_pixels = pixels[indices]
            
            # Apply Gaussian Mixture Model
            gmm = GaussianMixture(n_components=num_colors, random_state=42)
            gmm.fit(sample_pixels)
            
            # Get the cluster centers
            cluster_colors = gmm.means_
            
            # Convert to integer RGB tuples
            self.palette_colors = [tuple(map(int, color)) for color in cluster_colors]
            
            # Update the color selection UI
            self.update_color_selection()


    def update_color_selection(self):
        """Update the UI with extracted colors"""
        # Clear existing color boxes
        for widget in self.color_boxes_frame.winfo_children():
            widget.destroy()
        
        # Create color boxes for each dominant color
        for i, color in enumerate(self.palette_colors):
            # Create a frame for each color
            color_frame = tk.Frame(self.color_boxes_frame)
            color_frame.pack(side=tk.LEFT, padx=5)
            
            # Convert RGB to hex for Tkinter
            hex_color = f'#{color[0]:02x}{color[1]:02x}{color[2]:02x}'
            
            # Create the color box
            color_box = tk.Canvas(color_frame, width=50, height=50, bg=hex_color, 
                                  highlightthickness=1, highlightbackground="black")
            color_box.pack()
            
            # Bind click event
            color_box.bind("<Button-1>", lambda event, c=color: self.select_color(c))
            
            # Show RGB values
            rgb_label = tk.Label(color_frame, text=f"RGB: {color[0]},{color[1]},{color[2]}")
            rgb_label.pack()
    
    def select_color(self, color):
        """Add a color to the selected colors list"""
        if color not in self.selected_colors:
            self.selected_colors.append(color)
            self.update_selected_colors_display()
    
    def update_selected_colors_display(self):
        """Update the display of selected colors"""
        # Clear existing selected color boxes
        for widget in self.selected_color_boxes_frame.winfo_children():
            widget.destroy()
        
        # Create color boxes for each selected color
        for i, color in enumerate(self.selected_colors):
            # Create a frame for each color
            color_frame = tk.Frame(self.selected_color_boxes_frame)
            color_frame.pack(side=tk.LEFT, padx=5)
            
            # Convert RGB to hex for Tkinter
            hex_color = f'#{color[0]:02x}{color[1]:02x}{color[2]:02x}'
            
            # Create the color box
            color_box = tk.Canvas(color_frame, width=50, height=50, bg=hex_color, 
                                 highlightthickness=1, highlightbackground="black")
            color_box.pack()
            
            # Bind right click to remove
            color_box.bind("<Button-3>", lambda event, c=color: self.remove_selected_color(c))
            
            # Show RGB values and index
            label_text = f"{i+1}: {color[0]},{color[1]},{color[2]}"
            rgb_label = tk.Label(color_frame, text=label_text)
            rgb_label.pack()
    
    def remove_selected_color(self, color):
        """Remove a color from the selected colors list"""
        if color in self.selected_colors:
            self.selected_colors.remove(color)
            self.update_selected_colors_display()
    
    def clear_selected_colors(self):
        """Clear all selected colors"""
        self.selected_colors = []
        self.update_selected_colors_display()
    
    def extract_metadata(self):
        """Extract metadata from the image"""
        # Initialize metadata variables
        camera_make = ""
        camera_model = ""
        lens_make = ""
        lens_info = ""
        aperture = ""
        shutter = ""
        iso = ""
        date_taken = ""
        
        # Use exifread to extract metadata
        try:
            with open(self.image_path, 'rb') as f:
                tags = exifread.process_file(f, details=False)
                
                # Camera make and model
                if 'Image Make' in tags:
                    camera_make = str(tags['Image Make'])
                if 'Image Model' in tags:
                    camera_model = str(tags['Image Model'])
                
                # Lens make and info
                if 'EXIF LensMake' in tags:
                    lens_make = str(tags['EXIF LensMake'])
                if 'EXIF LensModel' in tags:
                    lens_info = str(tags['EXIF LensModel'])
                elif 'EXIF LensSpecification' in tags:
                    lens_info = str(tags['EXIF LensSpecification'])
                
                # Aperture
                if 'EXIF FNumber' in tags:
                    fnumber = tags['EXIF FNumber'].values[0]
                    aperture = f"f/{float(fnumber.num)/float(fnumber.den):.1f}"
                elif 'EXIF ApertureValue' in tags:
                    av = tags['EXIF ApertureValue'].values[0]
                    aperture = f"f/{2**(float(av.num)/float(av.den)/2):.1f}"
                
                # Shutter speed
                if 'EXIF ExposureTime' in tags:
                    et = tags['EXIF ExposureTime'].values[0]
                    if et.num < et.den:
                        shutter = f"1/{int(et.den/et.num)}s"
                    else:
                        shutter = f"{float(et.num)/float(et.den):.1f}s"
                elif 'EXIF ShutterSpeedValue' in tags:
                    ssv = tags['EXIF ShutterSpeedValue'].values[0]
                    ss = 2**(-(float(ssv.num)/float(ssv.den)))
                    if ss < 1:
                        shutter = f"1/{int(1/ss)}s"
                    else:
                        shutter = f"{ss:.1f}s"
                
                # ISO
                if 'EXIF ISOSpeedRatings' in tags:
                    iso = f"ISO{tags['EXIF ISOSpeedRatings']}"
                
                # Date
                if 'EXIF DateTimeOriginal' in tags:
                    date_taken = str(tags['EXIF DateTimeOriginal'])
        except Exception as e:
            print(f"Error extracting EXIF data: {e}")
        
        # Format the camera and lens information
        if camera_make and camera_model and not camera_model.startswith(camera_make):
            camera_info = f"{camera_make} {camera_model}"
        else:
            camera_info = camera_model
        
        if lens_make and lens_info and not lens_info.startswith(lens_make):
            lens_full_info = f"{lens_make} {lens_info}"
        else:
            lens_full_info = lens_info
        
        # Format date and time
        if date_taken:
            try:
                date_time_obj = datetime.strptime(date_taken, "%Y:%m:%d %H:%M:%S")
                formatted_date = date_time_obj.strftime("%Y.%m.%d")
                formatted_time = date_time_obj.strftime("%H:%M:%S")
            except:
                formatted_date = date_taken
                formatted_time = ""
        else:
            now = datetime.now()
            formatted_date = now.strftime("%Y.%m.%d")
            formatted_time = now.strftime("%H:%M:%S")
        
        return {
            'camera_info': camera_info,
            'lens_info': lens_full_info,
            'aperture': aperture,
            'shutter': shutter,
            'iso': iso,
            'date': formatted_date,
            'time': formatted_time
        }
    
    def get_font(self):
        """Get the selected font with the selected size"""
        font_selection = self.font_var.get()
        font_size = self.font_size_var.get()  # Get the selected font size
        
        if font_selection == "default":
            return ImageFont.load_default()
        
        # Find the actual font path from the available fonts
        for font_path in self.available_fonts:
            if os.path.basename(font_path) == font_selection:
                try:
                    return ImageFont.truetype(font_path, font_size)
                except Exception as e:
                    print(f"Error loading font {font_path}: {e}")
                    return ImageFont.load_default()
        
        return ImageFont.load_default()
    
    def preview_result(self):
        """Preview the result before saving"""
        if not self.image_path:
            messagebox.showwarning("Warning", "Please open an image first.")
            return
        
        try:
            # Extract colors if they haven't been extracted yet
            if not self.palette_colors:
                self.extract_colors()
            
            # Create the preview - use selected colors if available, otherwise use all palette colors
            colors_to_use = self.selected_colors if self.selected_colors else self.palette_colors
            preview_image = self.create_image_with_metadata_and_palette(colors_to_use)
            
            # Display the preview
            self.display_preview(preview_image)
        except Exception as e:
            messagebox.showerror("Error", f"Could not create preview: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def display_preview(self, preview_image):
        """Display the preview image"""
        # Create a new window for the preview
        preview_window = tk.Toplevel(self.root)
        preview_window.title("Preview")
        
        # Calculate the size for the preview window
        width, height = preview_image.size
        max_width = 800
        max_height = 900
        
        scale = min(max_width / width, max_height / height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        preview_window.geometry(f"{new_width}x{new_height}")
        
        # Resize the preview image
        preview_image_resized = preview_image.resize((new_width, new_height), Image.LANCZOS)
        
        # Convert to PhotoImage
        preview_tk_image = tk.PhotoImage(data=self.pil_to_data(preview_image_resized))
        
        # Create a canvas to display the preview
        preview_canvas = tk.Canvas(preview_window, width=new_width, height=new_height)
        preview_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Display the image
        preview_canvas.create_image(0, 0, anchor=tk.NW, image=preview_tk_image)
        
        # Keep a reference to prevent garbage collection
        preview_window.preview_image = preview_tk_image
    
    def create_image_with_metadata_and_palette(self, colors_to_use):
        """Create a new image with metadata and color palette"""
        # Get the original image
        img = Image.open(self.image_path)
        original_width, original_height = img.size
        
        # Extract metadata
        metadata = self.extract_metadata()
        
        # Create Instagram Stories format (9:16 aspect ratio)
        stories_ratio = 9 / 16
        
        # Determine the size of the Instagram Stories canvas
        stories_width = 1080
        stories_height = int(stories_width / stories_ratio)  # Should be 1920px
        
        # Create the white background canvas
        canvas = Image.new('RGB', (stories_width, stories_height), color=(255, 255, 255))
        
        # Define padding and section heights
        metadata_height = 180
        bottom_padding = 180
        available_height = stories_height - metadata_height - bottom_padding
        
        # Scale the original image to fit within the available area while preserving aspect ratio
        img_ratio = original_width / original_height
        
        # Add horizontal padding of 5% on each side
        horizontal_padding = int(stories_width * 0.05)
        max_image_width = stories_width - 2 * horizontal_padding
        
        if img_ratio > 1:  # Landscape image
            new_width = max_image_width
            new_height = int(new_width / img_ratio)
            if new_height > available_height:
                new_height = available_height
                new_width = int(new_height * img_ratio)
        else:  # Portrait image
            new_height = available_height
            new_width = int(new_height * img_ratio)
            if new_width > max_image_width:
                new_width = max_image_width
                new_height = int(new_width / img_ratio)
        
        # Resize the image
        img_resized = img.resize((new_width, new_height), Image.LANCZOS)
        
        # Calculate position to center the image
        x_position = (stories_width - new_width) // 2
        y_position = metadata_height + (available_height - new_height) // 2
        
        # Add shadow if requested
        if self.shadow_var.get():
            # Create a slightly larger black image for the shadow
            shadow_offset = 15
            shadow_blur = 8
            shadow = Image.new('RGBA', (new_width + shadow_blur*10, new_height + shadow_blur*10), (0, 0, 0, 0))
            
            # Create a mask for the shadow
            shadow_mask = Image.new('L', (new_width, new_height), 0)
            shadow_mask_draw = ImageDraw.Draw(shadow_mask)
            shadow_mask_draw.rectangle([(0, 0), (new_width, new_height)], fill=256)
            
            # Apply the mask to create shadow
            shadow.paste((0, 0, 0, 128), (shadow_blur, shadow_blur, shadow_blur + new_width, shadow_blur + new_height), shadow_mask)
            
            # Blur the shadow
            shadow = shadow.filter(ImageFilter.GaussianBlur(shadow_blur))
            
            # Paste the shadow onto the canvas
            shadow_x = x_position - shadow_blur + shadow_offset
            shadow_y = y_position - shadow_blur + shadow_offset
            canvas.paste(shadow, (shadow_x, shadow_y), shadow)
        
        # Paste the resized image onto the white canvas
        canvas.paste(img_resized, (x_position, y_position))
        
        draw = ImageDraw.Draw(canvas)
        
        # Make the color palette thicker and add horizontal padding
        palette_height = 80  # Thicker palette
        palette_padding = horizontal_padding  # Use same padding as image
        
        # Calculate available width for palette after padding
        palette_total_width = stories_width - (2 * palette_padding)
        palette_box_width = palette_total_width / len(colors_to_use) if colors_to_use else 0
        
        # Position palette in the middle between image bottom and canvas bottom
        image_bottom = y_position + new_height
        palette_y = image_bottom + ((stories_height - image_bottom) // 2) - (palette_height // 2)
        
        # Draw color boxes with padding
        for i, color in enumerate(colors_to_use):
            left = palette_padding + (i * palette_box_width)
            right = palette_padding + ((i + 1) * palette_box_width)
            draw.rectangle([left, palette_y, right, palette_y + palette_height], fill=color)
        
        # Get the selected font
        font = self.get_font()
        
        # Position metadata in the middle between top border and image top
        metadata_center_y = y_position // 2 - 30  # Center minus offset for text height
        
        # Draw the camera and lens information (left side)
        draw.text((20, metadata_center_y), metadata['camera_info'], fill=(0, 0, 0), font=font)
        draw.text((20, metadata_center_y + 40), metadata['lens_info'], fill=(0, 0, 0), font=font)
        
        # Draw the technical specs (right side)
        tech_info = f"{metadata['aperture']} {metadata['shutter']} {metadata['iso']}".strip()
        draw.text((stories_width - 300, metadata_center_y), tech_info, fill=(0, 0, 0), font=font)
        
        # Draw the date and time on the same line (right side, below technical specs)
        date_time_info = f"{metadata['date']} {metadata['time']}"
        draw.text((stories_width - 300, metadata_center_y + 40), date_time_info, fill=(0, 0, 0), font=font)
        
        return canvas
    
    def save_image(self):
        """Save the image with metadata and palette"""
        if not self.image_path:
            messagebox.showwarning("Warning", "Please open an image first.")
            return
        
        # Open save file dialog
        output_path = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            filetypes=[("JPEG files", "*.jpg"), ("PNG files", "*.png"), ("All files", "*.*")],
            initialfile=os.path.splitext(os.path.basename(self.image_path))[0] + "_with_metadata"
        )
        
        if not output_path:
            return
        
        try:
            # Extract colors if they haven't been extracted yet
            if not self.palette_colors:
                self.extract_colors()
            
            # Create the image - use selected colors if available, otherwise use all palette colors
            colors_to_use = self.selected_colors if self.selected_colors else self.palette_colors
            result_image = self.create_image_with_metadata_and_palette(colors_to_use)
            
            # Save with high quality
            result_image.save(output_path, quality=95, subsampling=0)
            
            messagebox.showinfo("Success", f"Image saved to {output_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save image: {str(e)}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    root = tk.Tk()
    app = MetadataPaletteGenerator(root)
    root.mainloop()