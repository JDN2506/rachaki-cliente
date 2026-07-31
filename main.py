import flet as ft
import sqlite3
from datetime import datetime
import time
import threading
import os

# ---------------------------------------------------------------------------
# Paleta de cores - baseada no documento "Paleta de Cores - Rachaki"
# (mesma paleta utilizada em todos os apps, para manter harmonia visual)
# ---------------------------------------------------------------------------
CORES_CLARO = {
    "primaria": "#8BA88B",
    "secundaria": "#FDD7B1",
    "fundo_principal": "#F8F8F8",
    "fundo_secundario": "#FFFFFF",
    "cards": "#F0F0F0",
    "texto_principal": "#333333",
    "texto_secundario": "#666666",
    "borda": "#E0E0E0",
    "sucesso": "#A2D9A2",
    "aviso": "#FFDDAA",
    "erro": "#FFB2B2",
    "on_success": "#1B5E20", # Adicionado para app_garcom
    "on_warning": "#7A4A00", # Adicionado para app_garcom
    "on_error": "#7A0000",   # Adicionado para app_garcom
}

CORES_ESCURO = {
    "primaria": "#5C7A5C",
    "secundaria": "#E0A070",
    "fundo_principal": "#1A1A1A",
    "fundo_secundario": "#2B2B2B",
    "cards": "#2B2B2B",
    "texto_principal": "#E0E0E0",
    "texto_secundario": "#A0A0A0",
    "borda": "#404040",
    "sucesso": "#7CB37C",
    "aviso": "#FFC180",
    "erro": "#FF8080",
    "on_success": "#EAF7EA", # Adicionado para app_garcom
    "on_warning": "#3A2400", # Adicionado para app_garcom
    "on_error": "#3A0000",   # Adicionado para app_garcom
}

# Funções utilitárias para compatibilidade Flet e tema
def criar_borda(cor, largura=1):
    try:
        return ft.border.all(largura, cor)
    except AttributeError:
        lado = ft.BorderSide(largura, cor)
        return ft.Border(top=lado, right=lado, bottom=lado, left=lado)

def alinhamento_centro():
    try:
        return ft.alignment.center
    except AttributeError:
        return ft.Alignment(0, 0)

def criar_padding_simetrico(horizontal=0, vertical=0):
    try:
        return ft.padding.symmetric(horizontal=horizontal, vertical=vertical)
    except AttributeError:
        return ft.Padding(left=horizontal, top=vertical, right=horizontal, bottom=vertical)

def obter_cores_tema(page_theme_mode):
    if page_theme_mode == ft.ThemeMode.DARK:
        return CORES_ESCURO
    elif page_theme_mode == ft.ThemeMode.LIGHT:
        return CORES_CLARO
    # Fallback para SYSTEM, usando o tema claro como padrão se não houver brilho da plataforma
    return CORES_CLARO

def criar_cabecalho_tema(page, cores, mudar_tema_callback):
    """
    Barra superior com a marca do app e o seletor de tema,
    presente em todas as telas para dar consistência visual.
    """
    return ft.Row(
        [
            ft.Row([
                ft.Text("🍽️", size=20),
                ft.Text("Rachaki", size=16, weight="bold", color=cores["primaria"]),
            ], spacing=6),
            ft.PopupMenuButton(
                icon=ft.Icons.PALETTE_OUTLINED,
                icon_color=cores["texto_secundario"],
                items=[
                    ft.PopupMenuItem(
                        content=ft.Row([ft.Icon(ft.Icons.BRIGHTNESS_AUTO, size=18, color=cores["texto_secundario"]), ft.Text("Sistema")]),
                        data="Sistema", on_click=mudar_tema_callback
                    ),
                    ft.PopupMenuItem(
                        content=ft.Row([ft.Icon(ft.Icons.LIGHT_MODE, size=18, color=cores["texto_secundario"]), ft.Text("Claro")]),
                        data="Claro", on_click=mudar_tema_callback
                    ),
                    ft.PopupMenuItem(
                        content=ft.Row([ft.Icon(ft.Icons.DARK_MODE, size=18, color=cores["texto_secundario"]), ft.Text("Escuro")]),
                        data="Escuro", on_click=mudar_tema_callback
                    ),
                ]
            )
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
    )

def criar_botao(texto, on_click, cor_fundo, cor_texto="#FFFFFF", icone=None, altura=54, disabled=False):
    """
    Botão padronizado com cantos arredondados, usado em todas as telas.
    """
    return ft.Button(
        texto,
        icon=icone,
        on_click=on_click,
        height=altura,
        disabled=disabled,
        style=ft.ButtonStyle(
            bgcolor=cor_fundo,
            color=cor_texto,
            shape=ft.RoundedRectangleBorder(radius=10),
        )
    )

def criar_chip(texto, cor_fundo, cor_texto):
    return ft.Container(
        content=ft.Text(texto, size=13, weight="bold", color=cor_texto),
        bgcolor=cor_fundo,
        padding=criar_padding_simetrico(horizontal=14, vertical=6),
        border_radius=20,
    )

def mostrar_snackbar(page, mensagem, cor_fundo, cor_texto):
    try:
        snack = ft.SnackBar(
        content=ft.Text(mensagem, color=cor_texto, weight="bold"),
        bgcolor=cor_fundo,
        duration=1800,
        behavior=ft.SnackBarBehavior.FLOATING,
        margin=ft.Margin(left=20, top=0, right=20, bottom=20),
    )
    except AttributeError:
        snack = ft.SnackBar(
        content=ft.Text(mensagem, color=cor_texto, weight="bold"),
        bgcolor=cor_fundo,
        duration=1800,
    )

    try:
        page.open(snack)
    except AttributeError:
        page.snack_bar = snack
        page.snack_bar.open = True
        page.update()

# Inicializa o banco de dados e garante as colunas necessárias para TODOS os apps
def inicializar_banco():
    conexao = sqlite3.connect('rachaki.db')
    cursor = conexao.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS restaurantes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, email TEXT, senha TEXT, status_plano TEXT, data_cadastro TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS funcionarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, senha TEXT, cargo TEXT, id_restaurante INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS mesas (id INTEGER PRIMARY KEY AUTOINCREMENT, numero_mesa INTEGER, id_restaurante INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS comandas (id INTEGER PRIMARY KEY AUTOINCREMENT, nome_cliente TEXT, id_mesa INTEGER, status TEXT, id_restaurante INTEGER, hora_abertura TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS cardapio (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, preco REAL, descricao TEXT, disponivel INTEGER, id_restaurante INTEGER, categoria TEXT DEFAULT 'Outros')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS pedidos (id INTEGER PRIMARY KEY AUTOINCREMENT, id_comanda INTEGER, id_produto INTEGER, status_pedido TEXT, lote INTEGER DEFAULT 1, observacao TEXT)''')

    # Adicionar colunas se não existirem (para compatibilidade com apps existentes)
    try:
        cursor.execute("ALTER TABLE funcionarios ADD COLUMN login TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE cardapio ADD COLUMN categoria TEXT DEFAULT 'Outros'")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE pedidos ADD COLUMN lote INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE pedidos ADD COLUMN observacao TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE comandas ADD COLUMN hora_pedido_conta TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE pedidos ADD COLUMN hora_pedido TEXT")
    except sqlite3.OperationalError:
        pass

    # Insere dados de exemplo se o restaurante não existir
    cursor.execute("SELECT COUNT(*) FROM restaurantes")
    if cursor.fetchone()[0] == 0:
        hoje = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("INSERT INTO restaurantes (nome, email, senha, status_plano, data_cadastro) VALUES ('Mario Pizza', 'mario@pizza.com', 'admin', 'ativo', ?)", (hoje,))
        rest_id = cursor.lastrowid
        cursor.execute("INSERT INTO funcionarios (nome, senha, cargo, id_restaurante, login) VALUES ('Chef Mario', '123', 'Cozinha', ?, 'chef.mario')", (rest_id,))
        cursor.execute("INSERT INTO funcionarios (nome, senha, cargo, id_restaurante, login) VALUES ('Garçom Luigi', '123', 'Garçom', ?, 'garcom.luigi')", (rest_id,))
        for i in range(1, 6):
            cursor.execute("INSERT INTO mesas (numero_mesa, id_restaurante) VALUES (?, ?)", (i, rest_id))
        cursor.execute("INSERT INTO cardapio (nome, preco, descricao, disponivel, id_restaurante, categoria) VALUES ('Pizza Margherita', 35.00, 'Molho de tomate, mussarela, manjericão', 1, ?, 'Pratos Principais')", (rest_id,))
        cursor.execute("INSERT INTO cardapio (nome, preco, descricao, disponivel, id_restaurante, categoria) VALUES ('Coca-Cola', 7.00, 'Lata 350ml', 1, ?, 'Bebidas')", (rest_id,))
        cursor.execute("INSERT INTO cardapio (nome, preco, descricao, disponivel, id_restaurante, categoria) VALUES ('Água Mineral', 5.00, 'Garrafa 500ml', 1, ?, 'Bebidas')", (rest_id,))
        cursor.execute("INSERT INTO cardapio (nome, preco, descricao, disponivel, id_restaurante, categoria) VALUES ('Batata Frita', 20.00, 'Porção grande com cheddar e bacon', 1, ?, 'Porções')", (rest_id,))
        cursor.execute("INSERT INTO cardapio (nome, preco, descricao, disponivel, id_restaurante, categoria) VALUES ('Brownie com Sorvete', 25.00, 'Brownie de chocolate com sorvete de creme', 1, ?, 'Sobremesas')", (rest_id,))

    conexao.commit()
    conexao.close()

inicializar_banco()

# ==========================================================================
# Lógica principal do aplicativo Flet
# ==========================================================================
def main(page: ft.Page):
    page.title = "Rachaki - Sistema de Gerenciamento de Restaurantes"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.padding = 20
    page.theme = ft.Theme(color_scheme_seed=CORES_CLARO["primaria"])
    page.dark_theme = ft.Theme(color_scheme_seed=CORES_ESCURO["primaria"])

    # Estado global para o aplicativo unificado
    global_state = {
        "id_restaurante": 0, "nome_usuario": "", "email_restaurante": "", "cargo": "",
        "loop_ativo": False, "sessao": 0, "aba_atual": "visao_geral",
        "carrinho": [], "id_comanda": 0, "numero_mesa": 0,
        "recarregar": lambda: None, # Placeholder para função de recarregar a tela atual
    }

    lock_ui = threading.Lock() # Para sincronizar atualizações de UI em threads

    def get_current_theme_colors():
        return obter_cores_tema(page.theme_mode)

    def mudar_tema_global(e):
        if e.control.data == "Claro":
            page.theme_mode = ft.ThemeMode.LIGHT
        elif e.control.data == "Escuro":
            page.theme_mode = ft.ThemeMode.DARK
        else:
            page.theme_mode = ft.ThemeMode.SYSTEM

        # Tenta recarregar a tela atual para aplicar o tema
        if global_state["recarregar"]:
            global_state["recarregar"]()
        else:
            page.update()

    # ==========================================================================
    # 0. TELA DE LOGIN/ACESSO UNIFICADA (ROTA: /)
    # ==========================================================================
    def view_root():
        global_state["loop_ativo"] = False # Garante que loops de atualização anteriores parem
        cores = get_current_theme_colors()
        global_state["recarregar"] = view_root # Define a função de recarregar para esta view

        page.clean()
        page.bgcolor = cores["fundo_principal"]
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

        # Campos para login de equipe/dono
        campo_login_equipe = ft.TextField(
            label="Login de Acesso (Ex: chef.mario)",
            hint_text="Para Equipe ou Dono",
            prefix_icon=ft.Icons.PERSON_OUTLINE,
            border_radius=10,
        )
        campo_senha_equipe = ft.TextField(
            label="Senha",
            password=True,
            can_reveal_password=True,
            prefix_icon=ft.Icons.LOCK_OUTLINE,
            border_radius=10,
        )
        msg_erro_login = ft.Text(value="", color=cores["erro"], weight="bold", text_align=ft.TextAlign.CENTER)

        def processar_login_equipe(e):
            login_digitado = campo_login_equipe.value.strip()
            senha_digitada = campo_senha_equipe.value.strip()

            if not login_digitado or not senha_digitada:
                msg_erro_login.value = "Preencha login e senha."
                page.update()
                return

            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()

            # Tenta login como Dono
            cursor.execute('SELECT id, nome FROM restaurantes WHERE email = ? AND senha = ?', (login_digitado, senha_digitada))
            restaurante = cursor.fetchone()
            if restaurante:
                global_state["id_restaurante"] = restaurante[0]
                global_state["nome_usuario"] = restaurante[1]
                global_state["email_restaurante"] = login_digitado
                global_state["cargo"] = "Dono"
                conexao.close()
                page.go("/dono")
                return

            # Tenta login como Funcionário
            cursor.execute('SELECT id, nome, cargo, id_restaurante FROM funcionarios WHERE login = ? AND senha = ?', (login_digitado, senha_digitada))
            func = cursor.fetchone()
            conexao.close()

            if func:
                global_state["id_funcionario"], global_state["nome_usuario"], global_state["cargo"], global_state["id_restaurante"] = func[0], func[1], func[2], func[3]
                if global_state["cargo"] == "Garçom":
                    page.go("/garcom")
                elif global_state["cargo"] == "Cozinha":
                    page.go("/cozinha")
                else:
                    msg_erro_login.value = "Cargo não reconhecido."
                    page.update()
            else:
                msg_erro_login.value = "Login ou senha incorretos para equipe/dono."
                page.update()

        def acessar_cliente(e):
            # Redireciona para o simulador de QR (primeira tela do app_visual)
            page.go("/visual")

        page.add(
            criar_cabecalho_tema(page, cores, mudar_tema_global),
            ft.ResponsiveRow(
                [ft.Container(col={"xs": 12, "sm": 10, "md": 8, "lg": 6}, content=ft.Card(
                    elevation=6,
                    content=ft.Container(
                        padding=35,
                        border_radius=16,
                        bgcolor=cores["fundo_secundario"],
                        border=criar_borda(cores["borda"]),
                        content=ft.Column([
                            ft.Text("Bem-vindo ao Rachaki", size=26, weight="bold", color=cores["texto_principal"], text_align=ft.TextAlign.CENTER),
                            ft.Text("Escolha como deseja acessar o sistema:", size=14, color=cores["texto_secundario"], text_align=ft.TextAlign.CENTER),
                            ft.Divider(height=25, color="transparent"),
                            ft.Text("Acesso para Clientes", size=18, weight="bold", color=cores["primaria"]),
                            criar_botao("Fazer Pedido (Cliente)", acessar_cliente, cores["sucesso"], icone=ft.Icons.MENU_BOOK_OUTLINED),
                            ft.Divider(height=25, color="transparent"),
                            ft.Text("Acesso para Equipe e Dono", size=18, weight="bold", color=cores["primaria"]),
                            campo_login_equipe,
                            campo_senha_equipe,
                            ft.Container(height=10),
                            criar_botao("Entrar (Equipe/Dono)", processar_login_equipe, cores["primaria"], icone=ft.Icons.LOGIN),
                            msg_erro_login
                        ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=14)
                    )
                ))],
                alignment=ft.MainAxisAlignment.CENTER
            )
        )
        page.update()

    # ==========================================================================
    # 1. APP VISUAL (CLIENTE) - ROTA: /visual
    # ==========================================================================
    def view_visual():
        global_state["loop_ativo"] = False
        cores = get_current_theme_colors()
        global_state["recarregar"] = view_visual

        page.clean()
        page.bgcolor = cores["fundo_principal"]
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

        campo_restaurante = ft.TextField(
            label="ID do Restaurante",
            hint_text="Ex: 1",
            prefix_icon=ft.Icons.STORE_MALL_DIRECTORY_OUTLINED,
            border_radius=10,
        )
        campo_mesa = ft.TextField(
            label="Número da Mesa",
            hint_text="Ex: 5",
            prefix_icon=ft.Icons.TABLE_RESTAURANT_OUTLINED,
            border_radius=10,
        )
        msg_erro = ft.Text(value="", color=cores["erro"], weight="bold", text_align=ft.TextAlign.CENTER)

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
                        global_state["id_restaurante"], global_state["numero_mesa"] = id_rest, num_mesa
                        page.go("/visual/boasvindas")
                else:
                    msg_erro.value = "Mesa ou Restaurante não encontrados."
                conexao.close()
                page.update()
            except ValueError:
                msg_erro.value = "Digite apenas números."
                page.update()

        cartao = ft.Card(
            elevation=6,
            content=ft.Container(
                padding=35,
                border_radius=16,
                bgcolor=cores["fundo_secundario"],
                border=criar_borda(cores["borda"]),
                content=ft.Column([
                    ft.Container(content=ft.Text("🍽️", size=54), alignment=alinhamento_centro()),
                    ft.Text("Bem-vindo ao Rachaki", size=26, weight="bold", color=cores["texto_principal"], text_align=ft.TextAlign.CENTER),
                    ft.Text("Escaneie o QR Code da mesa ou informe os dados abaixo", size=14, color=cores["texto_secundario"], text_align=ft.TextAlign.CENTER),
                    ft.Divider(height=25, color="transparent"),
                    campo_restaurante,
                    campo_mesa,
                    ft.Container(height=10),
                    criar_botao("Acessar Mesa", acessar_mesa, cores["primaria"], icone=ft.Icons.LOGIN),
                    msg_erro
                ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=14)
            )
        )

        page.views.append(
            ft.View(
                "/visual",
                [
                    criar_cabecalho_tema(page, cores, mudar_tema_global),
                    ft.ResponsiveRow(
                        [ft.Container(col={"xs": 12, "sm": 10, "md": 8, "lg": 4, "xl": 4}, content=cartao)],
                        alignment=ft.MainAxisAlignment.CENTER
                    )
                ],
                scroll_to_top=True
            )
        )
        page.update()

    def view_visual_boasvindas():
        cores = get_current_theme_colors()
        global_state["recarregar"] = view_visual_boasvindas

        page.clean()
        page.bgcolor = cores["fundo_principal"]
        page.vertical_alignment = ft.MainAxisAlignment.CENTER

        campo_nome = ft.TextField(
            label="Qual o seu nome ou apelido?",
            prefix_icon=ft.Icons.PERSON_OUTLINE,
            border_radius=10,
        )
        msg_erro = ft.Text(value="", color=cores["erro"], text_align=ft.TextAlign.CENTER)

        def abrir_comanda(e):
            nome = campo_nome.value.strip()
            if nome:
                conexao = sqlite3.connect('rachaki.db')
                cursor = conexao.cursor()
                agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                # Precisa do id_mesa, que foi obtido na tela anterior
                cursor.execute('SELECT id FROM mesas WHERE id_restaurante = ? AND numero_mesa = ?', (global_state["id_restaurante"], global_state["numero_mesa"]))
                id_mesa = cursor.fetchone()[0]

                cursor.execute('INSERT INTO comandas (nome_cliente, id_mesa, status, id_restaurante, hora_abertura) VALUES (?, ?, ?, ?, ?)', (nome, id_mesa, 'Aberta', global_state["id_restaurante"], agora))
                global_state["id_comanda"] = cursor.lastrowid
                conexao.commit()
                conexao.close()
                global_state["nome_usuario"] = nome
                page.go("/visual/cardapio")
            else:
                msg_erro.value = "Por favor, informe como quer ser chamado."
                page.update()

        cartao = ft.Card(
            elevation=6,
            content=ft.Container(
                padding=35,
                border_radius=16,
                bgcolor=cores["fundo_secundario"],
                border=criar_borda(cores["borda"]),
                content=ft.Column([
                    ft.Container(content=criar_chip(f"Mesa {global_state['numero_mesa']}", cores["secundaria"], cores["texto_principal"]), alignment=alinhamento_centro()),
                    ft.Text("Como podemos te chamar?", size=26, weight="bold", color=cores["texto_principal"], text_align=ft.TextAlign.CENTER),
                    ft.Divider(height=20, color="transparent"),
                    campo_nome,
                    ft.Container(height=10),
                    criar_botao("Abrir Comanda e Ver Cardápio", abrir_comanda, cores["sucesso"], cor_texto=cores["texto_principal"], icone=ft.Icons.MENU_BOOK_OUTLINED),
                    msg_erro
                ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=14)
            )
        )

        page.views.append(
            ft.View(
                "/visual/boasvindas",
                [
                    criar_cabecalho_tema(page, cores, mudar_tema_global),
                    ft.ResponsiveRow(
                        [ft.Container(col={"xs": 12, "sm": 10, "md": 8, "lg": 4}, content=cartao)],
                        alignment=ft.MainAxisAlignment.CENTER
                    )
                ],
                scroll_to_top=True
            )
        )
        page.update()

    def view_visual_cardapio():
        global_state["loop_ativo"] = False
        cores = get_current_theme_colors()
        global_state["recarregar"] = view_visual_cardapio

        page.clean()
        page.bgcolor = cores["fundo_principal"]
        page.vertical_alignment = ft.MainAxisAlignment.START

        cabecalho = ft.Column([
            ft.Text(f"Olá, {global_state['nome_usuario']}! 👋", size=24, weight="bold", color=cores["texto_principal"], text_align=ft.TextAlign.CENTER),
            ft.Container(content=criar_chip(f"Mesa {global_state['numero_mesa']}", cores["secundaria"], cores["texto_principal"]), alignment=alinhamento_centro()),
            ft.Divider()
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)

        lista_produtos = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=12)

        def adicionar_item(e, id_item, nome, preco, categoria):
            global_state["carrinho"].append({"id": id_item, "nome": nome, "preco": preco, "categoria": categoria})
            e.control.text = "Adicionado!"
            e.control.icon = ft.Icons.CHECK_CIRCLE
            e.control.style = ft.ButtonStyle(bgcolor=cores["sucesso"], color=cores["texto_principal"], shape=ft.RoundedRectangleBorder(radius=10))
            page.update()
            time.sleep(1)
            e.control.text = "Adicionar"
            e.control.icon = ft.Icons.ADD_SHOPPING_CART
            e.control.style = ft.ButtonStyle(bgcolor=cores["primaria"], color="#FFFFFF", shape=ft.RoundedRectangleBorder(radius=10))
            page.update()

        conexao = sqlite3.connect('rachaki.db')
        cursor = conexao.cursor()
        cursor.execute('SELECT id, nome, preco, descricao, categoria FROM cardapio WHERE id_restaurante = ? AND disponivel = 1', (global_state["id_restaurante"],))
        itens = cursor.fetchall()
        conexao.close()

        if len(itens) == 0:
            lista_produtos.controls.append(
                ft.Container(
                    content=ft.Text("O cardápio está vazio no momento.", color=cores["texto_secundario"], text_align=ft.TextAlign.CENTER),
                    bgcolor=cores["cards"], padding=20, border_radius=10, alignment=alinhamento_centro()
                )
            )
        else:
            itens_por_categoria = {}
            for id_item, nome_item, preco_item, descricao_item, categoria in itens:
                cat = categoria if categoria else "Outros"
                if cat not in itens_por_categoria:
                    itens_por_categoria[cat] = []
                itens_por_categoria[cat].append((id_item, nome_item, preco_item, descricao_item))

            ordem_categorias = ["Entradas", "Pratos Principais", "Lanches", "Sobremesas", "Bebidas", "Outros"]

            for categoria in ordem_categorias:
                if categoria in itens_por_categoria:
                    lista_produtos.controls.append(
                        ft.Container(
                            content=ft.Text(categoria.upper(), size=15, weight="bold", color="#FFFFFF"),
                            bgcolor=cores["primaria"],
                            padding=criar_padding_simetrico(horizontal=16, vertical=10),
                            border_radius=20,
                            margin=ft.Margin(top=15, bottom=5, left=0, right=0)
                        )
                    )

                    for id_item, nome_item, preco_item, descricao_item in itens_por_categoria[categoria]:
                        card = ft.Card(
                            elevation=3,
                            content=ft.Container(
                                padding=16,
                                border_radius=12,
                                bgcolor=cores["fundo_secundario"],
                                content=ft.Column([
                                    ft.Text(nome_item, size=17, weight="bold", color=cores["texto_principal"]),
                                    ft.Text(descricao_item, size=13, color=cores["texto_secundario"]) if descricao_item else ft.Container(),
                                    ft.Row([
                                        ft.Text(f"R$ {preco_item:.2f}", size=16, weight="bold", color=cores["primaria"]),
                                        ft.Button(
                                            "Adicionar",
                                            icon=ft.Icons.ADD_SHOPPING_CART,
                                            style=ft.ButtonStyle(bgcolor=cores["primaria"], color="#FFFFFF", shape=ft.RoundedRectangleBorder(radius=10)),
                                            on_click=lambda e, id_i=id_item, n=nome_item, p=preco_item, c=categoria: adicionar_item(e, id_i, n, p, c)
                                        )
                                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                                ], spacing=6)
                            )
                        )
                        lista_produtos.controls.append(card)

        qtd_itens_carrinho = len(global_state["carrinho"])
        texto_botao_carrinho = f"Ver Minha Conta / Carrinho ({qtd_itens_carrinho})" if qtd_itens_carrinho > 0 else "Ver Minha Conta / Carrinho"

        botao_ver_conta = criar_botao(
            texto_botao_carrinho,
            lambda e: page.go("/visual/conta"),
            cores["secundaria"],
            cor_texto=cores["texto_principal"],
            icone=ft.Icons.SHOPPING_CART_OUTLINED
        )

        conteudo_principal = ft.Column([
            cabecalho,
            lista_produtos,
            ft.Divider(height=20, color="transparent"),
            botao_ver_conta
        ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

        page.views.append(
            ft.View(
                "/visual/cardapio",
                [
                    criar_cabecalho_tema(page, cores, mudar_tema_global),
                    ft.ResponsiveRow(
                        [ft.Container(col={"xs": 12, "md": 8, "lg": 6}, content=conteudo_principal)],
                        alignment=ft.MainAxisAlignment.CENTER
                    )
                ],
                scroll_to_top=True
            )
        )
        page.update()

    def view_visual_conta():
        global_state["loop_ativo"] = True
        cores = get_current_theme_colors()
        global_state["recarregar"] = view_visual_conta

        page.clean()
        page.bgcolor = cores["fundo_principal"]
        page.vertical_alignment = ft.MainAxisAlignment.START

        area_carrinho = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=10)
        coluna_pedidos_conta = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=8)
        area_total = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=14)

        total_conta = 0

        campo_observacao_geral = ft.TextField(
            label="Observações do pedido (opcional)",
            hint_text="Ex: Favor retirar o tomate do sanduíche",
            prefix_icon=ft.Icons.EDIT_NOTE_OUTLINED,
            multiline=True,
            min_lines=2,
            max_lines=4,
            border_radius=10,
        )

        def atualizar_carrinho():
            area_carrinho.controls.clear()
            area_carrinho.controls.append(
                ft.Row([
                    ft.Icon(ft.Icons.SHOPPING_CART, color=cores["secundaria"]),
                    ft.Text("Ordem Atual (Não enviada)", size=19, weight="bold", color=cores["texto_principal"])
                ], alignment=ft.MainAxisAlignment.CENTER)
            )

            if len(global_state["carrinho"]) == 0:
                area_carrinho.controls.append(
                    ft.Text("Sua ordem de pedido está vazia.", color=cores["texto_secundario"], text_align=ft.TextAlign.CENTER)
                )
            else:
                subtotal = sum(item['preco'] for item in global_state["carrinho"])
                for item in global_state["carrinho"]:
                    def remover_item(e, item_rem=item):
                        global_state["carrinho"].remove(item_rem)
                        atualizar_carrinho()
                        page.update()

                    linha_topo = ft.Row([
                        ft.Text(f"{item['nome']} - R$ {item['preco']:.2f}", weight="bold", color=cores["texto_principal"], expand=True),
                        ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color=cores["erro"], on_click=remover_item)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

                    controles_item = [linha_topo]

                    if item.get('categoria') == 'Bebidas':
                        if 'observacao' not in item:
                            item['observacao'] = "Junto com o prato principal"

                        def mudar_obs(e, it=item):
                            it['observacao'] = e.control.value

                        dropdown_bebida = ft.Dropdown(
                            options=[
                                ft.dropdown.Option("Junto com o prato principal"),
                                ft.dropdown.Option("Pode servir agora")
                            ],
                            value=item['observacao'],
                            expand=True,
                            border_radius=10,
                        )
                        dropdown_bebida.on_change = mudar_obs
                        item['controle_dropdown'] = dropdown_bebida
                        controles_item.append(ft.Row([ft.Icon(ft.Icons.LOCAL_DRINK, size=20, color=cores["texto_secundario"]), dropdown_bebida]))

                    area_carrinho.controls.append(
                        ft.Container(
                            content=ft.Column(controles_item, spacing=8),
                            bgcolor=cores["cards"], padding=12, border_radius=10, border=criar_borda(cores["borda"])
                        )
                    )

                area_carrinho.controls.append(ft.Container(height=6))
                area_carrinho.controls.append(campo_observacao_geral)
                area_carrinho.controls.append(ft.Divider())
                area_carrinho.controls.append(
                    ft.Text(f"Subtotal a enviar: R$ {subtotal:.2f}", color=cores["texto_principal"], weight="bold", text_align=ft.TextAlign.CENTER)
                )

                def confirmar_envio(e):
                    e.control.disabled = True
                    e.control.text = "Enviando..."
                    page.update()
                    conexao = sqlite3.connect('rachaki.db')
                    cursor = conexao.cursor()

                    cursor.execute('SELECT MAX(lote) FROM pedidos WHERE id_comanda = ?', (global_state["id_comanda"],))
                    resultado_lote = cursor.fetchone()[0]
                    novo_lote = (resultado_lote or 0) + 1
                    agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                    for item_c in global_state["carrinho"]:
                        if item_c.get('categoria') == 'Bebidas':
                            if 'controle_dropdown' in item_c:
                                obs_final = item_c['controle_dropdown'].value
                            else:
                                obs_final = item_c.get('observacao', '')
                        else:
                            obs_final = campo_observacao_geral.value.strip() if campo_observacao_geral.value else ""

                        cursor.execute('INSERT INTO pedidos (id_comanda, id_produto, status_pedido, lote, observacao, hora_pedido) VALUES (?, ?, ?, ?, ?, ?)',
                                       (global_state["id_comanda"], item_c['id'], 'Recebido', novo_lote, obs_final, agora))

                    conexao.commit()
                    conexao.close()
                    global_state["carrinho"].clear()
                    campo_observacao_geral.value = ""
                    atualizar_carrinho()
                    nonlocal dados_anteriores_conta
                    dados_anteriores_conta = None
                    carregar_pedidos_conta()

                area_carrinho.controls.append(
                    criar_botao("Confirmar e Enviar para Cozinha", confirmar_envio, cores["sucesso"], cor_texto=cores["texto_principal"], icone=ft.Icons.SEND_OUTLINED)
                )

        atualizar_carrinho()
        texto_total_valor = ft.Text("TOTAL CONFIRMADO: R$ 0.00", size=22, weight="bold", color=cores["erro"], text_align=ft.TextAlign.CENTER)

        campo_pessoas = ft.TextField(label="Dividir por quantos?", prefix_icon=ft.Icons.GROUP_OUTLINED, expand=True, border_radius=10)
        texto_divisao = ft.Text(value="", size=18, weight="bold", color=cores["primaria"], text_align=ft.TextAlign.CENTER)

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

        area_divisao = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.CALCULATE_OUTLINED, color=cores["texto_secundario"]),
                    ft.Text("Dividir a conta", size=15, weight="bold", color=cores["texto_principal"])
                ]),
                ft.Row([campo_pessoas, criar_botao("Calcular", calcular_divisao, cores["primaria"], altura=48)]),
                texto_divisao
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
            bgcolor=cores["cards"], padding=15, border_radius=10, border=criar_borda(cores["borda"])
        )

        def encerrar_comanda(e):
            global_state["loop_ativo"] = False
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()
            agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("UPDATE comandas SET status = 'Aguardando Pagamento', hora_pedido_conta = ? WHERE id = ?", (agora, global_state["id_comanda"],))
            conexao.commit()
            conexao.close()

            cores_atuais = get_current_theme_colors()
            page.clean()
            page.bgcolor = cores_atuais["fundo_principal"]
            page.vertical_alignment = ft.MainAxisAlignment.CENTER

            cartao_despedida = ft.Card(
                elevation=6,
                content=ft.Container(
                    padding=35,
                    border_radius=16,
                    bgcolor=cores_atuais["fundo_secundario"],
                    border=criar_borda(cores_atuais["borda"]),
                    content=ft.Column([
                        ft.Container(content=ft.Text("🔔", size=48), alignment=alinhamento_centro()),
                        ft.Text("Garçom chamado!", size=24, color=cores_atuais["texto_principal"], weight="bold", text_align=ft.TextAlign.CENTER),
                        ft.Text("Aguarde na mesa. O garçom está indo até você para realizar o pagamento.", size=15, color=cores_atuais["texto_secundario"], text_align=ft.TextAlign.CENTER),
                        ft.Divider(height=20, color="transparent"),
                        criar_botao("Sair da Mesa", lambda e: page.go("/visual"), cores_atuais["primaria"], icone=ft.Icons.LOGOUT)
                    ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=14)
                )
            )

            page.views.append(
                ft.View(
                    "/visual/despedida",
                    [
                        ft.ResponsiveRow(
                            [ft.Container(col={"xs": 12, "sm": 10, "md": 8, "lg": 4}, content=cartao_despedida)],
                            alignment=ft.MainAxisAlignment.CENTER
                        )
                    ],
                    scroll_to_top=True
                )
            )
            page.update()

        botoes_finais = ft.ResponsiveRow([
            ft.Container(col={"xs": 12, "sm": 6}, content=criar_botao(
                "Voltar ao Cardápio", lambda e: page.go("/visual/cardapio"), cores["fundo_secundario"], cor_texto=cores["primaria"], icone=ft.Icons.ARROW_BACK
            )),
            ft.Container(col={"xs": 12, "sm": 6}, content=criar_botao(
                "Encerrar e Pagar", encerrar_comanda, cores["erro"], cor_texto=cores["texto_principal"], icone=ft.Icons.PAYMENTS_OUTLINED
            ))
        ])

        area_total.controls.extend([
            texto_total_valor, area_divisao, ft.Divider(), botoes_finais
        ])

        dados_anteriores_conta = None

        def carregar_pedidos_conta():
            nonlocal dados_anteriores_conta, total_conta
            if not global_state["loop_ativo"]:
                return
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()
            cursor.execute('SELECT cardapio.nome, cardapio.preco, pedidos.status_pedido FROM pedidos JOIN cardapio ON pedidos.id_produto = cardapio.id WHERE pedidos.id_comanda = ?', (global_state["id_comanda"],))
            meus_pedidos = cursor.fetchall()
            conexao.close()

            if meus_pedidos == dados_anteriores_conta:
                return
            dados_anteriores_conta = meus_pedidos
            coluna_pedidos_conta.controls.clear()
            coluna_pedidos_conta.controls.append(
                ft.Row([
                    ft.Icon(ft.Icons.RECEIPT_LONG_OUTLINED, color=cores["primaria"]),
                    ft.Text("Pedidos Confirmados", size=19, weight="bold", color=cores["texto_principal"])
                ], alignment=ft.MainAxisAlignment.CENTER)
            )

            total_conta = 0
            if len(meus_pedidos) == 0:
                coluna_pedidos_conta.controls.append(
                    ft.Text("Você ainda não enviou nenhum pedido.", size=15, color=cores["texto_secundario"], text_align=ft.TextAlign.CENTER)
                )
            else:
                mapa_status = {
                    "Recebido": ("🕒 Enviado", cores["aviso"]),
                    "Preparando": ("🍳 Preparando", cores["aviso"]),
                    "Pronto": ("🔔 Pronto", cores["sucesso"]),
                    "Entregue": ("✅ Entregue", cores["sucesso"]),
                }
                for nome_produto, preco_produto, status_pedido in meus_pedidos:
                    total_conta += preco_produto
                    status_str, cor_status = mapa_status.get(status_pedido, ("✅ Entregue", cores["sucesso"]))
                    coluna_pedidos_conta.controls.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Text(f"{nome_produto} - R$ {preco_produto:.2f}", size=15, weight="bold", color=cores["texto_principal"], expand=True),
                                criar_chip(status_str, cor_status, cores["texto_principal"])
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            bgcolor=cores["fundo_secundario"], padding=12, border_radius=10, border=criar_borda(cores["borda"])
                        )
                    )

            texto_total_valor.value = f"TOTAL CONFIRMADO: R$ {total_conta:.2f}"
            page.update()

        def loop_conta():
            while global_state["loop_ativo"]:
                carregar_pedidos_conta()
                time.sleep(5)

        carregar_pedidos_conta()
        threading.Thread(target=loop_conta, daemon=True).start()

        conteudo_principal = ft.Column([
            ft.Text(f"Minha Conta - {global_state['nome_usuario']}", size=24, weight="bold", color=cores["texto_principal"], text_align=ft.TextAlign.CENTER),
            ft.Container(content=criar_chip(f"Mesa {global_state['numero_mesa']}", cores["secundaria"], cores["texto_principal"]), alignment=alinhamento_centro()),
            ft.Divider(),
            area_carrinho,
            ft.Divider(),
            coluna_pedidos_conta,
            ft.Divider(),
            area_total
        ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

        page.views.append(
            ft.View(
                "/visual/conta",
                [
                    criar_cabecalho_tema(page, cores, mudar_tema_global),
                    ft.ResponsiveRow(
                        [ft.Container(col={"xs": 12, "md": 8, "lg": 6}, content=conteudo_principal)],
                        alignment=ft.MainAxisAlignment.CENTER
                    )
                ],
                scroll_to_top=True
            )
        )
        page.update()

    # ==========================================================================
    # 2. APP GARÇOM - ROTA: /garcom
    # ==========================================================================
    def view_garcom():
        global_state["loop_ativo"] = True
        global_state["sessao"] += 1
        minha_sessao = global_state["sessao"]

        t = get_current_theme_colors()
        global_state["recarregar"] = view_garcom

        page.clean()
        page.bgcolor = t["fundo_principal"]
        page.vertical_alignment = ft.MainAxisAlignment.START
        page.horizontal_alignment = ft.CrossAxisAlignment.START

        def agrupar_com_quantidade(lista_nomes):
            contagem, ordem = {}, []
            for nome in lista_nomes:
                if nome not in contagem:
                    contagem[nome] = 0
                    ordem.append(nome)
                contagem[nome] += 1
            return [(nome, contagem[nome]) for nome in ordem]

        def texto_item_qtd(nome, qtd):
            return f"{nome} (x{qtd})" if qtd > 1 else nome

        def fazer_logout_garcom(e=None):
            global_state["loop_ativo"] = False
            global_state["id_funcionario"] = 0
            global_state["nome_usuario"] = ""
            global_state["cargo"] = ""
            global_state["id_restaurante"] = 0
            page.go("/")

        # --- MODAL DE HISTÓRICO ---
        lista_historico = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=10, height=420)

        def fechar_historico(e):
            dlg_historico.open = False
            page.update()

        dlg_historico = ft.AlertDialog(
            title=ft.Text("Histórico de Entregas", weight="bold", color=t["texto_principal"]),
            content=ft.Container(width=500, content=lista_historico),
            bgcolor=t["fundo_secundario"],
            actions=[ft.TextButton("Fechar", on_click=fechar_historico, style=ft.ButtonStyle(color=t["primaria"]))],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dlg_historico)

        def abrir_historico(e):
            lista_historico.controls.clear()

            largura_dialog = 500
            if page.width:
                largura_dialog = min(600, max(300, page.width - 60))
            dlg_historico.content.width = largura_dialog

            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()

            cursor.execute('''
                SELECT pedidos.id, cardapio.nome, mesas.numero_mesa, pedidos.lote, comandas.nome_cliente, comandas.id
                FROM pedidos JOIN comandas ON pedidos.id_comanda = comandas.id
                JOIN mesas ON comandas.id_mesa = mesas.id JOIN cardapio ON pedidos.id_produto = cardapio.id
                WHERE comandas.id_restaurante = ? AND pedidos.status_pedido = 'Entregue'
                ORDER BY pedidos.id DESC LIMIT 50
            ''', (global_state["id_restaurante"],))

            entregues = cursor.fetchall()
            conexao.close()

            if not entregues:
                lista_historico.controls.append(ft.Text("Nenhum pedido entregue recentemente.", color=t["texto_secundario"]))
            else:
                lotes_entregues = {}
                for id_ped, nome_prod, num_mesa, lote, nome_cli, id_com in entregues:
                    chave = (id_com, num_mesa, nome_cli, lote)
                    lotes_entregues.setdefault(chave, []).append(nome_prod)

                for chave, itens in lotes_entregues.items():
                    id_com, num_mesa, nome_cli, lote = chave
                    coluna_itens = ft.Column(spacing=2)

                    for nome, qtd in agrupar_com_quantidade(itens):
                        coluna_itens.controls.append(
                            ft.Text(f"• {texto_item_qtd(nome, qtd)}", size=15, color=t["texto_secundario"],
                                    style=ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH))
                        )

                    card = ft.Container(
                        content=ft.Column([
                            ft.Text(f"Mesa {num_mesa} ({nome_cli}) - Lote {lote}", weight="bold", color=t["texto_principal"]),
                            ft.Divider(height=1, color=t["borda"]),
                            coluna_itens,
                            ft.Text("✅ Entregue", color=t["sucesso"], size=12, weight="bold")
                        ]), bgcolor=t["cards"], padding=12, border_radius=10
                    )
                    lista_historico.controls.append(card)

            dlg_historico.open = True
            page.update()
        # ------------------------------------

        icone_tema = ft.Icons.DARK_MODE if page.theme_mode == ft.ThemeMode.LIGHT else ft.Icons.LIGHT_MODE

        cabecalho = ft.Container(
            content=ft.ResponsiveRow([
                ft.Container(col={"xs": 12, "sm": 6},
                             content=ft.Text(f"Salão - {global_state['nome_usuario']}", size=24, weight="bold", color=t["primaria"])),
                ft.Container(col={"xs": 12, "sm": 6}, content=ft.Row([
                    ft.IconButton(icon=icone_tema, tooltip="Alternar tema", on_click=mudar_tema_global, icon_color=t["texto_secundario"]),
                    ft.IconButton(icon=ft.Icons.HISTORY, tooltip="Histórico", on_click=abrir_historico, icon_color=t["texto_secundario"]),
                    ft.IconButton(icon=ft.Icons.REFRESH, tooltip="Atualizar", on_click=lambda e: carregar_dados_salao(), icon_color=t["texto_secundario"]),
                    ft.IconButton(icon=ft.Icons.LOGOUT, tooltip="Sair", on_click=fazer_logout_garcom, icon_color=t["erro"]),
                ], alignment=ft.MainAxisAlignment.END, wrap=True))
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=t["fundo_secundario"], padding=15, border_radius=14,
            shadow=ft.BoxShadow(blur_radius=8, color=ft.Colors.with_opacity(0.08, ft.Colors.BLACK), offset=ft.Offset(0, 2))
        )

        coluna_servir_agora = ft.Column(spacing=10)
        coluna_prontos = ft.Column(spacing=10)
        coluna_pagamento = ft.Column(spacing=10)

        def marcar_entregue_agora(e):
            ids_pedidos = e.control.data
            e.control.disabled = True
            page.update()
            with lock_ui:
                conexao = sqlite3.connect('rachaki.db')
                cursor = conexao.cursor()
                placeholders = ",".join(["?"] * len(ids_pedidos))
                cursor.execute(f"UPDATE pedidos SET status_pedido = 'Entregue' WHERE id IN ({placeholders})", ids_pedidos)
                conexao.commit()
                conexao.close()
            carregar_dados_salao()

        def marcar_lote_entregue(e, id_comanda, lote):
            e.control.disabled = True
            page.update()
            with lock_ui:
                conexao = sqlite3.connect('rachaki.db')
                cursor = conexao.cursor()
                cursor.execute("UPDATE pedidos SET status_pedido = 'Entregue' WHERE id_comanda = ? AND lote = ? AND status_pedido = 'Pronto'", (id_comanda, lote))
                conexao.commit()
                conexao.close()
            carregar_dados_salao()

        def fechar_conta(e):
            e.control.disabled = True
            page.update()
            id_comanda = e.control.data
            with lock_ui:
                conexao = sqlite3.connect('rachaki.db')
                cursor = conexao.cursor()
                cursor.execute("UPDATE comandas SET status = 'Fechada' WHERE id = ?", (id_comanda,))
                conexao.commit()
                conexao.close()
            carregar_dados_salao()

        def carregar_dados_salao():
            if not global_state["loop_ativo"] or global_state["sessao"] != minha_sessao:
                return

            with lock_ui:
                coluna_servir_agora.controls.clear()
                coluna_prontos.controls.clear()
                coluna_pagamento.controls.clear()

                conexao = sqlite3.connect('rachaki.db')
                cursor = conexao.cursor()

                cursor.execute('''
                    SELECT pedidos.id, cardapio.nome, mesas.numero_mesa, comandas.nome_cliente
                    FROM pedidos JOIN comandas ON pedidos.id_comanda = comandas.id
                    JOIN mesas ON comandas.id_mesa = mesas.id JOIN cardapio ON pedidos.id_produto = cardapio.id
                    WHERE comandas.id_restaurante = ?
                    AND pedidos.status_pedido IN ('Recebido', 'Preparando', 'Pronto')
                    AND pedidos.observacao LIKE '%agora%'
                ''', (global_state["id_restaurante"],))

                servir_agora = cursor.fetchall()
                if not servir_agora:
                    coluna_servir_agora.controls.append(ft.Text("Nenhuma bebida pendente.", color=t["texto_secundario"]))
                else:
                    grupos_agora = {}
                    for id_ped, nome_prod, num_mesa, nome_cli in servir_agora:
                        chave = (num_mesa, nome_cli, nome_prod)
                        grupos_agora.setdefault(chave, []).append(id_ped)

                    for (num_mesa, nome_cli, nome_prod), ids_pedidos in grupos_agora.items():
                        qtd = len(ids_pedidos)
                        card = ft.Container(
                            content=ft.Column([
                                ft.Text(f"Mesa {num_mesa} - {nome_cli}", weight="bold", size=14, color=t["on_warning"]),
                                ft.Text(texto_item_qtd(nome_prod, qtd), size=18, color=t["on_warning"], weight="bold"),
                                ft.Button("Marcar Entregue", data=ids_pedidos, on_click=marcar_entregue_agora,
                                          style=ft.ButtonStyle(bgcolor=t["primaria"], color=t["on_primary"], shape=ft.RoundedRectangleBorder(radius=8)))
                            ], spacing=6),
                            bgcolor=t["aviso"], padding=15, border_radius=12, margin=ft.Margin(left=0, top=0, right=0, bottom=10)
                        )
                        coluna_servir_agora.controls.append(card)

                cursor.execute('''
                    SELECT pedidos.id, cardapio.nome, mesas.numero_mesa, pedidos.lote, comandas.nome_cliente, comandas.id
                    FROM pedidos JOIN comandas ON pedidos.id_comanda = comandas.id
                    JOIN mesas ON comandas.id_mesa = mesas.id JOIN cardapio ON pedidos.id_produto = cardapio.id
                    WHERE comandas.id_restaurante = ? AND pedidos.status_pedido = 'Pronto'
                    AND (pedidos.observacao IS NULL OR pedidos.observacao NOT LIKE '%agora%')
                    ORDER BY comandas.id ASC, pedidos.lote ASC
                ''', (global_state["id_restaurante"],))

                prontos = cursor.fetchall()
                if not prontos:
                    coluna_prontos.controls.append(ft.Text("Nenhum pedido aguardando entrega.", color=t["texto_secundario"]))
                else:
                    lotes_prontos = {}
                    for id_ped, nome_prod, num_mesa, lote, nome_cli, id_com in prontos:
                        chave = (id_com, num_mesa, nome_cli, lote)
                        lotes_prontos.setdefault(chave, []).append(nome_prod)

                    for chave, itens in lotes_prontos.items():
                        id_com, num_mesa, nome_cli, lote = chave
                        coluna_itens = ft.Column(spacing=5)

                        for nome, qtd in agrupar_com_quantidade(itens):
                            coluna_itens.controls.append(ft.Text(f"• {texto_item_qtd(nome, qtd)}", size=16, weight="bold", color=t["on_success"]))

                        card = ft.Container(
                            content=ft.Column([
                                ft.Text(f"Mesa {num_mesa} ({nome_cli}) - Lote {lote}", weight="bold", size=18, color=t["on_success"]),
                                ft.Divider(height=1, color=ft.Colors.with_opacity(0.3, t["on_success"])),
                                coluna_itens,
                                ft.Container(height=5),
                                ft.Row([
                                    ft.Button("Entregar Tudo", on_click=lambda e, id_c=id_com, l=lote: marcar_lote_entregue(e, id_c, l),
                                              style=ft.ButtonStyle(bgcolor=t["primaria"], color=t["on_primary"], shape=ft.RoundedRectangleBorder(radius=8)))
                                ], alignment=ft.MainAxisAlignment.END)
                            ]), bgcolor=t["sucesso"], padding=15, border_radius=12, margin=ft.Margin(left=0, top=0, right=0, bottom=10)
                        )
                        coluna_prontos.controls.append(card)

                cursor.execute('''
                    SELECT comandas.id, mesas.numero_mesa, comandas.nome_cliente
                    FROM comandas JOIN mesas ON comandas.id_mesa = mesas.id
                    WHERE comandas.id_restaurante = ? AND comandas.status = 'Aguardando Pagamento'
                ''', (global_state["id_restaurante"],))

                mesas_pagamento = cursor.fetchall()
                if not mesas_pagamento:
                    coluna_pagamento.controls.append(ft.Text("Nenhuma mesa aguardando pagamento.", color=t["texto_secundario"]))
                else:
                    for id_com, num_mesa, nome_cli in mesas_pagamento:
                        cursor.execute('SELECT SUM(cardapio.preco) FROM pedidos JOIN cardapio ON pedidos.id_produto = cardapio.id WHERE pedidos.id_comanda = ?', (id_com,))
                        total_mesa = cursor.fetchone()[0] or 0.0

                        card = ft.Container(
                            content=ft.Column([
                                ft.Text(f"Mesa {num_mesa} - {nome_cli}", weight="bold", color=t["on_error"]),
                                ft.Text(f"Total: R$ {total_mesa:.2f}", size=16, color=t["on_error"], weight="bold"),
                                ft.Button("Fechar Conta", on_click=fechar_conta, data=id_com,
                                          style=ft.ButtonStyle(bgcolor=t["fundo_secundario"], color=t["erro"], shape=ft.RoundedRectangleBorder(radius=8)))
                            ]), bgcolor=t["erro"], padding=15, border_radius=12, margin=ft.Margin(left=0, top=0, right=0, bottom=10)
                        )
                        coluna_pagamento.controls.append(card)

                conexao.close()

            page.update()

        def loop_salao():
            while global_state["loop_ativo"] and global_state["sessao"] == minha_sessao:
                carregar_dados_salao()
                time.sleep(5)

        def cabecalho_secao(icone, texto, cor):
            return ft.Row([ft.Icon(icone, color=cor, size=20), ft.Text(texto, size=18, weight="bold", color=t["texto_principal"])],
                          alignment=ft.MainAxisAlignment.CENTER)

        area_colunas = ft.ResponsiveRow([
            ft.Container(col={"xs": 12, "md": 4}, content=ft.Column([
                cabecalho_secao(ft.Icons.NOTIFICATIONS_ACTIVE, "Servir Agora", t["aviso"]),
                coluna_servir_agora
            ])),
            ft.Container(col={"xs": 12, "md": 4}, content=ft.Column([
                cabecalho_secao(ft.Icons.CHECK_CIRCLE, "Prontos", t["sucesso"]),
                coluna_prontos
            ])),
            ft.Container(col={"xs": 12, "md": 4}, content=ft.Column([
                cabecalho_secao(ft.Icons.ATTACH_MONEY, "Pagamento", t["erro"]),
                coluna_pagamento
            ]))
        ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START)

        page.views.append(
            ft.View(
                "/garcom",
                [cabecalho, ft.Container(height=15), area_colunas],
                scroll_to_top=True
            )
        )
        page.update()
        carregar_dados_salao()
        threading.Thread(target=loop_salao, daemon=True).start()

    # ==========================================================================
    # 3. APP COZINHA - ROTA: /cozinha
    # ==========================================================================
    def view_cozinha():
        global_state["loop_ativo"] = True
        global_state["sessao"] += 1
        minha_sessao = global_state["sessao"]

        t = get_current_theme_colors()
        global_state["recarregar"] = view_cozinha

        page.clean()
        page.bgcolor = t["fundo_principal"]
        page.vertical_alignment = ft.MainAxisAlignment.START
        page.horizontal_alignment = ft.CrossAxisAlignment.START

        dados_anteriores_cozinha = None

        def fazer_logout_cozinha(e):
            global_state["loop_ativo"] = False
            global_state["id_funcionario"] = 0
            global_state["nome_usuario"] = ""
            global_state["cargo"] = ""
            global_state["id_restaurante"] = 0
            page.go("/")

        def forcar_atualizacao(e):
            nonlocal dados_anteriores_cozinha
            dados_anteriores_cozinha = None
            carregar_dados_cozinha()

        # --- LÓGICA DO MODAL DE HISTÓRICO DA COZINHA ---
        lista_historico = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=10, height=400)

        def fechar_historico(e):
            dlg_historico.open = False
            page.update()

        dlg_historico = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.Icons.HISTORY, color=t["primaria"]),
                ft.Text("Histórico de Preparos", weight="bold", color=t["texto_principal"])
            ]),
            content=ft.Container(width=500, content=lista_historico),
            bgcolor=t["fundo_secundario"],
            actions=[ft.TextButton("Fechar", on_click=fechar_historico)],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dlg_historico)

        def abrir_historico(e):
            lista_historico.controls.clear()
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()

            cursor.execute('''
                SELECT pedidos.id, cardapio.nome, mesas.numero_mesa, pedidos.lote, comandas.nome_cliente, comandas.id
                FROM pedidos JOIN comandas ON pedidos.id_comanda = comandas.id
                JOIN mesas ON comandas.id_mesa = mesas.id JOIN cardapio ON pedidos.id_produto = cardapio.id
                WHERE comandas.id_restaurante = ? AND pedidos.status_pedido IN ('Pronto', 'Entregue')
                ORDER BY pedidos.id DESC LIMIT 50
            ''', (global_state["id_restaurante"],))

            finalizados = cursor.fetchall()
            conexao.close()

            if not finalizados:
                lista_historico.controls.append(ft.Text("Nenhum pedido finalizado recentemente.", color=t["texto_secundario"]))
            else:
                lotes_finalizados = {}
                for id_ped, nome_prod, num_mesa, lote, nome_cli, id_com in finalizados:
                    chave = (id_com, num_mesa, nome_cli, lote)
                    if chave not in lotes_finalizados:
                        lotes_finalizados[chave] = []
                    lotes_finalizados[chave].append(nome_prod)

                for chave, itens in lotes_finalizados.items():
                    id_com, num_mesa, nome_cli, lote = chave
                    coluna_itens = ft.Column(spacing=2)

                    for item in itens:
                        coluna_itens.controls.append(
                            ft.Text(f"• {item}", size=16, color=t["texto_secundario"], style=ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH))
                        )

                    card = ft.Container(
                        content=ft.Column([
                            ft.Text(f"Mesa {num_mesa} ({nome_cli}) - Lote {lote}", weight="bold", color=t["texto_principal"]),
                            ft.Divider(height=1, color=t["borda"]),
                            coluna_itens,
                            ft.Container(height=5),
                            ft.Row([ft.Text("✅ Finalizado", color=t["sucesso"], weight="bold")], alignment=ft.MainAxisAlignment.END)
                        ]),
                        bgcolor=t["cards"], padding=15, border_radius=10, border=criar_borda(t["borda"]),
                        margin=ft.Margin(left=0, top=0, right=0, bottom=10)
                    )
                    lista_historico.controls.append(card)

            dlg_historico.open = True
            page.update()

        # --- CABEÇALHO ---
        cabecalho = ft.Container(
            content=ft.ResponsiveRow([
                ft.Container(
                    col={"xs": 12, "sm": 6},
                    content=ft.Row([
                        ft.Icon(ft.Icons.SOUP_KITCHEN_OUTLINED, color=t["primaria"], size=28),
                        ft.Text(f"Cozinha - {global_state['nome_usuario']}", size=22, weight="bold", color=t["texto_principal"])
                    ])
                ),
                ft.Container(
                    col={"xs": 12, "sm": 6},
                    content=ft.Row([
                        ft.Button(
                            "Histórico", icon=ft.Icons.HISTORY, on_click=abrir_historico,
                            style=ft.ButtonStyle(bgcolor=t["secundaria"], color=t["texto_principal"], shape=ft.RoundedRectangleBorder(radius=10))
                        ),
                        ft.Button(
                            "Atualizar", icon=ft.Icons.REFRESH, on_click=forcar_atualizacao,
                            style=ft.ButtonStyle(bgcolor=t["primaria"], color="#FFFFFF", shape=ft.RoundedRectangleBorder(radius=10))
                        ),
                        ft.Button(
                            "Sair", icon=ft.Icons.LOGOUT, on_click=fazer_logout_cozinha,
                            style=ft.ButtonStyle(bgcolor=t["erro"], color=t["texto_principal"], shape=ft.RoundedRectangleBorder(radius=10))
                        ),
                    ], alignment=ft.MainAxisAlignment.END, wrap=True)
                ),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        )

        coluna_novos = ft.Column(spacing=10)
        coluna_preparo = ft.Column(spacing=10)

        def atualizar_status_lote(e, id_comanda, lote, status_atual, novo_status):
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()
            cursor.execute(
                "UPDATE pedidos SET status_pedido = ? WHERE id_comanda = ? AND lote = ? AND status_pedido = ?",
                (novo_status, id_comanda, lote, status_atual)
            )
            conexao.commit()
            conexao.close()
            carregar_dados_cozinha()

        def carregar_dados_cozinha():
            nonlocal dados_anteriores_cozinha
            if not global_state["loop_ativo"] or global_state["sessao"] != minha_sessao:
                return

            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()

            cursor.execute('''
                SELECT pedidos.id, cardapio.nome, mesas.numero_mesa, pedidos.status_pedido, pedidos.lote, pedidos.observacao, comandas.nome_cliente, comandas.id, cardapio.categoria
                FROM pedidos
                JOIN comandas ON pedidos.id_comanda = comandas.id
                JOIN mesas ON comandas.id_mesa = mesas.id
                JOIN cardapio ON pedidos.id_produto = cardapio.id
                WHERE comandas.id_restaurante = ? AND comandas.status != 'Fechada'
                ORDER BY comandas.id ASC, pedidos.lote ASC, pedidos.id ASC
            ''', (global_state["id_restaurante"],))

            pedidos = cursor.fetchall()
            conexao.close()

            if pedidos == dados_anteriores_cozinha:
                return
            dados_anteriores_cozinha = pedidos

            coluna_novos.controls.clear()
            coluna_preparo.controls.clear()

            if len(pedidos) == 0:
                coluna_novos.controls.append(ft.Text("Nenhum pedido novo.", color=t["texto_secundario"]))
                coluna_preparo.controls.append(ft.Text("Nenhum pedido em preparo.", color=t["texto_secundario"]))
                page.update()
                return

            lotes_dict = {}
            for id_ped, nome_prato, num_mesa, status, lote, obs, nome_cliente, id_comanda, categoria in pedidos:
                chave = (id_comanda, num_mesa, nome_cliente, lote)
                if chave not in lotes_dict:
                    lotes_dict[chave] = {'itens': [], 'status_geral': 'Pronto'}

                lotes_dict[chave]['itens'].append({'id': id_ped, 'nome': nome_prato, 'status': status, 'obs': obs, 'categoria': categoria})

                if status == 'Recebido':
                    lotes_dict[chave]['status_geral'] = 'Recebido'
                elif status == 'Preparando' and lotes_dict[chave]['status_geral'] != 'Recebido':
                    lotes_dict[chave]['status_geral'] = 'Preparando'

            for chave, dados in lotes_dict.items():
                id_comanda, num_mesa, nome_cliente, lote = chave
                status_geral = dados['status_geral']

                if status_geral not in ['Recebido', 'Preparando']:
                    continue

                coluna_itens = ft.Column(spacing=6)
                observacao_unica = None

                for item in dados['itens']:
                    obs = item['obs']
                    status_item = item['status']
                    categoria_item = item.get('categoria')

                    aviso_cozinha = ft.Container()

                    if categoria_item == 'Bebidas' and obs:
                        if 'agora' in obs.lower():
                            if status_item == 'Entregue':
                                aviso_cozinha = ft.Text("✅ Bebida já entregue pelo garçom", color=t["sucesso"], size=13, weight="bold")
                            else:
                                aviso_cozinha = ft.Text("🚨 Servir agora (Garçom notificado)", color=t["erro"], size=13, weight="bold")
                        elif obs.strip() != "":
                            aviso_cozinha = ft.Text(f"Obs: {obs}", color=t["primaria"], size=13, weight="bold")
                    else:
                        if obs and obs.strip() != "" and observacao_unica is None:
                            observacao_unica = obs

                    cor_texto = t["texto_secundario"] if status_item in ['Pronto', 'Entregue'] else t["texto_principal"]
                    estilo_texto = ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH) if status_item in ['Pronto', 'Entregue'] else None

                    texto_prato = ft.Text(f"• {item['nome']}", size=16, color=cor_texto, weight="bold", style=estilo_texto)
                    coluna_itens.controls.append(ft.Column([texto_prato, aviso_cozinha], spacing=0))

                if observacao_unica:
                    coluna_itens.controls.append(
                        ft.Container(
                            padding=ft.Padding(top=8, left=0, right=0, bottom=0),
                            content=ft.Row([
                                ft.Icon(ft.Icons.EDIT_NOTE_OUTLINED, size=18, color=t["texto_secundario"]),
                                ft.Text(f"Obs: {observacao_unica}", color=t["texto_principal"], size=14, weight="bold", italic=True, expand=True)
                            ])
                        )
                    )

                if status_geral == 'Recebido':
                    botao_acao = ft.Button(
                        "Preparar Tudo", icon=ft.Icons.LOCAL_FIRE_DEPARTMENT_OUTLINED,
                        on_click=lambda e, id_c=id_comanda, l=lote: atualizar_status_lote(e, id_c, l, 'Recebido', 'Preparando'),
                        style=ft.ButtonStyle(bgcolor=t["primaria"], color="#FFFFFF", shape=ft.RoundedRectangleBorder(radius=10))
                    )
                    coluna_destino = coluna_novos
                    cor_faixa = t["secundaria"]
                else:
                    botao_acao = ft.Button(
                        "Marcar Tudo Pronto", icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                        on_click=lambda e, id_c=id_comanda, l=lote: atualizar_status_lote(e, id_c, l, 'Preparando', 'Pronto'),
                        style=ft.ButtonStyle(bgcolor=t["sucesso"], color=t["texto_principal"], shape=ft.RoundedRectangleBorder(radius=10))
                    )
                    coluna_destino = coluna_preparo
                    cor_faixa = t["primaria"]

                card = ft.Card(
                    elevation=3,
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Container(width=6, height=22, bgcolor=cor_faixa, border_radius=3),
                                ft.Text(f"Mesa {num_mesa} ({nome_cliente}) - Lote {lote}", weight="bold", size=17, color=t["texto_principal"])
                            ], spacing=8),
                            ft.Divider(height=1, color=t["borda"]),
                            coluna_itens,
                            ft.Container(height=6),
                            ft.Row([botao_acao], alignment=ft.MainAxisAlignment.END)
                        ]),
                        bgcolor=t["fundo_secundario"], padding=16, border_radius=12, border=criar_borda(t["borda"]),
                        margin=ft.Margin(left=0, top=0, right=0, bottom=12)
                    )
                )

                coluna_destino.controls.append(card)

            if len(coluna_novos.controls) == 0:
                coluna_novos.controls.append(ft.Text("Nenhum pedido novo.", color=t["texto_secundario"]))
            if len(coluna_preparo.controls) == 0:
                coluna_preparo.controls.append(ft.Text("Nenhum pedido em preparo.", color=t["texto_secundario"]))

            page.update()

        def loop_atualizacao():
            while global_state["loop_ativo"] and global_state["sessao"] == minha_sessao:
                carregar_dados_cozinha()
                time.sleep(5)

        def criar_titulo_coluna(icone, texto, cor):
            return ft.Container(
                padding=ft.Padding(left=14, top=8, right=14, bottom=8), border_radius=20, bgcolor=cor,
                content=ft.Row([
                    ft.Icon(icone, color="#FFFFFF", size=18),
                    ft.Text(texto, size=15, weight="bold", color="#FFFFFF")
                ], spacing=6, tight=True),
            )

        area_colunas = ft.ResponsiveRow([
            ft.Container(col={"xs": 12, "md": 6}, padding=10, content=ft.Column([
                criar_titulo_coluna(ft.Icons.INBOX_OUTLINED, "Novos Pedidos", t["secundaria"]),
                ft.Container(height=10),
                coluna_novos
            ])),
            ft.Container(col={"xs": 12, "md": 6}, padding=10, content=ft.Column([
                criar_titulo_coluna(ft.Icons.SOUP_KITCHEN_OUTLINED, "Em Preparo", t["primaria"]),
                ft.Container(height=10),
                coluna_preparo
            ])),
        ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START)

        page.views.append(
            ft.View(
                "/cozinha",
                [cabecalho, ft.Divider(color=t["borda"]), area_colunas],
                scroll_to_top=True
            )
        )
        page.update()
        carregar_dados_cozinha()
        threading.Thread(target=loop_atualizacao, daemon=True).start()

    # ==========================================================================
    # 4. APP DONO - ROTA: /dono
    # ==========================================================================
    def view_dono():
        global_state["loop_ativo"] = True
        cores = get_current_theme_colors()
        global_state["recarregar"] = view_dono

        page.clean()
        page.scroll = ft.ScrollMode.AUTO
        page.bgcolor = cores["fundo_principal"]
        page.vertical_alignment = ft.MainAxisAlignment.START
        page.horizontal_alignment = ft.CrossAxisAlignment.START

        def fazer_logout_dono(e=None):
            global_state["loop_ativo"] = False
            global_state["id_restaurante"] = 0
            global_state["nome_usuario"] = ""
            global_state["email_restaurante"] = ""
            global_state["cargo"] = ""
            global_state["aba_atual"] = "visao_geral"
            page.go("/")

        cabecalho = ft.Row([
            ft.Text(f"Olá, {global_state['nome_usuario']} (Painel do Dono)", size=24, weight="bold", color=cores["texto_principal"], expand=True),
            ft.Button("Atualizar", on_click=lambda e: atualizar_dashboard(), icon="refresh", icon_color=cores["primaria"]),
            ft.Button("Sair", on_click=fazer_logout_dono, icon="logout", icon_color=cores["erro"])
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        # --- ABA 1: VISÃO GERAL ---
        secao_alertas = ft.Column()
        secao_resumo = ft.ResponsiveRow()
        secao_top5 = ft.Column()

        conteudo_visao_geral = ft.Column([
            ft.Container(
                content=ft.Column([
                    ft.Text("Alertas em tempo real", size=20, weight="bold", color=cores["texto_principal"]),
                    secao_alertas
                ]),
                bgcolor=cores["cards"], padding=15, border_radius=8, border=criar_borda(cores["borda"])
            ),
            ft.Divider(),
            ft.Text("Resumo de Hoje", size=20, weight="bold", color=cores["texto_principal"]),
            secao_resumo,
            ft.Divider(),
            ft.Text("Top 5 Mais Vendidos", size=20, weight="bold", color=cores["texto_principal"]),
            secao_top5
        ], scroll=ft.ScrollMode.AUTO, expand=True)

        def criar_card_resumo(titulo, valor, icone):
            return ft.Container(
                col={"xs": 12, "sm": 6, "md": 3},
                content=ft.Card(
                    elevation=2,
                    content=ft.Container(
                        padding=20,
                        bgcolor=cores["fundo_secundario"],
                        border_radius=8,
                        content=ft.Column([
                            ft.Text(icone, size=30),
                            ft.Text(titulo, size=16, color=cores["texto_secundario"]),
                            ft.Text(valor, size=24, weight="bold", color=cores["texto_principal"])
                        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                    )
                )
            )

        def atualizar_dashboard():
            if not global_state["loop_ativo"] or global_state["cargo"] != "Dono":
                return

            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()

            # Alertas em tempo real
            cursor.execute('''
                SELECT c.id_mesa, c.hora_abertura, c.status, c.hora_pedido_conta,
                       (SELECT COUNT(*) FROM pedidos p WHERE p.id_comanda = c.id) as qtd_pedidos
                FROM comandas c
                WHERE c.id_restaurante = ? AND c.status != 'Fechada'
            ''', (global_state["id_restaurante"],))
            comandas_ativas = cursor.fetchall()

            secao_alertas.controls.clear()
            novos_alertas = []
            agora = datetime.now()

            for id_mesa, hora_abertura, status, hora_pedido_conta, qtd_pedidos in comandas_ativas:
                try:
                    hora_ab = datetime.strptime(hora_abertura, '%Y-%m-%d %H:%M:%S')
                    minutos_aberta = (agora - hora_ab).total_seconds() / 60
                    if qtd_pedidos == 0 and minutos_aberta > 15:
                        novos_alertas.append((f"Mesa {id_mesa} está aberta há {int(minutos_aberta)} min sem nenhum pedido.", "aviso"))
                except (ValueError, TypeError):
                    pass

                if status == "Aguardando Pagamento" and hora_pedido_conta:
                    try:
                        hora_pedido = datetime.strptime(hora_pedido_conta, '%Y-%m-%d %H:%M:%S')
                        minutos_esperando = (agora - hora_pedido).total_seconds() / 60
                        if minutos_esperando > 10:
                            novos_alertas.append((f"Mesa {id_mesa} aguarda pagamento há {int(minutos_esperando)} min.", "erro"))
                    except (ValueError, TypeError):
                        pass

            if not novos_alertas:
                secao_alertas.controls.append(ft.Text("Nenhum alerta no momento. Tudo tranquilo! ✅", color=cores["sucesso"]))
            else:
                for texto_alerta, tipo in novos_alertas:
                    cor_alerta = cores["erro"] if tipo == "erro" else cores["aviso"]
                    secao_alertas.controls.append(
                        ft.Container(
                            content=ft.Text(f"⚠️ {texto_alerta}", color=cores["texto_principal"]),
                            bgcolor=cor_alerta, padding=10, border_radius=6
                        )
                    )

            # Resumo de hoje
            hoje = datetime.now().strftime('%Y-%m-%d')

            cursor.execute('''
                SELECT COALESCE(SUM(ca.preco), 0)
                FROM pedidos p
                JOIN cardapio ca ON p.id_produto = ca.id
                JOIN comandas co ON p.id_comanda = co.id
                WHERE co.id_restaurante = ? AND co.status = 'Fechada' AND co.hora_abertura LIKE ?
            ''', (global_state["id_restaurante"], f"{hoje}%"))
            faturamento = cursor.fetchone()[0]

            cursor.execute('''
                SELECT COALESCE(SUM(ca.preco), 0)
                FROM pedidos p
                JOIN cardapio ca ON p.id_produto = ca.id
                JOIN comandas co ON p.id_comanda = co.id
                WHERE co.id_restaurante = ? AND co.status != 'Fechada'
            ''', (global_state["id_restaurante"],))
            valor_em_aberto = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM comandas WHERE id_restaurante = ? AND status != 'Fechada'", (global_state["id_restaurante"],))
            comandas_abertas = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM comandas WHERE id_restaurante = ? AND status = 'Fechada' AND hora_abertura LIKE ?", (global_state["id_restaurante"], f"{hoje}%"))
            comandas_fechadas_hoje = cursor.fetchone()[0]

            secao_resumo.controls.clear()
            secao_resumo.controls.append(criar_card_resumo("Faturamento (Hoje)", f"R$ {faturamento:.2f}", "💰"))
            secao_resumo.controls.append(criar_card_resumo("Em Aberto", f"R$ {valor_em_aberto:.2f}", "⏳"))
            secao_resumo.controls.append(criar_card_resumo("Comandas Abertas", str(comandas_abertas), "📖"))
            secao_resumo.controls.append(criar_card_resumo("Comandas Fechadas (Hoje)", str(comandas_fechadas_hoje), "✅"))

            cursor.execute('''
                SELECT ca.nome, COUNT(p.id) as qtd
                FROM pedidos p
                JOIN cardapio ca ON p.id_produto = ca.id
                JOIN comandas co ON p.id_comanda = co.id
                WHERE co.id_restaurante = ?
                GROUP BY ca.nome
                ORDER BY qtd DESC
                LIMIT 5
            ''', (global_state["id_restaurante"],))
            top5 = cursor.fetchall()
            conexao.close()

            secao_top5.controls.clear()
            if not top5:
                secao_top5.controls.append(ft.Text("Ainda não há pedidos registrados.", color=cores["texto_secundario"]))
            else:
                for posicao, (nome_prod, qtd) in enumerate(top5, start=1):
                    secao_top5.controls.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Text(f"#{posicao}", weight="bold", color=cores["primaria"]),
                                ft.Text(nome_prod, color=cores["texto_principal"], expand=True),
                                ft.Text(f"{qtd} vendidos", color=cores["texto_secundario"])
                            ]),
                            bgcolor=cores["cards"], padding=10, border_radius=6, border=criar_borda(cores["borda"])
                        )
                    )
            page.update()

        # --- ABA 2: COMANDAS ATIVAS ---
        grade_mesas = ft.ResponsiveRow()
        conteudo_comandas = ft.Column([
            ft.Text("Selecione uma mesa para ver detalhes", size=20, weight="bold", color=cores["texto_principal"]),
            grade_mesas
        ], scroll=ft.ScrollMode.AUTO, expand=True)

        def abrir_dialogo_detalhes_comanda(e):
            id_comanda = e.control.data
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()

            cursor.execute('''
                SELECT c.nome_cliente, m.numero_mesa, c.hora_abertura, c.status
                FROM comandas c
                JOIN mesas m ON c.id_mesa = m.id
                WHERE c.id = ?
            ''', (id_comanda,))
            dados_comanda = cursor.fetchone()
            if not dados_comanda:
                conexao.close()
                return
            nome_cliente, numero_mesa, hora_abertura, status_comanda = dados_comanda

            cursor.execute('''
                SELECT COALESCE(SUM(ca.preco), 0)
                FROM pedidos p
                JOIN cardapio ca ON p.id_produto = ca.id
                WHERE p.id_comanda = ?
            ''', (id_comanda,))
            valor_em_aberto = cursor.fetchone()[0]

            cursor.execute('''
                SELECT status_pedido, hora_pedido
                FROM pedidos WHERE id_comanda = ?
                ORDER BY id DESC LIMIT 1
            ''', (id_comanda,))
            ultimo_pedido = cursor.fetchone()
            conexao.close()

            if ultimo_pedido:
                status_pedido, hora_pedido = ultimo_pedido
                referencia = hora_pedido if hora_pedido else hora_abertura
                try:
                    hora_ref = datetime.strptime(referencia, '%Y-%m-%d %H:%M:%S')
                    minutos_desde = int((datetime.now() - hora_ref).total_seconds() / 60)
                    texto_tempo = f"há {minutos_desde} minutos"
                except (ValueError, TypeError):
                    texto_tempo = "não disponível"
            else:
                status_pedido = "Nenhum pedido registrado"
                texto_tempo = "não disponível"

            def confirmar_fechar_comanda(e_fechar):
                conexao2 = sqlite3.connect('rachaki.db')
                cursor2 = conexao2.cursor()
                cursor2.execute("UPDATE comandas SET status = 'Fechada' WHERE id = ?", (id_comanda,))
                conexao2.commit()
                conexao2.close()
                fechar_dialogo(dialogo_detalhes)
                carregar_mesas_ativas()
                atualizar_dashboard()

            def apenas_fechar_dialogo(e_cancelar):
                fechar_dialogo(dialogo_detalhes)

            dialogo_detalhes = ft.AlertDialog(
                title=ft.Text(f"Mesa {numero_mesa}"),
                content=ft.Column([
                    ft.Text(f"Nome na comanda: {nome_cliente or 'Não informado'}"),
                    ft.Text(f"Hora de abertura: {hora_abertura}"),
                    ft.Text(f"Valor em aberto: R$ {valor_em_aberto:.2f}"),
                    ft.Text(f"Último pedido: {texto_tempo}"),
                    ft.Text(f"Status do pedido: {status_pedido}"),
                ], tight=True, spacing=10),
                actions=[
                    ft.TextButton("Cancelar", on_click=apenas_fechar_dialogo),
                    ft.TextButton("Fechar Comanda", on_click=confirmar_fechar_comanda),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.overlay.append(dialogo_detalhes)
            dialogo_detalhes.open = True
            page.update()

        def carregar_mesas_ativas():
            grade_mesas.controls.clear()
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()
            cursor.execute('''
                SELECT c.id, m.numero_mesa, c.nome_cliente, c.status
                FROM comandas c
                JOIN mesas m ON c.id_mesa = m.id
                WHERE c.id_restaurante = ? AND c.status != 'Fechada'
                ORDER BY CAST(m.numero_mesa AS INTEGER)
            ''', (global_state["id_restaurante"],))
            comandas_abertas = cursor.fetchall()
            conexao.close()

            if not comandas_abertas:
                grade_mesas.controls.append(ft.Text("Nenhuma comanda aberta no momento.", color=cores["texto_secundario"]))
            else:
                for id_comanda, numero_mesa, nome_cliente, status in comandas_abertas:
                    cor_mesa = cores["erro"] if status == "Aguardando Pagamento" else cores["aviso"]

                    grade_mesas.controls.append(
                        ft.Container(
                            col={"xs": 6, "sm": 4, "md": 3, "lg": 2},
                            content=ft.Container(
                                content=ft.Column([
                                    ft.Text(f"Mesa {numero_mesa}", size=18, weight="bold", color=cores["texto_principal"]),
                                    ft.Text(status, size=14, color=cores["texto_secundario"])
                                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                                bgcolor=cor_mesa, padding=20, border_radius=8, alignment=alinhamento_centro(),
                                ink=True,
                                on_click=abrir_dialogo_detalhes_comanda,
                                data=id_comanda
                            )
                        )
                    )
            page.update()

        # --- ABA 3: CARDÁPIO ---
        campo_nome_prod = ft.TextField(label="Nome do Produto")
        campo_preco_prod = ft.TextField(label="Preço (R$)", prefix_icon="R$ ")
        campo_desc_prod = ft.TextField(label="Descrição (Opcional)")
        dropdown_cat_prod = ft.Dropdown(
            label="Categoria",
            options=[
                ft.dropdown.Option("Bebidas"), ft.dropdown.Option("Pratos Principais"),
                ft.dropdown.Option("Porções"), ft.dropdown.Option("Sobremesas"), ft.dropdown.Option("Outros")
            ],
            value="Outros"
        )
        msg_cardapio = ft.Text(value="", color=cores["sucesso"])
        lista_cardapio = ft.Column()

        def adicionar_produto(e):
            nome = campo_nome_prod.value
            preco = campo_preco_prod.value
            desc = campo_desc_prod.value
            cat = dropdown_cat_prod.value

            if nome and preco:
                try:
                    preco_float = float(preco.replace(',', '.'))
                    conexao = sqlite3.connect('rachaki.db')
                    cursor = conexao.cursor()
                    cursor.execute('INSERT INTO cardapio (nome, preco, descricao, disponivel, id_restaurante, categoria) VALUES (?, ?, ?, 1, ?, ?)',
                                   (nome, preco_float, desc, global_state["id_restaurante"], cat))
                    conexao.commit()
                    conexao.close()
                    campo_nome_prod.value = ""
                    campo_preco_prod.value = ""
                    campo_desc_prod.value = ""
                    msg_cardapio.value, msg_cardapio.color = "Produto adicionado com sucesso!", cores["sucesso"]
                    carregar_cardapio()
                except ValueError:
                    msg_cardapio.value, msg_cardapio.color = "Preço inválido. Use números.", cores["erro"]
            else:
                msg_cardapio.value, msg_cardapio.color = "Preencha nome e preço.", cores["erro"]
            page.update()

        def alternar_disponibilidade(e):
            id_prod = e.control.data
            novo_status = 1 if e.control.value else 0
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()
            cursor.execute('UPDATE cardapio SET disponivel = ? WHERE id = ?', (novo_status, id_prod))
            conexao.commit()
            conexao.close()

        def abrir_dialogo_editar_produto(e):
            dados = e.control.data
            id_prod = dados['id']

            campo_edit_nome = ft.TextField(label="Nome do Produto", value=dados['nome'])
            campo_edit_preco = ft.TextField(label="Preço (R$)", value=str(dados['preco']), prefix_icon="R$ ")
            campo_edit_desc = ft.TextField(label="Descrição (Opcional)", value=dados['descricao'])
            dropdown_edit_cat = ft.Dropdown(
                label="Categoria",
                options=[
                    ft.dropdown.Option("Bebidas"), ft.dropdown.Option("Pratos Principais"),
                    ft.dropdown.Option("Porções"), ft.dropdown.Option("Sobremesas"), ft.dropdown.Option("Outros")
                ],
                value=dados['categoria']
            )
            msg_edicao = ft.Text(value="", color=cores["erro"])

            def salvar_edicao(e_salvar):
                nome = campo_edit_nome.value
                preco = campo_edit_preco.value
                desc = campo_edit_desc.value
                cat = dropdown_edit_cat.value

                if nome and preco:
                    try:
                        preco_float = float(preco.replace(',', '.'))
                        conexao = sqlite3.connect('rachaki.db')
                        cursor = conexao.cursor()
                        cursor.execute('UPDATE cardapio SET nome = ?, preco = ?, descricao = ?, categoria = ? WHERE id = ?',
                                       (nome, preco_float, desc, cat, id_prod))
                        conexao.commit()
                        conexao.close()
                        fechar_dialogo(dialogo_edicao_produto)
                        msg_cardapio.value, msg_cardapio.color = "Produto atualizado com sucesso!", cores["sucesso"]
                        carregar_cardapio()
                    except ValueError:
                        msg_edicao.value = "Preço inválido. Use números."
                        page.update()
                else:
                    msg_edicao.value = "Preencha nome e preço."
                    page.update()

            def fechar_dialogo(dialogo):
                dialogo.open = False
                page.update()

            dialogo_edicao_produto = ft.AlertDialog(
                title=ft.Text("Editar Produto"),
                content=ft.Column([
                    campo_edit_nome, campo_edit_preco, dropdown_edit_cat, campo_edit_desc, msg_edicao
                ], tight=True, spacing=10),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda e: fechar_dialogo(dialogo_edicao_produto)),
                    ft.TextButton("Salvar Alterações", on_click=salvar_edicao)
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.overlay.append(dialogo_edicao_produto)
            dialogo_edicao_produto.open = True
            page.update()

        def deletar_produto(e):
            id_prod = e.control.data
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()
            cursor.execute('DELETE FROM cardapio WHERE id = ?', (id_prod,))
            conexao.commit()
            conexao.close()
            carregar_cardapio()

        def carregar_cardapio():
            lista_cardapio.controls.clear()
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()
            cursor.execute('SELECT id, nome, preco, descricao, disponivel, categoria FROM cardapio WHERE id_restaurante = ? ORDER BY categoria, nome', (global_state["id_restaurante"],))
            produtos = cursor.fetchall()
            conexao.close()

            if not produtos:
                lista_cardapio.controls.append(ft.Text("Cardápio vazio.", color=cores["texto_secundario"]))
            else:
                categoria_atual = ""
                for id_prod, nome, preco, desc, disp, cat in produtos:
                    if cat != categoria_atual:
                        lista_cardapio.controls.append(ft.Text(cat, size=18, weight="bold", color=cores["primaria"]))
                        categoria_atual = cat

                    info_prod = ft.Column([
                        ft.Text(f"{nome} - R$ {preco:.2f}", size=16, weight="bold", color=cores["texto_principal"]),
                        ft.Text(desc, size=14, color=cores["texto_secundario"])
                    ], expand=True)

                    botoes_acao = ft.Row([
                        ft.Switch(label="Disponível", value=bool(disp), on_change=alternar_disponibilidade, data=id_prod),
                        ft.Button(
                            "Editar", on_click=abrir_dialogo_editar_produto,
                            data={'id': id_prod, 'nome': nome, 'preco': preco, 'descricao': desc, 'categoria': cat},
                            icon="edit", icon_color=cores["primaria"]
                        ),
                        ft.Button("Excluir", on_click=deletar_produto, data=id_prod, icon="delete", icon_color=cores["erro"])
                    ], wrap=True)

                    lista_cardapio.controls.append(
                        ft.Container(
                            content=ft.Row([info_prod, botoes_acao], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            bgcolor=cores["fundo_secundario"], padding=10, border_radius=8, border=criar_borda(cores["borda"])
                        )
                    )
            page.update()

        conteudo_cardapio = ft.Column([
            ft.Text("Adicionar Produto", size=20, weight="bold", color=cores["texto_principal"]),
            ft.ResponsiveRow([
                ft.Container(col={"xs": 12, "md": 4}, content=campo_nome_prod),
                ft.Container(col={"xs": 12, "md": 2}, content=campo_preco_prod),
                ft.Container(col={"xs": 12, "md": 2}, content=dropdown_cat_prod),
                ft.Container(col={"xs": 12, "md": 4}, content=campo_desc_prod),
                ft.Container(col={"xs": 12}, content=ft.Button("Salvar Produto", on_click=adicionar_produto, height=50))
            ]),
            msg_cardapio,
            ft.Divider(),
            ft.Text("Itens do Cardápio", size=20, weight="bold", color=cores["texto_principal"]),
            lista_cardapio
        ], scroll=ft.ScrollMode.AUTO, expand=True)

        # --- ABA 4: EQUIPE ---
        campo_func_nome = ft.TextField(label="Nome do Funcionário", expand=True)
        campo_func_senha = ft.TextField(label="Senha de Acesso", password=True, can_reveal_password=True)
        dropdown_cargo = ft.Dropdown(
            label="Cargo",
            options=[ft.dropdown.Option("Garçom"), ft.dropdown.Option("Cozinha")], # Alterado de Atendente para Garçom
            value="Garçom"
        )
        msg_equipe = ft.Text(value="", color=cores["sucesso"])
        lista_equipe = ft.Column()

        def adicionar_funcionario(e):
            nome = campo_func_nome.value
            senha = campo_func_senha.value
            cargo = dropdown_cargo.value
            login = f"{nome.split()[0].lower()}{global_state['id_restaurante']}"

            if nome and senha:
                conexao = sqlite3.connect('rachaki.db')
                cursor = conexao.cursor()
                cursor.execute('INSERT INTO funcionarios (nome, senha, cargo, id_restaurante, login) VALUES (?, ?, ?, ?, ?)',
                               (nome, senha, cargo, global_state["id_restaurante"], login))
                conexao.commit()
                conexao.close()
                campo_func_nome.value = ""
                campo_func_senha.value = ""
                msg_equipe.value, msg_equipe.color = f"Cadastrado! Login: {login}", cores["sucesso"]
                carregar_equipe()
            else:
                msg_equipe.value, msg_equipe.color = "Preencha nome e senha.", cores["erro"]
            page.update()

        def deletar_funcionario(e):
            id_func = e.control.data
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()
            cursor.execute('DELETE FROM funcionarios WHERE id = ?', (id_func,))
            conexao.commit()
            conexao.close()
            carregar_equipe()

        def abrir_dialogo_senha(e):
            id_func = e.control.data['id']
            nome_func = e.control.data['nome']
            campo_nova_senha = ft.TextField(label="Nova Senha", password=True, can_reveal_password=True)

            def salvar_senha(e_salvar):
                nova_senha = campo_nova_senha.value
                if nova_senha:
                    conexao = sqlite3.connect('rachaki.db')
                    cursor = conexao.cursor()
                    cursor.execute('UPDATE funcionarios SET senha = ? WHERE id = ?', (nova_senha, id_func))
                    conexao.commit()
                    conexao.close()
                    fechar_dialogo(dialogo_edicao)
                    msg_equipe.value, msg_equipe.color = f"Senha de {nome_func} atualizada com sucesso!", cores["sucesso"]
                    page.update()
                else:
                    campo_nova_senha.error_text = "A senha não pode ser vazia"
                    page.update()

            def fechar_dialogo(dialogo):
                dialogo.open = False
                page.update()

            dialogo_edicao = ft.AlertDialog(
                title=ft.Text(f"Editar senha de {nome_func}"),
                content=campo_nova_senha,
                actions=[ft.TextButton("Cancelar", on_click=lambda e: fechar_dialogo(dialogo_edicao)), ft.TextButton("Salvar Nova Senha", on_click=salvar_senha)],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.overlay.append(dialogo_edicao)
            dialogo_edicao.open = True
            page.update()

        def carregar_equipe():
            lista_equipe.controls.clear()
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()
            cursor.execute('SELECT id, nome, cargo, login FROM funcionarios WHERE id_restaurante = ?', (global_state["id_restaurante"],))
            funcionarios = cursor.fetchall()
            conexao.close()
            if len(funcionarios) == 0:
                lista_equipe.controls.append(ft.Text("Nenhum funcionário cadastrado.", color=cores["texto_secundario"]))
            else:
                for id_func, nome_func, cargo_func, login_func in funcionarios:
                    info_func = ft.Column([
                        ft.Text(f"{nome_func} ({cargo_func})", size=16, weight="bold", color=cores["texto_principal"]),
                        ft.Text(f"Login: {login_func}", size=14, color=cores["primaria"])
                    ], spacing=2)

                    botoes_acao = ft.Row([
                        ft.Button("Editar Senha", on_click=abrir_dialogo_senha, data={'id': id_func, 'nome': nome_func}, icon="edit", icon_color=cores["primaria"]),
                        ft.Button("Remover", on_click=deletar_funcionario, data=id_func, icon="delete", icon_color=cores["erro"])
                    ], wrap=True)

                    lista_equipe.controls.append(ft.Row([info_func, botoes_acao], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
                    lista_equipe.controls.append(ft.Divider())
            page.update()

        formulario_equipe = ft.ResponsiveRow([
            ft.Container(
                col={"xs": 12, "md": 10, "lg": 8},
                content=ft.Column([
                    ft.Text("Cadastrar Funcionário", size=20, weight="bold", color=cores["texto_principal"]),
                    ft.ResponsiveRow([
                        ft.Container(col={"xs": 12, "md": 5}, content=campo_func_nome),
                        ft.Container(col={"xs": 12, "md": 3}, content=campo_func_senha),
                        ft.Container(col={"xs": 12, "md": 2}, content=dropdown_cargo),
                        ft.Container(col={"xs": 12, "md": 2}, content=ft.Button("Cadastrar", on_click=adicionar_funcionario, height=50))
                    ]),
                    msg_equipe
                ])
            )
        ])

        conteudo_equipe = ft.Column([formulario_equipe, ft.Divider(), lista_equipe], scroll=ft.ScrollMode.AUTO, expand=True)

        # --- ABA 5: CONFIGURAÇÕES ---
        campo_mesas = ft.TextField(label="Quantas mesas o restaurante possui atualmente?")
        msg_mesas = ft.Text(value="", color=cores["sucesso"])

        def configurar_mesas(e):
            try:
                qtd = int(campo_mesas.value)
                if qtd > 0:
                    conexao = sqlite3.connect('rachaki.db')
                    cursor = conexao.cursor()
                    cursor.execute("SELECT COUNT(*) FROM comandas WHERE id_restaurante = ? AND status != 'Fechada'", (global_state["id_restaurante"],))
                    if cursor.fetchone()[0] > 0:
                        msg_mesas.value, msg_mesas.color = "⚠️ Erro: Feche todas as comandas abertas antes de alterar as mesas.", cores["erro"]
                    else:
                        cursor.execute('DELETE FROM mesas WHERE id_restaurante = ?', (global_state["id_restaurante"],))
                        for i in range(1, qtd + 1):
                            cursor.execute('INSERT INTO mesas (numero_mesa, id_restaurante) VALUES (?, ?)', (i, global_state["id_restaurante"]))
                        conexao.commit()
                        msg_mesas.value, msg_mesas.color = f"✅ {qtd} mesas configuradas com sucesso!", cores["sucesso"]
                        atualizar_dashboard()
                    conexao.close()
                else:
                    msg_mesas.value, msg_mesas.color = "Digite um número maior que zero.", cores["erro"]
            except ValueError:
                msg_mesas.value, msg_mesas.color = "Digite apenas números inteiros.", cores["erro"]
            page.update()

        seletor_tema = ft.Row([
            ft.Button("Claro", icon="light_mode", icon_color=cores["primaria"], on_click=mudar_tema_global, data="Claro"),
            ft.Button("Escuro", icon="dark_mode", icon_color=cores["primaria"], on_click=mudar_tema_global, data="Escuro"),
            ft.Button("Sistema", icon="brightness_auto", icon_color=cores["primaria"], on_click=mudar_tema_global, data="Sistema"),
        ], wrap=True)

        conteudo_config = ft.Column([
            ft.Text("Atenção: Gerar novas mesas apagará a numeração atual.", color=cores["texto_secundario"]),
            ft.ResponsiveRow([
                ft.Container(col={"xs": 12, "sm": 8, "md": 4}, content=campo_mesas),
                ft.Container(col={"xs": 12, "sm": 4, "md": 3}, content=ft.Button("Gerar Mesas", on_click=configurar_mesas, height=50))
            ]),
            msg_mesas,
            ft.Divider(),
            ft.Text("Aparência", size=18, weight="bold", color=cores["texto_principal"]),
            seletor_tema
        ], scroll=ft.ScrollMode.AUTO, expand=True)

        # --- MONTANDO AS ABAS COM ATUALIZAÇÃO AUTOMÁTICA ---
        mapa_abas = {
            "visao_geral": conteudo_visao_geral,
            "comandas": conteudo_comandas,
            "cardapio": conteudo_cardapio,
            "equipe": conteudo_equipe,
            "config": conteudo_config,
        }
        area_conteudo = ft.Container(content=mapa_abas.get(global_state["aba_atual"], conteudo_visao_geral), padding=20, expand=True)

        def mudar_aba(conteudo):
            area_conteudo.content = conteudo
            page.update()

        def nav_visao_geral(e):
            global_state["aba_atual"] = "visao_geral"
            atualizar_dashboard()
            mudar_aba(conteudo_visao_geral)

        def nav_comandas(e):
            global_state["aba_atual"] = "comandas"
            carregar_mesas_ativas()
            mudar_aba(conteudo_comandas)

        def nav_cardapio(e):
            global_state["aba_atual"] = "cardapio"
            carregar_cardapio()
            mudar_aba(conteudo_cardapio)

        def nav_equipe(e):
            global_state["aba_atual"] = "equipe"
            carregar_equipe()
            mudar_aba(conteudo_equipe)

        def nav_config(e):
            global_state["aba_atual"] = "config"
            mudar_aba(conteudo_config)

        page.views.append(
            ft.View(
                "/dono",
                [
                    cabecalho,
                    ft.Divider(),
                    ft.Row([
                        ft.Button("Visão Geral", on_click=nav_visao_geral),
                        ft.Button("Comandas Ativas", on_click=nav_comandas),
                        ft.Button("Cardápio", on_click=nav_cardapio),
                        ft.Button("Equipe", on_click=nav_equipe),
                        ft.Button("Configurações", on_click=nav_config),
                    ], wrap=True),
                    ft.Divider(),
                    area_conteudo
                ],
                scroll_to_top=True
            )
        )
        page.update()

        # Carrega os dados iniciais da aba padrão
        if global_state["aba_atual"] == "visao_geral":
            atualizar_dashboard()
        elif global_state["aba_atual"] == "comandas":
            carregar_mesas_ativas()
        elif global_state["aba_atual"] == "cardapio":
            carregar_cardapio()
        elif global_state["aba_atual"] == "equipe":
            carregar_equipe()


    # ==========================================================================
    # GERENCIAMENTO DE ROTAS
    # ==========================================================================
    def route_change(route):
        page.views.clear()
        if page.route == "/":
            view_root()
        elif page.route == "/visual":
            view_visual()
        elif page.route == "/visual/boasvindas":
            view_visual_boasvindas()
        elif page.route == "/visual/cardapio":
            view_visual_cardapio()
        elif page.route == "/visual/conta":
            view_visual_conta()
        elif page.route == "/dono":
            if global_state["cargo"] == "Dono":
                view_dono()
            else:
                page.go("/") # Redireciona se não for o dono
        elif page.route == "/garcom":
            if global_state["cargo"] == "Garçom":
                view_garcom()
            else:
                page.go("/") # Redireciona se não for garçom
        elif page.route == "/cozinha":
            if global_state["cargo"] == "Cozinha":
                view_cozinha()
            else:
                page.go("/") # Redireciona se não for cozinha
        else:
            page.views.append(
                ft.View(
                    "/404",
                    [
                        ft.AppBar(title=ft.Text("404 - Página não encontrada")),
                        ft.Text("Ops! A página que você procura não existe.", size=24),
                        ft.ElevatedButton("Voltar para o Início", on_click=lambda e: page.go("/")),
                    ],
                    vertical_alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER
                )
            )
        page.update()

    def view_pop(view):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go(page.route) # Inicia o roteamento

# Configuração para deploy web (Render)
if __name__ == "__main__":
    # Obtém a porta do ambiente, se disponível (para Render)
    port = int(os.environ.get("PORT", 8000))
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=port)