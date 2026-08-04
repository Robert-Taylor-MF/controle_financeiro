import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setup.settings')
django.setup()

from core.models import Transacao, Rateio, Pessoa

def migrar():
    print("Iniciando migração de transações rateadas...")
    rateadas = Transacao.objects.filter(descricao__icontains='(Rateio:')
    
    owner = Pessoa.objects.filter(is_owner=True).first()
    if not owner:
        print("Erro: Owner não encontrado.")
        return
        
    for trans_party in rateadas:
        # descricao = "Netflix Entretenimento (Rateio: Caciane)"
        base_desc = trans_party.descricao.split('(Rateio:')[0].strip()
        
        # Encontra a transacao original do Owner com mesma data e base_desc
        # (Pode haver múltiplas, mas pegamos a primeira que bater no mesmo mês/ano)
        trans_original = Transacao.objects.filter(
            responsavel=owner,
            data_compra=trans_party.data_compra,
            descricao__startswith=base_desc
        ).first()
        
        if trans_original:
            # Cria o Rateio para a pessoa
            Rateio.objects.get_or_create(
                transacao=trans_original,
                pessoa=trans_party.responsavel,
                valor=trans_party.valor
            )
            # Atualiza o valor original para incluir o valor rateado (assim o valor total da fatura não se perde)
            trans_original.valor += trans_party.valor
            trans_original.save()
            
            # Deleta a transação duplicada
            trans_party.delete()
            print(f"Migrado: {trans_party.descricao} -> Adicionado Rateio em ID {trans_original.id}")
        else:
            # Se não achou original (ex: dono rateou 100% da compra e ficou com 0, então não tinha original dele)
            pessoa_old = trans_party.responsavel
            trans_party.descricao = base_desc
            trans_party.responsavel = owner
            trans_party.save()
            
            Rateio.objects.get_or_create(
                transacao=trans_party,
                pessoa=pessoa_old,
                valor=trans_party.valor
            )
            print(f"Migrado (Sem Original): {trans_party.descricao} -> Transação convertida para Owner e criado Rateio.")

if __name__ == '__main__':
    migrar()
    print("Concluído!")
