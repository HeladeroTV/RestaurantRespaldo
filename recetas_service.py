 # recetas_service.py
# Cliente HTTP para interactuar con la API de recetas del sistema de restaurante.

import requests
from typing import List, Dict, Any

class RecetasService:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url.rstrip("/")

    # === MÉTODO: obtener_recetas ===
    # Obtiene todas las recetas desde el backend.
    def obtener_recetas(self) -> List[Dict[str, Any]]:
        r = requests.get(f"{self.base_url}/recetas/")
        r.raise_for_status()
        return r.json()

    # === MÉTODO: obtener_receta_por_plato ===
    # Obtiene una receta específica por el nombre del plato.
    def obtener_receta_por_plato(self, nombre_plato: str) -> Dict[str, Any]:
        r = requests.get(f"{self.base_url}/recetas/{nombre_plato}")
        r.raise_for_status()
        return r.json()

    # === MÉTODO: crear_receta ===
    # Crea una nueva receta en el backend.
    def crear_receta(self, nombre_plato: str, descripcion: str, instrucciones: str, ingredientes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Args:
            nombre_plato (str): Nombre del plato del menú al que pertenece la receta.
            descripcion (str): Descripción de la receta.
            instrucciones (str): Instrucciones de preparación.
            ingredientes (List[Dict[str, Any]]): Lista de ingredientes con id, cantidad_necesaria y unidad_medida_necesaria.
                Ej: [{"ingrediente_id": 1, "cantidad_necesaria": 0.1, "unidad_medida_necesaria": "kg"}, ...]
        Returns:
            Dict[str, Any]: La receta creada.
        """
        payload = {
            "nombre_plato": nombre_plato,
            "descripcion": descripcion,
            "instrucciones": instrucciones,
            "ingredientes": ingredientes
        }
        r = requests.post(f"{self.base_url}/recetas/", json=payload)
        r.raise_for_status()
        return r.json()

    # === MÉTODO: actualizar_receta ===
    # Actualiza una receta existente en el backend.
    def actualizar_receta(self, nombre_plato: str, nueva_descripcion: str = None, nuevas_instrucciones: str = None, nuevos_ingredientes: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Args:
            nombre_plato (str): Nombre del plato del menú al que pertenece la receta (clave primaria).
            nueva_descripcion (str, optional): Nueva descripción.
            nuevas_instrucciones (str, optional): Nuevas instrucciones.
            nuevos_ingredientes (List[Dict[str, Any]], optional): Nueva lista de ingredientes (reemplaza los anteriores).
        Returns:
            Dict[str, Any]: La receta actualizada.
        """
        payload = {}
        if nueva_descripcion is not None:
            payload["descripcion"] = nueva_descripcion
        if nuevas_instrucciones is not None:
            payload["instrucciones"] = nuevas_instrucciones
        if nuevos_ingredientes is not None:
            # Suponemos que se reemplazan todos los ingredientes
            payload["ingredientes"] = nuevos_ingredientes

        r = requests.put(f"{self.base_url}/recetas/{nombre_plato}", json=payload)
        r.raise_for_status()
        return r.json()

    # === MÉTODO: eliminar_receta ===
    # Elimina una receta por el nombre del plato.
    def eliminar_receta(self, nombre_plato: str) -> Dict[str, Any]:
        """
        Args:
            nombre_plato (str): Nombre del plato del menú al que pertenece la receta.
        Returns:
            Dict[str, Any]: Mensaje de confirmación.
        """
        r = requests.delete(f"{self.base_url}/recetas/{nombre_plato}")
        r.raise_for_status()
        return r.json()

# Opcional: Método para probar la conexión
def test_recetas_service():
    service = RecetasService()
    try:
        # Intentar obtener una lista vacía o con datos (debe devolver JSON)
        recetas = service.obtener_recetas()
        print(f"Conexión exitosa con RecetasService. Número de recetas: {len(recetas)}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con RecetasService: {e}")
        return False

if __name__ == "__main__":
    test_recetas_service()