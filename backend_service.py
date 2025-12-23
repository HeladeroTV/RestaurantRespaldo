# === BACKEND_SERVICE.PY ===
# Cliente HTTP para interactuar con la API del backend del sistema de restaurante.

import requests
from typing import List, Dict, Any
from datetime import datetime, timedelta

class BackendService:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url.rstrip("/")

    # === MÉTODO: obtener_menu ===
    # Obtiene todos los ítems del menú desde el backend.

    def obtener_menu(self) -> List[Dict[str, Any]]:
        """Obtiene todos los ítems del menú desde el backend."""
        r = requests.get(f"{self.base_url}/menu/items")
        r.raise_for_status()
        return r.json()

    # === MÉTODO: crear_pedido ===
    # Crea un nuevo pedido en el backend.

    def crear_pedido(self, mesa_numero: int, items: List[Dict[str, Any]], estado: str = "Pendiente", notas: str = "") -> Dict[str, Any]:
        """Crea un nuevo pedido en el backend."""
        payload = {
            "mesa_numero": mesa_numero,
            "items": items,
            "estado": estado,
            "notas": notas
        }
        r = requests.post(f"{self.base_url}/pedidos", json=payload)
        if r.status_code != 200:
            try:
                error_detail = r.json().get('detail', r.text)
            except ValueError:
                error_detail = r.text
            raise Exception(f"{error_detail}") # Solo el mensaje limpio
        return r.json()

    # === MÉTODO: obtener_pedidos_activos ===
    # Obtiene todos los pedidos activos desde el backend.

    def obtener_pedidos_activos(self) -> List[Dict[str, Any]]:
        """Obtiene todos los pedidos activos desde el backend."""
        r = requests.get(f"{self.base_url}/pedidos/activos")
        r.raise_for_status()
        return r.json()

    # === MÉTODO: actualizar_estado_pedido ===
    # Actualiza el estado de un pedido en el backend.

    def actualizar_estado_pedido(self, pedido_id: int, nuevo_estado: str) -> Dict[str, Any]:
        """Actualiza el estado de un pedido en el backend."""
        r = requests.patch(f"{self.base_url}/pedidos/{pedido_id}/estado", params={"estado": nuevo_estado})
        r.raise_for_status()
        return r.json()

    # === MÉTODO: obtener_mesas ===
    # Obtiene la lista de mesas desde el backend.

    def obtener_mesas(self) -> List[Dict[str, Any]]:
        """Obtiene la lista de mesas desde el backend."""
        r = requests.get(f"{self.base_url}/mesas")
        r.raise_for_status()
        return r.json()

    # === MÉTODO: eliminar_ultimo_item ===
    # Elimina el último ítem de un pedido en el backend.

    def eliminar_ultimo_item(self, pedido_id: int) -> Dict[str, Any]:
        """
        Elimina el último ítem de un pedido en el backend.
        """
        r = requests.delete(f"{self.base_url}/pedidos/{pedido_id}/ultimo_item")
        r.raise_for_status()
        return r.json()

    # === MÉTODO: actualizar_pedido ===
    # Actualiza completamente un pedido en el backend.

    def actualizar_pedido(self, pedido_id: int, mesa_numero: int, items: List[Dict[str, Any]], estado: str = "Pendiente", notas: str = "") -> Dict[str, Any]:
        """
        Actualiza completamente un pedido en el backend.
        """
        payload = {
            "mesa_numero": mesa_numero,
            "items": items,
            "estado": estado,
            "notas": notas
        }
        r = requests.put(f"{self.base_url}/pedidos/{pedido_id}", json=payload)
        r.raise_for_status()
        return r.json()

    # === MÉTODO: eliminar_pedido ===
    # Elimina un pedido completamente del backend.

    def eliminar_pedido(self, pedido_id: int) -> Dict[str, Any]:
        """
        Elimina un pedido completamente del backend.
        """
        r = requests.delete(f"{self.base_url}/pedidos/{pedido_id}")
        r.raise_for_status()
        return r.json()

    # === MÉTODO: agregar_item_menu ===
    # Agrega un nuevo ítem al menú en el backend.

    def agregar_item_menu(self, nombre: str, precio: float, tipo: str) -> Dict[str, Any]:
        """
        Agrega un nuevo ítem al menú en el backend.
        """
        payload = {
            "nombre": nombre,
            "precio": precio,
            "tipo": tipo
        }
        r = requests.post(f"{self.base_url}/menu/items", json=payload)
        r.raise_for_status()
        return r.json()

    # === MÉTODO: eliminar_item_menu ===
    # Elimina un ítem del menú en el backend.

    def eliminar_item_menu(self, nombre: str, tipo: str) -> Dict[str, Any]:
        """
        Elimina un ítem del menú en el backend.
        """
        r = requests.delete(f"{self.base_url}/menu/items", params={"nombre": nombre, "tipo": tipo})
        r.raise_for_status()
        return r.json()

    # === MÉTODO: obtener_clientes ===
    # Obtiene la lista de clientes del backend.

    def obtener_clientes(self) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de clientes del backend.
        """
        r = requests.get(f"{self.base_url}/clientes")
        r.raise_for_status()
        return r.json()

    # === MÉTODO: agregar_cliente ===
    # Agrega un nuevo cliente al backend.

    def agregar_cliente(self, nombre: str, domicilio: str, celular: str) -> Dict[str, Any]:
        """
        Agrega un nuevo cliente al backend.
        """
        payload = {
            "nombre": nombre,
            "domicilio": domicilio,
            "celular": celular
        }
        r = requests.post(f"{self.base_url}/clientes", json=payload)
        r.raise_for_status()
        return r.json()

    # === MÉTODO: eliminar_cliente ===
    # Elimina un cliente del backend.

    def eliminar_cliente(self, cliente_id: int) -> Dict[str, Any]:
        """
        Elimina un cliente del backend.
        """
        r = requests.delete(f"{self.base_url}/clientes/{cliente_id}")
        r.raise_for_status()
        return r.json()
    
    def obtener_reporte(self, tipo: str, fecha: datetime) -> Dict[str, Any]:
        """Obtiene estadísticas de ventas para un tipo y fecha específicos."""
        # Construir parámetros de fecha
        if tipo == "Diario":
            start_date = fecha.strftime("%Y-%m-%d")
            end_date = (fecha + timedelta(days=1)).strftime("%Y-%m-%d")
        elif tipo == "Semanal":
            start_date = (fecha - timedelta(days=fecha.weekday())).strftime("%Y-%m-%d")
            end_date = (fecha + timedelta(days=6 - fecha.weekday())).strftime("%Y-%m-%d")
        elif tipo == "Mensual":
            start_date = fecha.replace(day=1).strftime("%Y-%m-%d")
            end_date = (fecha.replace(day=1) + timedelta(days=32)).replace(day=1).strftime("%Y-%m-%d")
        else:  # Anual
            start_date = fecha.replace(month=1, day=1).strftime("%Y-%m-%d")
            end_date = fecha.replace(month=12, day=31).strftime("%Y-%m-%d")

        # Llamar al backend
        params = {
            "tipo": tipo.lower(),
            "start_date": start_date,
            "end_date": end_date
        }
        r = requests.get(f"{self.base_url}/reportes/", params=params)
        r.raise_for_status()
        return r.json()
    
    
    def obtener_analisis_productos(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """
        Obtiene el análisis de productos vendidos.
        """
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        r = requests.get(f"{self.base_url}/analisis/productos/", params=params)
        r.raise_for_status()
        return r.json()
    
    # --- NUEVO MÉTODO: obtener_ventas_por_hora ---
    def obtener_ventas_por_hora(self, fecha: str) -> Dict[str, float]:
        """
        Obtiene el total de ventas por hora para una fecha específica.
        Args:
            fecha (str): Fecha en formato 'YYYY-MM-DD'.
        Returns:
            Dict[str, float]: Diccionario con hora (00-23) como clave y total de ventas como valor.
        """
        params = {"fecha": fecha}
        r = requests.get(f"{self.base_url}/reportes/ventas_por_hora", params=params)
        r.raise_for_status()
        return r.json()
    # --- FIN NUEVO MÉTODO ---
    
    # --- NUEVO MÉTODO: obtener_eficiencia_cocina ---
    def obtener_eficiencia_cocina(self, tipo: str, fecha: datetime) -> Dict[str, Any]:
        """
        Obtiene estadísticas de eficiencia de cocina para un tipo y fecha específicos.
        Args:
            tipo (str): "Diario", "Semanal", "Mensual", "Anual".
            fecha (datetime): Fecha de referencia para el cálculo.
        Returns:
            Dict[str, Any]: Diccionario con 'promedio_minutos' y 'detalle_pedidos'.
        """
        # Construir parámetros de fecha (igual que en obtener_reporte)
        if tipo == "Diario":
            start_date = fecha.strftime("%Y-%m-%d")
            end_date = (fecha + timedelta(days=1)).strftime("%Y-%m-%d")
        elif tipo == "Semanal":
            start_date = (fecha - timedelta(days=fecha.weekday())).strftime("%Y-%m-%d")
            end_date = (fecha + timedelta(days=6 - fecha.weekday())).strftime("%Y-%m-%d")
        elif tipo == "Mensual":
            start_date = fecha.replace(day=1).strftime("%Y-%m-%d")
            end_date = (fecha.replace(day=1) + timedelta(days=32)).replace(day=1).strftime("%Y-%m-%d")
        else:  # Anual
            start_date = fecha.replace(month=1, day=1).strftime("%Y-%m-%d")
            end_date = fecha.replace(month=12, day=31).strftime("%Y-%m-%d")

        # Llamar al nuevo endpoint
        params = {
            "tipo": tipo.lower(),
            "start_date": start_date,
            "end_date": end_date
        }
        r = requests.get(f"{self.base_url}/reportes/eficiencia_cocina", params=params)
        r.raise_for_status()
        return r.json()
    # --- FIN NUEVO MÉTODO ---

    # === MÉTODO: crear_respaldo ===
    def crear_respaldo(self) -> Dict[str, Any]:
        """
        Solicita al backend crear un respaldo de la base de datos.
        """
        r = requests.post(f"{self.base_url}/backup")
        if r.status_code != 200:
            try:
                error_detail = r.json().get('detail', r.text)
            except ValueError:
                error_detail = r.text
            raise Exception(f"Error del backend ({r.status_code}): {error_detail}")
        return r.json()
