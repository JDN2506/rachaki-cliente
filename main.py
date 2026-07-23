import flet as ft
import sqlite3
from datetime import datetime
import time
import threading

# --- COLE ESTE BLOCO AQUI ---
def inicializar_banco():
    conexao = sqlite3.connect('rachaki.db')
    cursor = conexao.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS restaurantes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, email TEXT, senha TEXT, status_plano TEXT, data_cadastro TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS funcionarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, senha TEXT, cargo TEXT, id_restaurante INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS mesas (id INTEGER PRIMARY KEY AUTOINCREMENT, numero_mesa INTEGER, id_restaurante INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS comandas (id INTEGER PRIMARY KEY AUTOINCREMENT, nome_cliente TEXT, id_mesa INTEGER, status TEXT, id_restaurante INTEGER, hora_abertura TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS cardapio (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, preco REAL, descricao TEXT, disponivel INTEGER, id_restaurante INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS pedidos (id INTEGER PRIMARY KEY AUTOINCREMENT, id_comanda INTEGER, id_produto INTEGER, status_pedido TEXT)''')

    # Cria um dono de teste automaticamente se o banco estiver vazio
    cursor.execute("SELECT COUNT(*) FROM restaurantes")
    if cursor.fetchone()[0] == 0:
        hoje = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("INSERT INTO restaurantes (nome, email, senha, status_plano, data_cadastro) VALUES ('Restaurante Teste', 'admin', 'admin', 'ativo', ?)", (hoje,))

    conexao.commit()
    conexao.close()

inicializar_banco()
# ----------------------------

def main(page: ft.Page):
    page.title = "Rachaki - Sistema Integrado"
    page.scroll = ft.ScrollMode.AUTO

    # Define o tema inicial para seguir o sistema do usuário (Claro ou Escuro)
    page.theme_mode = ft.ThemeMode.SYSTEM

    # Memória global da sessão do usuário atual
    estado = {
        "id_restaurante": 0, "nome_usuario": "", "cargo": "",
        "loop_ativo": False, "carrinho": [], "id_comanda": 0, "numero_mesa": 0
    }

    def fazer_logout(e=None):
        estado["loop_ativo"] = False
        estado["id_restaurante"] = 0
        estado["nome_usuario"] = ""
        estado["cargo"] = ""
        estado["carrinho"] = []
        estado["id_comanda"] = 0
        mostrar_portal()

    # Função para o usuário trocar o tema manualmente
    def mudar_tema(e):
        # Agora usamos e.control.data em vez de e.control.text
        if e.control.data == "Claro":
            page.theme_mode = ft.ThemeMode.LIGHT
        elif e.control.data == "Escuro":
            page.theme_mode = ft.ThemeMode.DARK
        else:
            page.theme_mode = ft.ThemeMode.SYSTEM
        page.update()

    # ==========================================
    # 1. PORTAL DE ACESSO (TELA INICIAL)
    # ==========================================
    def mostrar_portal():
        estado["loop_ativo"] = False
        page.clean()
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

        # Adicionamos o parâmetro data="..." em cada botão
        seletor_tema = ft.Row([
            ft.Text("Tema:", color="grey"),
            ft.TextButton("Sistema", data="Sistema", on_click=mudar_tema),
            ft.TextButton("Claro", data="Claro", on_click=mudar_tema),
            ft.TextButton("Escuro", data="Escuro", on_click=mudar_tema)
        ], alignment=ft.MainAxisAlignment.END)

        page.add(
            seletor_tema,
            ft.Divider(height=20, color="transparent"),
            ft.Text("Bem-vindo ao Rachaki", size=35, weight="bold", color="blue"),
            ft.Text("Selecione o seu perfil de acesso abaixo:", size=18, color="grey"),
            ft.Divider(height=30, color="transparent"),
            ft.Button("📱 Sou Cliente (Acessar Mesa)", on_click=lambda e: mostrar_simulador_qr(), width=300, height=60, style=ft.ButtonStyle(bgcolor="blue", color="white")),
            ft.Divider(height=10, color="transparent"),
            ft.Button("💼 Sou da Equipe / Dono", on_click=lambda e: mostrar_login_equipe(), width=300, height=60, style=ft.ButtonStyle(bgcolor="#333333", color="white"))
        )
        page.update()
        
    # ==========================================
    # 2. LOGIN UNIFICADO (EQUIPE E DONO)
    # ==========================================
    def mostrar_login_equipe(mensagem=""):
        page.clean()
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

        page.add(ft.Text("Acesso Restrito", size=30, weight="bold", color="purple"))

        campo_login = ft.TextField(label="E-mail (Dono) ou Nome (Funcionário)", width=300)
        campo_senha = ft.TextField(label="Senha", width=300, password=True, can_reveal_password=True)
        msg_erro = ft.Text(value=mensagem, color="red")

        def processar_login(e):
            login, senha = campo_login.value.strip(), campo_senha.value.strip()
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()

            # Tenta logar como Dono
            cursor.execute('SELECT id, nome, status_plano, data_cadastro FROM restaurantes WHERE email = ? AND senha = ?', (login, senha))
            dono = cursor.fetchone()

            if dono:
                estado["id_restaurante"], estado["nome_usuario"], estado["cargo"] = dono[0], dono[1], "Dono"
                status_plano, data_cadastro_str = dono[2], dono[3]
                conexao.close()

                if status_plano == 'trial' and data_cadastro_str:
                    dias_passados = (datetime.now() - datetime.strptime(data_cadastro_str, '%Y-%m-%d')).days
                    if dias_passados > 14: mostrar_tela_bloqueio()
                    else: mostrar_painel_dono(14 - dias_passados)
                elif status_plano == 'ativo': mostrar_painel_dono(None)
                else: mostrar_tela_bloqueio()
                return

            # Tenta logar como Funcionário
            cursor.execute("SELECT id_restaurante, nome, cargo FROM funcionarios WHERE nome = ? AND senha = ?", (login, senha))
            func = cursor.fetchone()
            conexao.close()

            if func:
                estado["id_restaurante"], estado["nome_usuario"], estado["cargo"] = func[0], func[1], func[2]
                if estado["cargo"] == "Cozinha": mostrar_painel_cozinha()
                elif estado["cargo"] == "Garçom": mostrar_painel_garcom()
                return

            msg_erro.value = "Login ou senha incorretos."
            page.update()

        page.add(campo_login, campo_senha, ft.Button("Entrar", on_click=processar_login), ft.TextButton("Voltar ao Início", on_click=lambda e: mostrar_portal()), msg_erro)
        page.update()

    # ==========================================
    # 3. MÓDULO DO CLIENTE
    # ==========================================
    def mostrar_simulador_qr():
        page.clean()
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

        page.add(ft.Text("Simulador de QR Code", size=30, weight="bold", color="blue"))
        page.add(ft.Text("Na vida real, a câmera leria isso automaticamente.", size=14, color="grey"))

        campo_restaurante = ft.TextField(label="ID do Restaurante (Ex: 1)", width=300)
        campo_mesa = ft.TextField(label="Número da Mesa (Ex: 5)", width=300)
        msg_erro = ft.Text(value="", color="red", weight="bold")

        def acessar_mesa(e):
            try:
                id_rest, num_mesa = int(campo_restaurante.value), int(campo_mesa.value)
                conexao = sqlite3.connect('rachaki.db')
                cursor = conexao.cursor()
                cursor.execute('SELECT id FROM mesas WHERE id_restaurante = ? AND numero_mesa = ?', (id_rest, num_mesa))
                resultado = cursor.fetchone()

                if resultado:
                    id_mesa = resultado[0]
                    cursor.execute("SELECT id FROM comandas WHERE id_mesa = ? AND status != 'Fechada'", (id_mesa,))
                    if cursor.fetchone():
                        msg_erro.value = "⚠️ Mesa com comanda em aberto. Chame o garçom."
                    else:
                        estado["id_restaurante"], estado["numero_mesa"] = id_rest, num_mesa
                        mostrar_boas_vindas(id_mesa)
                else:
                    msg_erro.value = "Mesa ou Restaurante não encontrados."
                conexao.close()
                page.update()
            except ValueError:
                msg_erro.value = "Digite apenas números."
                page.update()

        page.add(campo_restaurante, campo_mesa, ft.Button("Acessar Mesa", on_click=acessar_mesa), ft.TextButton("Voltar", on_click=lambda e: mostrar_portal()), msg_erro)
        page.update()

    def mostrar_boas_vindas(id_mesa):
        page.clean()
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

        campo_nome = ft.TextField(label="Qual o seu nome?", width=300)
        texto_resultado = ft.Text(value="", color="red")
        estado["carrinho"] = []

        def abrir_comanda_click(e):
            nome = campo_nome.value.strip()
            if nome != "":
                agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                conexao = sqlite3.connect('rachaki.db')
                cursor = conexao.cursor()
                cursor.execute('INSERT INTO comandas (nome_cliente, id_mesa, status, id_restaurante, hora_abertura) VALUES (?, ?, ?, ?, ?)', 
                               (nome, id_mesa, 'Aberta', estado["id_restaurante"], agora))
                estado["id_comanda"], estado["nome_usuario"] = cursor.lastrowid, nome
                conexao.commit()
                conexao.close()
                mostrar_cardapio_cliente()
            else:
                texto_resultado.value = "Por favor, digite seu nome."
                page.update()

        page.add(ft.Text(f"Bem-vindo à Mesa {estado['numero_mesa']}!", size=30, weight="bold"), campo_nome, ft.Button("Abrir Comanda", on_click=abrir_comanda_click), texto_resultado)
        page.update()

    def mostrar_cardapio_cliente():
        estado["loop_ativo"] = True
        page.clean()
        page.vertical_alignment = ft.MainAxisAlignment.START
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

        page.add(ft.Text(f"Comanda: {estado['nome_usuario']} (Mesa {estado['numero_mesa']})", size=20, weight="bold", color="blue"))
        page.add(ft.Text("Cardápio", size=24, weight="bold"))

        aviso_pedido = ft.Text(value="", color="green", weight="bold")
        coluna_cardapio = ft.Column(width=500, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        page.add(aviso_pedido, coluna_cardapio)

        def fazer_pedido_click(e):
            id_produto, nome_produto, preco_produto = e.control.data
            estado["carrinho"].append({"id": id_produto, "nome": nome_produto, "preco": preco_produto})
            aviso_pedido.value = f"✅ {nome_produto} adicionado à ordem!"
            page.update()
            def limpar_aviso():
                time.sleep(3)
                aviso_pedido.value = ""
                page.update()
            threading.Thread(target=limpar_aviso, daemon=True).start()

        dados_anteriores = None

        def carregar_itens():
            nonlocal dados_anteriores
            if not estado["loop_ativo"]: return
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()
            cursor.execute('SELECT id, nome, preco, descricao, disponivel FROM cardapio WHERE id_restaurante = ?', (estado["id_restaurante"],))
            itens = cursor.fetchall()
            conexao.close()

            if itens == dados_anteriores: return
            dados_anteriores = itens
            coluna_cardapio.controls.clear()

            for id_item, nome_item, preco_item, descricao_item, disponivel_bd in itens:
                disponivel = bool(disponivel_bd) if disponivel_bd is not None else True
                if disponivel:
                    status_visual = ft.Row([ft.Container(width=10, height=10, border_radius=5, bgcolor="green"), ft.Text("Disponível", size=12, color="green")])
                    botao_pedir = ft.Button("Adicionar", on_click=fazer_pedido_click, data=[id_item, nome_item, preco_item])
                else:
                    status_visual = ft.Row([ft.Container(width=10, height=10, border_radius=5, bgcolor="orange"), ft.Text("Esgotado", size=12, color="orange")])
                    botao_pedir = ft.Button("Esgotado", disabled=True)

                info_produto = ft.Column([ft.Text(f"{nome_item} - R$ {preco_item:.2f}", size=16, weight="bold"), ft.Text(descricao_item if descricao_item else "", size=14, color="grey"), status_visual], spacing=2)
                coluna_cardapio.controls.append(ft.Row([info_produto, botao_pedir], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
                coluna_cardapio.controls.append(ft.Divider())
            page.update()

        def loop_cardapio():
            while estado["loop_ativo"]:
                carregar_itens()
                time.sleep(5)

        carregar_itens()
        threading.Thread(target=loop_cardapio, daemon=True).start()
        page.add(ft.Button("Ver meus pedidos / Minha Conta", on_click=lambda e: mostrar_conta_cliente()))
        page.update()

    def mostrar_conta_cliente():
        estado["loop_ativo"] = True
        page.clean()
        page.vertical_alignment = ft.MainAxisAlignment.START
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

        page.add(ft.Text(f"Meus Pedidos - {estado['nome_usuario']}", size=24, weight="bold", color="blue"))

        area_carrinho = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
        coluna_pedidos_conta = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        area_total = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
        page.add(area_carrinho, ft.Divider(), coluna_pedidos_conta, ft.Divider(), area_total)

        total_conta = 0 # Variável para guardar o total e usar na divisão

        def atualizar_carrinho():
            area_carrinho.controls.clear()
            area_carrinho.controls.append(ft.Text("🛒 Ordem de Pedido (Não enviados)", size=20, weight="bold", color="orange"))

            if len(estado["carrinho"]) == 0:
                area_carrinho.controls.append(ft.Text("Sua ordem de pedido está vazia.", color="grey"))
            else:
                subtotal = sum(item['preco'] for item in estado["carrinho"])
                for item in estado["carrinho"]:
                    def remover_item(e, item_rem=item):
                        estado["carrinho"].remove(item_rem)
                        atualizar_carrinho()
                        page.update()
                    area_carrinho.controls.append(ft.Row([ft.Text(f"{item['nome']} - R$ {item['preco']:.2f}", weight="bold"), ft.Button("Remover", on_click=remover_item)], alignment=ft.MainAxisAlignment.CENTER))

                area_carrinho.controls.append(ft.Text(f"Subtotal a enviar: R$ {subtotal:.2f}", color="orange", weight="bold"))

                def confirmar_envio(e):
                    e.control.disabled = True
                    e.control.text = "Enviando..."
                    page.update()
                    conexao = sqlite3.connect('rachaki.db')
                    cursor = conexao.cursor()
                    for item_c in estado["carrinho"]:
                        cursor.execute('INSERT INTO pedidos (id_comanda, id_produto, status_pedido) VALUES (?, ?, ?)', (estado["id_comanda"], item_c['id'], 'Recebido'))
                    conexao.commit()
                    conexao.close()
                    estado["carrinho"].clear()
                    atualizar_carrinho()
                    nonlocal dados_anteriores_conta
                    dados_anteriores_conta = None
                    carregar_pedidos_conta()

                area_carrinho.controls.append(ft.Button("Confirmar e Enviar para Cozinha", on_click=confirmar_envio))

        atualizar_carrinho()
        texto_total_valor = ft.Text("TOTAL CONFIRMADO: R$ 0.00", size=22, weight="bold", color="red")

        # --- LÓGICA DO RACHAKI (DIVISÃO DE CONTA) ---
        campo_pessoas = ft.TextField(label="Dividir por quantos?", width=200)
        texto_divisao = ft.Text(value="", size=18, weight="bold", color="green")

        def calcular_divisao(e):
            try:
                qtd = int(campo_pessoas.value)
                if qtd > 0 and total_conta > 0:
                    valor_por_pessoa = total_conta / qtd
                    texto_divisao.value = f"Fica R$ {valor_por_pessoa:.2f} para cada um!"
                elif total_conta == 0:
                    texto_divisao.value = "Não há valor para dividir."
                else:
                    texto_divisao.value = "Digite um número maior que zero."
            except ValueError:
                texto_divisao.value = "Digite um número válido."
            page.update()

        area_divisao = ft.Column([
            ft.Row([campo_pessoas, ft.Button("Calcular Divisão", on_click=calcular_divisao)], alignment=ft.MainAxisAlignment.CENTER),
            texto_divisao
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        # --------------------------------------------

        def encerrar_comanda(e):
            estado["loop_ativo"] = False
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()
            cursor.execute("UPDATE comandas SET status = 'Aguardando Pagamento' WHERE id = ?", (estado["id_comanda"],))
            conexao.commit()
            conexao.close()
            page.clean()
            page.vertical_alignment = ft.MainAxisAlignment.CENTER
            page.add(ft.Text("Garçom chamado!", size=24, color="orange", weight="bold"))
            page.add(ft.Text("Aguarde na mesa. O garçom está indo até você para realizar o pagamento.", size=18))
            page.add(ft.Button("Sair da Mesa", on_click=fazer_logout))
            page.update()

        area_total.controls.extend([
            texto_total_valor,
            area_divisao, # Adicionando a área de divisão aqui na tela
            ft.Row([ft.Button("Voltar ao Cardápio", on_click=lambda e: mostrar_cardapio_cliente()), ft.Button("Encerrar e Pagar", on_click=encerrar_comanda)], alignment=ft.MainAxisAlignment.CENTER)
        ])

        dados_anteriores_conta = None

        def carregar_pedidos_conta():
            nonlocal dados_anteriores_conta, total_conta
            if not estado["loop_ativo"]: return
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()
            cursor.execute('SELECT cardapio.nome, cardapio.preco, pedidos.status_pedido FROM pedidos JOIN cardapio ON pedidos.id_produto = cardapio.id WHERE pedidos.id_comanda = ?', (estado["id_comanda"],))
            meus_pedidos = cursor.fetchall()
            conexao.close()

            if meus_pedidos == dados_anteriores_conta: return
            dados_anteriores_conta = meus_pedidos
            coluna_pedidos_conta.controls.clear()
            coluna_pedidos_conta.controls.append(ft.Text("🧾 Pedidos Confirmados (Na Cozinha)", size=20, weight="bold", color="green"))

            total_conta = 0 # Reseta e recalcula o total
            if len(meus_pedidos) == 0:
                coluna_pedidos_conta.controls.append(ft.Text("Você ainda não enviou nenhum pedido.", size=16))
            else:
                for nome_produto, preco_produto, status_pedido in meus_pedidos:
                    total_conta += preco_produto
                    status_str = "🕒 Enviado" if status_pedido == 'Recebido' else "🍳 Preparando" if status_pedido == 'Preparando' else "🔔 Pronto" if status_pedido == 'Pronto' else "✅ Entregue"
                    coluna_pedidos_conta.controls.append(ft.Text(f"- {nome_produto}: R$ {preco_produto:.2f} ({status_str})", size=16, weight="bold"))

            texto_total_valor.value = f"TOTAL CONFIRMADO: R$ {total_conta:.2f}"
            page.update()

        def loop_conta():
            while estado["loop_ativo"]:
                carregar_pedidos_conta()
                time.sleep(5)

        carregar_pedidos_conta()
        threading.Thread(target=loop_conta, daemon=True).start()

    # ==========================================
    # 4. MÓDULO DA COZINHA
    # ==========================================
    def mostrar_painel_cozinha():
        estado["loop_ativo"] = True
        page.clean()
        page.vertical_alignment = ft.MainAxisAlignment.START
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

        dados_anteriores_cozinha = None

        def forcar_atualizacao(e):
            nonlocal dados_anteriores_cozinha
            dados_anteriores_cozinha = None
            carregar_dados()

        page.add(
            ft.Row([
                ft.Text(f"Cozinha - {estado['nome_usuario']}", size=24, weight="bold", color="orange"),
                ft.Row([ft.Button("Atualizar", on_click=forcar_atualizacao), ft.Button("Sair", on_click=fazer_logout)])
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider()
        )

        coluna_novos = ft.Column(width=400)
        coluna_preparo = ft.Column(width=400)
        page.add(ft.Row([ft.Container(content=coluna_novos, padding=10), ft.Container(content=coluna_preparo, padding=10)], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.START))

        def atualizar_status_pedido(e, id_pedido, novo_status):
            e.control.disabled = True
            e.control.text = "Atualizando..."
            page.update()
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()
            cursor.execute("UPDATE pedidos SET status_pedido = ? WHERE id = ?", (novo_status, id_pedido))
            conexao.commit()
            conexao.close()
            nonlocal dados_anteriores_cozinha
            dados_anteriores_cozinha = None
            carregar_dados()

        def carregar_dados():
            nonlocal dados_anteriores_cozinha
            if not estado["loop_ativo"]: return
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()
            cursor.execute('''
                SELECT pedidos.id, cardapio.nome, mesas.numero_mesa, pedidos.status_pedido, comandas.nome_cliente 
                FROM pedidos JOIN comandas ON pedidos.id_comanda = comandas.id JOIN mesas ON comandas.id_mesa = mesas.id JOIN cardapio ON pedidos.id_produto = cardapio.id 
                WHERE comandas.id_restaurante = ? AND pedidos.status_pedido IN ('Recebido', 'Preparando')
            ''', (estado["id_restaurante"],))
            pedidos = cursor.fetchall()
            conexao.close()

            if pedidos == dados_anteriores_cozinha: return
            dados_anteriores_cozinha = pedidos

            coluna_novos.controls.clear()
            coluna_preparo.controls.clear()
            coluna_novos.controls.append(ft.Text("📝 Novos Pedidos", size=20, weight="bold"))
            coluna_preparo.controls.append(ft.Text("🍳 Em Preparo", size=20, weight="bold"))

            for id_ped, nome_prato, num_mesa, status, nome_cliente in pedidos:
                if status == 'Recebido':
                    botao_acao = ft.Button("Preparar", on_click=lambda e, id_p=id_ped: atualizar_status_pedido(e, id_p, 'Preparando'))
                    coluna_destino = coluna_novos
                else:
                    botao_acao = ft.Button("Marcar Pronto", on_click=lambda e, id_p=id_ped: atualizar_status_pedido(e, id_p, 'Pronto'))
                    coluna_destino = coluna_preparo

                coluna_destino.controls.append(ft.Row([
                    ft.Column([ft.Text(f"Mesa {num_mesa} ({nome_cliente})", weight="bold"), ft.Text(f"{nome_prato}", size=16, color="blue")]),
                    botao_acao
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
                coluna_destino.controls.append(ft.Divider())
            page.update()

        def loop_atualizacao():
            while estado["loop_ativo"]:
                carregar_dados()
                time.sleep(5)

        carregar_dados()
        threading.Thread(target=loop_atualizacao, daemon=True).start()
    # ==========================================
    # 5. MÓDULO DO GARÇOM
    # ==========================================
    def mostrar_painel_garcom():
        estado["loop_ativo"] = True
        page.clean()
        page.vertical_alignment = ft.MainAxisAlignment.START
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

        dados_anteriores_prontos = None
        dados_anteriores_pagamentos = None

        def forcar_atualizacao(e):
            nonlocal dados_anteriores_prontos, dados_anteriores_pagamentos
            dados_anteriores_prontos = None
            dados_anteriores_pagamentos = None
            carregar_dados()

        page.add(
            ft.Row([
                ft.Text(f"Salão - {estado['nome_usuario']}", size=24, weight="bold", color="green"),
                ft.Row([ft.Button("Atualizar", on_click=forcar_atualizacao), ft.Button("Sair", on_click=fazer_logout)])
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider()
        )

        coluna_prontos = ft.Column(width=400)
        coluna_pagamentos = ft.Column(width=400)
        page.add(ft.Row([ft.Container(content=coluna_prontos, padding=10), ft.Container(content=coluna_pagamentos, padding=10)], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.START))

        def entregar_pedido(e, id_pedido):
            e.control.disabled = True
            e.control.text = "Atualizando..."
            page.update()
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()
            cursor.execute("UPDATE pedidos SET status_pedido = 'Entregue' WHERE id = ?", (id_pedido,))
            conexao.commit()
            conexao.close()
            nonlocal dados_anteriores_prontos
            dados_anteriores_prontos = None
            carregar_dados()

        def confirmar_pagamento(e, id_comanda):
            e.control.disabled = True
            e.control.text = "Atualizando..."
            page.update()
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()
            cursor.execute("UPDATE comandas SET status = 'Fechada' WHERE id = ?", (id_comanda,))
            conexao.commit()
            conexao.close()
            nonlocal dados_anteriores_pagamentos
            dados_anteriores_pagamentos = None
            carregar_dados()

        def carregar_dados():
            nonlocal dados_anteriores_prontos, dados_anteriores_pagamentos
            if not estado["loop_ativo"]: return
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()

            cursor.execute('''
                SELECT pedidos.id, cardapio.nome, mesas.numero_mesa, comandas.nome_cliente 
                FROM pedidos JOIN comandas ON pedidos.id_comanda = comandas.id JOIN mesas ON comandas.id_mesa = mesas.id JOIN cardapio ON pedidos.id_produto = cardapio.id 
                WHERE comandas.id_restaurante = ? AND pedidos.status_pedido = 'Pronto'
            ''', (estado["id_restaurante"],))
            pedidos_prontos = cursor.fetchall()

            cursor.execute('''
                SELECT comandas.id, mesas.numero_mesa, comandas.nome_cliente 
                FROM comandas JOIN mesas ON comandas.id_mesa = mesas.id 
                WHERE comandas.id_restaurante = ? AND comandas.status = 'Aguardando Pagamento'
            ''', (estado["id_restaurante"],))
            pagamentos_pendentes = cursor.fetchall()
            conexao.close()

            atualizou = False
            if pedidos_prontos != dados_anteriores_prontos:
                dados_anteriores_prontos = pedidos_prontos
                coluna_prontos.controls.clear()
                coluna_prontos.controls.append(ft.Text("🔔 Prontos para Entrega", size=20, weight="bold", color="green"))
                for id_ped, nome_prato, num_mesa, nome_cliente in pedidos_prontos:
                    coluna_prontos.controls.append(ft.Row([
                        ft.Column([ft.Text(f"Mesa {num_mesa} ({nome_cliente})", weight="bold"), ft.Text(f"{nome_prato}", size=16, color="blue")]),
                        ft.Button("Entregar", on_click=lambda e, id_p=id_ped: entregar_pedido(e, id_p))
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
                    coluna_prontos.controls.append(ft.Divider())
                atualizou = True

            if pagamentos_pendentes != dados_anteriores_pagamentos:
                dados_anteriores_pagamentos = pagamentos_pendentes
                coluna_pagamentos.controls.clear()
                coluna_pagamentos.controls.append(ft.Text("💰 Aguardando Pagamento", size=20, weight="bold", color="red"))
                for id_com, num_mesa, nome_cliente in pagamentos_pendentes:
                    conexao = sqlite3.connect('rachaki.db')
                    cursor = conexao.cursor()
                    cursor.execute('SELECT SUM(cardapio.preco) FROM pedidos JOIN cardapio ON pedidos.id_produto = cardapio.id WHERE pedidos.id_comanda = ?', (id_com,))
                    total_comanda = cursor.fetchone()[0] or 0.0
                    conexao.close()
                    coluna_pagamentos.controls.append(ft.Row([
                        ft.Column([ft.Text(f"Mesa {num_mesa} ({nome_cliente})", weight="bold"), ft.Text(f"Total: R$ {total_comanda:.2f}", size=16, color="red")]),
                        ft.Button("Confirmar Pagamento", on_click=lambda e, id_c=id_com: confirmar_pagamento(e, id_c))
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
                    coluna_pagamentos.controls.append(ft.Divider())
                atualizou = True

            if atualizou: page.update()

        def loop_atualizacao():
            while estado["loop_ativo"]:
                carregar_dados()
                time.sleep(5)

        carregar_dados()
        threading.Thread(target=loop_atualizacao, daemon=True).start()

    # ==========================================
    # 6. MÓDULO DO DONO (DASHBOARD)
    # ==========================================
    def mostrar_tela_bloqueio():
        page.clean()
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.add(ft.Text("🔒", size=80), ft.Text("Seu período de testes acabou!", size=30, weight="bold", color="red"))
        page.add(ft.Button("Assinar Plano (R$ 97,00/mês)"), ft.TextButton("Sair", on_click=fazer_logout))
        page.update()

    def mostrar_painel_dono(dias_restantes):
        estado["loop_ativo"] = True
        page.clean()
        page.vertical_alignment = ft.MainAxisAlignment.START
        page.horizontal_alignment = ft.CrossAxisAlignment.START

        page.add(ft.Row([
            ft.Text(f"Painel de Controle - {estado['nome_usuario']}", size=30, weight="bold", color="purple"),
            ft.Button("Sair do Painel", on_click=fazer_logout)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))

        if dias_restantes is not None:
            page.add(ft.Container(content=ft.Text(f"Período de testes: Restam {dias_restantes} dias.", color="white", weight="bold"), bgcolor="orange", padding=10, border_radius=5))

        # --- ABA 1: VISÃO GERAL ---
        texto_faturamento = ft.Text("R$ 0.00", size=24, weight="bold", color="white")
        texto_aberto = ft.Text("R$ 0.00", size=24, weight="bold", color="white")
        texto_ticket = ft.Text("R$ 0.00", size=24, weight="bold", color="white")
        texto_fila = ft.Text("0", size=24, weight="bold", color="white")

        def criar_card(titulo, controle_texto, cor, icone):
            return ft.Container(content=ft.Column([ft.Text(f"{icone} {titulo}", color="white", size=16), controle_texto]), bgcolor=cor, padding=20, border_radius=10, width=220)

        linha_kpis = ft.Row([
            criar_card("Faturamento Hoje", texto_faturamento, "green", "💰"),
            criar_card("Valor em Aberto", texto_aberto, "blue", "⏳"),
            criar_card("Ticket Médio", texto_ticket, "purple", "🧾"),
            criar_card("Fila da Cozinha", texto_fila, "orange", "🍳")
        ], wrap=True, alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        coluna_top5 = ft.Column()
        coluna_alertas = ft.Column(spacing=10)

        painel_operacao = ft.Container(content=ft.Column([ft.Text("🏆 Top 5 Produtos Mais Vendidos", size=20, weight="bold"), coluna_top5]), expand=True, padding=10)

        painel_alertas = ft.Container(
            content=ft.Column([ft.Text("⚠️ Alertas em Tempo Real", size=20, weight="bold", color="red"), coluna_alertas]), 
            width=350, padding=15, border_radius=10
        )

        conteudo_visao_geral = ft.Column([linha_kpis, ft.Divider(), ft.Row([painel_operacao, painel_alertas], vertical_alignment=ft.CrossAxisAlignment.START)])

        def atualizar_dashboard():
            if not estado["loop_ativo"]: return
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()
            hoje_str = datetime.now().strftime('%Y-%m-%d')

            cursor.execute("SELECT SUM(cardapio.preco) FROM pedidos JOIN comandas ON pedidos.id_comanda = comandas.id JOIN cardapio ON pedidos.id_produto = cardapio.id WHERE comandas.id_restaurante = ? AND comandas.status = 'Fechada' AND comandas.hora_abertura LIKE ?", (estado["id_restaurante"], hoje_str + '%'))
            faturamento = cursor.fetchone()[0] or 0.0
            texto_faturamento.value = f"R$ {faturamento:.2f}"

            cursor.execute("SELECT SUM(cardapio.preco) FROM pedidos JOIN comandas ON pedidos.id_comanda = comandas.id JOIN cardapio ON pedidos.id_produto = cardapio.id WHERE comandas.id_restaurante = ? AND comandas.status != 'Fechada'", (estado["id_restaurante"],))
            em_aberto = cursor.fetchone()[0] or 0.0
            texto_aberto.value = f"R$ {em_aberto:.2f}"

            cursor.execute("SELECT COUNT(id) FROM comandas WHERE id_restaurante = ? AND status = 'Fechada' AND hora_abertura LIKE ?", (estado["id_restaurante"], hoje_str + '%'))
            qtd_comandas = cursor.fetchone()[0] or 0
            texto_ticket.value = f"R$ {(faturamento / qtd_comandas if qtd_comandas > 0 else 0.0):.2f}"

            cursor.execute("SELECT COUNT(pedidos.id) FROM pedidos JOIN comandas ON pedidos.id_comanda = comandas.id WHERE comandas.id_restaurante = ? AND pedidos.status_pedido IN ('Recebido', 'Preparando')", (estado["id_restaurante"],))
            texto_fila.value = f"{cursor.fetchone()[0] or 0} pedidos"

            coluna_top5.controls.clear()
            cursor.execute("SELECT cardapio.nome, COUNT(pedidos.id) as qtd FROM pedidos JOIN comandas ON pedidos.id_comanda = comandas.id JOIN cardapio ON pedidos.id_produto = cardapio.id WHERE comandas.id_restaurante = ? GROUP BY cardapio.id ORDER BY qtd DESC LIMIT 5", (estado["id_restaurante"],))
            for i, (nome_prod, qtd) in enumerate(cursor.fetchall()):
                coluna_top5.controls.append(ft.Row([ft.Text(f"{i+1}º {nome_prod}", size=16, weight="bold"), ft.Text(f"{qtd} vendidos", color="green")], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
                coluna_top5.controls.append(ft.Divider())

            coluna_alertas.controls.clear()
            agora = datetime.now()
            cursor.execute("SELECT comandas.id, comandas.nome_cliente, mesas.numero_mesa, comandas.hora_abertura FROM comandas JOIN mesas ON comandas.id_mesa = mesas.id WHERE comandas.id_restaurante = ? AND comandas.status = 'Aberta'", (estado["id_restaurante"],))
            for id_com, nome_cli, num_mesa, hora_abertura_str in cursor.fetchall():
                if hora_abertura_str:
                    minutos_passados = (agora - datetime.strptime(hora_abertura_str, '%Y-%m-%d %H:%M:%S')).total_seconds() / 60
                    if minutos_passados >= 10:
                        cursor.execute('SELECT COUNT(*) FROM pedidos WHERE id_comanda = ?', (id_com,))
                        if cursor.fetchone()[0] == 0:
                            coluna_alertas.controls.append(ft.Container(content=ft.Text(f"Mesa {num_mesa} ({nome_cli}) ociosa há {int(minutos_passados)} min.", color="white"), bgcolor="orange", padding=10, border_radius=5))

            cursor.execute("SELECT comandas.nome_cliente, mesas.numero_mesa FROM comandas JOIN mesas ON comandas.id_mesa = mesas.id WHERE comandas.id_restaurante = ? AND comandas.status = 'Aguardando Pagamento'", (estado["id_restaurante"],))
            for nome_cli, num_mesa in cursor.fetchall():
                coluna_alertas.controls.append(ft.Container(content=ft.Text(f"Mesa {num_mesa} ({nome_cli}) pediu a conta!", color="white", weight="bold"), bgcolor="red", padding=10, border_radius=5))

            if len(coluna_alertas.controls) == 0: coluna_alertas.controls.append(ft.Text("Tudo tranquilo no momento! ✅", color="green"))
            conexao.close()
            page.update()

        threading.Thread(target=lambda: [atualizar_dashboard() or time.sleep(5) for _ in iter(lambda: estado["loop_ativo"], False)], daemon=True).start()

        # --- ABA 2: COMANDAS ATIVAS ---
        lista_mesas_ativas = ft.Column()
        def forcar_fechamento(e):
            id_comanda = e.control.data
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()
            cursor.execute("DELETE FROM pedidos WHERE id_comanda = ?", (id_comanda,))
            cursor.execute("DELETE FROM comandas WHERE id = ?", (id_comanda,))
            conexao.commit()
            conexao.close()
            carregar_mesas_ativas()
            atualizar_dashboard()

        def carregar_mesas_ativas():
            lista_mesas_ativas.controls.clear()
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()
            cursor.execute("SELECT comandas.id, comandas.nome_cliente, mesas.numero_mesa, comandas.status FROM comandas JOIN mesas ON comandas.id_mesa = mesas.id WHERE comandas.id_restaurante = ? AND comandas.status != 'Fechada'", (estado["id_restaurante"],))
            ativas = cursor.fetchall()
            conexao.close()
            if len(ativas) == 0:
                lista_mesas_ativas.controls.append(ft.Text("Nenhuma mesa ocupada no momento.", color="green"))
            else:
                for id_com, nome_cli, num_mesa, status_com in ativas:
                    lista_mesas_ativas.controls.append(ft.Row([ft.Text(f"Mesa {num_mesa} - {nome_cli} (Status: {status_com})", size=16, weight="bold"), ft.Button("Forçar Fechamento", on_click=forcar_fechamento, data=id_com)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
                    lista_mesas_ativas.controls.append(ft.Divider())
            page.update()

        conteudo_comandas = ft.Column([ft.Text("Use esta área para forçar o fechamento de comandas abandonadas ou testes.", size=14, color="grey"), ft.Button("Atualizar Lista de Mesas", on_click=lambda e: carregar_mesas_ativas()), ft.Divider(), lista_mesas_ativas])

        # --- ABA 3: CARDÁPIO ---
        campo_nome = ft.TextField(label="Nome do Produto", width=250)
        campo_preco = ft.TextField(label="Preço (Ex: 25.90)", width=120)
        campo_descricao = ft.TextField(label="Descrição (Opcional)", width=380)
        mensagem_erro = ft.Text(value="", color="red")
        lista_produtos = ft.Column()

        def adicionar_produto(e):
            nome, descricao, preco_texto = campo_nome.value.strip().capitalize(), campo_descricao.value.strip().capitalize(), campo_preco.value.replace(",", ".")
            if nome != "" and preco_texto != "":
                try:
                    preco_float = float(preco_texto)
                    conexao = sqlite3.connect('rachaki.db')
                    cursor = conexao.cursor()
                    cursor.execute('INSERT INTO cardapio (nome, preco, descricao, id_restaurante, disponivel) VALUES (?, ?, ?, ?, 1)', (nome, preco_float, descricao, estado["id_restaurante"]))
                    conexao.commit()
                    conexao.close()
                    campo_nome.value, campo_preco.value, campo_descricao.value, mensagem_erro.value = "", "", "", ""
                    carregar_cardapio()
                except ValueError:
                    mensagem_erro.value = "Erro: Digite um preço válido."
            else:
                mensagem_erro.value = "Preencha o nome e o preço."
            page.update()

        def deletar_produto(e):
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()
            cursor.execute('DELETE FROM cardapio WHERE id = ? AND id_restaurante = ?', (e.control.data, estado["id_restaurante"]))
            conexao.commit()
            conexao.close()
            carregar_cardapio()

        def alternar_disponibilidade(e):
            esta_disponivel = 1 if e.control.value else 0
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()
            cursor.execute('UPDATE cardapio SET disponivel = ? WHERE id = ?', (esta_disponivel, e.control.data))
            conexao.commit()
            conexao.close()
            e.control.label = "Disponível" if esta_disponivel else "Indisponível"
            page.update()

        def carregar_cardapio():
            lista_produtos.controls.clear()
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()
            cursor.execute('SELECT id, nome, preco, descricao, disponivel FROM cardapio WHERE id_restaurante = ?', (estado["id_restaurante"],))
            itens = cursor.fetchall()
            conexao.close()
            if len(itens) == 0:
                lista_produtos.controls.append(ft.Text("O cardápio está vazio."))
            else:
                for id_item, nome_item, preco_item, descricao_item, disponivel_bd in itens:
                    disponivel = bool(disponivel_bd) if disponivel_bd is not None else True
                    info_produto = ft.Column([ft.Text(f"{nome_item} - R$ {preco_item:.2f}", size=16, weight="bold"), ft.Text(descricao_item if descricao_item else "", size=14, color="grey")], spacing=2)
                    lista_produtos.controls.append(ft.Row([info_produto, ft.Row([ft.Switch(label="Disponível" if disponivel else "Indisponível", value=disponivel, on_change=alternar_disponibilidade, data=id_item, active_color="green"), ft.Button("Apagar", on_click=deletar_produto, data=id_item)])], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
                    lista_produtos.controls.append(ft.Divider())
            page.update()

        conteudo_cardapio = ft.Column([ft.Row([campo_nome, campo_preco]), ft.Row([campo_descricao, ft.Button("Salvar Produto", on_click=adicionar_produto)]), mensagem_erro, ft.Divider(), lista_produtos])

        # --- ABA 4: EQUIPE ---
        campo_func_nome = ft.TextField(label="Nome do Funcionário", width=250)
        campo_func_senha = ft.TextField(label="Criar Senha", width=150, password=True, can_reveal_password=True)
        dropdown_cargo = ft.Dropdown(label="Cargo", width=150, value="Garçom", options=[ft.dropdown.Option("Garçom"), ft.dropdown.Option("Cozinha")])
        msg_equipe = ft.Text(value="", color="red")
        lista_equipe = ft.Column()

        def adicionar_funcionario(e):
            nome, senha = campo_func_nome.value.strip(), campo_func_senha.value.strip()
            if nome != "" and senha != "":
                conexao = sqlite3.connect('rachaki.db')
                cursor = conexao.cursor()
                cursor.execute('INSERT INTO funcionarios (nome, senha, cargo, id_restaurante) VALUES (?, ?, ?, ?)', (nome, senha, dropdown_cargo.value, estado["id_restaurante"]))
                conexao.commit()
                conexao.close()
                campo_func_nome.value, campo_func_senha.value = "", ""
                msg_equipe.value, msg_equipe.color = "✅ Funcionário cadastrado!", "green"
                carregar_equipe()
            else:
                msg_equipe.value, msg_equipe.color = "Preencha nome e senha.", "red"
            page.update()

        def deletar_funcionario(e):
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()
            cursor.execute('DELETE FROM funcionarios WHERE id = ? AND id_restaurante = ?', (e.control.data, estado["id_restaurante"]))
            conexao.commit()
            conexao.close()
            carregar_equipe()

        def carregar_equipe():
            lista_equipe.controls.clear()
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()
            cursor.execute('SELECT id, nome, cargo FROM funcionarios WHERE id_restaurante = ?', (estado["id_restaurante"],))
            funcionarios = cursor.fetchall()
            conexao.close()
            if len(funcionarios) == 0:
                lista_equipe.controls.append(ft.Text("Nenhum funcionário cadastrado.", color="grey"))
            else:
                for id_func, nome_func, cargo_func in funcionarios:
                    lista_equipe.controls.append(ft.Row([ft.Text(f"{nome_func} ({cargo_func})", size=16, weight="bold"), ft.Button("Remover", on_click=deletar_funcionario, data=id_func)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
                    lista_equipe.controls.append(ft.Divider())
            page.update()

        conteudo_equipe = ft.Column([ft.Row([campo_func_nome, campo_func_senha, dropdown_cargo, ft.Button("Cadastrar", on_click=adicionar_funcionario)]), msg_equipe, ft.Divider(), lista_equipe])

        # --- ABA 5: CONFIGURAÇÕES ---
        campo_mesas = ft.TextField(label="Quantas mesas o restaurante possui atualmente?", width=350)
        msg_mesas = ft.Text(value="", color="green")

        def configurar_mesas(e):
            try:
                qtd = int(campo_mesas.value)
                if qtd > 0:
                    conexao = sqlite3.connect('rachaki.db')
                    cursor = conexao.cursor()
                    cursor.execute("SELECT COUNT(*) FROM comandas WHERE id_restaurante = ? AND status != 'Fechada'", (estado["id_restaurante"],))
                    if cursor.fetchone()[0] > 0:
                        msg_mesas.value, msg_mesas.color = "⚠️ Erro: Feche todas as comandas abertas antes de alterar as mesas.", "red"
                    else:
                        cursor.execute('DELETE FROM mesas WHERE id_restaurante = ?', (estado["id_restaurante"],))
                        for i in range(1, qtd + 1):
                            cursor.execute('INSERT INTO mesas (numero_mesa, id_restaurante) VALUES (?, ?)', (i, estado["id_restaurante"]))
                        conexao.commit()
                        msg_mesas.value, msg_mesas.color = f"✅ {qtd} mesas configuradas com sucesso!", "green"
                        atualizar_dashboard()
                    conexao.close()
                else:
                    msg_mesas.value, msg_mesas.color = "Digite um número maior que zero.", "red"
            except ValueError:
                msg_mesas.value, msg_mesas.color = "Digite apenas números inteiros.", "red"
            page.update()

        conteudo_config = ft.Column([ft.Text("Atenção: Gerar novas mesas apagará a numeração atual.", color="grey"), ft.Row([campo_mesas, ft.Button("Gerar Mesas", on_click=configurar_mesas)]), msg_mesas])

        # --- MONTANDO AS ABAS ---
        area_conteudo = ft.Container(content=conteudo_visao_geral, padding=20, expand=True)
        def mudar_aba(conteudo):
            area_conteudo.content = conteudo
            page.update()

        page.add(ft.Row([
            ft.Button("Visão Geral", on_click=lambda e: mudar_aba(conteudo_visao_geral)),
            ft.Button("Comandas Ativas", on_click=lambda e: mudar_aba(conteudo_comandas)),
            ft.Button("Cardápio", on_click=lambda e: mudar_aba(conteudo_cardapio)),
            ft.Button("Equipe", on_click=lambda e: mudar_aba(conteudo_equipe)),
            ft.Button("Configurações", on_click=lambda e: mudar_aba(conteudo_config)),
        ], alignment=ft.MainAxisAlignment.CENTER, wrap=True), ft.Divider(), area_conteudo)

        atualizar_dashboard()
        carregar_cardapio()
        carregar_equipe()
        carregar_mesas_ativas()

    # Inicia o aplicativo mostrando o portal
    mostrar_portal()

ft.app(target=main)