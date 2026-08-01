import flet as ft
import sqlite3
from datetime import datetime

# ---------------------------------------------------------------------------
# Paleta de cores - baseada no documento "Paleta de Cores - Rachaki"
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
}


def criar_borda(cor, largura=1):
    """
    Cria uma borda compatível com diferentes versões do Flet.
    Algumas versões não possuem mais o atalho ft.border.all(),
    então aqui montamos a borda manualmente como fallback seguro.
    """
    try:
        return ft.border.all(largura, cor)
    except AttributeError:
        lado = ft.BorderSide(largura, cor)
        return ft.Border(top=lado, right=lado, bottom=lado, left=lado)
    
def alinhamento_centro():
    """
    Retorna o alinhamento central compatível com diferentes versões do Flet.
    """
    try:
        return ft.alignment.center
    except AttributeError:
        return ft.Alignment(0, 0)

# Inicializa o banco de dados e garante as colunas novas
def inicializar_banco():
    conexao = sqlite3.connect('rachaki.db')
    cursor = conexao.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS restaurantes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, email TEXT, senha TEXT, status_plano TEXT, data_cadastro TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS funcionarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, senha TEXT, cargo TEXT, id_restaurante INTEGER)''')

    try:
        cursor.execute("ALTER TABLE funcionarios ADD COLUMN login TEXT")
    except sqlite3.OperationalError:
        pass

    cursor.execute('''CREATE TABLE IF NOT EXISTS mesas (id INTEGER PRIMARY KEY AUTOINCREMENT, numero_mesa INTEGER, id_restaurante INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS comandas (id INTEGER PRIMARY KEY AUTOINCREMENT, nome_cliente TEXT, id_mesa INTEGER, status TEXT, id_restaurante INTEGER, hora_abertura TEXT)''')

    # Nova coluna para o alerta de tempo de pagamento
    try:
        cursor.execute("ALTER TABLE comandas ADD COLUMN hora_pedido_conta TEXT")
    except sqlite3.OperationalError:
        pass

    cursor.execute('''CREATE TABLE IF NOT EXISTS cardapio (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, preco REAL, descricao TEXT, disponivel INTEGER, id_restaurante INTEGER, categoria TEXT DEFAULT 'Outros')''')

    try:
        cursor.execute("ALTER TABLE cardapio ADD COLUMN categoria TEXT DEFAULT 'Outros'")
    except sqlite3.OperationalError:
        pass

    cursor.execute('''CREATE TABLE IF NOT EXISTS pedidos (id INTEGER PRIMARY KEY AUTOINCREMENT, id_comanda INTEGER, id_produto INTEGER, status_pedido TEXT, lote INTEGER DEFAULT 1)''')

    try:
        cursor.execute("ALTER TABLE pedidos ADD COLUMN lote INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("ALTER TABLE pedidos ADD COLUMN hora_pedido TEXT")
    except sqlite3.OperationalError:
        pass

    cursor.execute("SELECT COUNT(*) FROM restaurantes")
    if cursor.fetchone()[0] == 0:
        hoje = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("INSERT INTO restaurantes (nome, email, senha, status_plano, data_cadastro) VALUES ('Mario Pizza', 'mario@pizza.com', 'admin', 'ativo', ?)", (hoje,))

    conexao.commit()
    conexao.close()

inicializar_banco()

def main(page: ft.Page):
    page.title = "Rachaki - Painel do Dono"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.padding = 20
    page.theme = ft.Theme(color_scheme_seed=CORES_CLARO["primaria"])
    page.dark_theme = ft.Theme(color_scheme_seed=CORES_ESCURO["primaria"])

    estado = {
        "id_restaurante": 0, "nome_usuario": "", "email_restaurante": "", "cargo": "", "loop_ativo": False,
        "aba_atual": "visao_geral"
    }

    def obter_cores():
        if page.theme_mode == ft.ThemeMode.DARK:
            return CORES_ESCURO
        elif page.theme_mode == ft.ThemeMode.LIGHT:
            return CORES_CLARO
        brilho = getattr(page, "platform_brightness", None)
        return CORES_ESCURO if brilho == ft.Brightness.DARK else CORES_CLARO

    def abrir_dialogo(dialogo):
        """
        Registra o diálogo em page.overlay e o abre.
        """
        if dialogo not in page.overlay:
            page.overlay.append(dialogo)
        dialogo.open = True
        page.update()

    def fechar_dialogo(dialogo):
        """
        Apenas marca o diálogo como fechado e atualiza a página.
        NÃO remove o controle de page.overlay aqui: removê-lo
        imediatamente após fechar causa conflito com a animação
        de fechamento do AlertDialog nesta versão do Flet, fazendo
        o diálogo "travar" visualmente na tela.
        """
        dialogo.open = False
        page.update()

    def fazer_logout(e=None):
        estado["loop_ativo"] = False
        estado["id_restaurante"] = 0
        estado["nome_usuario"] = ""
        estado["email_restaurante"] = ""
        estado["cargo"] = ""
        estado["aba_atual"] = "visao_geral"
        mostrar_login()

    def mudar_tema(e):
        if e.control.data == "Claro":
            page.theme_mode = ft.ThemeMode.LIGHT
        elif e.control.data == "Escuro":
            page.theme_mode = ft.ThemeMode.DARK
        else:
            page.theme_mode = ft.ThemeMode.SYSTEM

        # Reconstrói a tela atual para aplicar a nova paleta em todos os elementos
        if estado["loop_ativo"]:
            mostrar_painel_dono()
        else:
            page.update()

    # --- TELA DE LOGIN ---
    def mostrar_login():
        cores = obter_cores()
        page.controls.clear()
        page.scroll = None
        page.bgcolor = cores["fundo_principal"]
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

        campo_email = ft.TextField(label="E-mail do Restaurante", width=300)
        campo_senha = ft.TextField(label="Senha", password=True, can_reveal_password=True, width=300)
        msg_erro = ft.Text(value="", color=cores["erro"])

        def tentar_login(e):
            email = campo_email.value
            senha = campo_senha.value
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()
            cursor.execute('SELECT id, nome FROM restaurantes WHERE email = ? AND senha = ?', (email, senha))
            restaurante = cursor.fetchone()
            conexao.close()

            if restaurante:
                estado["id_restaurante"] = restaurante[0]
                estado["nome_usuario"] = restaurante[1]
                estado["email_restaurante"] = email
                estado["cargo"] = "Dono"
                estado["loop_ativo"] = True
                mostrar_painel_dono()
            else:
                msg_erro.value = "E-mail ou senha incorretos."
                page.update()

        caixa_login = ft.Container(
            content=ft.Column([
                ft.Text("🏢", size=50),
                ft.Text("Rachaki - Login do Dono", size=24, weight="bold", color=cores["texto_principal"]),
                campo_email,
                campo_senha,
                msg_erro,
                ft.Button("Entrar", on_click=tentar_login, width=300, height=50)
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=40,
            border_radius=10,
            bgcolor=cores["fundo_secundario"],
            border=criar_borda(cores["borda"])
        )

        page.add(caixa_login)
        page.update()

    # --- PAINEL DO DONO ---
    def mostrar_painel_dono():
        cores = obter_cores()
        page.controls.clear()
        page.scroll = ft.ScrollMode.AUTO
        page.bgcolor = cores["fundo_principal"]
        page.vertical_alignment = ft.MainAxisAlignment.START
        page.horizontal_alignment = ft.CrossAxisAlignment.START

        cabecalho = ft.Row([
            ft.Text(f"Olá, {estado['nome_usuario']} (Painel do Dono)", size=24, weight="bold", color=cores["texto_principal"], expand=True),
            ft.Button("Atualizar", on_click=lambda e: atualizar_dashboard(), icon="refresh", icon_color=cores["primaria"]),
            ft.Button("Sair", on_click=fazer_logout, icon="logout", icon_color=cores["erro"])
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

        def criar_card(titulo, valor, icone):
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
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()

            # Alertas em tempo real
            cursor.execute('''
                SELECT c.id_mesa, c.hora_abertura, c.status, c.hora_pedido_conta,
                       (SELECT COUNT(*) FROM pedidos p WHERE p.id_comanda = c.id) as qtd_pedidos
                FROM comandas c
                WHERE c.id_restaurante = ? AND c.status != 'Fechada'
            ''', (estado["id_restaurante"],))
            comandas_ativas = cursor.fetchall()

            secao_alertas.controls.clear()
            novos_alertas = []
            agora = datetime.now()

            for id_mesa, hora_abertura, status, hora_pedido_conta, qtd_pedidos in comandas_ativas:
                # Alerta 1: Mais de 15 min sem nenhum pedido registrado
                try:
                    hora_ab = datetime.strptime(hora_abertura, '%Y-%m-%d %H:%M:%S')
                    minutos_aberta = (agora - hora_ab).total_seconds() / 60
                    if qtd_pedidos == 0 and minutos_aberta > 15:
                        novos_alertas.append((f"Mesa {id_mesa} está aberta há {int(minutos_aberta)} min sem nenhum pedido.", "aviso"))
                except (ValueError, TypeError):
                    pass

                # Alerta 2: Aguardando pagamento há mais de 10 min
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

            # Faturamento: soma apenas pedidos de comandas já FECHADAS (pagas)
            cursor.execute('''
                SELECT COALESCE(SUM(ca.preco), 0)
                FROM pedidos p
                JOIN cardapio ca ON p.id_produto = ca.id
                JOIN comandas co ON p.id_comanda = co.id
                WHERE co.id_restaurante = ? AND co.status = 'Fechada' AND co.hora_abertura LIKE ?
            ''', (estado["id_restaurante"], f"{hoje}%"))
            faturamento = cursor.fetchone()[0]

            # Valor em aberto: soma pedidos de comandas que ainda não foram marcadas como pagas
            cursor.execute('''
                SELECT COALESCE(SUM(ca.preco), 0)
                FROM pedidos p
                JOIN cardapio ca ON p.id_produto = ca.id
                JOIN comandas co ON p.id_comanda = co.id
                WHERE co.id_restaurante = ? AND co.status != 'Fechada'
            ''', (estado["id_restaurante"],))
            valor_em_aberto = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM comandas WHERE id_restaurante = ? AND status != 'Fechada'", (estado["id_restaurante"],))
            comandas_abertas = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM comandas WHERE id_restaurante = ? AND status = 'Fechada' AND hora_abertura LIKE ?", (estado["id_restaurante"], f"{hoje}%"))
            comandas_fechadas_hoje = cursor.fetchone()[0]

            secao_resumo.controls.clear()
            secao_resumo.controls.append(criar_card("Faturamento (Hoje)", f"R$ {faturamento:.2f}", "💰"))
            secao_resumo.controls.append(criar_card("Em Aberto", f"R$ {valor_em_aberto:.2f}", "⏳"))
            secao_resumo.controls.append(criar_card("Comandas Abertas", str(comandas_abertas), "📖"))
            secao_resumo.controls.append(criar_card("Comandas Fechadas (Hoje)", str(comandas_fechadas_hoje), "✅"))

            # Top 5 mais vendidos
            cursor.execute('''
                SELECT ca.nome, COUNT(p.id) as qtd
                FROM pedidos p
                JOIN cardapio ca ON p.id_produto = ca.id
                JOIN comandas co ON p.id_comanda = co.id
                WHERE co.id_restaurante = ?
                GROUP BY ca.nome
                ORDER BY qtd DESC
                LIMIT 5
            ''', (estado["id_restaurante"],))
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
            abrir_dialogo(dialogo_detalhes)
        
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
            ''', (estado["id_restaurante"],))
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
                                   (nome, preco_float, desc, estado["id_restaurante"], cat))
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

            def fechar_dialogo_edicao(e_fechar):
                fechar_dialogo(dialogo_edicao_produto)

            dialogo_edicao_produto = ft.AlertDialog(
                title=ft.Text("Editar Produto"),
                content=ft.Column([
                    campo_edit_nome, campo_edit_preco, dropdown_edit_cat, campo_edit_desc, msg_edicao
                ], tight=True, spacing=10),
                actions=[
                    ft.TextButton("Cancelar", on_click=fechar_dialogo_edicao),
                    ft.TextButton("Salvar Alterações", on_click=salvar_edicao)
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            abrir_dialogo(dialogo_edicao_produto)

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
            cursor.execute('SELECT id, nome, preco, descricao, disponivel, categoria FROM cardapio WHERE id_restaurante = ? ORDER BY categoria, nome', (estado["id_restaurante"],))
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
            options=[ft.dropdown.Option("Atendente"), ft.dropdown.Option("Cozinha")],
            value="Atendente"
        )
        msg_equipe = ft.Text(value="", color=cores["sucesso"])
        lista_equipe = ft.Column()

        def adicionar_funcionario(e):
            nome = campo_func_nome.value
            senha = campo_func_senha.value
            cargo = dropdown_cargo.value
            login = f"{nome.split()[0].lower()}{estado['id_restaurante']}"

            if nome and senha:
                conexao = sqlite3.connect('rachaki.db')
                cursor = conexao.cursor()
                cursor.execute('INSERT INTO funcionarios (nome, senha, cargo, id_restaurante, login) VALUES (?, ?, ?, ?, ?)',
                               (nome, senha, cargo, estado["id_restaurante"], login))
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

            def fechar_dialogo_senha(e_fechar):
                fechar_dialogo(dialogo_edicao)

            dialogo_edicao = ft.AlertDialog(
                title=ft.Text(f"Editar senha de {nome_func}"),
                content=campo_nova_senha,
                actions=[ft.TextButton("Cancelar", on_click=fechar_dialogo_senha), ft.TextButton("Salvar Nova Senha", on_click=salvar_senha)],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            abrir_dialogo(dialogo_edicao)

        def carregar_equipe():
            lista_equipe.controls.clear()
            conexao = sqlite3.connect('rachaki.db')
            cursor = conexao.cursor()
            cursor.execute('SELECT id, nome, cargo, login FROM funcionarios WHERE id_restaurante = ?', (estado["id_restaurante"],))
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
                    cursor.execute("SELECT COUNT(*) FROM comandas WHERE id_restaurante = ? AND status != 'Fechada'", (estado["id_restaurante"],))
                    if cursor.fetchone()[0] > 0:
                        msg_mesas.value, msg_mesas.color = "⚠️ Erro: Feche todas as comandas abertas antes de alterar as mesas.", cores["erro"]
                    else:
                        cursor.execute('DELETE FROM mesas WHERE id_restaurante = ?', (estado["id_restaurante"],))
                        for i in range(1, qtd + 1):
                            cursor.execute('INSERT INTO mesas (numero_mesa, id_restaurante) VALUES (?, ?)', (i, estado["id_restaurante"]))
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
            ft.Button("Claro", icon="light_mode", icon_color=cores["primaria"], on_click=mudar_tema, data="Claro"),
            ft.Button("Escuro", icon="dark_mode", icon_color=cores["primaria"], on_click=mudar_tema, data="Escuro"),
            ft.Button("Sistema", icon="brightness_auto", icon_color=cores["primaria"], on_click=mudar_tema, data="Sistema"),
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
        area_conteudo = ft.Container(content=mapa_abas.get(estado["aba_atual"], conteudo_visao_geral), padding=20, expand=True)

        def mudar_aba(conteudo):
            area_conteudo.content = conteudo
            page.update()

        def nav_visao_geral(e):
            estado["aba_atual"] = "visao_geral"
            atualizar_dashboard()
            mudar_aba(conteudo_visao_geral)

        def nav_comandas(e):
            estado["aba_atual"] = "comandas"
            carregar_mesas_ativas()
            mudar_aba(conteudo_comandas)

        def nav_cardapio(e):
            estado["aba_atual"] = "cardapio"
            mudar_aba(conteudo_cardapio)

        def nav_equipe(e):
            estado["aba_atual"] = "equipe"
            mudar_aba(conteudo_equipe)

        def nav_config(e):
            estado["aba_atual"] = "config"
            mudar_aba(conteudo_config)

        page.add(
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
        )

        atualizar_dashboard()
        carregar_cardapio()
        carregar_equipe()
        carregar_mesas_ativas()

    # Inicia o aplicativo
    mostrar_login()

#ft.app(target=main)
ft.app(target=main, view=ft.WEB_BROWSER, port=os.environ.get("PORT", 8000))