import os
import flet as ft
import sqlite3

def main(page: ft.Page):
    page.title = "Rachaki - Cliente"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # --- TELA 4: A CONTA DO CLIENTE ---
    def mostrar_conta(id_comanda, nome_cliente, id_restaurante, numero_mesa):
        page.clean()
        page.vertical_alignment = ft.MainAxisAlignment.START

        page.add(ft.Text(f"Conta de {nome_cliente}", size=24, weight="bold", color="blue"))

        conexao = sqlite3.connect('rachaki.db')
        cursor = conexao.cursor()
        cursor.execute('''
            SELECT cardapio.nome, cardapio.preco 
            FROM pedidos 
            JOIN cardapio ON pedidos.id_produto = cardapio.id 
            WHERE pedidos.id_comanda = ?
        ''', (id_comanda,))
        meus_pedidos = cursor.fetchall()
        conexao.close()

        total = 0

        if len(meus_pedidos) == 0:
            page.add(ft.Text("Você ainda não pediu nada.", size=16))
        else:
            for pedido in meus_pedidos:
                nome_produto = pedido[0]
                preco_produto = pedido[1]
                total = total + preco_produto
                page.add(ft.Text(f"- {nome_produto}: R$ {preco_produto:.2f}", size=16))

        page.add(ft.Divider())
        page.add(ft.Text(f"TOTAL: R$ {total:.2f}", size=22, weight="bold", color="red"))

        page.add(ft.Text("Rachar a conta?", size=18, weight="bold"))
        campo_pessoas = ft.TextField(label="Dividir por quantos?", value="1", width=200, text_align=ft.TextAlign.CENTER)
        texto_divisao = ft.Text(value="", size=20, color="green", weight="bold")

        def calcular_divisao(e):
            try:
                num_pessoas = int(campo_pessoas.value)
                if num_pessoas > 0:
                    valor_por_pessoa = total / num_pessoas
                    texto_divisao.value = f"Fica R$ {valor_por_pessoa:.2f} para cada um!"
                else:
                    texto_divisao.value = "Digite um número maior que zero."
                    texto_divisao.color = "red"
            except ValueError:
                texto_divisao.value = "Por favor, digite apenas números."
                texto_divisao.color = "red"
            page.update()

        botao_calcular = ft.ElevatedButton("Calcular Divisão", on_click=calcular_divisao, bgcolor="green", color="white")
        page.add(campo_pessoas, botao_calcular, texto_divisao)
        page.add(ft.Divider())

        def encerrar_comanda(e):
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()
            cursor.execute("UPDATE comandas SET status = 'Fechada' WHERE id = ?", (id_comanda,))
            conexao.commit()
            conexao.close()

            page.clean()
            page.vertical_alignment = ft.MainAxisAlignment.CENTER
            page.add(ft.Text("Comanda encerrada com sucesso!", size=24, color="green", weight="bold"))
            page.add(ft.Text("Obrigado pela preferência e volte sempre!", size=18))
            page.add(ft.ElevatedButton("Simular Novo Cliente", on_click=lambda e: simulador_qr_code()))
            page.update()

        linha_botoes_finais = ft.Row([
            ft.ElevatedButton("Voltar ao Cardápio", on_click=lambda e: mostrar_cardapio(id_comanda, nome_cliente, id_restaurante, numero_mesa)),
            ft.ElevatedButton("Encerrar e Pagar", on_click=encerrar_comanda, bgcolor="red", color="white")
        ], alignment=ft.MainAxisAlignment.CENTER)

        page.add(linha_botoes_finais)
        page.update()

    # --- TELA 3: O CARDÁPIO ---
    def mostrar_cardapio(id_comanda, nome_cliente, id_restaurante, numero_mesa):
        page.clean()
        page.vertical_alignment = ft.MainAxisAlignment.START

        page.add(ft.Text(f"Comanda: {nome_cliente} (Mesa {numero_mesa})", size=20, weight="bold", color="blue"))
        page.add(ft.Text("Cardápio", size=24, weight="bold"))

        aviso_pedido = ft.Text(value="", color="green", weight="bold")
        page.add(aviso_pedido)

        conexao = sqlite3.connect('rachaki.db')
        cursor = conexao.cursor()
        # Busca apenas o cardápio do restaurante atual
        cursor.execute('SELECT * FROM cardapio WHERE id_restaurante = ?', (id_restaurante,))
        itens = cursor.fetchall()
        conexao.close()

        def fazer_pedido_click(e):
            id_produto = e.control.data[0]
            nome_produto = e.control.data[1]

            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()
            cursor.execute('INSERT INTO pedidos (id_comanda, id_produto, status_pedido) VALUES (?, ?, ?)', (id_comanda, id_produto, 'Recebido'))
            conexao.commit()
            conexao.close()

            aviso_pedido.value = f"✅ {nome_produto} adicionado!"
            page.update()

        for item in itens:
            id_item = item[0]
            nome_item = item[1]
            preco_item = item[2]
            descricao_item = item[3] if len(item) > 3 and item[3] else ""

            botao_pedir = ft.ElevatedButton("Pedir", on_click=fazer_pedido_click, data=[id_item, nome_item])

            texto_principal = ft.Text(f"{nome_item} - R$ {preco_item:.2f}", size=16, weight="bold")

            # Adiciona a descrição se ela existir
            if descricao_item != "":
                info_produto = ft.Column([texto_principal, ft.Text(descricao_item, size=14, color="grey")], spacing=2)
            else:
                info_produto = ft.Column([texto_principal], spacing=2)

            linha_produto = ft.Row([info_produto, botao_pedir], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            page.add(linha_produto)
            page.add(ft.Divider())

        botao_conta = ft.ElevatedButton("Ver Minha Conta", on_click=lambda e: mostrar_conta(id_comanda, nome_cliente, id_restaurante, numero_mesa), bgcolor="blue", color="white")
        page.add(botao_conta)
        page.update()

    # --- TELA 2: BOAS-VINDAS ---
    def mostrar_boas_vindas(id_restaurante, id_mesa, numero_mesa):
        page.clean()
        page.vertical_alignment = ft.MainAxisAlignment.CENTER

        titulo = ft.Text(f"Bem-vindo à Mesa {numero_mesa}!", size=30, weight="bold")
        campo_nome = ft.TextField(label="Qual o seu nome?", width=300)
        texto_resultado = ft.Text(value="", size=18, color="red")

        def abrir_comanda_click(e):
            nome = campo_nome.value.strip()
            if nome != "":
                conexao = sqlite3.connect('rachaki.db')
                cursor = conexao.cursor()
                # Salva a comanda vinculada à mesa e ao restaurante
                cursor.execute('INSERT INTO comandas (nome_cliente, id_mesa, status, id_restaurante) VALUES (?, ?, ?, ?)', 
                               (nome, id_mesa, 'Aberta', id_restaurante))
                id_comanda = cursor.lastrowid
                conexao.commit()
                conexao.close()

                mostrar_cardapio(id_comanda, nome, id_restaurante, numero_mesa)
            else:
                texto_resultado.value = "Por favor, digite seu nome."
                page.update()

        botao_abrir = ft.ElevatedButton("Abrir Comanda", on_click=abrir_comanda_click)
        page.add(titulo, campo_nome, botao_abrir, texto_resultado)
        page.update()

    # --- TELA 1: SIMULADOR DE QR CODE ---
    def simulador_qr_code():
        page.clean()
        page.vertical_alignment = ft.MainAxisAlignment.CENTER

        page.add(ft.Text("Simulador de QR Code", size=30, weight="bold", color="blue"))
        page.add(ft.Text("Na vida real, a câmera do celular leria esses dados automaticamente.", size=14, color="grey"))

        campo_restaurante = ft.TextField(label="ID do Restaurante (Ex: 1)", width=300)
        campo_mesa = ft.TextField(label="Número da Mesa (Ex: 5)", width=300)
        msg_erro = ft.Text(value="", color="red")

        def acessar_mesa(e):
            try:
                id_rest = int(campo_restaurante.value)
                num_mesa = int(campo_mesa.value)

                conexao = sqlite3.connect('rachaki.db')
                cursor = conexao.cursor()
                # Verifica se essa mesa realmente existe nesse restaurante
                cursor.execute('SELECT id FROM mesas WHERE id_restaurante = ? AND numero_mesa = ?', (id_rest, num_mesa))
                resultado = cursor.fetchone()
                conexao.close()

                if resultado:
                    id_mesa = resultado[0]
                    mostrar_boas_vindas(id_rest, id_mesa, num_mesa)
                else:
                    msg_erro.value = "Mesa ou Restaurante não encontrados. Verifique os números."
                    page.update()
            except ValueError:
                msg_erro.value = "Digite apenas números."
                page.update()

        botao_acessar = ft.ElevatedButton("Simular Leitura do QR Code", on_click=acessar_mesa, bgcolor="blue", color="white")
        page.add(campo_restaurante, campo_mesa, botao_acessar, msg_erro)
        page.update()

    # Inicia o aplicativo na tela do simulador
    simulador_qr_code()


# Configuração para rodar na internet (Render)
porta = int(os.environ.get("PORT", 8080))
ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=porta, host="0.0.0.0")