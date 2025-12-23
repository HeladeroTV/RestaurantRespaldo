# reservas_view.py
import flet as ft
from typing import List, Dict, Any
from datetime import datetime, timedelta

def crear_vista_reservas(reservas_service, clientes_service, mesas_service, on_update_ui, page):
    # DatePicker para seleccionar la fecha de las reservas
    fecha_reservas_picker = ft.DatePicker(
        on_change=lambda e: actualizar_reservas_fecha(None)
    )
    fecha_reservas_button = ft.ElevatedButton(
        "Filtrar por Fecha",
        icon=ft.Icons.CALENDAR_TODAY,
        on_click=lambda _: page.open(fecha_reservas_picker)
    )
    fecha_reservas_text = ft.Text("Fecha: Hoy", size=16)

    # Dropdown para seleccionar cliente (solo clientes existentes) - CORREGIDO
    cliente_dropdown = ft.Dropdown(label="Cliente", width=300)

    # Dropdown para seleccionar la mesa (1 a 6)
    mesa_dropdown = ft.Dropdown(
        label="Mesa",
        options=[ft.dropdown.Option(str(i)) for i in range(1, 7)], # Opciones 1 a 6
        width=200
    )

    hora_inicio = ft.TextField(label="Hora Inicio (HH:MM)", width=150)
    duracion_horas = ft.TextField(label="Duración (Horas)", width=150, value="1")

    # Lista de reservas
    lista_reservas = ft.ListView(
        expand=1,
        spacing=10,
        padding=20,
        auto_scroll=True,
    )

    def cargar_clientes():
        """Carga la lista de clientes en el dropdown."""
        try:
            clientes = clientes_service.obtener_clientes()
            # CORREGIDO: Usar text=c["nombre"] para mostrar el nombre, y key=str(c["id"]) para el ID interno
            cliente_dropdown.options = [ft.dropdown.Option(text=c["nombre"], key=str(c["id"])) for c in clientes]
            page.update()
        except Exception as e:
            print(f"Error al cargar clientes: {e}")
            # CORREGIDO: Usar text= para el mensaje de error, y key= para un identificador único
            cliente_dropdown.options = [ft.dropdown.Option(text="Error al cargar clientes", key="-1")]


    def actualizar_reservas_fecha(e):
        try:
            fecha_str = fecha_reservas_text.value.split(": ")[1]
            if fecha_str == "Hoy":
                fecha = datetime.now().strftime("%Y-%m-%d")
            else:
                fecha = fecha_str
            # Asumiendo que el servicio maneja la fecha
            reservas = reservas_service.obtener_reservas(fecha=fecha)
            lista_reservas.controls.clear()
            for reserva in reservas:
                origen = f"Mesa {reserva['mesa_numero']} - {reserva['cliente_nombre']}"
                hora_inicio_str = reserva['fecha_hora_inicio'].split(" ")[1][:5] # HH:MM
                hora_fin_str = reserva['fecha_hora_fin'].split(" ")[1][:5] if reserva.get('fecha_hora_fin') else "N/A"
                item_row = ft.Container(
                    content=ft.Column([
                        ft.Text(origen, size=18, weight=ft.FontWeight.BOLD),
                        ft.Text(f"Horario: {hora_inicio_str} - {hora_fin_str}", size=14),
                        ft.ElevatedButton(
                            "Cancelar Reserva",
                            on_click=lambda e, id=reserva['id']: cancelar_reserva_click(id),
                            style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE)
                        )
                    ]),
                    bgcolor=ft.Colors.BLUE_GREY_900,
                    padding=10,
                    border_radius=10
                )
                lista_reservas.controls.append(item_row)
            page.update()
        except Exception as e:
            print(f"Error al cargar reservas: {e}")

    def crear_reserva_click(e):
        # CORREGIDO: Obtener la KEY del cliente seleccionado, no el texto
        cliente_id_str = cliente_dropdown.value # Esto obtiene el 'key' del Option seleccionado

        mesa_numero_str = mesa_dropdown.value # Obtener número de mesa del dropdown

        # CORREGIDO: Verificar si la KEY es None o el valor de error
        if not cliente_id_str or cliente_id_str == "-1" or not mesa_numero_str:
            print("Cliente y número de mesa son requeridos.")
            return # Salir si no hay cliente o mesa seleccionados

        try:
            # CORREGIDO: Convertir la KEY (string) a ID (int)
            cliente_id = int(cliente_id_str)
            print(f"Usando cliente con ID: {cliente_id}")

            # CORREGIDO: No es necesario buscar en la lista de clientes_existentes aquí
            # ya que el ID lo obtuvimos directamente del key del dropdown.
            # Si se quisiera mostrar el nombre en un mensaje, se podría hacer una
            # pequeña búsqueda local o asumir que el backend validará el ID.
            clientes_existentes = clientes_service.obtener_clientes()
            cliente_nombre = next((c["nombre"] for c in clientes_existentes if c["id"] == cliente_id), "Cliente No Encontrado")
            if cliente_nombre == "Cliente No Encontrado":
                 print(f"Cliente con ID {cliente_id} no encontrado en la lista cargada.")
                 return # Salir si el cliente no está en la lista (raro si se seleccionó del dropdown)


            mesa_numero = int(mesa_numero_str)
            fecha_base_str = fecha_reservas_text.value.split(": ")[1]
            if fecha_base_str == "Hoy":
                fecha_base = datetime.now().date()
            else:
                fecha_base = datetime.strptime(fecha_base_str, "%Y-%m-%d").date()

            hora_inicio_str = hora_inicio.value
            duracion_horas_str = duracion_horas.value

            # --- VALIDACIONES EXPLÍCITAS ANTES DE CONVERTIR ---
            if not hora_inicio_str:
                print("La hora de inicio es requerida.")
                return

            if not duracion_horas_str:
                print("La duración es requerida.")
                return

            # Intentar convertir hora_inicio_str
            try:
                hora_inicio_dt = datetime.strptime(hora_inicio_str, "%H:%M").time()
            except ValueError:
                print(f"Formato de hora inválido: {hora_inicio_str}. Use HH:MM (ej. 19:30).")
                return

            # Intentar convertir duracion_horas_str
            try:
                duracion_horas_float = float(duracion_horas_str)
                if duracion_horas_float <= 0:
                    print("La duración debe ser un número positivo.")
                    return
            except ValueError:
                print(f"Formato de duración inválido: {duracion_horas_str}. Use un número (ej. 1.5).")
                return
            # --- FIN VALIDACIONES ---

            # Construir datetime para inicio y fin
            inicio_dt = datetime.combine(fecha_base, hora_inicio_dt)
            duracion = timedelta(hours=duracion_horas_float)
            fin_dt = inicio_dt + duracion

            # Crear reserva
            print(f"Intentando crear reserva para Mesa {mesa_numero}, Cliente ID {cliente_id}, Fecha {fecha_base}, Hora Inicio {hora_inicio_str}, Duración {duracion_horas_float} horas.")
            resultado = reservas_service.crear_reserva(
                mesa_numero=mesa_numero,
                cliente_id=cliente_id, # CORREGIDO: Usar el ID obtenido del key del dropdown
                fecha_hora_inicio=inicio_dt.strftime("%Y-%m-%d %H:%M:%S"),
                fecha_hora_fin=fin_dt.strftime("%Y-%m-%d %H:%M:%S")
            )
            print(f"Reserva creada exitosamente: {resultado}")
            # Limpiar campos y actualizar vista
            cliente_dropdown.value = "" # Limpiar la selección de cliente
            mesa_dropdown.value = "" # Limpiar la selección de mesa
            hora_inicio.value = ""
            duracion_horas.value = "1" # Reiniciar a valor por defecto
            actualizar_reservas_fecha(None) # Actualizar la lista de esta vista
            on_update_ui() # Actualizar la vista de mesas también
            print(f"Reserva para {cliente_nombre} (ID: {cliente_id}) en Mesa {mesa_numero} el {fecha_base} a las {hora_inicio_str} creada exitosamente.")

        except ValueError as ve:
            print(f"Error de conversión de valor: {ve}")
        except Exception as ex:
            print(f"Error inesperado al crear reserva: {ex}") # Este debería capturar el 500 si ocurre aquí


    def cancelar_reserva_click(reserva_id: int):
        try:
            # Implementar método en ReservasService para eliminar
            reservas_service.eliminar_reserva(reserva_id)
            # Actualizar vistas
            actualizar_reservas_fecha(None)
            on_update_ui() # Actualizar la vista de mesas también
            print(f"Reserva con ID {reserva_id} cancelada exitosamente.")
        except Exception as ex:
            print(f"Error al cancelar reserva: {ex}")


    # Configurar DatePicker
    fecha_reservas_picker.on_change = lambda e: setattr(fecha_reservas_text, 'value', f"Fecha: {e.control.value.strftime('%Y-%m-%d')}") or page.update()

    # Cargar clientes al inicializar la vista
    cargar_clientes()

    vista = ft.Container(
        content=ft.Column([
            ft.Text("Gestión de Reservas", size=24, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Row([fecha_reservas_button, fecha_reservas_text]),
            ft.Divider(),
            ft.Text("Crear Nueva Reserva", size=18, weight=ft.FontWeight.BOLD),
            # --- CAMPOS MODIFICADOS ---
            cliente_dropdown,  # Dropdown para cliente existente
            mesa_dropdown,     # Dropdown para seleccionar mesa (1-6)
            # --- FIN CAMPOS MODIFICADOS ---
            ft.Row([hora_inicio, duracion_horas]),
            ft.ElevatedButton(
                "Crear Reserva",
                on_click=crear_reserva_click,
                style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)
            ),
            ft.Divider(),
            ft.Text("Reservas para la Fecha", size=18, weight=ft.FontWeight.BOLD),
            lista_reservas
        ]),
        padding=20,
        expand=True
    )

    # vista.cargar_clientes_mesas = cargar_clientes_mesas # Si decides usarlo
    return vista