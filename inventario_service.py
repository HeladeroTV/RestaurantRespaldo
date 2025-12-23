# === INVENTARIO_SERVICE.PY ===
# Cliente HTTP para interactuar con la API de inventario del sistema de restaurante.

import requests
from typing import List, Dict, Any

class InventoryService:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url.rstrip("/")

    # === MÉTODO: obtener_inventario ===
    # Obtiene la lista completa de items en inventario desde el backend.
    # Ahora incluye 'cantidad_minima_alerta'.
    def obtener_inventario(self) -> List[Dict[str, Any]]:
        r = requests.get(f"{self.base_url}/inventario")
        r.raise_for_status()
        return r.json() # El JSON devuelto por el backend ya incluye 'cantidad_minima_alerta'

    # === MÉTODO: agregar_item_inventario ===
    # Agrega un nuevo ítem al inventario en el backend o suma la cantidad si ya existe.
    # ✅ AHORA ACEPTA 'cantidad_minima_alerta' COMO PARÁMETRO.
    def agregar_item_inventario(self, nombre: str, cantidad: int, unidad: str = "unidad", cantidad_minima_alerta: float = 5.0) -> Dict[str, Any]:
        # Transformar el nombre: primera letra mayúscula, resto minúsculas
        nombre_formateado = nombre.strip().capitalize()
        payload = {
            "nombre": nombre_formateado,
            "cantidad_disponible": cantidad, # La cantidad que se va a sumar o insertar
            "unidad_medida": unidad,
            # --- AÑADIR EL NUEVO CAMPO AL PAYLOAD ---
            "cantidad_minima_alerta": cantidad_minima_alerta
            # --- FIN AÑADIR EL NUEVO CAMPO ---
        }
        r = requests.post(f"{self.base_url}/inventario", json=payload)
        r.raise_for_status()
        return r.json() # El JSON devuelto por el backend ya incluye 'cantidad_minima_alerta'

    # === MÉTODO: actualizar_item_inventario ===
    # Actualiza la cantidad, unidad y umbral de un ítem existente en el inventario.
    # ✅ AHORA ACEPTA 'cantidad_minima_alerta' COMO PARÁMETRO.
    def actualizar_item_inventario(self, item_id: int, cantidad: int, unidad: str = "unidad", cantidad_minima_alerta: float = 5.0) -> Dict[str, Any]:
        payload = {
            "cantidad_disponible": cantidad,
            "unidad_medida": unidad,
            # --- AÑADIR EL NUEVO CAMPO AL PAYLOAD ---
            "cantidad_minima_alerta": cantidad_minima_alerta
            # --- FIN AÑADIR EL NUEVO CAMPO ---
        }
        r = requests.put(f"{self.base_url}/inventario/{item_id}", json=payload)
        r.raise_for_status()
        return r.json() # El JSON devuelto por el backend ya incluye 'cantidad_minima_alerta'

    # === MÉTODO: eliminar_item_inventario ===
    # Elimina un ítem del inventario en el backend.
    # (No cambia, no involucra el nuevo campo)
    def eliminar_item_inventario(self, item_id: int) -> Dict[str, Any]:
        r = requests.delete(f"{self.base_url}/inventario/{item_id}")
        r.raise_for_status()
        return r.json()
