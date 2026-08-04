import os
import re

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
                    
                    # 1. Replace the styled name MoneyQuest -> MoneyQuest
                    content = re.sub(r'(?i)Forja\s*<span class="text-red-600">\s*Dev\s*</span>', 'Money<span class="text-red-600">Quest</span>', content)
                    content = re.sub(r'(?i)Forja<span class="text-red-600">Dev</span>', 'Money<span class="text-red-600">Quest</span>', content)
                    
                    # 2. Replace 'Forjar' with 'Registrar' or 'Adicionar'
                    content = content.replace('Forjar Cartão', 'Registrar Cartão')
                    content = content.replace('Forjar Líder', 'Registrar Líder')
                    content = content.replace('Forjar Nova Senha', 'Gerar Nova Senha')
                    content = content.replace('Forjar Banco', 'Registrar Banco')
                    content = content.replace('Forjar Nova Meta', 'Registrar Nova Meta')
                    content = content.replace('Forjar Mestre', 'Registrar Mestre')
                    content = content.replace('Forja de Dados', 'Baú de Dados')
                    content = content.replace('Forja de Transmutação', 'Edição de Dados')
                    content = content.replace('forjar o', 'carregar o')
                    content = content.replace('forjar um mundo', 'criar um mundo')
                    content = content.replace('Reforjar', 'Restaurar')
                    content = content.replace('MoneyQuest', 'MoneyQuest')

                    # 3. Replace data-lucide="coins" to "circle-dollar-sign" (Since they didn't like coins)
                    content = content.replace('data-lucide="coins"', 'data-lucide="circle-dollar-sign"')
                    
                    if content != original:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(content)
                        print(f'Updated {filepath}')
                except Exception as e:
                    print(f'Error {filepath}: {e}')

replace_in_files('.')
