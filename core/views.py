import json
import urllib.parse
import decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Q
from decimal import Decimal
from datetime import datetime, date
from .models import CartaoCredito, Transacao, Pessoa, Categoria, RendaMensal, Instituicao, Cofre, HistoricoCofre
from .services import processar_fatura_pdf
from .forms import CartaoCreditoForm, PessoaForm, CategoriaForm, RendaMensalForm, InstituicaoForm, CofreForm
from .forms import DespesaAvulsaForm

@login_required
def dashboard(request):
    # ==========================================
    # INTERCEPTADOR DE LANÇAMENTO MANUAL (POST)
    # ==========================================
    if request.method == 'POST' and request.POST.get('acao') == 'nova_despesa':
        form_despesa = DespesaAvulsaForm(request.POST)
        if form_despesa.is_valid():
            form_despesa.save()
            
            # ==========================================
            # MISSÃO DIÁRIA: RECOMPENSA DE XP
            # ==========================================
            titular = Pessoa.objects.filter(is_owner=True).first()
            if titular:
                subiu_de_nivel = titular.ganhar_xp(5)
                if subiu_de_nivel:
                    messages.success(request, f"LEVEL UP! Parabéns, você avançou para o Nível {titular.level}! 🚀")
                else:
                    messages.success(request, "Missão Diária concluída: Gasto anotado na hora vale ouro! (+5 XP) 🛡️")
            else:
                messages.success(request, "Despesa registrada com sucesso!")
                
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

    # 8. NOVO CÁLCULO: Puxa o tesouro total para o novo Card
    cofres = Cofre.objects.all()
    tesouro_total = sum(c.saldo_atual for c in cofres)
    
    # 9. PUXAR CARTÕES (Precisamos deles para o Modal do Oráculo funcionar no Dashboard)
    cartoes = CartaoCredito.objects.all()

    # 10. GASTOS DA PARTY (Visão da Party)
    gastos_party = []
    todos_gastos_mes = Transacao.objects.filter(mes_fatura=mes_atual, ano_fatura=ano_atual)
    for p in pessoas:
        total_p = todos_gastos_mes.filter(responsavel=p).aggregate(Sum('valor'))['valor__sum'] or 0
        gastos_party.append({
            'pessoa': p,
            'total': float(total_p)
        })
    total_sem_dono = todos_gastos_mes.filter(responsavel__isnull=True).aggregate(Sum('valor'))['valor__sum'] or 0

    # 11. CÁLCULO DE SALDO RESTANTE (Mana - Meus Gastos)
    total_gasto_pessoal = gasto_essencial + gasto_emocao + gasto_futuro + gasto_indefinido
    saldo_restante = renda - total_gasto_pessoal

    contexto = {
        'transacoes': ultimas_transacoes,
        'categorias': categorias,
        'pessoas': pessoas,
        'renda': renda,
        'saldo_restante': saldo_restante,
        'gastos': {'essencial': gasto_essencial, 'emocao': gasto_emocao, 'futuro': gasto_futuro, 'indefinido': gasto_indefinido},
        'metas': {'essencial': meta_essencial, 'emocao': meta_emocao, 'futuro': meta_futuro},
        'pcts': {'essencial': pct_essencial, 'emocao': pct_emocao, 'futuro': pct_futuro},
        'mes_atual': str(mes_atual), # Passado para o HTML saber quem está selecionado
        'ano_atual': str(ano_atual),
        'tesouro_total': float(tesouro_total),
        'cartoes': cartoes, # <- Adicione isso para o Modal saber quais cartões existem
        'gastos_party': gastos_party,
        'total_sem_dono': float(total_sem_dono),
        
        # Injetamos o formulário já com a competência atual da tela pré-preenchida!
        'form_despesa': DespesaAvulsaForm(initial={
            'mes_fatura': mes_atual, 
            'ano_fatura': ano_atual,
            'data_compra': hoje.strftime('%Y-%m-%d')
        }),
    }
    
    return render(request, 'dashboard.html', contexto)

@login_required
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
                messages.success(request, f"O Oráculo completou a extração! Todos os loots foram armazenados. Detalhes: {mensagem}")
                # Direciona para a página de Pergaminhos (Extrato) já com os filtros do mês, ano e cartão selecionados!
                return redirect(f"/extrato/?mes={mes_fatura}&ano={ano_fatura}&cartao_id={cartao_id}")
            else:
                messages.error(request, mensagem)
        else:
            messages.warning(request, "Por favor, selecione um cartão e envie um PDF.")
            
        # Mesmo se falhar, redirecionamos para o dashboard (pois a requisição veio do modal de lá)
        return redirect('dashboard')
            
    # Se alguém tentar acessar a URL diretamente por GET, joga de volta pro Dashboard
    return redirect('dashboard')

@login_required
def central_cadastros(request):
    if request.method == 'POST':
        acao = request.POST.get('acao')
        
        if acao == 'cartao':
            form = CartaoCreditoForm(request.POST)
            if form.is_valid(): form.save(); messages.success(request, "Arma (Cartão) forjada com sucesso!")
        elif acao == 'pessoa':
            form = PessoaForm(request.POST, request.FILES)
            form = PessoaForm(request.POST)
            if form.is_valid(): form.save(); messages.success(request, "Novo aliado recrutado para a Guilda!")
        elif acao == 'categoria':
            form = CategoriaForm(request.POST)
            if form.is_valid(): form.save(); messages.success(request, "Novo encantamento (Categoria) adicionado ao Grimório!")
        elif acao == 'renda':
            form = RendaMensalForm(request.POST)
            if form.is_valid(): form.save(); messages.success(request, "Mana (Renda Mensal) canalizada com sucesso!")
        elif acao == 'oraculo':
            api_key = request.POST.get('api_key_gemini', '')
            user = request.user
            from .models import MestreSeguranca
            m_seg, created = MestreSeguranca.objects.get_or_create(user=user, defaults={'pergunta_secreta': '-', 'resposta_secreta': '-'})
            m_seg.set_api_key(api_key)
            m_seg.save()
            messages.success(request, "A essência do Oráculo foi renovada com sucesso!")
        elif acao == 'configurar_backup':
            frequencia = request.POST.get('frequencia', 'MANUAL')
            horario = request.POST.get('horario')
            dias_list = request.POST.getlist('dias')
            dias = ",".join(dias_list) if dias_list else ""
            diretorio = request.POST.get('diretorio')
            
            user = request.user
            from .models import MestreSeguranca
            m_seg, created = MestreSeguranca.objects.get_or_create(user=user, defaults={'pergunta_secreta': '-', 'resposta_secreta': '-'})
            m_seg.frequencia_backup = frequencia
            m_seg.dias_backup = dias
            m_seg.diretorio_backup = diretorio
            
            if horario:
                m_seg.horario_backup = horario
            else:
                m_seg.horario_backup = None
                
            m_seg.save()
            messages.success(request, "Cronograma do Guardião do Tempo foi calibrado.")
        
        elif acao == 'backup_manual':
            from .backup_service import gerar_zip_backup
            caminho = gerar_zip_backup()
            messages.success(request, f"Bênção Temporal! Backup guardado com sucesso: {caminho}")
            
        elif acao == 'restauro_critico':
            senha = request.POST.get('senha_mestre')
            
            # Validação severa da senha da pessoa rodando o backup
            from django.contrib.auth import authenticate
            if not authenticate(username=request.user.username, password=senha):
                messages.error(request, "Senha Mestra incorreta! Protocolo de Restauração Abortado.")
                return redirect('central_cadastros')
                
            if request.FILES.get('arquivo_zip'):
                zip_file = request.FILES['arquivo_zip']
                import zipfile, os, shutil
                from django.conf import settings
                from django.db import connection
                
                tmp_dir = os.path.join(settings.BASE_DIR, 'tmp_restore')
                os.makedirs(tmp_dir, exist_ok=True)
                
                try:
                    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                        zip_ref.extractall(tmp_dir)
                        
                    db_extracted = os.path.join(tmp_dir, 'db.sqlite3')
                    media_extracted = os.path.join(tmp_dir, 'media')
                    
                    connection.close() # Solta o arquivo pro SO
                    
                    if os.path.exists(db_extracted):
                        shutil.copy2(db_extracted, os.path.join(settings.BASE_DIR, 'db.sqlite3'))
                    
                    if os.path.exists(media_extracted):
                        media_target = os.path.join(settings.BASE_DIR, 'media')
                        if os.path.exists(media_target):
                            shutil.rmtree(media_target)
                        shutil.copytree(media_extracted, media_target)
                        
                    messages.success(request, "Cronos obedece! O banco de dados foi completamente reconstruído pela linha do tempo importada. Acesse o sistema novamente.")
                    from django.contrib.auth import logout
                    logout(request)
                    return redirect('login') 
                    
                except Exception as e:
                    messages.error(request, f"Erro fatal ao invocar o túnel do tempo: {str(e)}")
                finally:
                    if os.path.exists(tmp_dir):
                        shutil.rmtree(tmp_dir)
            
        return redirect('central_cadastros')
    
    # Se for GET (apenas a carregar a página), preparamos os 4 formulários e as listas
    import os
    ms = getattr(request.user, 'seguranca', None)
    oraculo_key = ms.get_api_key() if ms else None
    has_env_fallback = bool(not oraculo_key and os.getenv("GEMINI_API_KEY"))
    
    backup_config = {
        'frequencia': ms.frequencia_backup if ms else 'MANUAL',
        'horario': ms.horario_backup if ms else None,
        'dias': ms.dias_backup if ms else '',
        'diretorio': ms.diretorio_backup if ms else '',
    }

    contexto = {
        'form_cartao': CartaoCreditoForm(),
        'form_pessoa': PessoaForm(),
        'form_categoria': CategoriaForm(),
        'form_renda': RendaMensalForm(),
        'cartoes': CartaoCredito.objects.all(),
        'pessoas': Pessoa.objects.all(),
        'categorias': Categoria.objects.all(),
        'rendas': RendaMensal.objects.all().order_by('-ano', '-mes'),
        'oraculo_key': oraculo_key,
        'has_env_fallback': has_env_fallback,
        'backup_config': backup_config
    }
    return render(request, 'central_cadastros.html', contexto)

@login_required
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
            
            messages.success(request, "Despesa fragmentada com sucesso (Rateio aplicado)!")
            
    # Redireciona de forma transparente para onde o usuário estava (Dashboard ou Extrato)
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

@login_required    
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

@login_required        
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
        
    # ==========================================
    # KPI 3: O Bestiário (Top 5 Ofensores do Mês)
    # ==========================================
    # Agrupa por nome do estabelecimento, soma os valores e ordena do maior para o menor
    top_gastos = gastos_mes.values('descricao').annotate(total=Sum('valor')).order_by('-total')[:5]
    
    top_labels = [item['descricao'] for item in top_gastos]
    top_dados = [float(item['total']) for item in top_gastos]

    contexto = {
        'cat_labels': json.dumps(categorias_labels),
        'cat_dados': json.dumps(categorias_dados),
        'hist_labels': json.dumps(historico_labels),
        'hist_gastos': json.dumps(historico_gastos),
        'hist_receitas': json.dumps(historico_receitas),
        'top_labels': json.dumps(top_labels),
        'top_dados': json.dumps(top_dados),
        'mes_atual': str(mes_atual), # Passamos para o select do HTML
        'ano_atual': str(ano_atual),
    }
    
    return render(request, 'sala_de_guerra.html', contexto)

@login_required
@csrf_exempt
def deletar_transacao(request, transacao_id):
    if request.method == 'DELETE': # Note que agora usamos o método DELETE
        try:
            transacao = Transacao.objects.get(id=transacao_id)
            transacao.delete()
            return JsonResponse({'status': 'sucesso', 'mensagem': 'Loot obliterado!'})
        except Exception as e:
            print(f"\n[ERRO API DELETAR] Falha ao destruir: {str(e)}\n")
            return JsonResponse({'status': 'erro', 'mensagem': str(e)}, status=400)
            
@login_required
@csrf_exempt
def deletar_fatura(request, mes, ano, cartao_id):
    if request.method == 'DELETE':
        try:
            deletados, _ = Transacao.objects.filter(
                mes_fatura=mes, 
                ano_fatura=ano, 
                cartao_id=cartao_id
            ).delete()
            return JsonResponse({'status': 'sucesso', 'mensagem': f'{deletados} loots obliterados!'})
        except Exception as e:
            print(f"\n[ERRO API OBLITERAR] Falha na magia: {str(e)}\n")
            return JsonResponse({'status': 'erro', 'mensagem': str(e)}, status=400)
        
# ==========================================
# MURAL DE RECOMPENSAS E FATURAMENTO
# ==========================================



@login_required
def fatura_pdf(request):
    pessoa_id = request.GET.get('pessoa_id')
    mes = int(request.GET.get('mes', datetime.now().month))
    ano = int(request.GET.get('ano', datetime.now().year))

    # Busca o devedor e o dono do sistema (você)
    aliado = Pessoa.objects.get(id=pessoa_id)
    dono = Pessoa.objects.filter(is_owner=True).first()

    # Busca as dívidas específicas da pessoa neste mês e soma tudo
    transacoes = Transacao.objects.filter(responsavel=aliado, mes_fatura=mes, ano_fatura=ano).order_by('data_compra')
    total = transacoes.aggregate(Sum('valor'))['valor__sum'] or 0

    # Cria a mensagem inteligente para o WhatsApp
    texto_zap = f"Fala {aliado.nome}! Aqui é o {dono.nome if dono else 'Titular'}. O fechamento da nossa party referente a {mes:02d}/{ano} deu R$ {float(total):.2f}. Segue a fatura! ⚔️"
    
    # Monta o link da API do WhatsApp (se ele tiver telefone cadastrado)
    link_zap = ""
    if aliado.telefone:
        numero_limpo = ''.join(filter(str.isdigit, aliado.telefone))
        link_zap = f"https://wa.me/55{numero_limpo}?text={urllib.parse.quote(texto_zap)}"

    contexto = {
        'aliado': aliado,
        'dono': dono,
        'transacoes': transacoes,
        'total': float(total),
        'mes': f"{mes:02d}",
        'ano': ano,
        'link_zap': link_zap,
        'data_emissao': datetime.now().strftime('%d/%m/%Y')
    }
    
    return render(request, 'fatura_pdf.html', contexto)

# ==========================================
# FORJA DE TRANSMUTAÇÃO (EDIÇÃO UNIVERSAL)
# ==========================================
@login_required
def editar_cadastro(request, tipo, id):
    # Um "dicionário mágico" que mapeia o que você clicou para o modelo e formulário corretos
    mapa_modelos = {
        'cartao': (CartaoCredito, CartaoCreditoForm, 'Arma (Cartão)'),
        'pessoa': (Pessoa, PessoaForm, 'Aliado (Pessoa)'),
        'categoria': (Categoria, CategoriaForm, 'Encantamento (Categoria)'),
        'renda': (RendaMensal, RendaMensalForm, 'Mana (Renda)'),
        'cofre': (Cofre, CofreForm, 'Baú (Cofrinho)'),
        'instituicao': (Instituicao, InstituicaoForm, 'Banco (Instituição)'),
    }

    # Se alguém tentar acessar uma URL que não existe, joga de volta pro QG
    if tipo not in mapa_modelos:
        return redirect('central_cadastros')

from django.http import JsonResponse
def api_selecionar_pasta(request):
    """
    Aciona o Tkinter localmente na máquina servidora (Seu Windows) 
    para abrir o diálago nativo de "Selecionar Pasta" e devolver o Target Dir.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        folder = filedialog.askdirectory(parent=root, title="Onde o Guardião deve salvar?")
        root.destroy()
        return JsonResponse({'path': folder})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

import json
def api_status_backup(request):
    """Lê o arquivo de estado do backup forjado na thread de background"""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'none'})
    status_file = os.path.join(settings.BASE_DIR, 'backups', 'status.json')
    if os.path.exists(status_file):
        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return JsonResponse(data)
        except Exception:
            return JsonResponse({'status': 'none'})
    return JsonResponse({'status': 'none'})

    Modelo, Formulario, nome_entidade = mapa_modelos[tipo]
    
    # Busca o item exato no banco de dados
    instancia = get_object_or_404(Modelo, id=id)

    if request.method == 'POST':
        # Carrega o formulário com os dados novos enviados pela tela, substituindo a instância velha
        form = Formulario(request.POST, request.FILES, instance=instancia)
        if form.is_valid():
            form.save()
            return redirect('central_cadastros')
    else:
        # Se for GET, apenas desenha o formulário já preenchido com os dados atuais
        form = Formulario(instance=instancia)

    contexto = {
        'form': form,
        'nome_entidade': nome_entidade,
        'tipo': tipo,
    }
    return render(request, 'editar_cadastro.html', contexto)

# ==========================================
# BANCO DA GUILDA (WEALTH MANAGEMENT)
# ==========================================

@login_required
def banco_guilda(request):
    # Processa o envio dos formulários de Nova Instituição ou Novo Cofre
    if request.method == 'POST':
        acao = request.POST.get('acao')
        if acao == 'instituicao':
            form = InstituicaoForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Instituição forjada com sucesso!")
                return redirect('banco_guilda')
        elif acao == 'cofre':
            form = CofreForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Novo Cofrinho ativado com sucesso!")
                return redirect('banco_guilda')

    instituicoes = Instituicao.objects.all()
    cofres = Cofre.objects.all().order_by('instituicao__nome')
    tesouro_total = sum(c.saldo_atual for c in cofres)

    # ==========================================
    # DATA SCIENCE: LIVRO RAZÃO E ALERTAS
    # ==========================================
    # Soma tudo que saiu e subtrai tudo que foi devolvido como reposição
    total_saidas = HistoricoCofre.objects.filter(tipo='saida').aggregate(Sum('valor'))['valor__sum'] or 0
    total_reposicoes = HistoricoCofre.objects.filter(tipo='reposicao').aggregate(Sum('valor'))['valor__sum'] or 0
    
    total_sacado = total_saidas - total_reposicoes
    if total_sacado < 0:
        total_sacado = 0 # Garante que a dívida nunca fique negativa

    # Agrupamento: Para onde foi o ouro sacado?
    saques_motivos = HistoricoCofre.objects.filter(tipo='saida').values('motivo').annotate(total=Sum('valor'))
    
    # Traduz a sigla do banco de dados para o texto bonito
    motivos_dict = dict(HistoricoCofre.MOTIVO_CHOICES)
    motivos_labels = [motivos_dict.get(item['motivo'], 'Outro') for item in saques_motivos]
    motivos_dados = [float(item['total']) for item in saques_motivos]

    contexto = {
        'form_instituicao': InstituicaoForm(),
        'form_cofre': CofreForm(),
        'cofres': cofres,
        'instituicoes': instituicoes,
        'tesouro_total': float(tesouro_total),
        'total_sacado': float(total_sacado),
        'motivos_labels': json.dumps(motivos_labels),
        'motivos_dados': json.dumps(motivos_dados),
    }
    return render(request, 'banco_guilda.html', contexto)

@login_required
@csrf_exempt
def atualizar_cofre(request, cofre_id):
    """ API para depositar ou sacar ouro gravando no Livro Razão e dando XP """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            valor = decimal.Decimal(str(data.get('valor', 0)))
            tipo = data.get('tipo') 
            motivo = data.get('motivo') 
            
            cofre = Cofre.objects.get(id=cofre_id)
            
            # Puxa o seu personagem para dar o XP
            titular = Pessoa.objects.filter(is_owner=True).first()
            
            if tipo == 'depositar':
                cofre.saldo_atual += valor
                HistoricoCofre.objects.create(cofre=cofre, tipo='entrada', valor=valor)
                # Recompensa: +50 XP por guardar dinheiro
                if titular: titular.ganhar_xp(50)
                
            elif tipo == 'repor':
                cofre.saldo_atual += valor
                HistoricoCofre.objects.create(cofre=cofre, tipo='reposicao', valor=valor)
                # Recompensa: +50 XP por pagar a dívida com o seu futuro
                # if titular: titular.ganhar_xp(50)
                
            elif tipo == 'sacar':
                cofre.saldo_atual -= valor
                if cofre.saldo_atual < 0:
                    cofre.saldo_atual = 0
                HistoricoCofre.objects.create(cofre=cofre, tipo='saida', valor=valor, motivo=motivo)
                # Nota: Não tiramos XP aqui pois o gráfico de vazamento já é a punição.
                    
            cofre.save()
            return JsonResponse({'status': 'sucesso'})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)}, status=400)
    return JsonResponse({'status': 'invalido'}, status=400)

@login_required
@csrf_exempt
def deletar_cofre(request, cofre_id):
    if request.method == 'DELETE':
        try:
            cofre = Cofre.objects.get(id=cofre_id)
            cofre.delete()
            return JsonResponse({'status': 'sucesso'})
        except Exception as e:
            return JsonResponse({'status': 'erro'}, status=400)
        
@login_required
@csrf_exempt
def deletar_instituicao(request, inst_id):
    if request.method == 'DELETE':
        try:
            inst = Instituicao.objects.get(id=inst_id)
            inst.delete()
            return JsonResponse({'status': 'sucesso'})
        except Exception as e:
            return JsonResponse({'status': 'erro'}, status=400)

@login_required
def enfrentar_boss_mes(request):
    """ Calcula se o jogador sobreviveu ao mês (Mana > Dano) para dar o bónus de XP """
    from .models import Transacao, Pessoa, RendaMensal 
    from datetime import date
    
    hoje = date.today()
    mes = int(request.GET.get('mes', hoje.month))
    ano = int(request.GET.get('ano', hoje.year))
    mes_ano_atual = f"{mes:02d}/{ano}"

    titular = Pessoa.objects.filter(is_owner=True).first()
    
    if not titular:
        messages.error(request, "Personagem Titular não encontrado na Guilda!")
        return redirect('dashboard')

    # 1. DANO (Despesas do mês selecionado)
    transacoes_mes = Transacao.objects.filter(mes_fatura=mes, ano_fatura=ano)
    
    if not transacoes_mes.exists():
        messages.warning(request, f"O Mapa de {mes_ano_atual} está vazio! Não existem inimigos (gastos) ou loot importado em combate para enfrentar o Boss.")
        return redirect(f"/?mes={mes}&ano={ano}")
        
    dano_total = sum(t.valor for t in transacoes_mes)

    # 2. MANA (Renda Mensal do mês selecionado)
    rendas_mes = RendaMensal.objects.filter(mes=mes, ano=ano)
    mana_total = sum(r.valor_liquido for r in rendas_mes)

    # Verifica o Histórico de Vitórias
    lista_fechados = []
    if titular.meses_fechados:
        lista_fechados = titular.meses_fechados.split(',')

    # 3. O Julgamento do Combate
    if mana_total > float(dano_total):
        # Vitória!
        if mes_ano_atual not in lista_fechados:
            titular.ganhar_xp(200)
            
            # Adiciona ao histórico do DB
            if titular.meses_fechados:
                titular.meses_fechados += f",{mes_ano_atual}"
            else:
                titular.meses_fechados = mes_ano_atual
                
            titular.ultimo_mes_fechado = mes_ano_atual # Mantém compatibilidade
            titular.save()
            messages.success(request, f"VITÓRIA ÉPICA na incursão de {mes_ano_atual}! A tua Mana (R$ {mana_total:.2f}) superou o Dano (R$ {dano_total:.2f}). Ganhaste +200 XP!")
        else:
            messages.info(request, f"VITÓRIA CONFIRMADA na incursão de {mes_ano_atual}! (Mana: R$ {mana_total:.2f} > Dano: R$ {dano_total:.2f}). Como o Boss deste mês já havia sido derrotado antes, não há novo drop de XP (Anti-Farm ativado).")
    else:
        # Derrota!
        messages.error(request, f"DERROTA na incursão de {mes_ano_atual}! O teu Dano (R$ {dano_total:.2f}) superou a tua Mana (R$ {mana_total:.2f}). O Boss venceu desta vez.")

    return redirect(f"/?mes={mes}&ano={ano}")

# ==========================================
# SETUP DE CONTA INICIAL E AUTENTICAÇÃO
# ==========================================
from django.contrib.auth import views as auth_views
from django.contrib.auth.models import User

@csrf_exempt
def custom_login_view(request):
    try:
        if User.objects.count() == 0:
            return redirect('inicio')
    except Exception:
        pass
    if not User.objects.filter(is_superuser=True).exists():
        return redirect('setup_admin')
    # Se existe o master, carrega a view de login oficial do Django
    return auth_views.LoginView.as_view(template_name='login.html')(request)

from django.db import connection
import zipfile
import os
import shutil
from django.conf import settings

def inicio(request):
    """
    A Encruzilhada: Apenas alcançável se o banco estiver vazio.
    Se já existe Superuser, manda pro login.
    """
    if User.objects.exists():
        return redirect('login')
        
    if request.method == 'POST':
        acao = request.POST.get('acao')
        if acao == 'restaurar' and request.FILES.get('arquivo_zip'):
            zip_file = request.FILES['arquivo_zip']
            
            tmp_dir = os.path.join(settings.BASE_DIR, 'tmp_restore')
            os.makedirs(tmp_dir, exist_ok=True)
            
            try:
                with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                    zip_ref.extractall(tmp_dir)
                    
                db_extracted = os.path.join(tmp_dir, 'db.sqlite3')
                media_extracted = os.path.join(tmp_dir, 'media')
                
                # Desconecta o BD para soltar o lock (vital no Windows)
                connection.close()
                
                if os.path.exists(db_extracted):
                    shutil.copy2(db_extracted, os.path.join(settings.BASE_DIR, 'db.sqlite3'))
                
                if os.path.exists(media_extracted):
                    media_target = os.path.join(settings.BASE_DIR, 'media')
                    if os.path.exists(media_target):
                        shutil.rmtree(media_target)
                    shutil.copytree(media_extracted, media_target)
                    
                messages.success(request, "Cronos retrocedeu o tempo! Banco de dados original restaurado. Por favor, inicie sua sessão.")
            except Exception as e:
                messages.error(request, f"Falha ao realizar a magia do tempo: {str(e)}")
            finally:
                if os.path.exists(tmp_dir):
                    shutil.rmtree(tmp_dir)
                    
            return redirect('login')
            
    return render(request, 'bem_vindo.html')

def setup_admin(request):
    """
    Cria a conta do líder da guilda no banco limpo e envia de volta ao form de login.
    """
    if User.objects.filter(is_superuser=True).exists():
        return redirect('login')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        pergunta = request.POST.get('pergunta_secreta')
        resposta = request.POST.get('resposta_secreta')
        api_key = request.POST.get('api_key_gemini', '')
        
        if password == password_confirm:
            try:
                user = User.objects.create_superuser(username, email, password)
                from .models import MestreSeguranca
                ms_obj = MestreSeguranca(user=user, pergunta_secreta=pergunta)
                ms_obj.set_resposta(resposta)
                ms_obj.set_api_key(api_key)
                ms_obj.save()
                
                messages.success(request, "Líder da guilda forjado com sucesso! Adentre a forja com o novo login.")
                return redirect('login')
            except Exception as e:
                messages.error(request, f"Erro ao forjar o líder: {str(e)}")
        else:
            messages.error(request, "As senhas não coincidem. Feitiço de defesa ativado.")
            
    return render(request, 'setup_admin.html')

from django.contrib.auth.decorators import login_required
from .models import Pessoa

@login_required
def setup_owner(request):
    """
    Força a criação do Titular do sistema (Pessoa com is_owner=True).
    Caso contrário o sistema entra em loop no middleware RequireOwnerMiddleware.
    """
    if Pessoa.objects.filter(is_owner=True).exists():
        return redirect('dashboard')
        
    if request.method == 'POST':
        nome = request.POST.get('nome')
        nome = nome.strip() if nome else ""
        telefone = request.POST.get('telefone', '')
        chave_pix = request.POST.get('chave_pix', '')
        foto_perfil = request.FILES.get('foto_perfil')
        
        if nome:
            Pessoa.objects.create(
                nome=nome,
                telefone=telefone,
                chave_pix=chave_pix,
                foto_perfil=foto_perfil,
                is_owner=True,
                ativo=True,
                level=1,
                xp_atual=0
            )
            messages.success(request, f"O Titular {nome} foi nomeado Mestre da Guilda! O Dashboard agora está acessível.")
            return redirect('dashboard')
        else:
            messages.error(request, "O Herói Principal precisa ter um nome. Revise o pergaminho.")
            
    return render(request, 'setup_owner.html')

def recuperar_acesso(request):
    """
    Fluxo que recupera acesso.
    Fase 1: Coleta username e acha pergunta.
    Fase 2: Coleta resposta e nova senha.
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        fase = request.POST.get('fase', '1') 
        
        user = User.objects.filter(username=username).first()
        if not user:
            messages.error(request, "Herói desconhecido nos registros.")
            return render(request, 'esqueceu_senha.html', {'fase': '1'})
            
        mestre_seguranca = getattr(user, 'seguranca', None)
        if not mestre_seguranca:
            messages.error(request, "Este herói não possui a Magia de Recuperação (Pergunta) configurada.")
            return render(request, 'esqueceu_senha.html', {'fase': '1'})

        if fase == '1':
            return render(request, 'esqueceu_senha.html', {
                'fase': '2',
                'username': username,
                'pergunta': mestre_seguranca.pergunta_secreta
            })
            
        elif fase == '2':
            resposta = request.POST.get('resposta')
            nova_senha = request.POST.get('nova_senha')
            nova_senha_conf = request.POST.get('nova_senha_confirm')
            
            if resposta and str(resposta).lower().strip() == str(mestre_seguranca.get_resposta()).lower().strip():
                if nova_senha == nova_senha_conf:
                    user.set_password(nova_senha)
                    user.save()
                    messages.success(request, "A Antiga Chave foi destruída. Nova Chave Forjada com Sucesso!")
                    return redirect('login')
                else:
                    messages.error(request, "As novas senhas não coincidem.")
            else:
                messages.error(request, "A Resposta Mágica está incorreta. O escudo refletiu sua magia.")
                
            return render(request, 'esqueceu_senha.html', {
                'fase': '2',
                'username': username,
                'pergunta': mestre_seguranca.pergunta_secreta
            })
            
    return render(request, 'esqueceu_senha.html', {'fase': '1'})

@login_required
def mudar_senha_interna(request):
    """ View restrita aos donos para alterar senha em uso. """
    if request.method == 'POST':
        senha_antiga = request.POST.get('senha_antiga')
        nova_senha = request.POST.get('nova_senha')
        nova_senha_conf = request.POST.get('nova_senha_confirm')
        
        user = request.user
        
        if user.check_password(senha_antiga):
            if nova_senha == nova_senha_conf:
                user.set_password(nova_senha)
                user.save()
                
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, user)
                
                messages.success(request, "Senha do Cofre atualizada e blindada com sucesso!")
                return redirect('dashboard')
            else:
                messages.error(request, "As novas senhas não coincidem.")
        else:
            messages.error(request, "Sua chave atual está incorreta. Refletindo o ataque.")
            
    return render(request, 'mudar_senha_interna.html')

from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

@login_required
@csrf_exempt
def deletar_cadastro(request, tipo, id):
    """
    Guardião da Exclusão.
    Assegura que nenhum loot perca o histórico validando conexões antes de exilar.
    """
    if request.method == 'DELETE':
        from .models import Pessoa, CartaoCredito, Categoria, RendaMensal, Transacao
        from django.http import JsonResponse
        try:
            if tipo == 'pessoa':
                obj = Pessoa.objects.get(id=id)
                if obj.is_owner:
                    return JsonResponse({'status': 'erro', 'mensagem': 'Você não pode banir o Titular do Sistema.'})
                if Transacao.objects.filter(responsavel=obj).exists() or RendaMensal.objects.filter(pessoa=obj).exists():
                    return JsonResponse({'status': 'erro', 'mensagem': 'Membro atrelado a faturas ou rendas. Exclusão bloqueada para preservar o histórico.'})
                obj.delete()
                
            elif tipo == 'cartao':
                obj = CartaoCredito.objects.get(id=id)
                if Transacao.objects.filter(cartao=obj).exists():
                    return JsonResponse({'status': 'erro', 'mensagem': 'Este cartão possui despesas associadas. Não pode ser destruído.'})
                obj.delete()
                
            elif tipo == 'categoria':
                obj = Categoria.objects.get(id=id)
                if Transacao.objects.filter(categoria=obj).exists():
                    return JsonResponse({'status': 'erro', 'mensagem': 'Existem pergaminhos usando esta categoria. Exclusão bloqueada.'})
                obj.delete()
                
            elif tipo == 'renda':
                obj = RendaMensal.objects.get(id=id)
                obj.delete()
                
            else:
                return JsonResponse({'status': 'erro', 'mensagem': 'Entidade de exclusão desconhecida.'})
                
            return JsonResponse({'status': 'sucesso', 'mensagem': 'Loot obliterado definitivamente.'})
            
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': f"Falha na exclusão: {str(e)}"})

    return JsonResponse({'status': 'erro', 'mensagem': 'Apenas método DELETE permitido.'})