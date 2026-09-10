import subprocess, re

# urls.py
subprocess.run(['git', 'checkout', 'origin/main', '--', 'core/urls.py'])
urls_remote = open('core/urls.py', 'r', encoding='utf-8').read()
urls_local_paths = """
    path('api/check-update/', views.api_check_update, name='api_check_update'),
    path('api/trigger-update/', views.api_trigger_update, name='api_trigger_update'),
"""
if 'api_check_update' not in urls_remote:
    urls_remote = urls_remote.replace(']', urls_local_paths + ']')
    open('core/urls.py', 'w', encoding='utf-8').write(urls_remote)

# views.py
subprocess.run(['git', 'checkout', 'origin/main', '--', 'core/views.py'])
views_remote = open('core/views.py', 'r', encoding='utf-8').read()
views_local_funcs = """
from .utils_update import check_for_updates, trigger_update_signal
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

@login_required
def api_check_update(request):
    update_available, local, remote, error = check_for_updates()
    return JsonResponse({
        'update_available': update_available,
        'local_version': local,
        'remote_version': remote,
        'error': error
    })

@login_required
@csrf_exempt
def api_trigger_update(request):
    if request.method == 'POST':
        success = trigger_update_signal()
        if success:
            return JsonResponse({'status': 'sucesso', 'mensagem': 'Sinal de sincronia enviado.'})
        return JsonResponse({'status': 'erro', 'mensagem': 'Falha.'}, status=500)
    return JsonResponse({'status': 'erro', 'mensagem': 'Metodo nao permitido'}, status=405)
"""
if 'api_check_update' not in views_remote:
    views_remote += '\n' + views_local_funcs + '\n'
    open('core/views.py', 'w', encoding='utf-8').write(views_remote)

subprocess.run(['git', 'add', 'core/urls.py', 'core/views.py'])
print('views and urls patched.')
