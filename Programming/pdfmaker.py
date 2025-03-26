import sys
import glob
import argparse
import io
from PIL import Image, ImageOps

def merge_images_to_pdf(files, output_pdf, dpi, compression, rotate, resize, grayscale, verbose):
    image_list = []
    for file in files:
        try:
            if verbose:
                print(f"Processing file: {file}")
            im = Image.open(file)
            
            # Rotate image if requested
            if rotate:
                im = im.rotate(rotate, expand=True)
                if verbose:
                    print(f"Rotated {file} by {rotate} degrees")
            
            # Resize image if requested
            if resize:
                try:
                    width, height = map(int, resize.split('x'))
                    im = im.resize((width, height), Image.ANTIALIAS)
                    if verbose:
                        print(f"Resized {file} to {width}x{height}")
                except Exception as e:
                    print(f"Error resizing {file}: {e}")
            
            # Convert to grayscale if requested
            if grayscale:
                im = ImageOps.grayscale(im)
                if verbose:
                    print(f"Converted {file} to grayscale")
            
            # Ensure image is in RGB mode (needed for PDF conversion)
            if im.mode in ("RGBA", "P"):
                im = im.convert("RGB")
            
            # Apply compression by converting the image to JPEG in memory if compression is set
            if compression:
                if verbose:
                    print(f"Compressing {file} to JPEG at {compression}% quality")
                img_byte_arr = io.BytesIO()
                im.save(img_byte_arr, format="JPEG", quality=compression)
                img_byte_arr.seek(0)
                im = Image.open(img_byte_arr)
                # Convert again to RGB in case mode changed
                if im.mode in ("RGBA", "P"):
                    im = im.convert("RGB")
            
            image_list.append(im)
        except Exception as e:
            print(f"Error processing {file}: {e}")

    if not image_list:
        print("No valid images to merge.")
        sys.exit(1)
    
    # Save the first image and append the rest as additional pages in the PDF.
    image_list[0].save(output_pdf, "PDF", resolution=dpi, save_all=True, append_images=image_list[1:])
    print(f"PDF saved as {output_pdf}")

def parse_arguments():
    parser = argparse.ArgumentParser(description="Merge images into a single PDF file using glob patterns.")
    parser.add_argument("pattern", help="Glob pattern for the images (e.g., '*.jpg').")
    parser.add_argument("-o", "--output", default="output.pdf", help="Output PDF file name. Default is output.pdf")
    parser.add_argument("-c", "--compression", type=int, default=75, help="JPEG compression quality percentage. Default is 75.")
    parser.add_argument("-d", "--dpi", type=int, default=100, help="DPI for the output PDF. Default is 100.")
    parser.add_argument("-r", "--rotate", type=int, default=0, help="Rotate images by specified degrees before merging. Default is 0.")
    parser.add_argument("-s", "--resize", help="Resize images to WIDTHxHEIGHT (e.g., 1024x768).")
    parser.add_argument("-g", "--grayscale", action="store_true", help="Convert images to grayscale.")
    parser.add_argument("--order", choices=['name', 'date'], default='name', help="Order to sort images: by name or modification date. Default is name.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output.")
    
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    # Get files using glob
    files = sorted(glob.glob(args.pattern))
    if args.order == 'date':
        files.sort(key=lambda x: glob.os.path.getmtime(x))
    
    if not files:
        print(f"No images found matching pattern: {args.pattern}")
        sys.exit(1)
    
    merge_images_to_pdf(files, args.output, args.dpi, args.compression, args.rotate, args.resize, args.grayscale, args.verbose)

if __name__ == "__main__":
    main()
