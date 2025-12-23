import json
import os
from pathlib import Path
from typing import List, Dict, Any

class ConfiguracionesService:
    def __init__(self, inventario_service=None):
        # ✅ GUARDAR EN CARPETA LOCAL DEL USUARIO
        self.carpeta_datos = Path.home() / ".restaurantia" / "datos"
        self.carpeta_datos.mkdir(parents=True, exist_ok=True)
        self.archivo = self.carpeta_datos / "configuraciones.json"
        self.inventario_service = inventario_service
        self._crear_archivo_si_no_existe()

    def _crear_archivo_si_no_existe(self):
        if not self.archivo.exists():
            with open(self.archivo, "w", encoding="utf-8") as f:
                json.dump({"configuraciones": []}, f, ensure_ascii=False, indent=4)

    def obtener_configuraciones(self) -> List[Dict[str, Any]]:
        with open(self.archivo, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["configuraciones"]

    def crear_configuracion(self, nombre: str, descripcion: str, ingredientes: List[Dict[str, Any]]) -> Dict[str, Any]:
        with open(self.archivo, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Generar ID único
        ids_existentes = [c["id"] for c in data["configuraciones"]]
        nuevo_id = max(ids_existentes, default=0) + 1

        nueva_config = {
            "id": nuevo_id,
            "nombre": nombre,
            "descripcion": descripcion,
            "ingredientes": ingredientes
        }

        data["configuraciones"].append(nueva_config)

        with open(self.archivo, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        return nueva_config

    def eliminar_configuracion(self, config_id: int) -> Dict[str, Any]:
        with open(self.archivo, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["configuraciones"] = [
            c for c in data["configuraciones"]
            if c["id"] != config_id
        ]

        with open(self.archivo, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        return {"status": "ok", "message": "Configuración eliminada"}

    def aplicar_configuracion(self, config_id: int) -> Dict[str, Any]:
        with open(self.archivo, "r", encoding="utf-8") as f:
            data = json.load(f)

        config = next((c for c in data["configuraciones"] if c["id"] == config_id), None)
        if not config:
            return {"status": "error", "message": "Configuración no encontrada"}

        # ✅ APLICAR INGREDIENTES AL INVENTARIO
        if self.inventario_service:
            for ing in config["ingredientes"]:
                try:
                    # ✅ AGREGAR INGREDIENTE AL INVENTARIO
                    self.inventario_service.agregar_item_inventario(
                        nombre=ing["nombre"],
                        cantidad=ing["cantidad"],
                        unidad=ing["unidad"]
                    )
                except Exception as e:
                    print(f"Error al agregar ingrediente {ing['nombre']}: {e}")

        return {"status": "ok", "message": "Configuración aplicada"}