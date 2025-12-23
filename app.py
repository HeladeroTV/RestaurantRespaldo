# === APP.PY ===
# Módulo principal de la interfaz gráfica del sistema de restaurante usando Flet.
import flet as ft
from typing import Optional, Callable, List, Dict, Any
from datetime import datetime
import threading
import time
import requests
import winsound
import time as time_module

# IMPORTAR LAS NUEVAS CLASES DE INVENTARIO Y LA NUEVA VISTA DE CAJA
from inventario_view import crear_vista_inventario
from inventario_service import InventoryService
from configuraciones_view import crear_vista_configuraciones
from reportes_view import crear_vista_reportes
from caja_view import crear_vista_caja # <-- IMPORTAR LA NUEVA VISTA DE CAJA
from reservas_view import crear_vista_reservas
from reservas_service import ReservasService # Asumiendo que creas este archivo
# --- AÑADIR ESTOS IMPORTS ---
from recetas_view import crear_vista_recetas
from recetas_service import RecetasService

# === FUNCIÓN: reproducir_sonido_pedido ===
# Reproduce una melodía simple cuando se confirma un pedido.
def reproducir_sonido_pedido():
    try:
        # Melodía: Do - Mi - Sol
        tones = [523, 659, 784]  # Hz
        for tone in tones:
            winsound.Beep(tone, 200)  # 200 ms por nota
            time_module.sleep(0.05)
    except Exception as e:
        print(f"Error al reproducir sonido: {e}")

# === FUNCIÓN: generar_resumen_pedido ===
# Genera un texto resumen del pedido actual con items y total.
def generar_resumen_pedido(pedido):
    if not pedido.get("items"):
        return "Sin items."
    total = sum(item["precio"] for item in pedido["items"])
    items_str = "\n".join(f"- {item['nombre']} (${item['precio']:.2f})" for item in pedido["items"])
    titulo = obtener_titulo_pedido(pedido)
    return f"[{titulo}]\n{items_str}\nTotal: ${total:.2f}"

# === FUNCIÓN: obtener_titulo_pedido ===
# Genera el título del pedido dependiendo si es de mesa o app.
def obtener_titulo_pedido(pedido):
    if pedido.get("mesa_numero") == 99 and pedido.get("numero_app"):
        return f"Digital #{pedido['numero_app']:03d}"  # ✅ CAMBIAR A "Digital"
    else:
        return f"Mesa {pedido['mesa_numero']}"

# === FUNCIÓN: crear_selector_item ===
# Crea un selector con dropdowns para filtrar y elegir items del menú.
def crear_selector_item(menu):
    tipos = list(set(item["tipo"] for item in menu))
    tipos.sort()
    tipo_dropdown = ft.Dropdown(
        label="Tipo de item",
        options=[ft.dropdown.Option(tipo) for tipo in tipos],
        value=tipos[0] if tipos else "Entradas",
        width=200,
    )
    search_field = ft.TextField(
        label="Buscar ítem...",
        prefix_icon=ft.Icons.SEARCH,
        width=200,
        hint_text="Escribe para filtrar..."
    )
    items_dropdown = ft.Dropdown(
        label="Seleccionar item",
        width=200,
    )
    def filtrar_items(e):
        query = search_field.value.lower().strip() if search_field.value else ""
        tipo_actual = tipo_dropdown.value
        if query:
            items_filtrados = [item for item in menu if query in item["nombre"].lower()]
        else:
            items_filtrados = [item for item in menu if item["tipo"] == tipo_actual]
        items_dropdown.options = [ft.dropdown.Option(item["nombre"]) for item in items_filtrados]
        items_dropdown.value = None
        if e and e.page:
            e.page.update()
    def actualizar_items(e):
        filtrar_items(e)
    tipo_dropdown.on_change = actualizar_items
    search_field.on_change = filtrar_items
    actualizar_items(None)
    container = ft.Column([
        tipo_dropdown,
        search_field,
        items_dropdown
    ], spacing=10)
    container.tipo_dropdown = tipo_dropdown
    container.search_field = search_field
    container.items_dropdown = items_dropdown
    def get_selected_item():
        tipo = tipo_dropdown.value
        nombre = items_dropdown.value
        if tipo and nombre:
            for item in menu:
                if item["nombre"] == nombre and item["tipo"] == tipo:
                    return item
        return None
    container.get_selected_item = get_selected_item
    return container

def crear_mesas_grid(backend_service, on_select):
    try:
        # Obtener el estado real de las mesas del backend
        mesas_backend = backend_service.obtener_mesas()
        # Si el backend no tiene mesas, usar valores por defecto
        if not mesas_backend:
            mesas_fisicas = [
                {"numero": 1, "capacidad": 2, "ocupada": False},
                {"numero": 2, "capacidad": 2, "ocupada": False},
                {"numero": 3, "capacidad": 4, "ocupada": False},
                {"numero": 4, "capacidad": 4, "ocupada": False},
                {"numero": 5, "capacidad": 6, "ocupada": False},
                {"numero": 6, "capacidad": 6, "ocupada": False},
            ]
        else:
            mesas_fisicas = mesas_backend
    except Exception as e:
        print(f"Error al obtener mesas del backend: {e}")
        # Usar valores por defecto si hay error
        mesas_fisicas = [
            {"numero": 1, "capacidad": 2, "ocupada": False},
            {"numero": 2, "capacidad": 2, "ocupada": False},
            {"numero": 3, "capacidad": 4, "ocupada": False},
            {"numero": 4, "capacidad": 4, "ocupada": False},
            {"numero": 5, "capacidad": 6, "ocupada": False},
            {"numero": 6, "capacidad": 6, "ocupada": False},
        ]
    grid = ft.GridView(
        expand=1,
        runs_count=3,
        max_extent=220, # Ajustar tamaño máximo de la carta
        child_aspect_ratio=1.0,
        spacing=15, # Ajustar espaciado
        run_spacing=15,
        padding=15,
    )
    for mesa in mesas_fisicas:
        if mesa["numero"] == 99:
            continue
        # Manejar claves de reserva de forma segura
        ocupada = mesa.get("ocupada", False) # Usar .get() con valor por defecto
        reservada = mesa.get("reservada", False) # Usar .get() con valor por defecto
        cliente_reservado_nombre = mesa.get("cliente_reservado_nombre", "N/A") # Usar .get() con valor por defecto
        fecha_hora_reserva = mesa.get("fecha_hora_reserva", "N/A") # Usar .get() con valor por defecto
        # Determinar color y estado basado en ocupada y reservada (COLORES ORIGINALES)
        if ocupada:
            color_base = ft.Colors.RED_700
            color_estado = ft.Colors.RED_700 # Color para hover
            estado = "OCUPADA"
            detalle = ""
        elif reservada:
            color_base = ft.Colors.BLUE_700 # Color para mesa reservada
            color_estado = ft.Colors.BLUE_700 # Color para hover
            estado = "RESERVADA"
            detalle = f"{cliente_reservado_nombre}\n{fecha_hora_reserva}"
        else:
            color_base = ft.Colors.GREEN_700
            color_estado = ft.Colors.GREEN_700 # Color para hover
            estado = "LIBRE"
            detalle = ""
        contenido_mesa = ft.Column(
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=5,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(ft.Icons.TABLE_RESTAURANT, color=ft.Colors.AMBER_400),
                            ft.Text(f"Mesa {mesa['numero']}", size=16, weight=ft.FontWeight.BOLD),
                        ]
                    ),
                    ft.Text(f"Capacidad: {mesa['capacidad']}", size=12),
                    ft.Text(estado, size=14, weight=ft.FontWeight.BOLD)
                ]
            )
        # Añadir detalle si existe (para mesas reservadas)
        if detalle:
            contenido_mesa.controls.append(ft.Text(detalle, size=10, color=ft.Colors.WHITE, italic=True))
        # Carta de Mesa con efectos de hover (USANDO EL COLOR DEL ESTADO COMO FONDO)
        carta_mesa = ft.Container(
            key=f"mesa-{mesa['numero']}",
            bgcolor=color_base, # ✅ USAR EL COLOR DEL ESTADO COMO FONDO
            border_radius=15, # Bordes más redondeados
            padding=15,
            ink=True,
            on_click=lambda e, num=mesa['numero']: on_select(num),
            content=contenido_mesa,
            # Efectos de hover - AHORA USANDO EL COLOR DEL ESTADO
            animate=ft.Animation(200, "easeOut"),
            animate_scale=ft.Animation(200, "easeOut"),
        )
        def on_hover_mesa(e, carta=carta_mesa, color_base=color_base, color_estado=color_estado):
            if e.data == "true":
                carta.scale = 1.05 # Aumentar tamaño ligeramente
                carta.bgcolor = color_estado # Cambiar a color del estado al hacer hover
            else:
                carta.scale = 1.0
                carta.bgcolor = color_base # Volver al color base
            carta.update()
        carta_mesa.on_hover = lambda e, carta=carta_mesa, color_base=color_base, color_estado=color_estado: on_hover_mesa(e, carta, color_base, color_estado)
        grid.controls.append(carta_mesa)
    # Mesa virtual (sin cambios)
    contenido_mesa_virtual = ft.Column(
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=5,
        controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.MOBILE_FRIENDLY, color=ft.Colors.AMBER_400),
                    ft.Text("Digital", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ]
            ),
            ft.Text("📱 Pedido por Digital", size=12, color=ft.Colors.WHITE),
            ft.Text("Siempre disponible", size=10, color=ft.Colors.WHITE),
        ]
    )
    carta_mesa_virtual = ft.Container(
        key="mesa-99",
        bgcolor=ft.Colors.BLUE_700,
        border_radius=15,
        padding=15,
        ink=True,
        on_click=lambda e: on_select(99),
        width=220,
        height=150, # Ajustar altura
        content=contenido_mesa_virtual,
        animate=ft.Animation(200, "easeOut"),
        animate_scale=ft.Animation(200, "easeOut"),
    )
    def on_hover_mesa_virtual(e, carta=carta_mesa_virtual, color_base=ft.Colors.BLUE_700):
        if e.data == "true":
            carta.scale = 1.05
            carta.bgcolor = ft.Colors.BLUE_800 # Color más oscuro al hacer hover
        else:
            carta.scale = 1.0
            carta.bgcolor = color_base
        carta.update()
    carta_mesa_virtual.on_hover = lambda e, carta=carta_mesa_virtual: on_hover_mesa_virtual(e, carta)
    grid.controls.append(carta_mesa_virtual)
    return grid

# === FUNCIÓN: crear_panel_gestion ===
# Crea el panel lateral para gestionar pedidos de una mesa seleccionada.
def crear_panel_gestion(backend_service, menu, on_update_ui, page, primary_color, primary_dark_color): # Añadir los parámetros
    estado = {"mesa_seleccionada": None, "pedido_actual": None}
    mesa_info = ft.Text("", size=16, weight=ft.FontWeight.BOLD)
    tamaño_grupo_input = ft.TextField(
        label="Tamaño del grupo",
        input_filter=ft.NumbersOnlyInputFilter(),
        prefix_icon=ft.Icons.PEOPLE
    )
    # Campo de texto para la nota
    nota_pedido = ft.TextField(
        label="Notas del pedido",
        multiline=True,
        max_lines=3,
        hint_text="Ej: Sin cebolla, sin salsa, etc.",
        width=400
    )
    selector_item = crear_selector_item(menu)
    # --- NUEVO: Selector de Cantidad ---
    cantidad_dropdown = ft.Dropdown(
        label="Cantidad",
        options=[ft.dropdown.Option(i) for i in range(1, 11)], # Opciones del 1 al 10
        value="1", # Valor por defecto
        width=100,
        disabled=True # Se habilita cuando se selecciona un ítem
    )
    # --- FIN NUEVO ---
    # --- BOTONES CON EFECTOS DE HOVER ESTILIZADOS ---
    asignar_btn = ft.ElevatedButton(
        text="Asignar Cliente",
        disabled=True,
        # Usar colores del tema principal para hover
        style=ft.ButtonStyle(
            color={"": "white"},
            bgcolor={"": ft.Colors.GREEN_700, "hovered": primary_dark_color}, # Cambia a PRIMARY_DARK al hacer hover
        ),
    )
    agregar_item_btn = ft.ElevatedButton(
        text="Agregar Item",
        disabled=True,
        style=ft.ButtonStyle(
            color={"": "white"},
            bgcolor={"": ft.Colors.BLUE_700, "hovered": primary_dark_color}, # Cambia a PRIMARY_DARK al hacer hover
        ),
    )
    eliminar_ultimo_btn = ft.ElevatedButton(
        text="Eliminar último ítem",
        disabled=True,
        style=ft.ButtonStyle(
            color={"": "white"},
            bgcolor={"": ft.Colors.RED_700, "hovered": primary_dark_color}, # Cambia a PRIMARY_DARK al hacer hover
        ),
    )
    # Nuevo botón: Confirmar Pedido
    confirmar_pedido_btn = ft.ElevatedButton(
        text="Confirmar Pedido",
        disabled=True,
        style=ft.ButtonStyle(
            color={"": "white"},
            bgcolor={"": ft.Colors.AMBER_700, "hovered": primary_dark_color}, # Cambia a PRIMARY_DARK al hacer hover
        ),
    )
    # --- FIN BOTONES ---
    resumen_pedido = ft.Text("", size=14)
    def actualizar_estado_botones():
        mesa_seleccionada = estado["mesa_seleccionada"]
        pedido_actual = estado["pedido_actual"]
        if not mesa_seleccionada:
            asignar_btn.disabled = True
            agregar_item_btn.disabled = True
            eliminar_ultimo_btn.disabled = True
            confirmar_pedido_btn.disabled = True
            # --- ACTUALIZACIÓN: Deshabilitar selector de cantidad ---
            cantidad_dropdown.disabled = True
            # --- FIN ACTUALIZACIÓN ---
            return
        if mesa_seleccionada.get("numero") == 99:
            asignar_btn.disabled = pedido_actual is not None
            agregar_item_btn.disabled = pedido_actual is None
            eliminar_ultimo_btn.disabled = pedido_actual is None or not pedido_actual.get("items", [])
            confirmar_pedido_btn.disabled = pedido_actual is None or not pedido_actual.get("items", [])
            # --- ACTUALIZACIÓN: Habilitar selector de cantidad si hay un pedido ---
            cantidad_dropdown.disabled = pedido_actual is None or selector_item.get_selected_item() is None
            # --- FIN ACTUALIZACIÓN ---
        else:
            asignar_btn.disabled = mesa_seleccionada.get("ocupada", False)
            agregar_item_btn.disabled = pedido_actual is None
            eliminar_ultimo_btn.disabled = pedido_actual is None or not pedido_actual.get("items", [])
            confirmar_pedido_btn.disabled = pedido_actual is None or not pedido_actual.get("items", [])
            # --- ACTUALIZACIÓN: Habilitar selector de cantidad si hay un pedido ---
            cantidad_dropdown.disabled = pedido_actual is None or selector_item.get_selected_item() is None
            # --- FIN ACTUALIZACIÓN ---
        page.update()
    # --- ACTUALIZACIÓN: Función para manejar cambio en selector de ítem ---
    def on_item_selected(e):
        # Habilitar el selector de cantidad solo si hay un ítem seleccionado y un pedido actual
        if estado["pedido_actual"] and selector_item.get_selected_item():
            cantidad_dropdown.disabled = False
        else:
            cantidad_dropdown.disabled = True
        page.update()
    # Asignar la función al cambio de selección en el dropdown de ítems
    selector_item.items_dropdown.on_change = on_item_selected
    # --- FIN ACTUALIZACIÓN ---
    def seleccionar_mesa_interna(numero_mesa):
        try:
            mesas = backend_service.obtener_mesas()
            mesa_seleccionada = next((m for m in mesas if m["numero"] == numero_mesa), None)
            estado["mesa_seleccionada"] = mesa_seleccionada
            estado["pedido_actual"] = None
            if not mesa_seleccionada:
                return
            # Validar estado de la mesa
            if mesa_seleccionada.get("ocupada", False):
                # Mesa ocupada, no se puede asignar nuevo cliente aquí, pero se puede gestionar el pedido existente
                # Buscar pedido existente para esta mesa
                pedidos_activos = backend_service.obtener_pedidos_activos()
                pedido_existente = next((p for p in pedidos_activos if p["mesa_numero"] == numero_mesa and p.get("estado") in ["Tomando pedido", "Pendiente", "En preparacion"]), None)
                if pedido_existente:
                    estado["pedido_actual"] = pedido_existente
                    mesa_info.value = f"Mesa {mesa_seleccionada['numero']} - Capacidad: {mesa_seleccionada['capacidad']} personas (Pedido Activo)"
                else:
                    # Caso raro: mesa ocupada pero sin pedido activo visible
                    mesa_info.value = f"Mesa {mesa_seleccionada['numero']} - Ocupada (Estado inconsistente)"
                    estado["pedido_actual"] = None
            elif mesa_seleccionada.get("reservada", False):
                # Mesa reservada, verificar fecha/hora
                fecha_reserva_str = mesa_seleccionada.get("fecha_hora_reserva")
                if fecha_reserva_str:
                    try:
                        # Parsear la fecha de reserva (ajusta el formato si es diferente)
                        fecha_reserva = datetime.strptime(fecha_reserva_str.split(".")[0], "%Y-%m-%d %H:%M:%S") # Remover microsegundos si existen
                        ahora = datetime.now()
                        # Permitir asignar si la reserva es ahora o en el pasado reciente (por ejemplo, 30 mins)
                        # O mostrar un mensaje si es en el futuro
                        if ahora >= fecha_reserva or (ahora - fecha_reserva).total_seconds() < 1800: # 30 minutos en segundos
                            mesa_info.value = f"Mesa {mesa_seleccionada['numero']} - Reservada para {mesa_seleccionada.get('cliente_reservado_nombre', 'N/A')} - Capacidad: {mesa_seleccionada['capacidad']} personas"
                        else:
                            # Reserva futura, no se debería asignar cliente nuevo aún
                            mesa_info.value = f"Mesa {mesa_seleccionada['numero']} - Reservada para {mesa_seleccionada.get('cliente_reservado_nombre', 'N/A')} el {fecha_reserva_str}"
                            estado["pedido_actual"] = None # No se puede asignar cliente nuevo
                            # Opcional: Mostrar mensaje o deshabilitar botones
                            asignar_btn.disabled = True
                            page.update()
                            return # Salir sin inicializar el pedido
                    except ValueError:
                        print(f"Error al parsear fecha de reserva para mesa {numero_mesa}: {fecha_reserva_str}")
                        mesa_info.value = f"Mesa {mesa_seleccionada['numero']} - Reservada (Fecha inválida)"
                else:
                    mesa_info.value = f"Mesa {mesa_seleccionada['numero']} - Reservada (Sin fecha)"
            else: # Mesa libre
                mesa_info.value = f"Mesa {mesa_seleccionada['numero']} - Capacidad: {mesa_seleccionada['capacidad']} personas"
            # ... (resto del código de seleccionar_mesa_interna)
            resumen_pedido.value = ""
            nota_pedido.value = ""
            actualizar_estado_botones()
        except Exception as e:
            print(f"Error seleccionando mesa: {e}")
            mesa_info.value = f"Error al seleccionar mesa {numero_mesa}"
    def asignar_cliente(e):
        mesa_seleccionada = estado["mesa_seleccionada"]
        if not mesa_seleccionada:
            return
        # Re-validar estado antes de asignar (por si cambió desde que se seleccionó)
        mesas_actualizadas = backend_service.obtener_mesas()
        mesa_estado_actual = next((m for m in mesas_actualizadas if m["numero"] == mesa_seleccionada["numero"]), None)
        if not mesa_estado_actual:
            print("Error: Mesa no encontrada al asignar cliente.")
            return
        # Verificar si la mesa está ocupada o reservada para otra fecha
        if mesa_estado_actual.get("ocupada", False):
            print(f"La mesa {mesa_seleccionada['numero']} ya está ocupada.")
            return # No hacer nada o mostrar mensaje
        elif mesa_estado_actual.get("reservada", False):
            # Opcional: Verificar fecha aquí también si no se hizo en seleccionar_mesa_interna
            fecha_reserva_str = mesa_estado_actual.get("fecha_hora_reserva")
            if fecha_reserva_str:
                try:
                    fecha_reserva = datetime.strptime(fecha_reserva_str.split(".")[0], "%Y-%m-%d %H:%M:%S")
                    ahora = datetime.now()
                    if ahora < fecha_reserva and (fecha_reserva - ahora).total_seconds() >= 1800: # Futura y no dentro de 30 mins
                        print(f"La mesa {mesa_seleccionada['numero']} está reservada para más tarde.")
                        return # No hacer nada o mostrar mensaje
                    # Si llega aquí, es una reserva actual o pasada recientemente, se puede "ocupar"
                except ValueError:
                    print(f"Error al parsear fecha de reserva para mesa {mesa_seleccionada['numero']}")
                    return
        try:
            # ✅ CREAR PEDIDO EN MEMORIA (NO EN BASE DE DATOS AÚN)
            nuevo_pedido = {
                "id": None,  # Aún no tiene ID
                "mesa_numero": mesa_seleccionada["numero"],
                "items": [],
                "estado": "Tomando pedido",  # ✅ ESTADO TEMPORAL
                "fecha_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "numero_app": None,
                "notas": nota_pedido.value
            }
            estado["pedido_actual"] = nuevo_pedido
            resumen_pedido.value = ""
            on_update_ui()
            actualizar_estado_botones()
        except Exception as ex:
            print(f"Error asignar cliente: {ex}")
    def agregar_item_pedido(e):
        mesa_seleccionada = estado["mesa_seleccionada"]
        pedido_actual = estado["pedido_actual"]
        if not mesa_seleccionada or not pedido_actual:
            return
        item = selector_item.get_selected_item()
        if not item:
            return
        # --- OBTENER CANTIDAD SELECCIONADA ---
        try:
            cantidad = int(cantidad_dropdown.value)
            if cantidad < 1:
                cantidad = 1 # Asegurar al menos 1
        except ValueError:
            cantidad = 1 # Valor por defecto si hay error
        # --- FIN OBTENER CANTIDAD ---
        try:
            # ✅ SOLO ACTUALIZAR EN MEMORIA SI AÚN NO TIENE ID
            if pedido_actual["id"] is None:
                items_actuales = pedido_actual.get("items", [])
                # Agregar el ítem 'cantidad' veces
                for _ in range(cantidad):
                    items_actuales.append({
                        "nombre": item["nombre"],
                        "precio": item["precio"],
                        "tipo": item["tipo"],
                        "cantidad": 1 # Cada ítem individual tiene cantidad 1
                    })
                pedido_actual["items"] = items_actuales
                estado["pedido_actual"] = pedido_actual
            else:
                # ✅ SI YA TIENE ID, ACTUALIZAR EN LA BASE DE DATOS
                items_actuales = pedido_actual.get("items", [])
                # Agregar el ítem 'cantidad' veces
                for _ in range(cantidad):
                    items_actuales.append({
                        "nombre": item["nombre"],
                        "precio": item["precio"],
                        "tipo": item["tipo"],
                        "cantidad": 1 # Cada ítem individual tiene cantidad 1
                    })
                # Actualizar el pedido en el backend
                resultado = backend_service.actualizar_pedido(
                    pedido_actual["id"],
                    pedido_actual["mesa_numero"],
                    items_actuales,
                    pedido_actual["estado"],
                    pedido_actual.get("notas", "")
                )
                # Actualizar el pedido localmente
                pedido_actual["items"] = items_actuales
                estado["pedido_actual"] = pedido_actual
            # Reiniciar el selector de cantidad a 1 después de agregar
            cantidad_dropdown.value = "1"
            cantidad_dropdown.disabled = selector_item.get_selected_item() is None # Deshabilitar si no hay ítem seleccionado
            # Actualizar resumen
            resumen = generar_resumen_pedido(pedido_actual)
            resumen_pedido.value = resumen
            on_update_ui()
            actualizar_estado_botones()
        except Exception as ex:
            print(f"Error al agregar ítem: {ex}")
    def eliminar_ultimo_item(e):
        pedido_actual = estado["pedido_actual"]
        if not pedido_actual:
            return
        try:
            if pedido_actual["id"] is None:
                # ✅ SOLO ACTUALIZAR EN MEMORIA (NO TIENE ID)
                items = pedido_actual.get("items", [])
                if items:
                    items.pop() # Elimina el último ítem agregado (independientemente de la cantidad)
                    pedido_actual["items"] = items
                    estado["pedido_actual"] = pedido_actual
                    resumen = generar_resumen_pedido(pedido_actual)
                    resumen_pedido.value = resumen
                else:
                    resumen_pedido.value = "Sin items."
            else:
                # ✅ SI TIENE ID, ELIMINAR EN LA BASE DE DATOS
                # OJO: Esto elimina el último ítem agregado, no necesariamente una "unidad" de un ítem repetido
                # Para eliminar unidades específicas, se necesitaría una lógica más compleja en el backend
                backend_service.eliminar_ultimo_item(pedido_actual["id"])
                pedidos_activos = backend_service.obtener_pedidos_activos()
                pedido_actualizado = next((p for p in pedidos_activos if p["id"] == pedido_actual["id"]), None)
                if pedido_actualizado:
                    estado["pedido_actual"] = pedido_actualizado
                    resumen = generar_resumen_pedido(pedido_actualizado)
                    resumen_pedido.value = resumen
                else:
                    resumen_pedido.value = "Sin items."
                    estado["pedido_actual"] = None
            on_update_ui()
            actualizar_estado_botones()
        except Exception as ex:
            print(f"Error al eliminar ítem: {ex}")
    def confirmar_pedido(e):
        pedido_actual = estado["pedido_actual"]
        if not pedido_actual:
            return
        if not pedido_actual.get("items"):
            return  # ✅ No confirmar si no tiene ítems
        try:
            nota_a_guardar = nota_pedido.value.strip() if nota_pedido.value else ""  # ✅ ASEGURAR QUE NO SEA None
            if pedido_actual["id"] is None:
                # ✅ ES UN NUEVO PEDIDO, CREARLO EN LA BASE DE DATOS
                nuevo_pedido = backend_service.crear_pedido(
                    pedido_actual["mesa_numero"],
                    pedido_actual["items"],
                    "Pendiente",  # ✅ ESTADO REAL
                    nota_a_guardar  # ✅ ENVIAR NOTA
                )
                estado["pedido_actual"] = nuevo_pedido
            else:
                # ✅ ACTUALIZAR UN PEDIDO EXISTENTE
                backend_service.actualizar_pedido(
                    pedido_actual["id"],
                    pedido_actual["mesa_numero"],
                    pedido_actual["items"],
                    "Pendiente",
                    nota_a_guardar  # ✅ ENVIAR NOTA
                )
            # Reiniciar el selector de cantidad
            cantidad_dropdown.value = "1"
            cantidad_dropdown.disabled = True
            
            # --- NUEVO: LIMPIAR ESTADO DE LA UI PARA QUE NO QUEDE EL RESUMEN ---
            estado["pedido_actual"] = None
            estado["mesa_seleccionada"] = None
            
            # Limpiar campos de texto
            mesa_info.value = ""
            resumen_pedido.value = ""
            nota_pedido.value = ""
            
            # Actualizar botones
            actualizar_estado_botones()
            # --- FIN NUEVO ---

            on_update_ui()  # ✅ ACTUALIZA LAS OTRAS PESTAÑAS
            # Reproducir sonido en un hilo separado para no bloquear la UI
            threading.Thread(target=reproducir_sonido_pedido, daemon=True).start()
        except Exception as ex:
            print(f"Error al confirmar pedido: {ex}")
            # --- MOSTRAR ERROR AL USUARIO CON ALERT DIALOG ---
            msg_error = str(ex)
            
            # Función para cerrar el diálogo
            def cerrar_alerta_stock(e):
                page.close(dlg_alerta)

            # Crear el diálogo
            dlg_alerta = ft.AlertDialog(
                title=ft.Text("⚠️ No se puede tomar la orden", color="red"),
                content=ft.Text(f"{msg_error}", size=16),
                actions=[
                    ft.TextButton("Entendido", on_click=cerrar_alerta_stock),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            
            # Utilizando el método moderno de Flet para abrir diálogos
            page.open(dlg_alerta)
            page.update()
            # --- FIN MOSTRAR ERROR ---
    asignar_btn.on_click = asignar_cliente
    agregar_item_btn.on_click = agregar_item_pedido
    eliminar_ultimo_btn.on_click = eliminar_ultimo_item
    confirmar_pedido_btn.on_click = confirmar_pedido
    panel = ft.Container(
        content=ft.Column(
            controls=[
                ft.Container(
                    content=mesa_info,
                    bgcolor=ft.Colors.BLUE_GREY_900,
                    padding=10,
                    border_radius=10,
                ),
                ft.Container(height=20),
                tamaño_grupo_input,
                asignar_btn,
                ft.Divider(),
                nota_pedido,
                ft.Divider(),
                selector_item,
                # --- AÑADIR SELECTOR DE CANTIDAD A LA INTERFAZ ---
                ft.Row([
                    cantidad_dropdown, # Selector de cantidad
                    ft.Text("   ", width=10), # Espaciado
                    agregar_item_btn # Botón Agregar Item
                ], alignment=ft.MainAxisAlignment.START), # Alinear al inicio
                # --- FIN AÑADIR SELECTOR ---
                eliminar_ultimo_btn,
                confirmar_pedido_btn,
                ft.Divider(),
                ft.Divider(),
                ft.Text("Resumen del pedido", size=16, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=resumen_pedido,
                    bgcolor=ft.Colors.BLUE_GREY_900,
                    padding=10,
                    border_radius=10,
                )
            ],
            spacing=10,
            expand=True,
        ),
        padding=20,
        expand=True
    )
    panel.seleccionar_mesa = seleccionar_mesa_interna
    return panel

# === FUNCIÓN: crear_vista_cocina ===
# Vista de cocina para ver y gestionar pedidos activos.
def crear_vista_cocina(backend_service, on_update_ui, page):
    lista_pedidos = ft.ListView(
        expand=1,
        spacing=10,
        padding=20,
        auto_scroll=True,
    )
    def actualizar():
        try:
            pedidos = backend_service.obtener_pedidos_activos()
            lista_pedidos.controls.clear()
            for pedido in pedidos:
                # ✅ SOLO MOSTRAR SI ESTÁ PENDIENTE O EN PREPARACIÓN
                if pedido.get("estado") in ["Pendiente", "En preparacion"] and pedido.get("items"):
                    lista_pedidos.controls.append(crear_item_pedido_cocina(pedido, backend_service, on_update_ui))
            page.update()
        except Exception as e:
            print(f"Error al cargar pedidos: {e}")
    def crear_item_pedido_cocina(pedido, backend_service, on_update_ui):
        def cambiar_estado(e, p, nuevo_estado):
            try:
                backend_service.actualizar_estado_pedido(p["id"], nuevo_estado)
                on_update_ui()  # ✅ ACTUALIZA AMBAS VISTAS
            except Exception as ex:
                print(f"Error al cambiar estado: {ex}")
        def eliminar_pedido_click(e):
            try:
                # ✅ ELIMINAR EL PEDIDO DE LA BASE DE DATOS
                backend_service.eliminar_pedido(pedido["id"])
                on_update_ui()  # ✅ ACTUALIZAR INTERFAZ
            except Exception as ex:
                print(f"Error al eliminar pedido: {ex}")
        origen = f"{obtener_titulo_pedido(pedido)} - {pedido.get('fecha_hora', 'Sin fecha')}"
        # --- MODIFICACIÓN PARA MOSTRAR "SIN NOTAS" ---
        # Verificar si 'notas' existe y no está vacío
        notas_pedido = pedido.get('notas', '')
        if not notas_pedido: # Si es None, '', o cualquier valor "falsy"
            nota = "Sin Nota"
        else:
            nota = f"Notas: {notas_pedido}"
        # --- FIN MODIFICACIÓN ---
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(origen, size=20, weight=ft.FontWeight.BOLD),
                    ft.IconButton(
                        icon=ft.Icons.DELETE,
                        on_click=eliminar_pedido_click,
                        tooltip="Eliminar pedido",
                        icon_color=ft.Colors.RED_700
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Text(generar_resumen_pedido(pedido)),
                ft.Text(nota, color=ft.Colors.YELLOW_200), # <-- Se usa la variable 'nota' modificada
                ft.Row([
                    ft.ElevatedButton(
                        "En preparacion",
                        on_click=lambda e, p=pedido: cambiar_estado(e, p, "En preparacion"),
                        disabled=pedido.get("estado") != "Pendiente",
                        style=ft.ButtonStyle(bgcolor=ft.Colors.ORANGE_700, color=ft.Colors.WHITE)
                    ),
                    ft.ElevatedButton(
                        "Listo",
                        on_click=lambda e, p=pedido: cambiar_estado(e, p, "Listo"),
                        disabled=pedido.get("estado") != "En preparacion",
                        style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)
                    ),
                ]),
                ft.Text(f"Estado: {pedido.get('estado', 'Pendiente')}", color=ft.Colors.BLUE_200)
            ]),
            bgcolor=ft.Colors.BLUE_GREY_900,
            padding=10,
            border_radius=10,
        )
    vista = ft.Container(
        content=ft.Column([
            ft.Text("Pedidos en Cocina", size=20, weight=ft.FontWeight.BOLD),
            lista_pedidos
        ]),
        padding=20,
        expand=True
    )
    vista.actualizar = actualizar
    return vista

def crear_vista_admin(backend_service, menu, on_update_ui, page):
    tipos = list(set(item["tipo"] for item in menu))
    tipos.sort()
    tipo_item_admin = ft.Dropdown(
        label="Tipo de item (Agregar)",
        options=[ft.dropdown.Option(tipo) for tipo in tipos],
        value=tipos[0] if tipos else "Entradas",
        width=250,
    )
    nombre_item = ft.TextField(label="Nombre de item", width=250)
    precio_item = ft.TextField(label="Precio", width=250)
    tipo_item_eliminar = ft.Dropdown(
        label="Tipo item (Eliminar)",
        options=[ft.dropdown.Option(tipo) for tipo in tipos],
        value=tipos[0] if tipos else "Entradas",
        width=250,
    )
    item_eliminar = ft.Dropdown(label="Seleccionar item a eliminar", width=300)
    def actualizar_items_eliminar(e):
        tipo = tipo_item_eliminar.value
        items = [item for item in menu if item["tipo"] == tipo]
        item_eliminar.options = [ft.dropdown.Option(item["nombre"]) for item in items]
        item_eliminar.value = None
        page.update()
    tipo_item_eliminar.on_change = actualizar_items_eliminar
    actualizar_items_eliminar(None)
    def agregar_item(e):
        tipo = tipo_item_admin.value
        nombre = (nombre_item.value or "").strip()
        texto_precio = (precio_item.value or "").strip()
        if not tipo or not nombre or not texto_precio:
            return
        texto_precio = texto_precio.replace(",", ".")
        try:
            precio = float(texto_precio)
        except ValueError:
            return
        if precio <= 0:
            return
        try:
            # Usar el nuevo método del backend
            backend_service.agregar_item_menu(nombre, precio, tipo)
            on_update_ui()
        except Exception as ex:
            print(f"Error al agregar item: {ex}")
    def eliminar_item(e):
        tipo = tipo_item_eliminar.value
        nombre = item_eliminar.value
        if not tipo or not nombre:
            return
        try:
            # Usar el nuevo método del backend
            backend_service.eliminar_item_menu(nombre, tipo)
            on_update_ui()
        except Exception as ex:
            print(f"Error al eliminar item: {ex}")
    # Campos para clientes
    nombre_cliente = ft.TextField(label="Nombre", width=300)
    domicilio_cliente = ft.TextField(label="Domicilio", width=300)
    # --- CAMBIO 2: Restringir celular a 10 números ---
    celular_cliente = ft.TextField(
        label="Celular",
        width=300,
        input_filter=ft.NumbersOnlyInputFilter(), # Solo números
        prefix_icon=ft.Icons.PHONE,
        max_length=10 # Máximo 10 caracteres
    )
    # --- FIN CAMBIO 2 ---
    # ✅ LISTA DE CLIENTES - SIN FONDO ESPECÍFICO
    lista_clientes = ft.ListView(
        expand=True,  # ✅ EXPANDIR PARA OCUPAR TODO EL ESPACIO
        spacing=10,
        padding=20,
        auto_scroll=True,
    )
    def actualizar_lista_clientes():
        try:
            clientes = backend_service.obtener_clientes()
            lista_clientes.controls.clear()
            for cliente in clientes:
                cliente_row = ft.Container(
                    content=ft.Column([
                        ft.Text(f"{cliente['nombre']}", size=18, weight=ft.FontWeight.BOLD),
                        ft.Text(f"Domicilio: {cliente['domicilio']}", size=14),
                        ft.Text(f"Celular: {cliente['celular']}", size=14),
                        ft.Text(f"Registrado: {cliente['fecha_registro']}", size=12, color=ft.Colors.GREY_500),
                        ft.ElevatedButton(
                            "Eliminar",
                            on_click=lambda e, id=cliente['id']: eliminar_cliente_click(id),
                            style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE)
                        )
                    ]),
                    bgcolor=ft.Colors.BLUE_GREY_900, # El contenedor de cada cliente sí tiene fondo
                    padding=10,
                    border_radius=10
                )
                lista_clientes.controls.append(cliente_row)
            page.update()
        except Exception as e:
            print(f"Error al cargar clientes: {e}")
    def agregar_cliente_click(e):
        nombre = nombre_cliente.value
        domicilio = domicilio_cliente.value
        celular = celular_cliente.value
        if not nombre or not domicilio or not celular:
            return
        try:
            backend_service.agregar_cliente(nombre, domicilio, celular)
            nombre_cliente.value = ""
            domicilio_cliente.value = ""
            celular_cliente.value = "" # Limpiar campo
            actualizar_lista_clientes()
        except Exception as ex:
            print(f"Error al agregar cliente: {ex}")
    def eliminar_cliente_click(cliente_id: int):
        try:
            backend_service.eliminar_cliente(cliente_id)
            actualizar_lista_clientes()
        except Exception as ex:
            print(f"Error al eliminar cliente: {ex}")
    # --- CAMBIO 1: QUITAR EL FONDO DEL CONTENEDOR PRINCIPAL ---
    # La vista ahora no tiene un bgcolor específico, por lo tanto heredará el fondo de la página (page.bgcolor = "#0a0e1a")
    vista = ft.Container(
        content=ft.Column([
            # Sección de menú
            ft.Text("Agregar item al menú", size=20, weight=ft.FontWeight.BOLD),
            tipo_item_admin,
            nombre_item,
            precio_item,
            ft.ElevatedButton(
                text="Agregar item",
                on_click=agregar_item,
                style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)
            ),
            ft.Divider(),
            ft.Text("Eliminar item del menú", size=20, weight=ft.FontWeight.BOLD),
            tipo_item_eliminar,
            item_eliminar,
            ft.ElevatedButton(
                text="Eliminar item",
                on_click=eliminar_item,
                style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE)
            ),
            ft.Divider(),
            # Sección de clientes
            ft.Text("Agregar Cliente", size=20, weight=ft.FontWeight.BOLD),
            nombre_cliente,
            domicilio_cliente,
            celular_cliente,
            ft.ElevatedButton(
                "Agregar Cliente",
                on_click=agregar_cliente_click,
                style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)
            ),
            ft.Divider(),
            ft.Text("Clientes Registrados", size=20, weight=ft.FontWeight.BOLD),
            # ✅ SECCIÓN SEPARADA PARA CLIENTES REGISTRADOS - SIN FONDO ESPECÍFICO
            ft.Container(
                content=lista_clientes,
                expand=True,  # ✅ CONTAINER EXPANDIDO
                height=500,  # ✅ ALTURA AMPLIA
                # No usar bgcolor aquí para que sea transparente y muestre el fondo de la página
                padding=10,
                border_radius=10,
            )
        ], expand=True, scroll="auto"),  # ✅ SCROLL VERTICAL EN LA COLUMNA
        padding=20,
        # NO USAR bgcolor aquí, se quita para que use el fondo de la página
        # bgcolor=ft.Colors.BLUE_GREY_900,  # <-- COMENTAR O ELIMINAR ESTA LÍNEA
        expand=True  # ✅ CONTAINER PRINCIPAL EXPANDIDO
    )
    # --- FIN CAMBIO 1 ---
    vista.actualizar_lista_clientes = actualizar_lista_clientes
    return vista

# === FUNCIÓN: crear_vista_personalizacion ===
# Crea la vista para personalizar umbrales de alerta.
def crear_vista_personalizacion(app_instance):
    """
    Crea la vista de personalización para umbrales de alerta.
    Args:
        app_instance (RestauranteGUI): Instancia de la aplicación principal.
    Returns:
        ft.Container: Contenedor con la interfaz de personalización.
    """
    # Campo para ingresar el nuevo umbral de tiempo
    tiempo_umbral_input = ft.TextField(
        label="Tiempo umbral para pedidos (minutos)",
        value=str(app_instance.tiempo_umbral_minutos), # Mostrar valor actual
        width=300,
        input_filter=ft.NumbersOnlyInputFilter(), # Solo números
        hint_text="Ej: 20"
    )

    def guardar_configuracion_click(e):
        """Guarda el nuevo umbral de tiempo ingresado."""
        try:
            nuevo_tiempo_umbral = int(tiempo_umbral_input.value)

            if nuevo_tiempo_umbral <= 0:
                print("El umbral de tiempo debe ser un número positivo.")
                # Opcional: Mostrar una alerta en la UI
                def cerrar_alerta(e):
                    page.close(dlg_error)
                
                dlg_error = ft.AlertDialog(
                    title=ft.Text("Error"),
                    content=ft.Text("El umbral de tiempo debe ser un número positivo."),
                    actions=[ft.TextButton("Aceptar", on_click=cerrar_alerta)],
                    actions_alignment=ft.MainAxisAlignment.END,
                )
                app_instance.page.dialog = dlg_error
                dlg_error.open = True
                app_instance.page.update()
                return

            # Actualizar el valor en la instancia de la aplicación
            app_instance.tiempo_umbral_minutos = nuevo_tiempo_umbral

            # Guardar la configuración en el archivo
            app_instance.guardar_configuracion()

            print(f"Configuración actualizada: Tiempo umbral: {nuevo_tiempo_umbral} min")

            # Opcional: Mostrar mensaje de éxito
            def cerrar_alerta_ok(e):
                page.close(dlg_success)
            
            dlg_success = ft.AlertDialog(
                title=ft.Text("Éxito"),
                content=ft.Text("Configuración guardada correctamente."),
                actions=[ft.TextButton("Aceptar", on_click=cerrar_alerta_ok)],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            app_instance.page.dialog = dlg_success
            dlg_success.open = True
            app_instance.page.update()

        except ValueError:
            print("Por favor, ingrese un valor numérico válido para el tiempo umbral.")
            # Opcional: Mostrar una alerta en la UI
            def cerrar_alerta_val(e):
                page.close(dlg_error_val)
            
            dlg_error_val = ft.AlertDialog(
                title=ft.Text("Error"),
                content=ft.Text("Por favor, ingrese un valor numérico válido para el tiempo umbral."),
                actions=[ft.TextButton("Aceptar", on_click=cerrar_alerta_val)],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            app_instance.page.dialog = dlg_error_val
            dlg_error_val.open = True
            app_instance.page.update()

    vista = ft.Container(
        content=ft.Column([
            ft.Text("Personalización de Alertas", size=24, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Text("Establece el umbral para las alertas de retraso de pedidos.", size=16),
            ft.Divider(),
            tiempo_umbral_input,
            ft.ElevatedButton(
                "Guardar Configuración",
                on_click=guardar_configuracion_click,
                style=ft.ButtonStyle(bgcolor=app_instance.PRIMARY, color=ft.Colors.WHITE)
            )
        ]),
        padding=20,
        expand=True
    )

    return vista

# === CLASE: RestauranteGUI ===
# Clase principal que maneja la interfaz gráfica y los estados del sistema.
class RestauranteGUI:
    def __init__(self):
        from backend_service import BackendService
        from configuraciones_service import ConfiguracionesService
        # from recetas_service import RecetasService # Asumiendo que está importado arriba
        self.backend_service = BackendService()
        self.inventory_service = InventoryService()
        self.config_service = ConfiguracionesService()
        self.recetas_service = RecetasService() # Añadir si no lo tienes
        self.page = None
        self.mesas_grid = None
        self.panel_gestion = None
        self.vista_cocina = None
        # self.vista_caja = None # <-- COMENTAR ESTA LINEA (ANTIGUA, si existe)
        self.vista_caja = None # <-- Asegurar inicialización
        self.vista_admin = None
        self.vista_inventario = None
        self.vista_recetas = None
        self.vista_configuraciones = None
        self.vista_reportes = None
        self.vista_personalizacion = None  # ✅ AGREGAR ESTO
        self.menu_cache = None
        self.hilo_sincronizacion = None
        # --- NUEVAS VARIABLES PARA ALERTA DE BAJOS STOCK ---
        self.hilo_verificacion_stock = None
        self.hay_stock_bajo = False # Bandera para indicar si hay stock bajo
        self.ingredientes_bajos_lista = [] # Lista de nombres de ingredientes bajos
        self.mostrar_detalle_stock = False # Bandera para mostrar/ocultar el detalle
        # --- FIN NUEVAS VARIABLES ---
        # --- NUEVAS VARIABLES PARA ALERTA DE RETRASOS ---
        self.hilo_verificacion_retrasos = None
        self.lista_alertas_retrasos = [] # Lista de diccionarios con info de alertas {id_pedido, mesa, titulo, tiempo_retraso, ...}
        self.hay_pedidos_atrasados = False # Bandera para indicar si hay pedidos atrasados
        self.mostrar_detalle_retrasos = False # Bandera para mostrar/ocultar el detalle de retrasos
        # --- FIN NUEVAS VARIABLES ---
        # --- NUEVAS VARIABLES PARA CONFIGURACIÓN ---
        self.tiempo_umbral_minutos = 20 # Umbral configurable en minutos (inicializado con valor por defecto)
        self.umbral_stock_bajo = 5 # Umbral configurable para stock bajo (inicializado con valor por defecto)
        # --- FIN NUEVAS VARIABLES ---
        # --- COLORES ESTÉTICOS ---
        self.PRIMARY = "#6366f1"
        self.PRIMARY_DARK = "#4f46e5"
        self.ACCENT = "#f59e0b"
        self.SUCCESS = "#10b981"
        self.DANGER = "#ef4444"
        self.CARD_BG = "#1a1f35"
        self.CARD_HOVER = "#252b45"
        # --- FIN COLORES ESTÉTICOS ---
        self.reservas_service = ReservasService() # Asumiendo que usas la clase ReservasService
        self.vista_reservas = None # Añadir esta línea
        # --- CARGAR CONFIGURACIÓN AL INICIAR ---
        self.cargar_configuracion()

    # --- FUNCIÓN: cargar_configuracion ---
    # Carga los umbrales desde un archivo local.
    def cargar_configuracion(self):
        import json
        from pathlib import Path
        carpeta_datos = Path.home() / ".restaurantia" / "datos"
        carpeta_datos.mkdir(parents=True, exist_ok=True)
        archivo_config = carpeta_datos / "config.json"

        if archivo_config.exists():
            try:
                with open(archivo_config, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    # Cargar valores si existen, sino usar valores por defecto
                    self.tiempo_umbral_minutos = config.get("tiempo_umbral_minutos", 20)
                    self.umbral_stock_bajo = config.get("umbral_stock_bajo", 5)
                    print(f"Configuración cargada: Tiempo umbral: {self.tiempo_umbral_minutos} min, Stock umbral: {self.umbral_stock_bajo}")
            except Exception as e:
                print(f"Error al cargar configuración: {e}")
                # Usar valores por defecto si hay error
                self.tiempo_umbral_minutos = 20
                self.umbral_stock_bajo = 5
        else:
            print("Archivo de configuración no encontrado, usando valores por defecto.")
            # Asegurar que el archivo exista con valores por defecto si no existe
            self.guardar_configuracion()

    # --- FUNCIÓN: guardar_configuracion ---
    # Guarda los umbrales en un archivo local.
    def guardar_configuracion(self):
        import json
        from pathlib import Path
        carpeta_datos = Path.home() / ".restaurantia" / "datos"
        carpeta_datos.mkdir(parents=True, exist_ok=True)
        archivo_config = carpeta_datos / "config.json"

        config = {
            "tiempo_umbral_minutos": self.tiempo_umbral_minutos,
            "umbral_stock_bajo": self.umbral_stock_bajo
        }
        try:
            with open(archivo_config, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            print(f"Configuración guardada: Tiempo umbral: {self.tiempo_umbral_minutos} min, Stock umbral: {self.umbral_stock_bajo}")
        except Exception as e:
            print(f"Error al guardar configuración: {e}")

    # --- FIN FUNCIONES DE CONFIGURACIÓN ---

    # --- FUNCIÓN: verificar_stock_periodicamente ---
    def verificar_stock_periodicamente(self):
        """Verifica el inventario cada 30 segundos y actualiza la bandera."""
        while True:
            try:
                items = self.inventory_service.obtener_inventario()
                # VERIFICAR ALERTAS DE INGREDIENTES BAJOS - USAR UMBRAL CONFIGURABLE
                # umbral_bajo = 5 # UMBRAL PARA AVISAR (PUEDES CAMBIAR ESTE VALOR) # <-- COMENTAR ESTA LINEA
                ingredientes_bajos = [item for item in items if item['cantidad_disponible'] <= self.umbral_stock_bajo] # <-- USAR self.umbral_stock_bajo
                # ACTUALIZAR CONTENIDO DE ALERTA
                if ingredientes_bajos:
                    nombres_bajos = ", ".join([item['nombre'] for item in ingredientes_bajos])
                    # Actualizar la bandera y la lista de ingredientes bajos
                    self.hay_stock_bajo = True
                    self.ingredientes_bajos_lista = [item['nombre'] for item in ingredientes_bajos]
                    print(f"Bandera de stock bajo activada. Ingredientes: {self.ingredientes_bajos_lista}") # Mensaje de depuración
                else:
                    self.hay_stock_bajo = False
                    self.ingredientes_bajos_lista = []
                    # Si no hay stock bajo, ocultar el detalle
                    self.mostrar_detalle_stock = False
                    print("Bandera de stock bajo desactivada.") # Mensaje de depuración
                time.sleep(30) # VERIFICAR CADA 30 SEGUNDOS
            except Exception as e:
                print(f"Error en verificación periódica de inventario (stock): {e}")
                time.sleep(30) # ESPERAR 30 SEGUNDOS ANTES DE REINTENTAR

    # --- NUEVA FUNCIÓN CORREGIDA: verificar_retrasos_periodicamente ---
    def verificar_retrasos_periodicamente(self):
        """Verifica pedidos activos cada 60 segundos y genera/elimina alertas si exceden el umbral."""
        while True:
            try:
                pedidos_activos = self.backend_service.obtener_pedidos_activos()
                ahora = datetime.now()
                nuevos_ids_activos = {pedido['id'] for pedido in pedidos_activos if pedido.get('estado') in ["Pendiente", "En preparacion"]}

                # Filtrar alertas antiguas que ya no estén en pedidos_activos o ya no estén atrasadas
                alertas_actualizadas = []
                for alerta in self.lista_alertas_retrasos:
                    id_pedido = alerta['id_pedido']
                    # Verificar si el pedido aún está activo (Pendiente o En preparacion)
                    pedido_activo = next((p for p in pedidos_activos if p['id'] == id_pedido and p.get('estado') in ["Pendiente", "En preparacion"]), None)
                    if pedido_activo:
                        # El pedido sigue activo, verificar si sigue atrasado
                        try:
                            fecha_pedido = datetime.strptime(pedido_activo.get('fecha_hora', ''), "%Y-%m-%d %H:%M:%S")
                            diferencia = (ahora - fecha_pedido).total_seconds() / 60  # Diferencia en minutos
                            if diferencia >= self.tiempo_umbral_minutos:
                                # Aún está atrasado, mantener la alerta
                                alerta['tiempo_retraso'] = round(diferencia, 2) # Opcional: actualizar el tiempo de retraso mostrado
                                alertas_actualizadas.append(alerta)
                            else:
                                # Ya no está atrasado, no mantener la alerta
                                print(f"Alerta eliminada para Pedido {id_pedido} - ya no está atrasado.")
                        except ValueError as ve:
                            print(f"Error al parsear fecha del pedido {id_pedido} en alertas: {pedido_activo.get('fecha_hora', '')} - {ve}")
                            # Si hay error de parseo, no mantener la alerta
                    else:
                        # El pedido ya no está activo (posiblemente cambió a Listo, Entregado, Pagado, o fue eliminado)
                        print(f"Alerta eliminada para Pedido {id_pedido} - ya no está activo.")
                        # No mantener la alerta

                # Actualizar la lista de alertas con las filtradas
                self.lista_alertas_retrasos = alertas_actualizadas

                # Generar nuevas alertas como antes
                nuevas_alertas = []
                ids_alertas_existentes = {alerta['id_pedido'] for alerta in self.lista_alertas_retrasos}

                for pedido in pedidos_activos:
                    estado = pedido.get('estado')
                    fecha_str = pedido.get('fecha_hora')
                    # Solo considerar pedidos Pendientes o En Preparación
                    if estado in ["Pendiente", "En preparacion"] and fecha_str:
                        try:
                            fecha_pedido = datetime.strptime(fecha_str.split(".")[0], "%Y-%m-%d %H:%M:%S")
                            diferencia = (ahora - fecha_pedido).total_seconds() / 60  # Diferencia en minutos

                            if diferencia >= self.tiempo_umbral_minutos:
                                id_pedido = pedido['id']

                                # Solo agregar si no existe una alerta para este pedido
                                if id_pedido not in ids_alertas_existentes:
                                    nueva_alerta = {
                                        "id_pedido": id_pedido,
                                        "titulo_pedido": obtener_titulo_pedido(pedido), # Usar la función auxiliar
                                        "estado": estado,
                                        "tiempo_retraso": round(diferencia, 2),
                                        "fecha_hora": fecha_pedido # Opcional: guardar el datetime original
                                    }
                                    nuevas_alertas.append(nueva_alerta)
                                    print(f"Alerta generada para Pedido {id_pedido} en {obtener_titulo_pedido(pedido)} - {diferencia:.2f} minutos retraso.")

                        except ValueError as ve:
                            print(f"Error al parsear fecha del pedido {pedido.get('id')}: {fecha_str} - {ve}")
                            continue # Saltar este pedido si hay error de parseo

                # Agregar las nuevas alertas a la lista ya filtrada
                self.lista_alertas_retrasos.extend(nuevas_alertas)

                # Actualizar la bandera de retrasos basada en la lista actualizada
                self.hay_pedidos_atrasados = len(self.lista_alertas_retrasos) > 0

                # Opcional: Mantener solo las últimas N alertas
                # self.lista_alertas_retrasos = self.lista_alertas_retrasos[-10:] # Por ejemplo, últimos 10

                time.sleep(60) # VERIFICAR CADA 60 SEGUNDOS
            except Exception as e:
                print(f"Error en verificación periódica de retrasos: {e}")
                time.sleep(60) # ESPERAR 60 SEGUNDOS ANTES DE REINTENTAR
    # --- FIN NUEVA FUNCIÓN CORREGIDA ---

    def iniciar_sincronizacion(self):
        """Inicia la sincronización automática en segundo plano."""
        def actualizar_periodicamente():
            while True:
                try:
                    # ✅ ACTUALIZAR INTERFAZ CADA 3 SEGUNDOS
                    self.actualizar_ui_completo()
                    time.sleep(3)  # ✅ INTERVALO DE ACTUALIZACIÓN
                except Exception as e:
                    print(f"Error en sincronización: {e}")
                    time.sleep(3)

        # ✅ INICIAR HILO DE SINCRONIZACIÓN GENERAL
        self.hilo_sincronizacion = threading.Thread(target=actualizar_periodicamente, daemon=True)
        self.hilo_sincronizacion.start()
        # ✅ INICIAR HILO DE VERIFICACIÓN DE STOCK
        self.hilo_verificacion_stock = threading.Thread(target=self.verificar_stock_periodicamente, daemon=True)
        self.hilo_verificacion_stock.start()
        # ✅ INICIAR HILO DE VERIFICACIÓN DE RETRASOS
        self.hilo_verificacion_retrasos = threading.Thread(target=self.verificar_retrasos_periodicamente, daemon=True)
        self.hilo_verificacion_retrasos.start()

    def main(self, page: ft.Page):
        self.page = page
        page.title = "RestIA"
        page.padding = 0
        page.theme_mode = "dark"
        page.bgcolor = "#0a0e1a" # Aplicar color de fondo oscuro principal
        reloj = ft.Text("", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_200)

        # --- INDICADOR PRINCIPAL DE STOCK BAJO (Botón) ---
        indicador_stock_bajo = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.WARNING, color=ft.Colors.WHITE, size=20),
                ft.Text("Stock Bajo", color=ft.Colors.WHITE, size=14, weight=ft.FontWeight.BOLD)
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=5),
            bgcolor=self.DANGER, # Usar color de peligro para el indicador
            padding=5,
            border_radius=5,
            width=120,
            height=30,
            visible=False, # Inicialmente oculto, se controla en actualizar_ui_completo
            ink=True, # Para efecto de click
            on_click=self.toggle_detalle_stock_bajo # Asociar la función de toggle
        )

        # --- INDICADOR PRINCIPAL DE RETRASOS (Botón) ---
        indicador_retrasos = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.ALARM, color=ft.Colors.WHITE, size=20), # Icono de alarma
                ft.Text("Retrasos", color=ft.Colors.WHITE, size=14, weight=ft.FontWeight.BOLD)
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=5),
            bgcolor=self.ACCENT, # Usar color naranja (ACCENT) para el indicador
            padding=5,
            border_radius=5,
            width=120,
            height=30,
            visible=False, # Inicialmente oculto, se controla en actualizar_ui_completo
            ink=True, # Para efecto de click
            on_click=self.toggle_detalle_retrasos # Asociar la función de toggle
        )
        # --- FIN INDICADOR DE RETRASOS ---

        # --- PANEL DESPLEGABLE DE DETALLES DE STOCK ---
        panel_detalle_stock = ft.Container(
            content=ft.Column([
                ft.Text("Ingredientes con bajo stock:", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                # Este ListView se llenará dinámicamente
                ft.ListView(
                    controls=[],
                    spacing=2,
                    padding=5,
                    height=100, # Altura fija para el panel
                    width=200,  # Ancho fijo para el panel
                    auto_scroll=False,
                    # bgcolor=ft.Colors.RED_900,  # <-- ❌ ESTE ARGUMENTO NO ES VÁLIDO EN ListView
                    # border_radius=5,            # <-- ❌ ESTE ARGUMENTO TAMPOCO ES VÁLIDO EN ListView
                )
            ], spacing=5),
            bgcolor=self.CARD_BG,  # Usar color base de carta
            padding=10,
            border_radius=5,
            visible=False, # Inicialmente oculto, se controla en actualizar_visibilidad_alerta
            width=220, # Ancho del panel
            # No usar ink=True aquí, solo el botón principal debe ser clickeable
        )
        # --- FIN PANEL DESPLEGABLE DE DETALLES DE STOCK ---

        # --- PANEL DESPLEGABLE DE DETALLES DE RETRASOS ---
        panel_detalle_retrasos = ft.Container(
            content=ft.Column([
                ft.Text("Pedidos con retraso:", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                # Este ListView se llenará dinámicamente
                ft.ListView(
                    controls=[],
                    spacing=2,
                    padding=5,
                    height=100, # Altura fija para el panel
                    width=200,  # Ancho fijo para el panel
                    auto_scroll=False,
                    # bgcolor=ft.Colors.ORANGE_900,  # <-- ❌ ESTE ARGUMENTO NO ES VÁLIDO EN ListView
                    # border_radius=5,            # <-- ❌ ESTE ARGUMENTO TAMPOCO ES VÁLIDO EN ListView
                )
            ], spacing=5),
            bgcolor=self.CARD_BG,  # Usar color base de carta
            padding=10,
            border_radius=5,
            visible=False, # Inicialmente oculto, se controla en actualizar_visibilidad_alerta
            width=220, # Ancho del panel
            # No usar ink=True aquí, solo el botón principal debe ser clickeable
        )
        # --- FIN PANEL DESPLEGABLE DE DETALLES DE RETRASOS ---

        def actualizar_reloj():
            reloj.value = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            page.update()

        def loop_reloj():
            while True:
                actualizar_reloj()
                time.sleep(1)

        hilo_reloj = threading.Thread(target=loop_reloj, daemon=True)
        hilo_reloj.start()

        try:
            self.menu_cache = self.backend_service.obtener_menu()
        except Exception as e:
            print(f"Error al cargar menú: {e}")
            self.menu_cache = []

        self.mesas_grid = crear_mesas_grid(self.backend_service, self.seleccionar_mesa)
        # --- PASAR LOS COLORES DEL TEMA PRINCIPAL ---
        self.panel_gestion = crear_panel_gestion(
            self.backend_service,
            self.menu_cache,
            self.actualizar_ui_completo,
            page,
            self.PRIMARY,       # Pasar PRIMARY desde RestauranteGUI
            self.PRIMARY_DARK   # Pasar PRIMARY_DARK desde RestauranteGUI
        )
        # --- FIN PASAR LOS COLORES ---
        self.vista_cocina = crear_vista_cocina(self.backend_service, self.actualizar_ui_completo, page)
        # self.vista_caja = crear_vista_caja(self.backend_service, self.actualizar_ui_completo, page) # <-- COMENTAR ESTA LINEA (ANTIGUA)
        self.vista_caja = crear_vista_caja(self.backend_service, self.actualizar_ui_completo, page) # <-- USAR LA NUEVA VISTA DE caja_view.py
        self.vista_admin = crear_vista_admin(self.backend_service, self.menu_cache, self.actualizar_ui_completo, page)
        # --- AÑADIR ESTA LINEA ---
        self.vista_recetas = crear_vista_recetas(
            self.recetas_service,      # Servicio de recetas
            self.backend_service,      # Para obtener menú (platos)
            self.inventory_service,    # Para obtener ingredientes
            self.actualizar_ui_completo,
            page
        )
        # --- FIN AÑADIR ESTA LINEA ---
        # self.vista_inventario = crear_vista_inventario(self.inventory_service, self.actualizar_ui_completo, page) # <-- COMENTAR ESTA LINEA
        self.vista_inventario = crear_vista_inventario(self.inventory_service, self.actualizar_ui_completo, page) # <-- QUITAR 'self'
        self.vista_configuraciones = crear_vista_configuraciones(
            self.config_service,
            self.inventory_service,
            self.backend_service, # ✅ AÑADIDO: Pasar backend_service
            self.actualizar_ui_completo,
            page
        )
        self.vista_reportes = crear_vista_reportes(self.backend_service, self.actualizar_ui_completo, page)
        self.vista_reservas = crear_vista_reservas(self.reservas_service, self.backend_service, self.backend_service, self.actualizar_ui_completo, page) # Pasar servicios necesarios
        # --- CREAR Y ASIGNAR LA VISTA DE PERSONALIZACIÓN ---
        self.vista_personalizacion = crear_vista_personalizacion(self) # <-- Crear la vista y pasar la instancia de la app
        # --- FIN CREAR Y ASIGNAR LA VISTA DE PERSONALIZACIÓN ---
        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(
                    text="Mesera",
                    icon=ft.Icons.PERSON,
                    content=self.crear_vista_mesera()
                ),
                ft.Tab(
                    text="Cocina",
                    icon=ft.Icons.RESTAURANT,
                    content=self.vista_cocina
                ),
                ft.Tab(
                    text="Caja",
                    icon=ft.Icons.POINT_OF_SALE,
                    content=self.vista_caja # <-- USAR LA NUEVA VISTA
                ),
                ft.Tab(
                    text="Administracion",
                    icon=ft.Icons.ADMIN_PANEL_SETTINGS,
                    content=self.vista_admin
                ),
                ft.Tab(
                    text="Inventario",
                    icon=ft.Icons.INVENTORY_2,
                    content=self.vista_inventario
                ),
                # --- AÑADIR ESTA PESTAÑA ---
                ft.Tab(
                    text="Recetas",
                    icon=ft.Icons.BOOKMARK_BORDER, # Elige un icono adecuado
                    content=self.vista_recetas
                ),
                # --- FIN AÑADIR ESTA PESTAÑA ---
                ft.Tab(
                    text="Configuraciones",
                    icon=ft.Icons.SETTINGS,
                    content=self.vista_configuraciones
                ),
                # --- AÑADIR ESTA PESTAÑA ---
                ft.Tab(
                    text="Personalización", # Nombre de la nueva pestaña
                    icon=ft.Icons.TUNE, # Icono para personalización
                    content=self.vista_personalizacion # Contenido de la nueva vista
                ),
                # --- FIN AÑADIR ESTA PESTAÑA ---
                ft.Tab(
                    text="Reservas",
                    icon=ft.Icons.CALENDAR_TODAY, # Icono para reservas
                    content=self.vista_reservas
                ),
                ft.Tab(
                    text="Reportes",
                    icon=ft.Icons.ANALYTICS,
                    content=self.vista_reportes
                ),
            ],
            expand=1
        )

        # Actualizar visibilidad del indicador y detalle en cada actualización de UI
        def actualizar_visibilidad_alerta():
            # Actualizar visibilidad del indicador principal de stock
            indicador_stock_bajo.visible = self.hay_stock_bajo
            # Actualizar visibilidad del panel de detalle de stock
            panel_detalle_stock.visible = self.hay_stock_bajo and self.mostrar_detalle_stock
            # Actualizar contenido del ListView dentro del panel de detalle de stock
            lista_detalle_stock = panel_detalle_stock.content.controls[1] # El ListView
            lista_detalle_stock.controls.clear()
            if self.hay_stock_bajo:
                for ingrediente in self.ingredientes_bajos_lista:
                    lista_detalle_stock.controls.append(
                        ft.Text(f"- {ingrediente}", size=12, color=ft.Colors.WHITE)
                    )

            # Actualizar visibilidad del indicador principal de retrasos
            indicador_retrasos.visible = self.hay_pedidos_atrasados
            # Actualizar visibilidad del panel de detalle de retrasos
            panel_detalle_retrasos.visible = self.hay_pedidos_atrasados and self.mostrar_detalle_retrasos
            # Actualizar contenido del ListView dentro del panel de detalle de retrasos
            lista_detalle_retrasos = panel_detalle_retrasos.content.controls[1] # El ListView
            lista_detalle_retrasos.controls.clear()
            if self.hay_pedidos_atrasados:
                for alerta in self.lista_alertas_retrasos:
                    lista_detalle_retrasos.controls.append(
                        ft.Text(f"- {alerta['titulo_pedido']} ({alerta['tiempo_retraso']} min)", size=12, color=ft.Colors.WHITE)
                    )

            page.update()

        # Agregar al Stack, ahora con el panel de detalle y el indicador de retrasos
        page.add(
            ft.Stack(
                controls=[
                    tabs,
                    # --- AÑADIR INDICADORES AL STACK (en la esquina superior derecha) ---
                    ft.Container(
                        content=ft.Column([
                            ft.Row([ # Contenedor para ambos indicadores en una fila
                                indicador_stock_bajo,
                                ft.Text("   ", width=10), # Espaciado entre indicadores
                                indicador_retrasos, # Indicador de retrasos
                            ], alignment=ft.MainAxisAlignment.START), # Alinear al inicio
                            # Añadir los paneles de detalle justo debajo de los indicadores
                            ft.Container(
                                content=ft.Column([
                                    panel_detalle_stock,
                                    panel_detalle_retrasos
                                ]),
                                # No usar top/right aquí para el panel, se posiciona relativo al botón
                                # Mejor: Usar coordenadas relativas al Stack
                                # La forma más simple es dejarlo aquí y que actualizar_visibilidad_alerta lo maneje
                            )
                        ], spacing=5), # Espacio entre el botón y el panel
                        top=10,  # Posición desde arriba para el contenedor padre (botones)
                        right=10, # Posición desde la derecha para el contenedor padre (botones)
                    ),
                    # --- FIN AÑADIR INDICADORES ---
                    ft.Container(
                        content=reloj,
                        right=20,   # <-- AÑADIR ESTA LÍNEA: 20px desde la derecha
                        bottom=50,  # <-- MANTENER ESTA LÍNEA: 50px desde la parte inferior
                        padding=10,
                        bgcolor=ft.Colors.BLUE_GREY_900,
                        border_radius=8,
                    )
                ],
                expand=True
            )
        )

        # ✅ INICIAR SINCRONIZACIÓN AUTOMÁTICA
        self.iniciar_sincronizacion()
        self.actualizar_ui_completo()
        # Llamar una vez inicialmente para reflejar el estado inicial
        actualizar_visibilidad_alerta()
        # Vincular la función de actualización de visibilidad a la clase para usarla en actualizar_ui_completo
        self.actualizar_visibilidad_alerta = actualizar_visibilidad_alerta

    def crear_vista_mesera(self):
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text("Mesas del restaurante", size=20, weight=ft.FontWeight.BOLD),
                            self.mesas_grid
                        ],
                        expand=True
                    ),
                    ft.VerticalDivider(),
                    ft.Container(
                        width=400,
                        content=self.panel_gestion,
                        expand=True
                    )
                ],
                expand=True
            ),
            expand=True
        )

    def seleccionar_mesa(self, numero_mesa: int):
        if self.panel_gestion:
            self.panel_gestion.seleccionar_mesa(numero_mesa)

    def actualizar_ui_completo(self):
        nuevo_grid = crear_mesas_grid(self.backend_service, self.seleccionar_mesa)
        self.mesas_grid.controls = nuevo_grid.controls
        self.mesas_grid.update()
        if hasattr(self.vista_cocina, 'actualizar'):
            self.vista_cocina.actualizar()
        # if hasattr(self.vista_caja, 'actualizar'): # <-- COMENTAR ESTA LINEA (ANTIGUA, si existe)
        #     self.vista_caja.actualizar()
        if hasattr(self.vista_caja, 'actualizar'): # <-- USAR EL METODO DE LA NUEVA VISTA
            self.vista_caja.actualizar()
        if hasattr(self.vista_admin, 'actualizar_lista_clientes'):
            self.vista_admin.actualizar_lista_clientes()
        # --- AÑADIR ESTA LÍNEA ---
        if hasattr(self.vista_recetas, 'actualizar_datos'):
            self.vista_recetas.actualizar_datos()
        # --- FIN AÑADIR ESTA LÍNEA ---
        if hasattr(self.vista_inventario, 'actualizar_lista'):
            self.vista_inventario.actualizar_lista()
        # --- ACTUALIZAR VISIBILIDAD DEL INDICADOR Y DETALLE ---
        if hasattr(self, 'actualizar_visibilidad_alerta'):
            self.actualizar_visibilidad_alerta()
        # --- FIN ACTUALIZAR VISIBILIDAD ---

        # --- MOSTRAR ALERTAS DE RETRASOS ---
        # Esta lógica ya se maneja en actualizar_visibilidad_alerta
        # No es necesario hacer nada adicional aquí
        # --- FIN MOSTRAR ALERTAS DE RETRASOS ---

        self.page.update()
        if hasattr(self.vista_reservas, 'cargar_clientes_mesas'): # O un método de actualización si lo defines
    # self.vista_reservas.cargar_clientes_mesas() # Si necesitas recargar datos específicos
            pass # Opcional, dependiendo de la lógica de la vista de reservas

    # --- FUNCIÓN: actualizar_lista_inventario ---
    # Actualiza la lista de inventario solo si no hay campo en edición.
    def actualizar_lista_inventario(self):
        """Llama a actualizar_lista de la vista de inventario solo si no hay campo en edición."""
        if hasattr(self.vista_inventario, 'campo_en_edicion_id') and hasattr(self.vista_inventario, 'actualizar_lista'):
            # Verificar si hay un campo en edición en la vista de inventario
            if getattr(self.vista_inventario, 'campo_en_edicion_id', None) is not None:
                print("Hay un campo en edición en la vista de inventario, se omite la actualización.")
                return # Salir sin actualizar la lista
        # Si no hay campo en edición o no se puede verificar, llamar a actualizar_lista
        if hasattr(self.vista_inventario, 'actualizar_lista'):
            self.vista_inventario.actualizar_lista()

    # --- NUEVA FUNCIÓN: toggle_detalle_stock_bajo ---
    # Alterna la visibilidad del detalle de ingredientes bajos.
    def toggle_detalle_stock_bajo(self, e):
        """Alterna la visibilidad del panel de detalles de stock bajo."""
        self.mostrar_detalle_stock = not self.mostrar_detalle_stock
        print(f"Detalle stock bajo mostrado: {self.mostrar_detalle_stock}") # Mensaje de depuración
        # Llamar a actualizar_ui_completo para que refleje el cambio de visibilidad
        self.actualizar_ui_completo() # <-- Opción que asegura actualización general

    # --- NUEVA FUNCIÓN: toggle_detalle_retrasos ---
    # Alterna la visibilidad del detalle de pedidos retrasados.
    def toggle_detalle_retrasos(self, e):
        """Alterna la visibilidad del panel de detalles de pedidos retrasados."""
        self.mostrar_detalle_retrasos = not self.mostrar_detalle_retrasos
        print(f"Detalle retrasos mostrado: {self.mostrar_detalle_retrasos}") # Mensaje de depuración
        # Llamar a actualizar_ui_completo para que refleje el cambio de visibilidad
        self.actualizar_ui_completo() # <-- Opción que asegura actualización general
    # --- FIN NUEVA FUNCIÓN ---

# === FUNCIÓN: crear_vista_personalizacion ===
# Crea la vista para personalizar umbrales de alerta.
def crear_vista_personalizacion(app_instance):
    """
    Crea la vista de personalización para umbrales de alerta.
    Args:
        app_instance (RestauranteGUI): Instancia de la aplicación principal.
    Returns:
        ft.Container: Contenedor con la interfaz de personalización.
    """
    # Campos para ingresar los nuevos umbrales
    tiempo_umbral_input = ft.TextField(
        label="Tiempo umbral para pedidos (minutos)",
        value=str(app_instance.tiempo_umbral_minutos), # Mostrar valor actual
        width=300,
        input_filter=ft.NumbersOnlyInputFilter(), # Solo números
        hint_text="Ej: 20"
    )
    stock_umbral_input = ft.TextField(
        label="Cantidad umbral para stock bajo",
        value=str(app_instance.umbral_stock_bajo), # Mostrar valor actual
        width=300,
        input_filter=ft.NumbersOnlyInputFilter(), # Solo números
        hint_text="Ej: 5"
    )

    def guardar_configuracion_click(e):
        """Guarda los nuevos umbrales ingresados."""
        try:
            nuevo_tiempo_umbral = int(tiempo_umbral_input.value)
            nuevo_stock_umbral = int(stock_umbral_input.value)

            if nuevo_tiempo_umbral <= 0 or nuevo_stock_umbral < 0:
                print("Los umbrales deben ser números positivos (tiempo) o cero/negativos (stock).")
                # Opcional: Mostrar una alerta en la UI
                def cerrar_alerta(e):
                    app_instance.page.close(dlg_error)
                
                dlg_error = ft.AlertDialog(
                    title=ft.Text("Error"),
                    content=ft.Text("Los umbrales deben ser números positivos (tiempo) o cero/negativos (stock)."),
                    actions=[ft.TextButton("Aceptar", on_click=cerrar_alerta)],
                    actions_alignment=ft.MainAxisAlignment.END,
                )
                app_instance.page.dialog = dlg_error
                dlg_error.open = True
                app_instance.page.update()
                return

            # Actualizar los valores en la instancia de la aplicación
            app_instance.tiempo_umbral_minutos = nuevo_tiempo_umbral
            app_instance.umbral_stock_bajo = nuevo_stock_umbral

            # Guardar la configuración en el archivo
            app_instance.guardar_configuracion()

            print(f"Configuración actualizada: Tiempo umbral: {nuevo_tiempo_umbral} min, Stock umbral: {nuevo_stock_umbral}")

            # Opcional: Mostrar mensaje de éxito
            def cerrar_alerta_ok(e):
                app_instance.page.close(dlg_success)
            
            dlg_success = ft.AlertDialog(
                title=ft.Text("Éxito"),
                content=ft.Text("Configuración guardada correctamente."),
                actions=[ft.TextButton("Aceptar", on_click=cerrar_alerta_ok)],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            app_instance.page.dialog = dlg_success
            dlg_success.open = True
            app_instance.page.update()

        except ValueError:
            print("Por favor, ingrese valores numéricos válidos.")
            # Opcional: Mostrar una alerta en la UI
            def cerrar_alerta_val(e):
                app_instance.page.close(dlg_error_val)
            
            dlg_error_val = ft.AlertDialog(
                title=ft.Text("Error"),
                content=ft.Text("Por favor, ingrese valores numéricos válidos."),
                actions=[ft.TextButton("Aceptar", on_click=cerrar_alerta_val)],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            app_instance.page.dialog = dlg_error_val
            dlg_error_val.open = True
            app_instance.page.update()

    vista = ft.Container(
        content=ft.Column([
            ft.Text("Personalización de Alertas", size=24, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Text("Establece los umbrales para las alertas de retraso de pedidos y bajo stock.", size=16),
            ft.Divider(),
            tiempo_umbral_input,
            stock_umbral_input,
            ft.ElevatedButton(
                "Guardar Configuración",
                on_click=guardar_configuracion_click,
                style=ft.ButtonStyle(bgcolor=app_instance.PRIMARY, color=ft.Colors.WHITE)
            )
        ]),
        padding=20,
        expand=True
    )

    return vista

def main():
    app = RestauranteGUI()
    ft.app(target=app.main)

if __name__ == "__main__":
    main()