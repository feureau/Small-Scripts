import sys
import pandas as pd
import os

def csv_to_excel():
    if len(sys.argv) < 2:
        print("Usage: python pandasheet.py <input_file.csv>")
        sys.exit(1)
    
    input_csv = sys.argv[1]
    output_excel = os.path.splitext(input_csv)[0] + '.xlsx'
    
    try:
        # Read CSV file
        df = pd.read_csv(input_csv)
        
        # Write to Excel
        df.to_excel(output_excel, index=False)
        print(f"Successfully converted '{input_csv}' to '{output_excel}'")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    csv_to_excel()