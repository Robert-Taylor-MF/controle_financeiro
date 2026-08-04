import re
from django.core.management.base import BaseCommand
from core.models import Transacao, Rateio, Pessoa

class Command(BaseCommand):
    help = 'Migra o sistema antigo de rateio (múltiplas Transacoes) para o novo formato (Tabela Rateio)'

    def handle(self, *args, **options):
        # Encontra todas as transações que têm "(Rateio:" no nome
        transacoes_rateadas = Transacao.objects.filter(descricao__icontains='(Rateio:')
        
        self.stdout.write(self.style.WARNING(f"Foram encontradas {transacoes_rateadas.count()} transações com rateio antigo."))
        
        if transacoes_rateadas.count() == 0:
            self.stdout.write(self.style.SUCCESS("Nenhuma transação para migrar."))
            return

        # Agrupar as transações por data_compra, cartao e mês/ano
        # A chave será (data_compra, cartao_id, mes, ano)
        # O valor será uma lista de transações
        grupos = {}
        for t in transacoes_rateadas:
            # Tentar extrair a descrição base
            # Caso 1: Owner: "(Rateio: IFood)" -> IFood
            # Caso 2: Party: "IFood (Rateio: Joao)" -> IFood
            
            desc_base = t.descricao
            if desc_base.startswith('(Rateio:'):
                desc_base = desc_base.replace('(Rateio: ', '').rstrip(')')
            else:
                desc_base = re.sub(r'\s*\(Rateio:.*?\)', '', desc_base)
                
            chave = (t.data_compra, t.cartao_id, t.mes_fatura, t.ano_fatura, desc_base.lower().strip())
            
            if chave not in grupos:
                grupos[chave] = []
            grupos[chave].append(t)
            
        # Agora iteramos sobre os grupos e unificamos
        for chave, lista_t in grupos.items():
            self.stdout.write(f"Processando grupo: {chave[4]} ({len(lista_t)} itens)")
            
            # Pega o responsável Owner, se tiver. Se não, o primeiro da lista.
            transacao_pai = None
            for t in lista_t:
                if t.responsavel and t.responsavel.is_owner:
                    transacao_pai = t
                    break
            
            if not transacao_pai:
                transacao_pai = lista_t[0]
                
            # Atualizar a descrição da transação pai para a base
            desc_base = transacao_pai.descricao
            if desc_base.startswith('(Rateio:'):
                desc_base = desc_base.replace('(Rateio: ', '').rstrip(')')
            else:
                desc_base = re.sub(r'\s*\(Rateio:.*?\)', '', desc_base)
                
            transacao_pai.descricao = desc_base
            
            # Somar os valores para ter a transação unificada
            valor_total = sum(t.valor for t in lista_t)
            transacao_pai.valor = valor_total
            transacao_pai.save()
            
            # Criar os rateios
            for t in lista_t:
                Rateio.objects.create(
                    transacao=transacao_pai,
                    pessoa=t.responsavel,
                    valor=t.valor
                )
                
                # Se não for a transação pai, podemos apagar a original
                if t.id != transacao_pai.id:
                    t.delete()
                    
        self.stdout.write(self.style.SUCCESS("Migração concluída com sucesso!"))
