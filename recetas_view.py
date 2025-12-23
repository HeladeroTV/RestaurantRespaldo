# recetas_view.py
import flet as ft
from typing import List, Dict, Any

def crear_vista_recetas(recetas_service, menu_service, inventario_service, on_update_ui, page):
    # Campos de entrada para la receta
    nombre_plato_dropdown = ft.Dropdown(label="Plato del Menú", width=300)
    descripcion_input = ft.TextField(label="Descripción", multiline=True, width=300)
    instrucciones_input = ft.TextField(label="Instrucciones", multiline=True, width=300)

    # Selector de ingrediente y cantidad
    ingrediente_dropdown = ft.Dropdown(label="Ingrediente", width=250)
    cantidad_ingrediente_input = ft.TextField(label="Cantidad", width=100, input_filter=ft.NumbersOnlyInputFilter())

    # --- NUEVO: Dropdown para Unidad ---
    # Define las opciones como en configuraciones_view.py
    unidad_ingrediente_dropdown = ft.Dropdown(
        label="Unidad",
        options=[
            ft.dropdown.Option("unidad"),
            ft.dropdown.Option("kg"),
            ft.dropdown.Option("g"),
            ft.dropdown.Option("lt"),
            ft.dropdown.Option("ml"),
        ],
        value="unidad", # Valor por defecto
        width=150
    )
    # --- FIN NUEVO ---

    # Botón para agregar ingrediente a la lista local
    agregar_ingrediente_btn = ft.ElevatedButton(
        "Agregar Ingrediente",
        on_click=lambda e: agregar_ingrediente_a_lista(),
        style=ft.ButtonStyle(bgcolor=ft.Colors.AMBER_700, color=ft.Colors.WHITE)
    )

    # Lista visual de ingredientes para la receta actual (en memoria)
    lista_ingredientes = ft.Column(spacing=5)

    # Botón para crear la receta
    crear_receta_btn = ft.ElevatedButton(
        "Crear Receta",
        on_click=lambda e: crear_receta_click(),
        style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)
    )

    # Lista de recetas guardadas
    lista_recetas_guardadas = ft.Column(spacing=10)

    ingredientes_seleccionados = [] # Lista temporal para almacenar ingredientes antes de crear la receta

    def cargar_datos_iniciales():
        """Carga los platos del menú y los ingredientes del inventario en los dropdowns."""
        try:
            # Cargar platos del menú
            menu_items = menu_service.obtener_menu()
            nombre_plato_dropdown.options = [ft.dropdown.Option(item["nombre"]) for item in menu_items]
            nombre_plato_dropdown.value = menu_items[0]["nombre"] if menu_items else None

            # Cargar ingredientes del inventario
            inventario_items = inventario_service.obtener_inventario()
            ingrediente_dropdown.options = [ft.dropdown.Option(text=item["nombre"], key=str(item["id"])) for item in inventario_items]
            # No seleccionar ninguno por defecto

        except Exception as e:
            print(f"Error al cargar datos iniciales para recetas: {e}")

    # --- FUNCIÓN PARA ACTUALIZAR DATOS (SOLO INVENTARIO AHORA) ---
    def actualizar_datos():
        """Actualiza los ingredientes disponibles en el dropdown."""
        try:
            # Cargar ingredientes del inventario
            inventario_items = inventario_service.obtener_inventario()
            ingrediente_dropdown.options = [ft.dropdown.Option(text=item["nombre"], key=str(item["id"])) for item in inventario_items]
            # No seleccionar ninguno por defecto
            page.update() # Asegurar que la UI se actualice
            print(f"Dropdown de ingredientes actualizado con {len(inventario_items)} items.")
        except Exception as e:
            print(f"Error al actualizar datos de recetas: {e}")

    # --- FIN FUNCIÓN ---

    def agregar_ingrediente_a_lista():
        """Agrega el ingrediente seleccionado a la lista visual y a la lista temporal."""
        ing_id_str = ingrediente_dropdown.value
        cantidad_str = cantidad_ingrediente_input.value
        # --- OBTENER UNIDAD DEL DROPDOWN ---
        unidad = unidad_ingrediente_dropdown.value # Obtener valor del dropdown
        # --- FIN OBTENER UNIDAD ---

        if not ing_id_str or not cantidad_str:
            print("Debe seleccionar un ingrediente y especificar una cantidad.")
            return

        try:
            ing_id = int(ing_id_str)
            cantidad = float(cantidad_str)

            # Obtener el nombre del ingrediente para mostrarlo
            inventario_items = inventario_service.obtener_inventario()
            nombre_ing = next((item["nombre"] for item in inventario_items if item["id"] == ing_id), "Ingrediente No Encontrado")

            if nombre_ing == "Ingrediente No Encontrado":
                print(f"Ingrediente con ID {ing_id} no encontrado en el inventario.")
                return

            item_row = ft.Container(
                content=ft.Row([
                    ft.Text(f"{nombre_ing} - Cantidad: {cantidad} {unidad}"), # Mostrar el nombre y la unidad seleccionada
                    ft.IconButton(
                        icon=ft.Icons.DELETE,
                        on_click=lambda e, id_ing=ing_id: eliminar_ingrediente_de_lista(id_ing)
                    )
                ]),
                bgcolor=ft.Colors.BLUE_GREY_800,
                padding=5,
                border_radius=5
            )
            lista_ingredientes.controls.append(item_row)

            # Agregar a la lista temporal
            ingredientes_seleccionados.append({
                "ingrediente_id": ing_id,
                "cantidad_necesaria": cantidad,
                "unidad_medida_necesaria": unidad # ✅ USAR EL VALOR DEL DROPDOWN
            })

            # Limpiar campos de ingrediente
            ingrediente_dropdown.value = ""
            cantidad_ingrediente_input.value = ""
            # --- LIMPIAR EL DROPDOWN DE UNIDAD ---
            unidad_ingrediente_dropdown.value = "unidad" # Reiniciar a valor por defecto
            # --- FIN LIMPIAR EL DROPDOWN DE UNIDAD ---

            page.update()
        except ValueError:
            print("Cantidad debe ser un número.")
            pass

    def eliminar_ingrediente_de_lista(ing_id: int):
        """Elimina un ingrediente de la lista visual y de la lista temporal."""
        # Eliminar de la lista visual
        lista_ingredientes.controls = [
            c for c in lista_ingredientes.controls
            if int(c.content.controls[0].value.split(" - ")[0].split(" ID ")[-1]) != ing_id # Asumiendo que se guarda el ID en el texto
        ]
        # Corrección: Buscar por ID en la lista temporal
        global ingredientes_seleccionados
        ingredientes_seleccionados = [ing for ing in ingredientes_seleccionados if ing["ingrediente_id"] != ing_id]

        page.update()

    def crear_receta_click():
        """Crea la receta usando el servicio."""
        nombre_plato = nombre_plato_dropdown.value
        descripcion = descripcion_input.value
        instrucciones = instrucciones_input.value

        if not nombre_plato or not ingredientes_seleccionados:
            print("Debe seleccionar un plato y al menos un ingrediente.")
            return

        try:
            receta_creada = recetas_service.crear_receta(
                nombre_plato=nombre_plato,
                descripcion=descripcion,
                instrucciones=instrucciones,
                ingredientes=ingredientes_seleccionados
            )
            print(f"Receta '{nombre_plato}' creada exitosamente.")
            # Limpiar campos y lista
            descripcion_input.value = ""
            instrucciones_input.value = ""
            lista_ingredientes.controls.clear()
            ingredientes_seleccionados.clear() # Limpiar la lista temporal
            # Actualizar vistas
            actualizar_lista_recetas_guardadas()
            on_update_ui()
        except Exception as ex:
            print(f"Error al crear receta: {ex}")

    def actualizar_lista_recetas_guardadas():
        """Obtiene recetas del backend y actualiza la lista visual."""
        try:
            recetas = recetas_service.obtener_recetas()
            lista_recetas_guardadas.controls.clear()
            for receta in recetas:
                item_row = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(f"{receta['nombre_plato']}", size=18, weight=ft.FontWeight.BOLD),
                            ft.IconButton(
                                icon=ft.Icons.DELETE,
                                on_click=lambda e, nombre_plato=receta['nombre_plato']: eliminar_receta_click(nombre_plato),
                                tooltip="Eliminar receta",
                                icon_color=ft.Colors.RED_700
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Text(f"Descripción: {receta['descripcion']}", size=14),
                        ft.Text(f"Instrucciones: {receta['instrucciones']}", size=14),
                        ft.Text("Ingredientes:", size=14, weight=ft.FontWeight.BOLD),
                        ft.Column([
                            ft.Text(f"- {ing['nombre_ingrediente']}: {ing['cantidad_necesaria']} {ing['unidad_medida_necesaria']}")
                            for ing in receta['ingredientes']
                        ]),
                    ]),
                    bgcolor=ft.Colors.BLUE_GREY_900,
                    padding=10,
                    border_radius=10
                )
                lista_recetas_guardadas.controls.append(item_row)
            page.update()
        except Exception as e:
            print(f"Error al cargar recetas guardadas: {e}")

    def eliminar_receta_click(nombre_plato: str):
        """Elimina una receta usando el servicio."""
        try:
            recetas_service.eliminar_receta(nombre_plato)
            print(f"Receta '{nombre_plato}' eliminada exitosamente.")
            actualizar_lista_recetas_guardadas()
            on_update_ui() # Actualiza otras vistas si es necesario
        except Exception as ex:
            print(f"Error al eliminar receta: {ex}")


    # Cargar datos iniciales al iniciar la vista
    cargar_datos_iniciales()
    # Cargar recetas guardadas
    actualizar_lista_recetas_guardadas()

    vista = ft.Container(
        content=ft.Column([
            ft.Text("Gestión de Recetas", size=24, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Text("Crear Nueva Receta", size=18, weight=ft.FontWeight.BOLD),
            nombre_plato_dropdown,
            descripcion_input,
            instrucciones_input,
            ft.Divider(),
            ft.Text("Agregar Ingredientes", size=16, weight=ft.FontWeight.BOLD),
            ft.Row([
                ingrediente_dropdown,
                cantidad_ingrediente_input,
                # --- CAMBIAR A DROPDOWN ---
                unidad_ingrediente_dropdown, # ✅ USAR EL DROPDOWN
                # --- FIN CAMBIAR A DROPDOWN ---
                agregar_ingrediente_btn
            ]),
            ft.Container(
                content=lista_ingredientes,
                bgcolor=ft.Colors.BLUE_GREY_800,
                padding=10,
                border_radius=5
            ),
            crear_receta_btn,
            ft.Divider(),
            ft.Text("Recetas Guardadas", size=18, weight=ft.FontWeight.BOLD),
            lista_recetas_guardadas  # ✅ LISTA DE CONFIGURACIONES
        ]),
        padding=20,
        expand=True
    )

    # vista.cargar_clientes_mesas = cargar_clientes_mesas # Si decides usarlo
    return vista