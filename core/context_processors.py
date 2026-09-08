import sys
from .models import Pessoa

def dados_rpg(request):
    data = {
        'is_portable': getattr(sys, 'frozen', False)
    }
    if request.user.is_authenticated:
        titular = Pessoa.objects.filter(is_owner=True).first()
        if titular:
            data['titular_rpg'] = titular
    return data