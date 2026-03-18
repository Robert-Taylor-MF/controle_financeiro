import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Q
from decimal import Decimal
from datetime import datetime
from .models import CartaoCredito, Transacao, Pessoa, Categoria, RendaMensal
from .services import processar_fatura_pdf
from .forms import CartaoCreditoForm, PessoaForm, CategoriaForm, RendaMensalForm
from .forms import DespesaAvulsaForm

def dashboard(request):
    # ==========================================
    # INTERCEPTADOR DE LANÇAMENTO MANUAL (POST)
    # ==========================================
    if request.method == 'POST' and request.POST.get('acao') == 'nova_despesa':
        form_despesa = DespesaAvulsaForm(request.POST)
        if form_despesa.is_valid():
            form_despesa.save()
            # Pega o mês e ano que você digitou no formulário para recarregar a tela no lugar certo
            m = request.POST.get('mes_fatura')
            a = request.POST.get('ano_fatura')
            return redirect(f"/?mes={m}&ano={a}")
            
    # ==========================================
    # LÓGICA DE EXIBIÇÃO NORMAL (GET)
    # ==========================================
    hoje = datetime.now()
    mes_atual = int(request.GET.get('mes', hoje.month))
    ano_atual = int(request.GET.get('ano', hoje.year))
    
    categorias = Categoria.objects.all()
    pessoas = Pessoa.objects.all()
    dono = Pessoa.objects.filter(is_owner=True).first()
    
    # 1. O Relógio do Sistema: Pega o mês da URL, se não tiver, usa o mês atual
    hoje = datetime.now()
    mes_atual = int(request.GET.get('mes', hoje.month))
    ano_atual = int(request.GET.get('ano', hoje.year))
    
    # 2. Vai à Tesouraria procurar a Renda ESPECÍFICA deste mês e ano
    if dono:
        renda_obj = RendaMensal.objects.filter(pessoa=dono, mes=mes_atual, ano=ano_atual).first()
        renda = float(renda_obj.valor_liquido) if renda_obj else 0.0
    else:
        renda = 0.0
        
    # 3. Calcula as fatias ideais com base no salário daquele mês
    meta_essencial = renda * 0.50
    meta_emocao = renda * 0.30
    meta_futuro = renda * 0.20
    
    # 4. TRUQUE MESTRE: Filtra os gastos apenas da competência selecionada!
    meus_gastos = Transacao.objects.filter(
        Q(responsavel=dono) | Q(responsavel__isnull=True),
        mes_fatura=mes_atual,
        ano_fatura=ano_atual
    )
    
    # 5. Soma o que já foi gasto nas categorias
    gasto_essencial = float(meus_gastos.filter(categoria__tipo_regra='ESSENCIAL').aggregate(Sum('valor'))['valor__sum'] or 0)
    gasto_emocao = float(meus_gastos.filter(categoria__tipo_regra='ESTILO_VIDA').aggregate(Sum('valor'))['valor__sum'] or 0)
    gasto_futuro = float(meus_gastos.filter(categoria__tipo_regra='FUTURO').aggregate(Sum('valor'))['valor__sum'] or 0)
    gasto_indefinido = float(meus_gastos.filter(categoria__isnull=True).aggregate(Sum('valor'))['valor__sum'] or 0)

    # 6. Calcula a percentagem consumida
    pct_essencial = min(int((gasto_essencial / meta_essencial) * 100) if meta_essencial > 0 else 0, 100)
    pct_emocao = min(int((gasto_emocao / meta_emocao) * 100) if meta_emocao > 0 else 0, 100)
    pct_futuro = min(int((gasto_futuro / meta_futuro) * 100) if meta_futuro > 0 else 0, 100)

    # 7. A lista de Loot também só mostra as coisas daquele mês
    ultimas_transacoes = Transacao.objects.filter(mes_fatura=mes_atual, ano_fatura=ano_atual).order_by('-data_compra')[:15]

    contexto = {
        'transacoes': ultimas_transacoes,
        'categorias': categorias,
        'pessoas': pessoas,
        'renda': renda,
        'gastos': {'essencial': gasto_essencial, 'emocao': gasto_emocao, 'futuro': gasto_futuro, 'indefinido': gasto_indefinido},
        'metas': {'essencial': meta_essencial, 'emocao': meta_emocao, 'futuro': meta_futuro},
        'pcts': {'essencial': pct_essencial, 'emocao': pct_emocao, 'futuro': pct_futuro},
        'mes_atual': str(mes_atual), # Passado para o HTML saber quem está selecionado
        'ano_atual': str(ano_atual),
        
        # Injetamos o formulário já com a competência atual da tela pré-preenchida!
        'form_despesa': DespesaAvulsaForm(initial={
            'mes_fatura': mes_atual, 
            'ano_fatura': ano_atual,
            'data_compra': hoje.strftime('%Y-%m-%d')
        }),
    }
    
    return render(request, 'dashboard.html', contexto)

def importar_fatura(request):
    # Busca os cartões no banco para montar o "Select" (dropdown) na tela
    cartoes = CartaoCredito.objects.all()
    
    if request.method == 'POST':
        # Recebe o arquivo PDF e o ID do cartão selecionado
        arquivo_pdf = request.FILES.get('fatura_pdf')
        cartao_id = request.POST.get('cartao_id')
        mes_fatura = request.POST.get('mes_fatura')
        ano_fatura = request.POST.get('ano_fatura')
        
        if arquivo_pdf and cartao_id and mes_fatura and ano_fatura:
            sucesso, mensagem = processar_fatura_pdf(arquivo_pdf, cartao_id, mes_fatura, ano_fatura)
            if sucesso:
                # O Django tem um sistema nativo de alertas (messages) para a tela
                messages.success(request, mensagem)
            else:
                messages.error(request, mensagem)
        else:
            messages.warning(request, "Por favor, selecione um cartão e envie um PDF.")
            
    return render(request, 'importar_fatura.html', {'cartoes': cartoes})

def central_cadastros(request):
    if request.method == 'POST':
        acao = request.POST.get('acao')
        
        if acao == 'cartao':
            form = CartaoCreditoForm(request.POST)
            if form.is_valid(): form.save(); messages.success(request, "Arma (Cartão) forjada com sucesso!")
        elif acao == 'pessoa':
            form = PessoaForm(request.POST)
            if form.is_valid(): form.save(); messages.success(request, "Novo aliado recrutado para a Guilda!")
        elif acao == 'categoria':
            form = CategoriaForm(request.POST)
            if form.is_valid(): form.save(); messages.success(request, "Novo encantamento (Categoria) adicionado ao Grimório!")
        elif acao == 'renda':
            form = RendaMensalForm(request.POST)
            if form.is_valid(): form.save(); messages.success(request, "Mana (Renda Mensal) canalizada com sucesso!")
            
        return redirect('central_cadastros')
    
    # Se for GET (apenas a carregar a página), preparamos os 4 formulários e as listas
    contexto = {
        'form_cartao': CartaoCreditoForm(),
        'form_pessoa': PessoaForm(),
        'form_categoria': CategoriaForm(),
        'form_renda': RendaMensalForm(),
        'cartoes': CartaoCredito.objects.all(),
        'pessoas': Pessoa.objects.all(),
        'categorias': Categoria.objects.all(),
        'rendas': RendaMensal.objects.all().order_by('-ano', '-mes'),
    }
    return render(request, 'central_cadastros.html', contexto)

def ratear_transacao(request, transacao_id):
    # Puxa a transação original do banco
    transacao_original = get_object_or_404(Transacao, id=transacao_id)
    # Puxa todas as pessoas cadastradas para você escolher com quem dividir
    pessoas = Pessoa.objects.filter(ativo=True)
    
    if request.method == 'POST':
        # Vamos somar para garantir que você não dividiu errado (ex: dividiu 140 sendo que a conta era 130)
        soma_rateio = Decimal('0.00')
        novos_registros = []
        
        for pessoa in pessoas:
            # Pega o valor digitado para essa pessoa no formulário (se houver)
            valor_str = request.POST.get(f'valor_pessoa_{pessoa.id}')
            
            if valor_str and float(valor_str) > 0:
                valor_decimal = Decimal(valor_str.replace(',', '.'))
                soma_rateio += valor_decimal
                
                # Prepara a nova transação
                descricao_rateio = f"{transacao_original.descricao} (Rateio: {pessoa.nome})"
                
                novos_registros.append(
                    Transacao(
                        descricao=descricao_rateio,
                        valor=valor_decimal,
                        data_compra=transacao_original.data_compra,
                        responsavel=pessoa,
                        cartao=transacao_original.cartao,
                        categoria=transacao_original.categoria,
                        status=transacao_original.status
                    )
                )
        
        # Regra de Ouro Financeira: O rateio TEM que bater com o valor original
        if soma_rateio != transacao_original.valor:
            messages.error(request, f"A soma da divisão (R$ {soma_rateio}) não bate com o valor original (R$ {transacao_original.valor}).")
        else:
            # Salva as novas transações no banco
            Transacao.objects.bulk_create(novos_registros)
            # Deleta a transação original para não duplicar sua fatura
            transacao_original.delete()
            
            messages.success(request, "Despesa fragmentada com sucesso!")
            return redirect('dashboard') # Volta para a tela inicial
            
    return render(request, 'ratear_transacao.html', {
        'transacao': transacao_original,
        'pessoas': pessoas
    })
    
def extrato_faturas(request):
    transacoes = Transacao.objects.all().order_by('-data_compra')
    cartoes = CartaoCredito.objects.all()
    categorias = Categoria.objects.all()

    # Captura os filtros que vierem pela URL (método GET)
    mes = request.GET.get('mes')
    ano = request.GET.get('ano')
    cartao_id = request.GET.get('cartao_id')

    # Aplica os filtros no QuerySet se eles existirem
    if mes:
        transacoes = transacoes.filter(mes_fatura=mes)
    if ano:
        transacoes = transacoes.filter(ano_fatura=ano)
    if cartao_id:
        transacoes = transacoes.filter(cartao_id=cartao_id)

    # Valores padrão para os campos do filtro não ficarem vazios
    contexto = {
        'transacoes': transacoes,
        'cartoes': cartoes,
        'categorias': categorias,
        'mes_atual': mes or str(datetime.now().month),
        'ano_atual': ano or str(datetime.now().year),
        'cartao_selecionado': cartao_id or "",
        'pessoas': Pessoa.objects.all()
    }
    return render(request, 'extrato.html', contexto)

@csrf_exempt  # <-- O Feitiço que baixa o escudo de segurança para esta API
def atualizar_categoria(request, transacao_id):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            nova_categoria_id = dados.get('categoria_id')
            
            transacao = Transacao.objects.get(id=transacao_id)
            
            if nova_categoria_id:
                transacao.categoria_id = nova_categoria_id
            else:
                transacao.categoria = None
                
            transacao.save()
            return JsonResponse({'status': 'sucesso'})
        except Exception as e:
            # Imprime o erro real no terminal negro do Django
            print(f"\n[ERRO API CATEGORIA] Falha ao forjar: {str(e)}\n")
            return JsonResponse({'status': 'erro', 'mensagem': str(e)}, status=400)

@csrf_exempt  # <-- O Feitiço que baixa o escudo de segurança para esta API
def atualizar_responsavel(request, transacao_id):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            nova_pessoa_id = dados.get('pessoa_id')
            
            transacao = Transacao.objects.get(id=transacao_id)
            
            if nova_pessoa_id:
                transacao.responsavel_id = nova_pessoa_id
            else:
                transacao.responsavel = None
                
            transacao.save()
            return JsonResponse({'status': 'sucesso'})
        except Exception as e:
            # Imprime o erro real no terminal negro do Django
            print(f"\n[ERRO API RESPONSAVEL] Falha ao forjar: {str(e)}\n")
            return JsonResponse({'status': 'erro', 'mensagem': str(e)}, status=400)
        
def sala_de_guerra(request):
    dono = Pessoa.objects.filter(is_owner=True).first()
    hoje = datetime.now()

    # O Relógio do Sistema com interceção do filtro (A "Máquina do Tempo")
    mes_atual = int(request.GET.get('mes', hoje.month))
    ano_atual = int(request.GET.get('ano', hoje.year))

    # ==========================================
    # KPI 1: Distribuição de Gastos da COMPETÊNCIA SELECIONADA
    # ==========================================
    gastos_mes = Transacao.objects.filter(responsavel=dono, mes_fatura=mes_atual, ano_fatura=ano_atual)

    categorias_labels = []
    categorias_dados = []
    
    for cat in Categoria.objects.all():
        total = gastos_mes.filter(categoria=cat).aggregate(Sum('valor'))['valor__sum'] or 0
        if total > 0:
            categorias_labels.append(cat.nome)
            categorias_dados.append(float(total))

    total_indefinido = gastos_mes.filter(categoria__isnull=True).aggregate(Sum('valor'))['valor__sum'] or 0
    if total_indefinido > 0:
        categorias_labels.append("Loot Indefinido")
        categorias_dados.append(float(total_indefinido))

    # ==========================================
    # KPI 2: Evolução (Últimos 6 Meses)
    # ==========================================
    historico_labels = []
    historico_gastos = []
    historico_receitas = []

    for i in range(5, -1, -1):
        # A evolução sempre se baseia no mês atual do relógio para manter os 6 meses fixos
        m = hoje.month - i
        a = hoje.year
        if m <= 0:
            m += 12
            a -= 1

        historico_labels.append(f"{m:02d}/{a}")

        total_gasto = Transacao.objects.filter(
            responsavel=dono, mes_fatura=m, ano_fatura=a
        ).aggregate(Sum('valor'))['valor__sum'] or 0
        historico_gastos.append(float(total_gasto))

        renda_obj = RendaMensal.objects.filter(pessoa=dono, mes=m, ano=a).first()
        total_receita = float(renda_obj.valor_liquido) if renda_obj else 0.0
        historico_receitas.append(total_receita)

    contexto = {
        'cat_labels': json.dumps(categorias_labels),
        'cat_dados': json.dumps(categorias_dados),
        'hist_labels': json.dumps(historico_labels),
        'hist_gastos': json.dumps(historico_gastos),
        'hist_receitas': json.dumps(historico_receitas),
        'mes_atual': str(mes_atual), # Passamos para o select do HTML
        'ano_atual': str(ano_atual),
    }
    
    return render(request, 'sala_de_guerra.html', contexto)