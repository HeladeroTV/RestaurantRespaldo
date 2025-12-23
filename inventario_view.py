# inventario_view.py
import flet as ft
from typing import List, Dict, Any
import threading
import time
import requests

def crear_vista_inventario(inventory_service, on_update_ui, page):
    # Campo para mostrar alerta de bajo umbral
    alerta_umbral = ft.Container(expand=False) # Contenedor para la alerta

    # Campos de entrada para agregar nuevo ítem
    nombre_input = ft.TextField(label="Nombre del producto", width=300)
    cantidad_input = ft.TextField(
        label="Cantidad disponible",
        width=300,
        input_filter=ft.NumbersOnlyInputFilter()
    )
    # --- NUEVO: Dropdown para Unidad (ya implementado anteriormente) ---
    unidad_dropdown = ft.Dropdown(
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
    # --- NUEVO: Campo para Umbral Personalizado ---
    umbral_input = ft.TextField(
        label="Umbral de alerta",
        width=150,
        input_filter=ft.NumbersOnlyInputFilter(),
        value="5" # Valor por defecto
    )
    # --- FIN NUEVOS CAMPOS ---

    # Lista de inventario
    lista_inventario = ft.ListView(
        expand=1,
        spacing=10,
        padding=20,
        auto_scroll=True,
    )

    # Variable para rastrear si hay un campo de cantidad en edición
    campo_en_edicion_id = None
    # Variable para rastrear si hay un campo de umbral en edición (opcional, similar a cantidad)
    campo_umbral_en_edicion_id = None

    # FUNCIÓN PARA VERIFICAR ALERTAS PERIÓDICAMENTE
    def verificar_alertas_periodicamente():
        while True:
            try:
                items = inventory_service.obtener_inventario()
                
                # --- VERIFICAR ALERTAS DE INGREDIENTES BAJOS - USAR UMBRAL PERSONALIZADO ---
                # umbral_bajo = 5 # UMBRAL PARA AVISAR (PUEDES CAMBIAR ESTE VALOR) # <-- COMENTAR ESTA LINEA
                # ingredientes_bajos = [item for item in items if item['cantidad_disponible'] <= umbral_bajo] # <-- COMENTAR ESTA LINEA
                # Verificar usando el umbral personalizado de cada ítem
                ingredientes_bajos = [item for item in items if item['cantidad_disponible'] <= item['cantidad_minima_alerta']]
                # --- FIN VERIFICACIÓN ---

                # ACTUALIZAR CONTENIDO DE ALERTA
                if ingredientes_bajos:
                    nombres_bajos = ", ".join([item['nombre'] for item in ingredientes_bajos])
                    alerta_umbral.content = ft.Row([
                        ft.Icon(ft.Icons.WARNING, color=ft.Colors.WHITE),
                        ft.Text(f"⚠️ Alerta de Inventario: {nombres_bajos} están por debajo del umbral personalizado", color=ft.Colors.WHITE)
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER)
                    alerta_umbral.bgcolor = ft.Colors.RED_700
                    alerta_umbral.padding = 10
                    alerta_umbral.border_radius = 5
                    alerta_umbral.visible = True
                else:
                    alerta_umbral.visible = False # Ocultar si no hay alertas
                # --- FIN VERIFICACIÓN ---
                
            except Exception as e:
                print(f"Error en verificación periódica: {e}")
                time.sleep(30) # ESPERAR 30 SEGUNDOS ANTES DE REINTENTAR

    # INICIAR VERIFICACIÓN PERIÓDICA EN UN HILO SEPARADO
    hilo_verificacion = threading.Thread(target=verificar_alertas_periodicamente, daemon=True)
    hilo_verificacion.start()

    def actualizar_lista():
        nonlocal campo_en_edicion_id, campo_umbral_en_edicion_id # Acceder a las variables del scope superior
        # Si hay un campo en edición (cantidad o umbral), NO actualizar la lista para no perder el foco/valor
        if campo_en_edicion_id is not None or campo_umbral_en_edicion_id is not None:
            print(f"No se actualiza la lista de inventario porque un campo está en edición.")
            return # Salir sin hacer nada

        print("Actualizando lista de inventario...") # Mensaje de depuración
        try:
            items = inventory_service.obtener_inventario()
            
            # --- VERIFICAR ALERTAS DE INGREDIENTES BAJOS - USAR UMBRAL PERSONALIZADO ---
            # umbral_bajo = 5 # UMBRAL PARA AVISAR (PUEDES CAMBIAR ESTE VALOR) # <-- COMENTAR ESTA LINEA
            # ingredientes_bajos = [item for item in items if item['cantidad_disponible'] <= umbral_bajo] # <-- COMENTAR ESTA LINEA
            # Verificar usando el umbral personalizado de cada ítem
            ingredientes_bajos = [item for item in items if item['cantidad_disponible'] <= item['cantidad_minima_alerta']]
            # --- FIN VERIFICACIÓN ---

            # ACTUALIZAR CONTENIDO DE ALERTA
            if ingredientes_bajos:
                nombres_bajos = ", ".join([item['nombre'] for item in ingredientes_bajos])
                alerta_umbral.content = ft.Row([
                    ft.Icon(ft.Icons.WARNING, color=ft.Colors.WHITE),
                    ft.Text(f"⚠️ Alerta de Inventario: {nombres_bajos} están por debajo del umbral personalizado", color=ft.Colors.WHITE)
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER)
                alerta_umbral.bgcolor = ft.Colors.RED_700
                alerta_umbral.padding = 10
                alerta_umbral.border_radius = 5
                alerta_umbral.visible = True
            else:
                alerta_umbral.visible = False # Ocultar si no hay alertas
            # --- FIN VERIFICACIÓN ---
            
            # Limpiar la lista visual antes de reconstruir
            lista_inventario.controls.clear()

            for item in items:
                item_id = item['id']
                # Campo de texto para ingresar la nueva cantidad
                nuevo_cantidad_input = ft.TextField(
                    label="Nueva Cantidad",
                    value=str(item['cantidad_disponible']), # Valor inicial es la cantidad actual
                    width=120,
                    input_filter=ft.NumbersOnlyInputFilter(),
                    hint_text=f"Actual: {item['cantidad_disponible']}",
                    data=item_id # Almacenar ID para identificarlo
                )
                # --- NUEVO: Campo de texto para ingresar el nuevo umbral ---
                nuevo_umbral_input = ft.TextField(
                    label="Umbral Alerta",
                    value=str(item['cantidad_minima_alerta']), # Valor inicial es el umbral actual
                    width=120,
                    input_filter=ft.NumbersOnlyInputFilter(), # Asumiendo que el umbral es numérico
                    hint_text=f"Actual: {item['cantidad_minima_alerta']}",
                    data=item_id # Almacenar ID para identificarlo
                )
                # --- FIN NUEVO ---

                # Función para manejar el foco (inicio de edición) - Cantidad
                def on_focus_cantidad(e, item_id=item_id):
                    nonlocal campo_en_edicion_id
                    campo_en_edicion_id = item_id
                    print(f"Campo cantidad {item_id} en edición.")

                # Función para manejar la pérdida de foco (fin de edición) - Cantidad
                def on_blur_cantidad(e, item_id=item_id):
                    nonlocal campo_en_edicion_id
                    if campo_en_edicion_id == item_id:
                        campo_en_edicion_id = None
                        print(f"Campo cantidad {item_id} dejó de estar en edición.")

                # Función para manejar el foco (inicio de edición) - Umbral
                def on_focus_umbral(e, item_id=item_id):
                    nonlocal campo_umbral_en_edicion_id
                    campo_umbral_en_edicion_id = item_id
                    print(f"Campo umbral {item_id} en edición.")

                # Función para manejar la pérdida de foco (fin de edición) - Umbral
                def on_blur_umbral(e, item_id=item_id):
                    nonlocal campo_umbral_en_edicion_id
                    if campo_umbral_en_edicion_id == item_id:
                        campo_umbral_en_edicion_id = None
                        print(f"Campo umbral {item_id} dejó de estar en edición.")

                # Asignar las funciones de foco
                nuevo_cantidad_input.on_focus = lambda e, id=item_id: on_focus_cantidad(e, id)
                nuevo_cantidad_input.on_blur = lambda e, id=item_id: on_blur_cantidad(e, id)
                # --- AÑADIR FUNCIONES DE FOCO PARA EL UMBRAL ---
                nuevo_umbral_input.on_focus = lambda e, id=item_id: on_focus_umbral(e, id)
                nuevo_umbral_input.on_blur = lambda e, id=item_id: on_blur_umbral(e, id)
                # --- FIN AÑADIR FUNCIONES DE FOCO ---

                # Botón Actualizar (ahora actualiza cantidad Y umbral)
                boton_actualizar = ft.ElevatedButton(
                    text="Actualizar",
                    on_click=lambda e, id=item_id, input_cantidad=nuevo_cantidad_input, input_umbral=nuevo_umbral_input, unidad_original=item['unidad_medida']: actualizar_ingrediente_y_umbral(id, input_cantidad, input_umbral, unidad_original),
                    style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE)
                )

                # Botón Eliminar
                boton_eliminar = ft.ElevatedButton(
                    text="Eliminar",
                    # --- MODIFICACIÓN: Permitir eliminar si cantidad_disponible <= 0 ---
                    # on_click=lambda e, id=item_id: eliminar_item_click(id) # <-- LÍNEA ANTERIOR
                    on_click=lambda e, id=item_id: eliminar_item_click(id), # <-- LÍNEA NUEVA (mismo comportamiento, pero revisamos la lógica en eliminar_item_click)
                    style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE)
                )

                # No se crea ningún campo de texto ni botón para editar cantidad
                # Solo se muestran los datos del ítem, el campo de texto para la nueva cantidad y los botones de eliminar y actualizar
                item_row = ft.Container(
                    content=ft.Column([
                        ft.Text(f"{item['nombre']}", size=18, weight=ft.FontWeight.BOLD),
                        ft.Text(f"Cantidad: {item['cantidad_disponible']} {item['unidad_medida']}", size=14),
                        ft.Text(f"Umbral Alerta: {item['cantidad_minima_alerta']}", size=14), # Mostrar umbral actual
                        ft.Text(f"Registrado: {item['fecha_registro']}", size=12, color=ft.Colors.GREY_500),
                        ft.Row([
                            nuevo_cantidad_input, # Campo de texto para nueva cantidad
                            nuevo_umbral_input,   # Campo de texto para nuevo umbral
                            boton_actualizar,      # Botón Actualizar (cantidad y umbral)
                            boton_eliminar         # Botón Eliminar
                        ])
                    ]),
                    bgcolor=ft.Colors.BLUE_GREY_900,
                    padding=10,
                    border_radius=10
                )
                lista_inventario.controls.append(item_row)
            page.update()
        except Exception as e:
            print(f"Error al cargar inventario: {e}")
            alerta_umbral.visible = False # Asegurar que no se muestre alerta si hay error al cargar
            page.update()

    # --- FUNCIÓN: actualizar_ingrediente_y_umbral ---
    # Actualiza la cantidad Y el umbral de un ingrediente específico.
    def actualizar_ingrediente_y_umbral(item_id: int, input_cantidad: ft.TextField, input_umbral: ft.TextField, unidad_original: str):
        """Actualiza la cantidad y el umbral de un ingrediente."""
        # Asegurarse de que los campos no estén en edición antes de tomar su valor
        # (esto puede no ser necesario si se maneja bien el foco)
        nonlocal campo_en_edicion_id, campo_umbral_en_edicion_id
        if campo_en_edicion_id == item_id or campo_umbral_en_edicion_id == item_id:
             # Opcional: Forzar la pérdida de foco antes de leer el valor
             # input_cantidad.blur() # Flet no tiene un blur() directo en el control aquí
             # Es mejor dejar que el usuario mueva el foco manualmente o use on_change
             # para capturar el valor antes de que se refresque la UI.
             # Para esta solución, asumimos que si se presiona "Actualizar",
             # el usuario ya ha terminado de escribir y movido el foco o presionado enter (si aplica).
             # Actualizamos el valor del backend con el del campo de texto.
             pass # No hacer nada especial aquí, solo leer el valor del campo

        try:
            nueva_cantidad_str = input_cantidad.value.strip()
            nuevo_umbral_str = input_umbral.value.strip() # Obtener valor del campo de umbral
            if not nueva_cantidad_str or not nuevo_umbral_str: # Verificar que ambos campos tengan valor
                print("Ingrese valores válidos para cantidad y umbral.")
                return
            nueva_cantidad = int(nueva_cantidad_str)
            nuevo_umbral = float(nuevo_umbral_str) # Convertir umbral a float
            if nueva_cantidad < 0: # Permitir cero para "agotado"
                print("La cantidad no puede ser negativa.")
                return
            if nuevo_umbral < 0: # Opcional: Permitir umbral cero o negativo
                print("El umbral no puede ser negativo.") # O permitirlo según lógica de negocio
                return # Quitar esta línea si se permite umbral <= 0

            # Actualizar el ítem en el backend (cantidad, unidad y umbral)
            inventory_service.actualizar_item_inventario(item_id, nueva_cantidad, unidad=unidad_original, cantidad_minima_alerta=nuevo_umbral)

            # Limpiar los indicadores de edición si es necesario
            if campo_en_edicion_id == item_id:
                campo_en_edicion_id = None
            if campo_umbral_en_edicion_id == item_id:
                campo_umbral_en_edicion_id = None

            # Actualizar la UI general
            on_update_ui() # Esto llamará a actualizar_lista
        except ValueError:
            print("Cantidad y umbral deben ser números válidos.")
        except Exception as ex:
            print(f"Error al actualizar ítem: {ex}")

    def agregar_item_click(e):
        nombre = nombre_input.value
        cantidad = cantidad_input.value
        unidad = unidad_dropdown.value
        # --- OBTENER UMBRAL DEL CAMPO ---
        umbral_str = umbral_input.value
        # --- FIN OBTENER UMBRAL ---
        if not nombre or not cantidad or not umbral_str: # Verificar que todos los campos tengan valor
            return

        try:
            # Transformar el nombre: primera letra mayúscula, resto minúsculas
            nombre_formateado = nombre.strip().capitalize()
            cantidad_int = int(cantidad)
            umbral_float = float(umbral_str) # Convertir umbral a float
            # Pasar el umbral personalizado al servicio
            inventory_service.agregar_item_inventario(nombre_formateado, cantidad_int, unidad, cantidad_minima_alerta=umbral_float)
            nombre_input.value = ""
            cantidad_input.value = ""
            unidad_dropdown.value = "unidad" # Reiniciar unidad si es necesario
            # --- REINICIAR EL UMBRAL ---
            umbral_input.value = "5" # Reiniciar al valor por defecto
            # --- FIN REINICIAR EL UMBRAL ---
            on_update_ui() # Actualiza toda la UI, incluyendo inventario
        except ValueError:
            print("Cantidad y umbral deben ser números válidos.")
        except Exception as ex:
            print(f"Error al agregar ítem: {ex}")

    def eliminar_item_click(item_id: int):
        try:
            # --- MODIFICACIÓN: Obtener el ítem antes de eliminar para verificar la cantidad ---
            items = inventory_service.obtener_inventario()
            item_a_eliminar = next((item for item in items if item['id'] == item_id), None)
            if not item_a_eliminar:
                print(f"Ítem con ID {item_id} no encontrado.")
                return

            # --- CHECK REMOVED: Allow deletion regardless of stock ---
            # (Previously checked if item_a_eliminar['cantidad_disponible'] > 0)
            pass
            # --- FIN CHECK REMOVED ---

            inventory_service.eliminar_item_inventario(item_id)
            on_update_ui() # Actualiza toda la UI, incluyendo inventario
        except requests.exceptions.HTTPError as http_err:
            if http_err.response.status_code == 400:
                # Mostrar mensaje de error específico del backend
                print(f"Error al eliminar ítem: {http_err.response.text}")
                # Mostrar una alerta en la interfaz de Flet
                def cerrar_alerta(e):
                    page.close(dlg_error)
                
                dlg_error = ft.AlertDialog(
                    title=ft.Text("No se puede eliminar"),
                    content=ft.Text(http_err.response.text), # Muestra el mensaje del backend
                    actions=[ft.TextButton("Aceptar", on_click=cerrar_alerta)],
                    actions_alignment=ft.MainAxisAlignment.END,
                )
                page.dialog = dlg_error
                dlg_error.open = True
                page.update()
            else:
                # Otro error HTTP (como 500)
                print(f"Error HTTP inesperado al eliminar ítem: {http_err}")
                # Opcional: Mostrar una alerta genérica para otros errores
                def cerrar_alerta_gen(e):
                    page.close(dlg_error_gen)
                
                dlg_error_gen = ft.AlertDialog(
                    title=ft.Text("Error"),
                    content=ft.Text(f"Error inesperado al eliminar: {http_err.response.text}"),
                    actions=[ft.TextButton("Aceptar", on_click=cerrar_alerta_gen)],
                    actions_alignment=ft.MainAxisAlignment.END,
                )
                page.dialog = dlg_error_gen
                dlg_error_gen.open = True
                page.update()
        except Exception as ex:
            print(f"Error inesperado al eliminar ítem: {ex}")
            # Opcional: Mostrar una alerta para errores no HTTP
            def cerrar_alerta_ex(e):
                page.close(dlg_error_ex)
            
            dlg_error_ex = ft.AlertDialog(
                title=ft.Text("Error"),
                content=ft.Text(f"Error inesperado: {str(ex)}"),
                actions=[ft.TextButton("Aceptar", on_click=cerrar_alerta_ex)],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.dialog = dlg_error_ex
            dlg_error_ex.open = True
            page.update()

    vista = ft.Container(
        content=ft.Column([
            alerta_umbral, # <-- AÑADIR EL CONTENADOR DE ALERTA AL PRINCIPIO
            ft.Divider(),
            ft.Text("Agregar nuevo ítem", size=18, weight=ft.FontWeight.BOLD),
            nombre_input,
            cantidad_input,
            # --- AÑADIR DROPDOWN DE UNIDAD Y CAMPO DE UMBRAL ---
            ft.Row([unidad_dropdown, umbral_input]), # Agrupar unidad y umbral
            # --- FIN AÑADIR ---
            ft.ElevatedButton(
                "Agregar ítem",
                on_click=agregar_item_click,
                style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)
            ),
            ft.Divider(),
            ft.Text("Inventario actual", size=18, weight=ft.FontWeight.BOLD),
            lista_inventario
        ]),
        padding=20,
        expand=True
    )
    vista.campo_en_edicion_id = campo_en_edicion_id
    vista.campo_umbral_en_edicion_id = campo_umbral_en_edicion_id # Opcional: si necesitas acceder desde fuera
    vista.actualizar_lista = actualizar_lista
    return vista