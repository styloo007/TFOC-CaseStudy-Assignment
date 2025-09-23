from docx import Document
import re
from typing import Dict, Any

def extract_entities_from_docx(uploaded_file) -> Dict[str, Any]:
    doc = Document(uploaded_file)
    
    # Extract text from paragraphs
    text = "\n".join([para.text for para in doc.paragraphs])
    
    # Also extract text from tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text
    
    entities = {}

    # Fixed patterns for the problematic fields only
    patterns = {
        # Keep the working patterns from before
        "Party_A": r"Party A[:\s]*([A-Za-z0-9 &]+)(?:\n|$)",
        "Party_B": r"Party B[:\s]*([A-Za-z0-9 &]+)(?:\n|$)",
        "Trade_Date": r"Trade Date[:\s]*([0-9]{1,2}[\s/-][A-Za-z0-9]+[\s/-][0-9]{4})",
        "Initial_Valuation_Date": r"Initial Valuation Date[:\s]*([0-9]{1,2}[\s/-][A-Za-z0-9]+[\s/-][0-9]{4})",
        "Effective_Date": r"Effective Date[:\s]*([0-9]{1,2}[\s/-][A-Za-z0-9]+[\s/-][0-9]{4})",
        "Termination_Date": r"Termination Date[:\s]*([0-9]{1,2}[\s/-][A-Za-z0-9]+[\s/-][0-9]{4})",
        "Underlying": r"Underlying[:\s]*([^(]+(?:\([^)]*\))?[^:]*?)(?=\n|Exchange)",
        "Exchange": r"Exchange[:\s]*([A-Za-z0-9]+)",
        "Coupon": r"Coupon[^:]*[:\s]*([0-9\.]+%)",
        "Business_Day": r"Business Day[:\s]*([A-Za-z0-9]+)",
        "Trade_Time": r"Trade Time[:\s]*([0-9]{2}:[0-9]{2}:[0-9]{2})",
        "Valuation_Date": r"(?<!Initial )\bValuation Date[:\s]*([0-9]{1,2}[\s/-][A-Za-z]+[\s/-][0-9]{4})",
        "Notional_Amount": r"Notional Amount[^:]*[:\s]*([A-Z]{3}[\s]+[0-9,\.]+[\s]*[A-Za-z]+)",
        "Upfront_Payment": r"Upfront Payment[^:]*[:\s]*([^:]+?on the Effective Date)",
        "Barrier": r"Barrier[:\- ]+([\d\.]+%)",
    }
    
    # Extract entities using patterns
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            value = match.group(1).strip()
            value = re.sub(r'\s+', ' ', value)
            entities[key] = value
        else:
            entities[key] = None
    
    return entities

# Alternative approach using line-by-line processing for better accuracy
def extract_entities_line_by_line(uploaded_file) -> Dict[str, Any]:
    doc = Document(uploaded_file)
    entities = {}
    
    # Get all text content
    all_text = ""
    for para in doc.paragraphs:
        all_text += para.text + "\n"
    
    for table in doc.tables:
        for row in table.rows:
            row_cells = []
            for cell in row.cells:
                if cell.text.strip():
                    row_cells.append(cell.text.strip())
            if len(row_cells) >= 2:
                # Join with a separator to preserve key-value structure
                all_text += row_cells[0] + " | " + " ".join(row_cells[1:]) + "\n"
    
    lines = all_text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Process each problematic field specifically
        
        # 1. Valuation Date (not Initial Valuation Date)
        if 'Valuation Date' in line and 'Initial' not in line:
            # Look for the date pattern
            date_match = re.search(r'([0-9]{1,2}[\s/-][A-Za-z]+[\s/-][0-9]{4})', line)
            if date_match:
                entities['Valuation_Date'] = date_match.group(1).strip()
        
        # 2. Notional Amount - look for EUR pattern
        if 'Notional Amount' in line:
            # Look for currency and amount - include the word "million"
            amount_match = re.search(r'(EUR[\s]+[0-9,\.]+[\s]*million)', line)
            if amount_match:
                entities['Notional_Amount'] = amount_match.group(1).strip()
        
        # 3. Upfront Payment - get the TBD part
        if 'Upfront Payment' in line:
            # Look for the percentage and description
            payment_match = re.search(r'(\*\*\*TBD\*\*\*[^|]+)', line)
            if payment_match:
                entities['Upfront_Payment'] = payment_match.group(1).strip()
        
        # 4. Barrier - ensure we get 75%
        if 'Barrier' in line and 'B)' not in line:  # Avoid confusion with other uses
            # Look for percentage with potential decimal
            barrier_match = re.search(r'([0-9]+\.?[0-9]*%)', line)
            if barrier_match:
                entities['Barrier'] = barrier_match.group(1).strip()
    
    return entities

# Debug function to check specific fields
def debug_problematic_fields(uploaded_file):
    doc = Document(uploaded_file)
    
    # Get all text
    all_text = ""
    for para in doc.paragraphs:
        all_text += para.text + "\n"
    
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                all_text += cell.text + "\n"
    
    print("=== SEARCHING FOR PROBLEMATIC FIELDS ===\n")
    
    # Check Valuation Date
    print("Lines containing 'Valuation Date':")
    for line in all_text.split('\n'):
        if 'valuation date' in line.lower():
            print(f"  -> {line.strip()}")
    
    print("\nLines containing 'Notional':")
    for line in all_text.split('\n'):
        if 'notional' in line.lower():
            print(f"  -> {line.strip()}")
    
    print("\nLines containing 'Upfront':")
    for line in all_text.split('\n'):
        if 'upfront' in line.lower():
            print(f"  -> {line.strip()}")
    
    print("\nLines containing 'Barrier':")
    for line in all_text.split('\n'):
        if 'barrier' in line.lower():
            print(f"  -> {line.strip()}")
    
    print("\n=== EXTRACTION RESULTS ===")
    result1 = extract_entities_from_docx(uploaded_file)
    result2 = extract_entities_line_by_line(uploaded_file)
    
    problematic_fields = ['Valuation_Date', 'Notional_Amount', 'Upfront_Payment', 'Barrier']
    
    print("\nMethod 1 (Fixed Regex):")
    for field in problematic_fields:
        print(f"  {field}: {result1.get(field, 'NOT FOUND')}")
    
    print("\nMethod 2 (Line-by-line):")
    for field in problematic_fields:
        print(f"  {field}: {result2.get(field, 'NOT FOUND')}")
    
    return result1, result2