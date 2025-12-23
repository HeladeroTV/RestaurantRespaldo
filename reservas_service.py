# reservas_service.py
import requests
from typing import List, Dict, Any

class ReservasService:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url.rstrip("/")

    # === MÉTODO: obtener_reservas ===
    # Obtiene la lista de reservas, opcionalmente filtrada por fecha.
    def obtener_reservas(self, fecha: str = None) -> List[Dict[str, Any]]:
        """
        Obtiene todas las reservas o filtra por fecha.
        Args:
            fecha (str, optional): Fecha en formato 'YYYY-MM-DD'.
        Returns:
            List[Dict[str, Any]]: Lista de reservas.
        """
        params = {}
        if fecha:
            params["fecha"] = fecha
        r = requests.get(f"{self.base_url}/reservas/", params=params)
        r.raise_for_status()
        return r.json()

    # === MÉTODO: crear_reserva ===
    # Crea una nueva reserva.
    def crear_reserva(self, mesa_numero: int, cliente_id: int, fecha_hora_inicio: str, fecha_hora_fin: str = None) -> Dict[str, Any]:
        """
        Crea una nueva reserva.
        Args:
            mesa_numero (int): Número de la mesa a reservar.
            cliente_id (int): ID del cliente que hace la reserva.
            fecha_hora_inicio (str): Fecha y hora de inicio de la reserva (formato: 'YYYY-MM-DD HH:MM:SS').
            fecha_hora_fin (str, optional): Fecha y hora de fin de la reserva (formato: 'YYYY-MM-DD HH:MM:SS').
        Returns:
            Dict[str, Any]: Detalles de la reserva creada.
        """
        payload = {
            "mesa_numero": mesa_numero,
            "cliente_id": cliente_id,
            "fecha_hora_inicio": fecha_hora_inicio,
        }
        if fecha_hora_fin:
            payload["fecha_hora_fin"] = fecha_hora_fin

        r = requests.post(f"{self.base_url}/reservas/", json=payload)
        r.raise_for_status()
        return r.json()

    # === MÉTODO: eliminar_reserva ===
    # Elimina una reserva existente por su ID.
    def eliminar_reserva(self, reserva_id: int) -> Dict[str, Any]:
        """
        Elimina una reserva por su ID.
        Args:
            reserva_id (int): ID de la reserva a eliminar.
        Returns:
            Dict[str, Any]: Mensaje de confirmación.
        """
        r = requests.delete(f"{self.base_url}/reservas/{reserva_id}")
        r.raise_for_status()
        return r.json()

    # === MÉTODO: actualizar_reserva ===
    # Actualiza una reserva existente por su ID.
    def actualizar_reserva(self, reserva_id: int, mesa_numero: int = None, cliente_id: int = None, fecha_hora_inicio: str = None, fecha_hora_fin: str = None) -> Dict[str, Any]:
        """
        Actualiza una reserva por su ID.
        Args:
            reserva_id (int): ID de la reserva a actualizar.
            mesa_numero (int, optional): Nuevo número de mesa.
            cliente_id (int, optional): Nuevo ID de cliente.
            fecha_hora_inicio (str, optional): Nueva fecha y hora de inicio.
            fecha_hora_fin (str, optional): Nueva fecha y hora de fin.
        Returns:
            Dict[str, Any]: Detalles de la reserva actualizada.
        """
        payload = {}
        if mesa_numero is not None:
            payload["mesa_numero"] = mesa_numero
        if cliente_id is not None:
            payload["cliente_id"] = cliente_id
        if fecha_hora_inicio is not None:
            payload["fecha_hora_inicio"] = fecha_hora_inicio
        if fecha_hora_fin is not None:
            payload["fecha_hora_fin"] = fecha_hora_fin

        r = requests.put(f"{self.base_url}/reservas/{reserva_id}", json=payload)
        r.raise_for_status()
        return r.json()

    # === MÉTODO: obtener_mesas_disponibles ===
    # Obtiene la lista de mesas disponibles para una fecha y hora específica.
    def obtener_mesas_disponibles(self, fecha_hora: str) -> List[Dict[str, Any]]:
        """
        Obtiene mesas disponibles para una fecha y hora específica.
        Args:
            fecha_hora (str): Fecha y hora para verificar disponibilidad (formato: 'YYYY-MM-DD HH:MM:SS').
        Returns:
            List[Dict[str, Any]]: Lista de mesas disponibles.
        """
        params = {"fecha_hora": fecha_hora}
        r = requests.get(f"{self.base_url}/mesas/disponibles/", params=params)
        r.raise_for_status()
        return r.json()

# Opcional: Método para probar la conexión
def test_reservas_service():
    service = ReservasService()
    try:
        # Intentar obtener una lista vacía o con datos (debe devolver JSON)
        reservas = service.obtener_reservas()
        print(f"Conexión exitosa con ReservasService. Número de reservas: {len(reservas)}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con ReservasService: {e}")
        return False

if __name__ == "__main__":
    test_reservas_service()