from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List
import psycopg2
from psycopg2.extras import RealDictCursor
import json

DATABASE_URL = "dbname=restaurant_db user=postgres password=postgres host=localhost port=5432"

def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()

class IngredienteConfig(BaseModel):
    nombre: str
    cantidad: int
    unidad: str = "unidad"

class ConfiguracionCreate(BaseModel):  # ✅ MODELO CORREGIDO
    nombre: str
    descripcion: str = ""
    ingredientes: List[IngredienteConfig]

class ConfiguracionResponse(BaseModel):
    id: int
    nombre: str
    descripcion: str
    ingredientes: List[dict]

# NUEVA SUB-APP PARA CONFIGURACIONES
configuraciones_app = FastAPI(title="Configuraciones API")

@configuraciones_app.get("/", response_model=List[ConfiguracionResponse])
def obtener_configuraciones(conn = Depends(get_db)):
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT c.id, c.nombre, c.descripcion, c.ingredientes
            FROM configuraciones c
            ORDER BY c.nombre
        """)
        configs = []
        for row in cursor.fetchall():
            configs.append({
                "id": row['id'],
                "nombre": row['nombre'],
                "descripcion": row['descripcion'],
                "ingredientes": json.loads(row['ingredientes'])  # ✅ CONVERTIR JSON A DICT
            })
        return configs

@configuraciones_app.post("/", response_model=ConfiguracionResponse)
def crear_configuracion(config: ConfiguracionCreate, conn = Depends(get_db)):
    with conn.cursor() as cursor:
        # Convertir ingredientes a JSON
        ingredientes_json = json.dumps([ing.dict() for ing in config.ingredientes])

        # Crear configuración
        cursor.execute("""
            INSERT INTO configuraciones (nombre, descripcion, ingredientes)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (config.nombre, config.descripcion, ingredientes_json))
        config_id = cursor.fetchone()['id']

        conn.commit()
        return obtener_config_por_id(config_id, conn)

def obtener_config_por_id(config_id: int, conn):
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT c.id, c.nombre, c.descripcion, c.ingredientes
            FROM configuraciones c
            WHERE c.id = %s
        """, (config_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Configuración no encontrada")

        return {
            "id": row['id'],
            "nombre": row['nombre'],
            "descripcion": row['descripcion'],
            "ingredientes": json.loads(row['ingredientes'])  # ✅ CONVERTIR JSON A DICT
        }

@configuraciones_app.delete("/{config_id}")
def eliminar_configuracion(config_id: int, conn = Depends(get_db)):
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM configuraciones WHERE id = %s", (config_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Configuración no encontrada")
        conn.commit()
        return {"status": "ok", "message": "Configuración eliminada"}

@configuraciones_app.post("/{config_id}/aplicar")
def aplicar_configuracion(config_id: int, conn = Depends(get_db)):
    with conn.cursor() as cursor:
        try:
            # Obtener ingredientes de la configuración
            cursor.execute("""
                SELECT ingredientes
                FROM configuraciones
                WHERE id = %s
            """, (config_id,))
            config = cursor.fetchone()
            if not config:
                raise HTTPException(status_code=404, detail="Configuración no encontrada")

            ingredientes = json.loads(config['ingredientes'])

            # Agregar ingredientes al inventario
            for ing in ingredientes:
                cursor.execute("""
                    INSERT INTO inventario (nombre, cantidad_disponible, unidad_medida)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (nombre) DO UPDATE SET
                        cantidad_disponible = inventario.cantidad_disponible + %s
                """, (ing['nombre'], ing['cantidad'], ing['unidad'], ing['cantidad']))

            conn.commit()
            return {"status": "ok", "message": "Configuración aplicada"}
        except Exception as e:
            conn.rollback()  # ✅ REVERTIR CAMBIOS EN CASO DE ERROR
            print(f"Error en aplicar_configuracion: {e}")  # ✅ IMPRIMIR ERROR
            raise HTTPException(status_code=500, detail=str(e))