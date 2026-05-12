import os
import re

def clean_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove common emojis and symbols that fail in Windows CP1252
    # This includes things like 🚀, ✅, ❌, ⚠️, 📦, 🧹, 🧪, 📜, 📁, 📚
    # A safe approach is to keep only ASCII + Vietnamese characters
    
    # Vietnamese characters range:
    # A-Z, a-z, 0-9, and specific Vietnamese chars
    # For simplicity, we'll just remove anything that can't be encoded in a safe-ish way
    # or specifically target the emojis I saw.
    
    emojis = [
        '\U0001f680', # Rocket
        '\u2705',     # Check mark
        '\u274c',     # Cross mark
        '\u26a0',     # Warning
        '\U0001f4e6', # Package
        '\U0001f9f9', # Broom
        '\U0001f9ea', # Test tube
        '\U0001f4dc', # Scroll
        '\U0001f4c1', # Folder
        '\U0001f4da', # Books
        '\u231b',     # Hourglass
        '\u23f3',     # Hourglass flowing
        '\u2728',     # Sparkles
        '\U0001f4a1', # Light bulb
        '\U0001f4d1', # Bookmark tabs
        '\U0001f4c4', # Page facing up
        '\u2139',     # Info
    ]
    
    new_content = content
    for e in emojis:
        new_content = new_content.replace(e, '')
    
    # Also remove any other characters outside BMP just in case
    new_content = re.sub(r'[\U00010000-\U0010ffff]', '', new_content)
    
    if content != new_content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

app_dir = 'app'
count = 0
for root, dirs, files in os.walk(app_dir):
    for file in files:
        if file.endswith('.py'):
            if clean_file(os.path.join(root, file)):
                count += 1
print(f"Cleaned {count} files.")
