# configuraciones_view.py
import flet as ft
from typing import List, Dict, Any

def crear_vista_configuraciones(config_service, inventory_service, on_update_ui, page):  # ✅ AGREGAR INVENTORY_SERVICE
    # Campos de entrada
    nombre_input = ft.TextField(label="Nombre de la configuración", width=300)
    descripcion_input = ft.TextField(label="Descripción", multiline=True, width=300)

    # Campo para nombre de ingrediente
    nombre_ingrediente_input = ft.TextField(label="Nombre del ingrediente", width=200)

    # Campo para cantidad de ingrediente
    cantidad_input = ft.TextField(
        label="Cantidad",
        width=200,
        input_filter=ft.NumbersOnlyInputFilter()
    )

    # --- NUEVO: Campo para umbral de ingrediente ---
    umbral_input = ft.TextField(
        label="Umbral Alerta",
        width=200,
        input_filter=ft.NumbersOnlyInputFilter(), # Asumiendo que el umbral es numérico
        value="5" # Valor por defecto
    )
    # --- FIN NUEVO ---

    # Dropdown para unidad
    unidad_dropdown = ft.Dropdown(
        label="Unidad",
        options=[
            ft.dropdown.Option("unidad"),
            ft.dropdown.Option("kg"),
            ft.dropdown.Option("g"),
            ft.dropdown.Option("lt"),
            ft.dropdown.Option("ml"),
        ],
        value="unidad",
        width=150
    )

    # Lista de ingredientes de la configuración
    lista_ingredientes = ft.Column(spacing=5)

    # Lista de configuraciones guardadas
    lista_configuraciones_guardadas = ft.Column(spacing=10)

    # Lista temporal para almacenar ingredientes antes de crear la configuración
    ingredientes_seleccionados = [] # Lista de diccionarios con detalles del ingrediente

    def aplicar_configuracion_click(config_id: int):
        try:
            configs = config_service.obtener_configuraciones()
            config = next((c for c in configs if c["id"] == config_id), None)
            if not config:
                return

            # ✅ APLICAR INGREDIENTES AL INVENTARIO DIRECTAMENTE
            for ing in config["ingredientes"]:
                try:
                    # ✅ AGREGAR INGREDIENTE AL INVENTARIO
                    # Ahora pasamos el umbral personalizado del ingrediente de la configuración
                    inventory_service.agregar_item_inventario(
                        nombre=ing["nombre"], # El nombre ya debería estar capitalizado
                        cantidad=ing["cantidad"],
                        unidad=ing["unidad"],
                        # --- PASAR EL UMBRAL DEL INGREDIENTE DE LA CONFIGURACIÓN ---
                        cantidad_minima_alerta=ing.get("umbral_alerta", 5.0) # Usar get para evitar KeyError si no existe
                        # --- FIN PASAR EL UMBRAL ---
                    )
                except Exception as e:
                    print(f"Error al agregar ingrediente {ing['nombre']}: {e}")

            on_update_ui()
        except Exception as ex:
            print(f"Error al aplicar configuración: {ex}")

    def eliminar_configuracion_click(config_id: int):
        try:
            config_service.eliminar_configuracion(config_id)
            actualizar_lista_configuraciones_guardadas()  # ✅ ACTUALIZAR LISTA
            on_update_ui()
        except Exception as ex:
            print(f"Error al eliminar configuración: {ex}")

    def agregar_ingrediente_click(e):
        nombre_ing = nombre_ingrediente_input.value
        cantidad = cantidad_input.value
        unidad = unidad_dropdown.value
        # --- OBTENER EL UMBRAL DEL INPUT ---
        umbral_str = umbral_input.value
        # --- FIN OBTENER EL UMBRAL ---

        if not nombre_ing or not cantidad or not umbral_str: # Verificar que todos los campos tengan valor
            return

        try:
            # Convertir valores
            cantidad_int = int(cantidad)
            umbral_float = float(umbral_str) # Convertir umbral a float

            # Capitalizar el nombre del ingrediente
            nombre_ing_capitalizado = nombre_ing.strip().capitalize()

            item_row = ft.Container(
                content=ft.Row([
                    ft.Text(f"{nombre_ing_capitalizado} - {cantidad_int} {unidad} (Umbral: {umbral_float})"), # Mostrar el nombre capitalizado, cantidad, unidad y umbral
                    ft.IconButton(
                        icon=ft.Icons.DELETE,
                        on_click=lambda e, nombre=nombre_ing_capitalizado: eliminar_ingrediente_click(nombre) # Pasar el nombre capitalizado
                    )
                ]),
                bgcolor=ft.Colors.BLUE_GREY_800,
                padding=5,
                border_radius=5
            )
            lista_ingredientes.controls.append(item_row)

            # Agregar a la lista temporal incluyendo el umbral
            ingredientes_seleccionados.append({
                "nombre": nombre_ing_capitalizado, # ✅ GUARDAR CON NOMBRE CAPITALIZADO
                "cantidad": cantidad_int,
                "unidad": unidad,
                # --- AÑADIR EL UMBRAL ---
                "umbral_alerta": umbral_float # Añadir el umbral a la lista temporal
                # --- FIN AÑADIR EL UMBRAL ---
            })

            # Limpiar campos de entrada de ingrediente
            nombre_ingrediente_input.value = ""
            cantidad_input.value = ""
            # --- LIMPIAR EL INPUT DEL UMBRAL ---
            umbral_input.value = "5" # Reiniciar al valor por defecto
            # --- FIN LIMPIAR EL INPUT DEL UMBRAL ---
            unidad_dropdown.value = "unidad" # Reiniciar unidad si es necesario

            page.update()

        except ValueError:
            print("Cantidad y umbral deben ser números válidos.")
            pass # Opcional: Mostrar un mensaje de error al usuario

    def eliminar_ingrediente_click(nombre_ing: str):
        # Eliminar de la lista visual
        lista_ingredientes.controls = [
            c for c in lista_ingredientes.controls
            if not c.content.controls[0].value.startswith(f"{nombre_ing} -") # Ajustar la comparación
        ]
        # Eliminar de la lista temporal
        global ingredientes_seleccionados
        ingredientes_seleccionados = [ing for ing in ingredientes_seleccionados if ing["nombre"] != nombre_ing]

        page.update()

    def crear_configuracion_click(e):
        nombre = nombre_input.value
        descripcion = descripcion_input.value

        # ✅ VALIDACIÓN: Verificar si la lista de ingredientes está vacía
        if not ingredientes_seleccionados:
            print("No se puede crear la configuración sin ingredientes.")
            # Opcional: Mostrar un mensaje en la interfaz
            def cerrar_alerta(e):
                page.close(dlg_error)

            dlg_error = ft.AlertDialog(
                title=ft.Text("Error"),
                content=ft.Text("No se puede crear la configuración sin ingredientes."),
                actions=[ft.TextButton("Aceptar", on_click=cerrar_alerta)],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.dialog = dlg_error
            dlg_error.open = True
            page.update()
            return # Salir de la función si no hay ingredientes

        if not nombre:
            return

        try:
            # ✅ MODIFICAR EL SERVICIO PARA ENVIAR NOMBRES CAPITALIZADOS Y UMBRALES
            # La lista 'ingredientes_seleccionados' ya contiene los nombres capitalizados y los umbrales
            config_service.crear_configuracion(nombre, descripcion, ingredientes_seleccionados)
            nombre_input.value = ""
            descripcion_input.value = ""
            nombre_ingrediente_input.value = ""
            cantidad_input.value = ""
            # --- REINICIAR EL INPUT DEL UMBRAL ---
            umbral_input.value = "5" # Reiniciar al valor por defecto
            # --- FIN REINICIAR EL INPUT DEL UMBRAL ---
            unidad_dropdown.value = "unidad"
            lista_ingredientes.controls.clear() # Limpiar la lista visual
            ingredientes_seleccionados.clear() # Limpiar la lista temporal
            actualizar_lista_configuraciones_guardadas()  # ✅ ACTUALIZAR LISTA
            on_update_ui()
        except Exception as ex:
            print(f"Error al crear configuración: {ex}")

    def actualizar_lista_configuraciones_guardadas():
        try:
            configs = config_service.obtener_configuraciones()
            lista_configuraciones_guardadas.controls.clear()
            for config in configs:
                item_row = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(f"{config['nombre']}", size=18, weight=ft.FontWeight.BOLD),
                            ft.IconButton(
                                icon=ft.Icons.DELETE,
                                on_click=lambda e, id=config['id']: eliminar_configuracion_click(id),
                                tooltip="Eliminar configuración",
                                icon_color=ft.Colors.RED_700
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Text(f"Descripción: {config['descripcion']}", size=14),
                        ft.Text("Ingredientes:", size=14, weight=ft.FontWeight.BOLD),
                        ft.Column([
                            # ft.Text(f"- {ing['nombre']}: {ing['cantidad']} {ing['unidad']}") # Mostrar nombre capitalizado
                            # --- MOSTRAR TAMBIÉN EL UMBRAL ---
                            ft.Text(f"- {ing['nombre']}: {ing['cantidad']} {ing['unidad']} (Umbral: {ing.get('umbral_alerta', 5.0)})") # Mostrar nombre, cantidad, unidad y umbral
                            # --- FIN MOSTRAR UMBRAL ---
                            for ing in config['ingredientes']
                        ]),
                        ft.ElevatedButton(
                            "Aplicar configuración",
                            on_click=lambda e, id=config['id']: aplicar_configuracion_click(id),
                            style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)
                        )
                    ]),
                    bgcolor=ft.Colors.BLUE_GREY_900,
                    padding=10,
                    border_radius=10
                )
                lista_configuraciones_guardadas.controls.append(item_row)
            page.update()
        except Exception as e:
            print(f"Error al cargar configuraciones: {e}")

    # ✅ CARGAR CONFIGURACIONES AL INICIAR
    actualizar_lista_configuraciones_guardadas()

    vista = ft.Container(
        content=ft.Column([
            ft.Text("Configuraciones", size=24, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Text("Crear nueva configuración", size=18, weight=ft.FontWeight.BOLD),
            nombre_input,
            descripcion_input,
            ft.Divider(),
            ft.Text("Agregar ingredientes", size=16, weight=ft.FontWeight.BOLD),
            ft.Row([
                nombre_ingrediente_input,
                cantidad_input,
                # --- AÑADIR EL INPUT DEL UMBRAL ---
                umbral_input, # Añadir el campo de umbral
                # --- FIN AÑADIR EL INPUT DEL UMBRAL ---
                unidad_dropdown,
                ft.ElevatedButton(
                    "Agregar ingrediente",
                    on_click=agregar_ingrediente_click,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.AMBER_700, color=ft.Colors.WHITE)
                )
            ]),
            ft.Container(
                content=lista_ingredientes,
                bgcolor=ft.Colors.BLUE_GREY_800,
                padding=10,
                border_radius=5
            ),
            ft.ElevatedButton(
                "Crear configuración",
                on_click=crear_configuracion_click,
                style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)
            ),
            ft.Divider(),
            ft.Text("Configuraciones guardadas", size=18, weight=ft.FontWeight.BOLD),
            lista_configuraciones_guardadas  # ✅ LISTA DE CONFIGURACIONES
        ]),
        padding=20,
        expand=True
    )

    vista.actualizar_lista_configuraciones_guardadas = actualizar_lista_configuraciones_guardadas  # ✅ AGREGAR FUNCIÓN
    return vista