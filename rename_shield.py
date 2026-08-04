import os
def replace_in_files(directory):
    for root, dirs, files in os.walk(directory):
        if 'venv' in root or '.git' in root or '__pycache__' in root:
            continue
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    original = content
                    content = content.replace('data-lucide="shield"', 'data-lucide="coins"')
                    content = content.replace('data-lucide="shield-check"', 'data-lucide="check-circle"')
                    content = content.replace('data-lucide="shield-alert"', 'data-lucide="alert-triangle"')
                    content = content.replace("'shield-check'", "'check-circle'")
                    if content != original:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(content)
                        print(f'Updated {filepath}')
                except Exception as e:
                    pass

replace_in_files('.')
