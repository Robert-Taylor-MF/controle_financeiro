import re
from collections import defaultdict
from core.models import Transacao, Categoria

STOP_WORDS = {
    'de', 'a', 'o', 'que', 'e', 'do', 'da', 'em', 'um', 'para', 'é', 'com', 'não', 'uma', 'os', 'no', 'se', 'na', 'por', 'mais', 'as', 'dos', 'como', 'mas', 'foi', 'ao', 'ele', 'das', 'tem', 'à', 'seu', 'sua', 'ou', 'ser', 'quando', 'muito', 'há', 'nos', 'já', 'está', 'eu', 'também', 'só', 'pelo', 'pela', 'até', 'isso', 'ela', 'entre', 'era', 'depois', 'sem', 'mesmo', 'aos', 'ter', 'seus', 'quem', 'nas', 'me', 'esse', 'eles', 'estão', 'você', 'tinha', 'foram', 'essa', 'num', 'nem', 'suas', 'meu', 'às', 'minha', 'têm', 'numa', 'pelos', 'elas', 'havia', 'seja', 'qual', 'será', 'nós', 'tenho', 'lhe', 'deles', 'essas', 'esses', 'pelas', 'este', 'fosse', 'dele', 'tu', 'te', 'vocês', 'vos', 'lhes', 'meus', 'minhas', 'teu', 'tua', 'teus', 'tuas', 'nosso', 'nossa', 'nossos', 'nossas', 'dela', 'delas', 'esta', 'estes', 'estas', 'aquele', 'aquela', 'aqueles', 'aquelas', 'isto', 'aquilo',
    'pagamento', 'pgto', 'compra', 'cartao', 'pix', 'transf', 'transferencia', 'ted', 'doc'
}

def limpar_e_tokenizar(texto):
    if not texto:
        return []
    texto = texto.lower()
    # Remove special chars and digits
    texto = re.sub(r'[^a-záéíóúâêîôûãõç]', ' ', texto)
    tokens = texto.split()
    # Remove stopwords and short words
    return [t for t in tokens if t not in STOP_WORDS and len(t) > 2]

def classificar_por_memoria(descricao, user=None):
    """
    Tenta adivinhar a categoria baseando-se no histórico.
    Retorna a Categoria (objeto) ou None.
    """
    if not descricao:
        return None

    # 1. Busca Exata
    historico_exato = Transacao.objects.filter(
        descricao__iexact=descricao, 
        categoria__isnull=False
    )
    if user:
        historico_exato = historico_exato.filter(responsavel=user)
    
    match_exato = historico_exato.order_by('-data_compra').first()
    if match_exato:
        return match_exato.categoria

    # 2. Busca Fuzzy (por tokens)
    tokens_alvo = limpar_e_tokenizar(descricao)
    if not tokens_alvo:
        return None

    # Pega transacoes já categorizadas
    base_historica = Transacao.objects.filter(categoria__isnull=False)
    if user:
        base_historica = base_historica.filter(responsavel=user)
    
    # Para não carregar o banco todo na memória sempre (o que poderia ser ruim num banco enorme),
    # Usaremos uma query Q para buscar transações que contenham pelo menos um dos tokens.
    from django.db.models import Q
    query = Q()
    for token in tokens_alvo:
        query |= Q(descricao__icontains=token)
        
    candidatos = base_historica.filter(query).values('descricao', 'categoria_id')
    
    if not candidatos:
        return None

    pontuacao_categorias = defaultdict(float)
    
    for cand in candidatos:
        tokens_cand = limpar_e_tokenizar(cand['descricao'])
        if not tokens_cand:
            continue
            
        # Calcula similaridade (interseção sobre união)
        intersecao = set(tokens_alvo).intersection(set(tokens_cand))
        if intersecao:
            score = len(intersecao) / (len(set(tokens_alvo).union(set(tokens_cand))))
            pontuacao_categorias[cand['categoria_id']] += score
            
    if not pontuacao_categorias:
        return None

    # Pega a categoria com maior pontuação
    melhor_cat_id = max(pontuacao_categorias.items(), key=lambda x: x[1])[0]
    
    try:
        return Categoria.objects.get(id=melhor_cat_id)
    except Categoria.DoesNotExist:
        return None
