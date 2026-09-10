import subprocess, re

code_local = subprocess.check_output(['git', 'show', 'bkp-local:core/templates/base.html']).decode('utf-8', errors='ignore')

# Capture the modal (from <div id="modal-update-arvana" to the third closing </div>)
# We can use a simpler regex or string index to find the blocks.
modal_start = code_local.find('<div id="modal-update-arvana"')
if modal_start != -1:
    modal_end = code_local.find('<!-- END MODAL UPDATE -->', modal_start)
    if modal_end == -1:
        # If there's no comment, we'll extract by guessing the length or doing a simple split
        pass

# Since regex was tricky with the exact tags, let's just find the blocks by lines.
lines = code_local.split('\n')
modal_lines = []
indicator_lines = []
js_lines = []

in_modal = False
in_indicator = False
in_js = False

for line in lines:
    if '<div id="modal-update-arvana"' in line:
        in_modal = True
    if '<!-- END UPDATE MODAL -->' in line or (in_modal and '<div id="update-indicator-floating"' in line):
        in_modal = False
    
    if '<div id="update-indicator-floating"' in line:
        in_indicator = True
    if '<!-- END UPDATE INDICATOR -->' in line or (in_indicator and '<!-- ==========================================' in line):
        in_indicator = False

    if '// --- SISTEMA DE ATUALIZA' in line:
        in_js = True
    if in_js and '</script>' in line:
        in_js = False
        
    if in_modal:
        modal_lines.append(line)
    if in_indicator:
        indicator_lines.append(line)
    if in_js:
        js_lines.append(line)

# Fetch remote
subprocess.run(['git', 'checkout', 'origin/main', '--', 'core/templates/base.html'])
code_remote = open('core/templates/base.html', 'r', encoding='utf-8').read()

modal_str = '\n'.join(modal_lines)
indicator_str = '\n'.join(indicator_lines)
js_str = '\n'.join(js_lines)

# Inject
code_remote = code_remote.replace('</body>', f'{modal_str}\n{indicator_str}\n</body>')
# The JS should go before the LAST </script> before </body>. 
# We'll just replace the last </script>
parts = code_remote.rsplit('</script>', 1)
if len(parts) > 1:
    code_remote = f"{parts[0]}\n{js_str}\n</script>{parts[1]}"

open('core/templates/base.html', 'w', encoding='utf-8').write(code_remote)
subprocess.run(['git', 'add', 'core/templates/base.html'])
print('base.html patched.')
