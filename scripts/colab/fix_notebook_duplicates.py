"""Fix duplicate code in notebook cells."""
import json

notebook_path = "scripts/colab/vnai_ablation_study.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

fixed_count = 0

for cell_idx, cell in enumerate(nb['cells']):
    if cell['cell_type'] != 'code':
        continue
    
    lines = cell.get('source', [])
    if not isinstance(lines, list) or len(lines) < 40:
        continue
    
    # Find duplicate section starting with blank line + latency_ms
    for i in range(20, len(lines) - 5):
        if (lines[i].strip() == '' and 
            i + 1 < len(lines) and 
            'latency_ms = (time.time() - start)' in lines[i + 1]):
            # Found duplicate, truncate here
            cell['source'] = lines[:i]
            fixed_count += 1
            print(f"Fixed cell {cell_idx}: removed {len(lines) - i} duplicate lines")
            break

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print(f"\n[OK] Fixed {fixed_count} cells total")
