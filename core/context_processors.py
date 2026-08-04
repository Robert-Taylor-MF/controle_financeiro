from .models import Pessoa

def dados_rpg(request):
    # Só busca os dados se alguém estiver logado no castelo
    if request.user.is_authenticated:
        # Puxa o Titular (Dono) do sistema para carregar o Level e a Foto
        titular = Pessoa.objects.filter(is_owner=True).first()
        if titular:
            return {'titular_rpg': titular}
    return {}