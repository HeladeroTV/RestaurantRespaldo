# caja_view.py
import flet as ft
from typing import List, Dict, Any

def crear_vista_caja(backend_service, on_update_ui, page):
    lista_cuentas = ft.ListView(
        expand=1,
        spacing=10,
        padding=20,
        auto_scroll=True,
    )

    # Variable para almacenar el pedido seleccionado para cobro
    pedido_seleccionado_para_cobro = None

    # Controles para el cobro del pedido seleccionado
    pago_cliente = ft.TextField(
        label="Con cuánto paga",
        input_filter=ft.NumbersOnlyInputFilter(),
        width=200,
        disabled=True # Se habilita cuando hay un pedido seleccionado
    )
    cambio_text = ft.Text("Cambio: $0.00", size=14, weight=ft.FontWeight.BOLD)
    metodo_pago = ft.Dropdown(
        label="Método de pago",
        options=[
            ft.dropdown.Option("Efectivo"),
            ft.dropdown.Option("Tarjeta"),
            ft.dropdown.Option("QR"),
        ],
        value="Efectivo",
        width=200,
        disabled=True # Se habilita cuando hay un pedido seleccionado
    )
    calcular_cambio_btn = ft.ElevatedButton(
        "Calcular cambio",
        on_click=lambda e: procesar_pago(e),
        style=ft.ButtonStyle(bgcolor=ft.Colors.AMBER_700, color=ft.Colors.WHITE),
        disabled=True # Se habilita cuando hay un pedido seleccionado
    )
    terminar_pedido_btn = ft.ElevatedButton(
        "Terminar pedido",
        on_click=lambda e: terminar_pedido_seleccionado(e),
        style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE),
        disabled=True # Se habilita cuando hay un pedido seleccionado y se ha calculado el cambio
    )
    cancelar_cobro_btn = ft.ElevatedButton(
        "Cancelar cobro",
        on_click=lambda e: cancelar_seleccion_pedido(e),
        style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE),
        disabled=True # Se habilita cuando hay un pedido seleccionado
    )

    def actualizar_estado_botones_cobro():
        """Habilita/deshabilita botones de cobro según si hay un pedido seleccionado."""
        hay_pedido = pedido_seleccionado_para_cobro is not None
        pago_cliente.disabled = not hay_pedido
        metodo_pago.disabled = not hay_pedido
        calcular_cambio_btn.disabled = not hay_pedido
        terminar_pedido_btn.disabled = not hay_pedido or not pago_cliente.value
        cancelar_cobro_btn.disabled = not hay_pedido

    def seleccionar_pedido_para_cobro(pedido):
        """Selecciona un pedido para cobro y actualiza los controles."""
        nonlocal pedido_seleccionado_para_cobro
        pedido_seleccionado_para_cobro = pedido
        # Reiniciar campos de pago
        pago_cliente.value = ""
        cambio_text.value = "Cambio: $0.00"
        metodo_pago.value = "Efectivo"
        actualizar_estado_botones_cobro()
        page.update()

    def cancelar_seleccion_pedido(e):
        """Deselecciona el pedido y limpia los controles."""
        nonlocal pedido_seleccionado_para_cobro
        pedido_seleccionado_para_cobro = None
        pago_cliente.value = ""
        cambio_text.value = "Cambio: $0.00"
        metodo_pago.value = "Efectivo"
        actualizar_estado_botones_cobro()
        page.update()

    def procesar_pago(e):
        if not pedido_seleccionado_para_cobro:
            return
        try:
            total_pedido = sum(item["precio"] for item in pedido_seleccionado_para_cobro["items"])
            pago = float(pago_cliente.value)
            if pago < total_pedido:
                return # Opcional: mostrar mensaje de pago insuficiente
            cambio = pago - total_pedido
            cambio_text.value = f"Cambio: ${cambio:.2f}"
            terminar_pedido_btn.disabled = False # Habilitar botón de terminar
            page.update()
        except ValueError:
            cambio_text.value = "Cambio: $0.00"
            terminar_pedido_btn.disabled = True # Deshabilitar botón de terminar si hay error
            page.update()
            pass

    def terminar_pedido_seleccionado(e):
        if not pedido_seleccionado_para_cobro:
            return
        try:
            # Cambiar estado del pedido seleccionado a 'Pagado'
            backend_service.actualizar_estado_pedido(pedido_seleccionado_para_cobro["id"], "Pagado")
            # Deseleccionar el pedido
            cancelar_seleccion_pedido(None)
            # Actualizar la lista general de pedidos
            on_update_ui()
        except Exception as ex:
            print(f"Error al terminar pedido: {ex}")

    def actualizar():
        try:
            pedidos = backend_service.obtener_pedidos_activos()
            lista_cuentas.controls.clear()
            for pedido in pedidos:
                # ✅ MOSTRAR SI ESTÁ LISTO, ENTREGADO (PAGADO generalmente no se muestra aquí para cobro)
                if pedido.get("estado") in ["Listo", "Entregado"] and pedido.get("items"):
                    item = crear_item_pedido_lista(pedido, backend_service, on_update_ui, page)
                    if item:
                        lista_cuentas.controls.append(item)
            page.update()
        except Exception as e:
            print(f"Error al cargar pedidos en vista de caja: {e}")

    def crear_item_pedido_lista(pedido, backend_service, on_update_ui, page):
        total_pedido = sum(item["precio"] for item in pedido["items"])
        origen = f"{obtener_titulo_pedido(pedido)} - {pedido.get('fecha_hora', 'Sin fecha')}"

        def cobrar_pedido_click(e):
            seleccionar_pedido_para_cobro(pedido)

        def eliminar_pedido(e):
            try:
                # Eliminar pedido del backend
                backend_service.eliminar_pedido(pedido["id"])
                on_update_ui() # Actualiza la UI general para que el pedido desaparezca de la lista
            except Exception as ex:
                print(f"Error al eliminar pedido: {ex}")

        return ft.Container(
            content=ft.Column([
                ft.Text(origen, size=20, weight=ft.FontWeight.BOLD),
                ft.Text(f"Estado: {pedido.get('estado', 'Pendiente')}", color=ft.Colors.BLUE_200),
                ft.Text(generar_resumen_pedido(pedido)),
                ft.Text(f"Total: ${total_pedido:.2f}", size=16, weight=ft.FontWeight.BOLD),
                ft.Row([
                    ft.ElevatedButton(
                        "Cobrar Pedido",
                        on_click=cobrar_pedido_click, # <-- Selecciona este pedido para cobro
                        style=ft.ButtonStyle(bgcolor=ft.Colors.AMBER_700, color=ft.Colors.WHITE)
                    ),
                    ft.ElevatedButton(
                        "Eliminar pedido",
                        on_click=eliminar_pedido,
                        style=ft.ButtonStyle(bgcolor=ft.Colors.RED_800, color=ft.Colors.WHITE),
                        tooltip="Eliminar pedido accidental"
                    )
                ])
            ]),
            bgcolor=ft.Colors.BLUE_GREY_900,
            padding=10,
            border_radius=10
        )

    # Vista principal
    vista = ft.Container(
        content=ft.Column([
            ft.Text("Cuentas por Cobrar", size=24, weight=ft.FontWeight.BOLD),
            # Sección para el pedido seleccionado para cobro
            ft.Container(
                content=ft.Column([
                    ft.Divider(),
                    ft.Text("Cobro de Pedido Seleccionado", size=18, weight=ft.FontWeight.BOLD),
                    ft.Row([pago_cliente, calcular_cambio_btn]),
                    cambio_text,
                    ft.Row([metodo_pago]),
                    ft.Row([terminar_pedido_btn, cancelar_cobro_btn]),
                    ft.Divider(),
                ]),
                bgcolor=ft.Colors.BLUE_GREY_800,
                padding=10,
                border_radius=10,
            ),
            # Lista de pedidos disponibles
            lista_cuentas
        ]),
        expand=True
    )
    vista.actualizar = actualizar
    return vista

# Función auxiliar para generar el resumen pedido (debe estar en caja_view.py si no está en un módulo compartido)
def generar_resumen_pedido(pedido):
    if not pedido.get("items"):
        return "Sin items."
    total = sum(item["precio"] for item in pedido["items"])
    items_str = "\n".join(f"- {item['nombre']} (${item['precio']:.2f})" for item in pedido["items"])
    titulo = obtener_titulo_pedido(pedido)
    return f"[{titulo}]\n{items_str}\nTotal: ${total:.2f}"

# Función auxiliar para obtener el título pedido (debe estar en caja_view.py si no está en un módulo compartido)
def obtener_titulo_pedido(pedido):
    if pedido.get("mesa_numero") == 99 and pedido.get("numero_app"):
        return f"Digital #{pedido['numero_app']:03d}"
    else:
        return f"Mesa {pedido['mesa_numero']}"