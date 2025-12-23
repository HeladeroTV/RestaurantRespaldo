# inventario_backend.py
# Backend API para gestionar el inventario de ingredientes.

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List
import psycopg2
from psycopg2.extras import RealDictCursor
# --- IMPORTAR LA EXCEPCIÓN DE INTEGRIDAD ---
import psycopg2.errors
# --- FIN IMPORTAR ---

DATABASE_URL = "dbname=restaurant_db user=postgres password=postgres host=localhost port=5432"

def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()

# --- MODELO: InventarioItem ---
# Para agregar un nuevo ítem al inventario.
class InventarioItem(BaseModel):
    nombre: str
    cantidad_disponible: int
    unidad_medida: str = "unidad"
    # --- AÑADIR EL NUEVO CAMPO ---
    cantidad_minima_alerta: float = 5.0 # Nuevo campo, con valor por defecto
    # --- FIN AÑADIR EL NUEVO CAMPO ---

# --- MODELO: InventarioUpdate ---
# Para actualizar un ítem existente en el inventario.
class InventarioUpdate(BaseModel):
    cantidad_disponible: int
    unidad_medida: str = "unidad"
    # --- AÑADIR EL NUEVO CAMPO ---
    cantidad_minima_alerta: float = 5.0 # Nuevo campo, con valor por defecto
    # --- FIN AÑADIR EL NUEVO CAMPO ---

# --- MODELO: InventarioResponse ---
# Para la respuesta al obtener ítems del inventario.
class InventarioResponse(BaseModel):
    id: int
    nombre: str
    cantidad_disponible: int
    unidad_medida: str
    # --- AÑADIR EL NUEVO CAMPO ---
    cantidad_minima_alerta: float # Nuevo campo
    # --- FIN AÑADIR EL NUEVO CAMPO ---
    fecha_registro: str
    fecha_actualizacion: str

# NUEVA API PARA INVENTARIO
inventario_app = FastAPI(title="Inventory API")

@inventario_app.get("/", response_model=List[InventarioResponse])
def obtener_inventario(conn: psycopg2.extensions.connection = Depends(get_db)):
    with conn.cursor() as cursor:
        # --- ACTUALIZAR CONSULTA: Incluir cantidad_minima_alerta ---
        cursor.execute("""
            SELECT id, nombre, cantidad_disponible, unidad_medida, cantidad_minima_alerta, fecha_registro, fecha_actualizacion
            FROM inventario
            ORDER BY nombre
        """)
        items = []
        for row in cursor.fetchall():
            items.append({
                "id": row['id'],
                "nombre": row['nombre'],
                "cantidad_disponible": row['cantidad_disponible'],
                "unidad_medida": row['unidad_medida'],
                # --- AÑADIR AL RESULTADO ---
                "cantidad_minima_alerta": row['cantidad_minima_alerta'],
                # --- FIN AÑADIR AL RESULTADO ---
                "fecha_registro": str(row['fecha_registro']),
                "fecha_actualizacion": str(row['fecha_actualizacion'])
            })
        return items

@inventario_app.post("/", response_model=InventarioResponse)
def agregar_item_inventario(item: InventarioItem, conn: psycopg2.extensions.connection = Depends(get_db)):
    with conn.cursor() as cursor:
        # --- ACTUALIZAR CONSULTA: Incluir cantidad_minima_alerta en INSERT y UPDATE ---
        cursor.execute("""
            INSERT INTO inventario (nombre, cantidad_disponible, unidad_medida, cantidad_minima_alerta)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (nombre) -- Asumiendo que 'nombre' tiene una restricción UNIQUE
            DO UPDATE SET
                cantidad_disponible = inventario.cantidad_disponible + %s,
                cantidad_minima_alerta = EXCLUDED.cantidad_minima_alerta, -- Tomar el valor del INSERT si es conflicto
                fecha_actualizacion = CURRENT_TIMESTAMP
            RETURNING id, nombre, cantidad_disponible, unidad_medida, cantidad_minima_alerta, fecha_registro, fecha_actualizacion
        """, (
            item.nombre, # Valor para INSERT
            item.cantidad_disponible, # Valor inicial para INSERT
            item.unidad_medida, # Valor para INSERT
            item.cantidad_minima_alerta, # Valor para INSERT (y potencial UPDATE)
            item.cantidad_disponible  # Valor para la suma en UPDATE de cantidad_disponible
        ))
        result = cursor.fetchone()
        conn.commit()
        return {
            "id": result['id'],
            "nombre": result['nombre'],
            "cantidad_disponible": result['cantidad_disponible'],
            "unidad_medida": result['unidad_medida'],
            # --- AÑADIR AL RESULTADO ---
            "cantidad_minima_alerta": result['cantidad_minima_alerta'],
            # --- FIN AÑADIR AL RESULTADO ---
            "fecha_registro": str(result['fecha_registro']),
            "fecha_actualizacion": str(result['fecha_actualizacion'])
        }

@inventario_app.put("/{item_id}", response_model=InventarioResponse)
def actualizar_item_inventario(item_id: int, update_data: InventarioUpdate, conn: psycopg2.extensions.connection = Depends(get_db)):
    with conn.cursor() as cursor:
        # --- ACTUALIZAR CONSULTA: Incluir cantidad_minima_alerta en SET ---
        cursor.execute("""
            UPDATE inventario
            SET cantidad_disponible = %s, unidad_medida = %s, cantidad_minima_alerta = %s, fecha_actualizacion = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, nombre, cantidad_disponible, unidad_medida, cantidad_minima_alerta, fecha_registro, fecha_actualizacion
        """, (update_data.cantidad_disponible, update_data.unidad_medida, update_data.cantidad_minima_alerta, item_id))
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Ítem no encontrado")
        conn.commit()
        return {
            "id": result['id'],
            "nombre": result['nombre'],
            "cantidad_disponible": result['cantidad_disponible'],
            "unidad_medida": result['unidad_medida'],
            # --- AÑADIR AL RESULTADO ---
            "cantidad_minima_alerta": result['cantidad_minima_alerta'],
            # --- FIN AÑADIR AL RESULTADO ---
            "fecha_registro": str(result['fecha_registro']),
            "fecha_actualizacion": str(result['fecha_actualizacion'])
        }

# --- CORRECCIÓN: Capturar la excepción de integridad referencial ---
@inventario_app.delete("/{item_id}")
def eliminar_item_inventario(item_id: int, conn = Depends(get_db)):
    with conn.cursor() as cursor:
        try:
            cursor.execute("DELETE FROM inventario WHERE id = %s", (item_id,))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Ítem no encontrado")
            conn.commit()
            return {"status": "ok"}
        # Capturar la excepción específica de PostgreSQL por la restricción ON DELETE RESTRICT
        except psycopg2.errors.ForeignKeyViolation as e:
            conn.rollback() # Revertir la transacción en caso de error
            # Devolver un error 400 indicando que el ítem está en uso
            raise HTTPException(status_code=400, detail=f"No se puede eliminar el ítem porque está siendo utilizado en una receta: {str(e)}")
        # Opcional: Capturar otras excepciones de integridad si es necesario
        except psycopg2.errors.IntegrityError as e:
            conn.rollback() # Revertir la transacción en caso de error
            print(f"Error de integridad al eliminar ítem {item_id}: {e}") # Para depuración
            raise HTTPException(status_code=500, detail="Error interno del servidor al eliminar el ítem.")

# --- FIN CORRECCIÓN ---

# Opcional: Si tienes una app principal, asegúrate de montar esta sub-app correctamente.
# Por ejemplo, si tienes una app principal llamada `app`, podrías hacer:
# from fastapi import FastAPI
# app = FastAPI()
# app.mount("/inventario", inventario_app)
# Pero esto depende de cómo tengas estructurado tu backend principal.