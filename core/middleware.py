from django.shortcuts import redirect
from django.urls import reverse
from core.models import Pessoa

class RequireOwnerMiddleware:
    """
    Verifica se existe pelo menos uma Pessoa cadastrada como Owner.
    Se a guilda não tem líder, trava o sistema e manda fundar a guilda.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                allowed_paths = [
                    reverse('setup_owner'),
                    reverse('logout'),
                    reverse('setup_admin'),
                    reverse('inicio'),
                ]
                
                # Ignora assets estáticos, mídia e painel admin padrão
                if not request.path.startswith('/admin/') and \
                   not request.path.startswith('/static/') and \
                   not request.path.startswith('/media/') and \
                   request.path not in allowed_paths:
                    
                    if not Pessoa.objects.filter(is_owner=True).exists():
                        return redirect('setup_owner')
            except Exception:
                pass # Falha ao reverter o PATH ou processar a URL
                
        response = self.get_response(request)
        return response
