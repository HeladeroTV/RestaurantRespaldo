# recetas_backend.py
# Backend API para gestionar recetas e ingredientes de recetas.

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List
import psycopg2
from psycopg2.extras import RealDictCursor
import json

# Configuración directa de PostgreSQL
DATABASE_URL = "dbname=restaurant_db user=postgres password=postgres host=localhost port=5432"

def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()

# Modelos Pydantic para Recetas e Ingredientes de Recetas
class IngredienteRecetaCreate(BaseModel):
    ingrediente_id: int
    cantidad_necesaria: float
    unidad_medida_necesaria: str

class RecetaCreate(BaseModel):
    nombre_plato: str # Debe coincidir con un nombre de plato en la tabla 'menu'
    descripcion: str = ""
    instrucciones: str = ""
    ingredientes: List[IngredienteRecetaCreate]

class IngredienteRecetaUpdate(BaseModel):
    ingrediente_id: int
    cantidad_necesaria: float
    unidad_medida_necesaria: str

class RecetaUpdate(BaseModel):
    nombre_plato: str = None # Opcional para renombrar el plato
    descripcion: str = None
    instrucciones: str = None
    ingredientes: List[IngredienteRecetaUpdate] = [] # Lista de ingredientes para actualizar/reemplazar

class RecetaResponse(BaseModel):
    id: int
    nombre_plato: str
    descripcion: str
    instrucciones: str
    fecha_creacion: str
    fecha_actualizacion: str
    ingredientes: List[dict] # Lista de diccionarios con detalles del ingrediente

# Nueva sub-app para Recetas
recetas_app = FastAPI(title="Recetas API")

# --- ENDPOINTS PARA RECETAS ---

@recetas_app.get("/", response_model=List[RecetaResponse])
def obtener_recetas(conn = Depends(get_db)):
    """
    Obtiene todas las recetas con sus ingredientes.
    """
    try:
        with conn.cursor() as cursor:
            # Obtener recetas
            cursor.execute("""
                SELECT id, nombre_plato, descripcion, instrucciones, fecha_creacion, fecha_actualizacion
                FROM recetas
                ORDER BY nombre_plato;
            """)
            recetas_db = cursor.fetchall()

            resultado = []
            for receta_db in recetas_db:
                # Obtener ingredientes para cada receta
                cursor.execute("""
                    SELECT ir.ingrediente_id, i.nombre as nombre_ingrediente, ir.cantidad_necesaria, ir.unidad_medida_necesaria
                    FROM ingredientes_recetas ir
                    JOIN inventario i ON ir.ingrediente_id = i.id
                    WHERE ir.receta_id = %s;
                """, (receta_db['id'],))
                ingredientes_db = cursor.fetchall()

                resultado.append({
                    "id": receta_db['id'],
                    "nombre_plato": receta_db['nombre_plato'],
                    "descripcion": receta_db['descripcion'],
                    "instrucciones": receta_db['instrucciones'],
                    "fecha_creacion": str(receta_db['fecha_creacion']),
                    "fecha_actualizacion": str(receta_db['fecha_actualizacion']),
                    "ingredientes": [
                        {
                            "ingrediente_id": ing['ingrediente_id'],
                            "nombre_ingrediente": ing['nombre_ingrediente'],
                            "cantidad_necesaria": ing['cantidad_necesaria'],
                            "unidad_medida_necesaria": ing['unidad_medida_necesaria']
                        }
                        for ing in ingredientes_db
                    ]
                })

            return resultado
    except Exception as e:
        print(f"Error en obtener_recetas: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor al obtener recetas.")


@recetas_app.get("/{nombre_plato}", response_model=RecetaResponse)
def obtener_receta_por_plato(nombre_plato: str, conn = Depends(get_db)):
    """
    Obtiene una receta específica por el nombre del plato.
    """
    try:
        with conn.cursor() as cursor:
            # Obtener receta
            cursor.execute("""
                SELECT id, nombre_plato, descripcion, instrucciones, fecha_creacion, fecha_actualizacion
                FROM recetas
                WHERE nombre_plato = %s;
            """, (nombre_plato,))
            receta_db = cursor.fetchone()

            if not receta_db:
                raise HTTPException(status_code=404, detail="Receta no encontrada para el plato especificado.")

            # Obtener ingredientes para la receta
            cursor.execute("""
                SELECT ir.ingrediente_id, i.nombre as nombre_ingrediente, ir.cantidad_necesaria, ir.unidad_medida_necesaria
                FROM ingredientes_recetas ir
                JOIN inventario i ON ir.ingrediente_id = i.id
                WHERE ir.receta_id = %s;
            """, (receta_db['id'],))
            ingredientes_db = cursor.fetchall()

            return {
                "id": receta_db['id'],
                "nombre_plato": receta_db['nombre_plato'],
                "descripcion": receta_db['descripcion'],
                "instrucciones": receta_db['instrucciones'],
                "fecha_creacion": str(receta_db['fecha_creacion']),
                "fecha_actualizacion": str(receta_db['fecha_actualizacion']),
                "ingredientes": [
                    {
                        "ingrediente_id": ing['ingrediente_id'],
                        "nombre_ingrediente": ing['nombre_ingrediente'],
                        "cantidad_necesaria": ing['cantidad_necesaria'],
                        "unidad_medida_necesaria": ing['unidad_medida_necesaria']
                    }
                    for ing in ingredientes_db
                ]
            }
    except HTTPException:
        # Re-raise HTTP exceptions (como 404)
        raise
    except Exception as e:
        print(f"Error en obtener_receta_por_plato: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor al obtener la receta.")


@recetas_app.post("/", response_model=RecetaResponse)
def crear_receta(receta: RecetaCreate, conn = Depends(get_db)):
    """
    Crea una nueva receta para un plato del menú.
    """
    try:
        with conn.cursor() as cursor:
            # Verificar que el plato exista en la tabla 'menu'
            cursor.execute("SELECT 1 FROM menu WHERE nombre = %s", (receta.nombre_plato,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Plato no encontrado en el menú.")

            # Insertar la receta
            cursor.execute("""
                INSERT INTO recetas (nombre_plato, descripcion, instrucciones)
                VALUES (%s, %s, %s)
                RETURNING id;
            """, (receta.nombre_plato, receta.descripcion, receta.instrucciones))
            receta_id = cursor.fetchone()['id']

            # Insertar los ingredientes de la receta
            for ing in receta.ingredientes:
                # Verificar que el ingrediente exista en la tabla 'inventario'
                cursor.execute("SELECT 1 FROM inventario WHERE id = %s", (ing.ingrediente_id,))
                if not cursor.fetchone():
                    conn.rollback() # Revertir si un ingrediente no existe
                    raise HTTPException(status_code=404, detail=f"Ingrediente con ID {ing.ingrediente_id} no encontrado en el inventario.")
                
                cursor.execute("""
                    INSERT INTO ingredientes_recetas (receta_id, ingrediente_id, cantidad_necesaria, unidad_medida_necesaria)
                    VALUES (%s, %s, %s, %s);
                """, (receta_id, ing.ingrediente_id, ing.cantidad_necesaria, ing.unidad_medida_necesaria))

            conn.commit()
            
            # Retornar la receta creada (opcional: llamar a obtener_receta_por_plato)
            return obtener_receta_por_plato(receta.nombre_plato, conn)

    except HTTPException:
        # Re-raise HTTP exceptions (como 404)
        raise
    except Exception as e:
        print(f"Error en crear_receta: {e}")
        import traceback
        traceback.print_exc() # Imprime el traceback completo
        conn.rollback() # Revertir la transacción en caso de error inesperado
        raise HTTPException(status_code=500, detail="Error interno del servidor al crear la receta.")


@recetas_app.put("/{nombre_plato}", response_model=RecetaResponse)
def actualizar_receta(nombre_plato: str, receta_actualizada: RecetaUpdate, conn = Depends(get_db)):
    """
    Actualiza una receta existente por el nombre del plato.
    """
    try:
        with conn.cursor() as cursor:
            # Verificar que la receta exista
            cursor.execute("SELECT id FROM recetas WHERE nombre_plato = %s", (nombre_plato,))
            receta_db = cursor.fetchone()
            if not receta_db:
                raise HTTPException(status_code=404, detail="Receta no encontrada.")
            
            receta_id = receta_db['id']

            # Actualizar campos básicos de la receta si se proporcionan
            if receta_actualizada.nombre_plato is not None:
                # Verificar que el nuevo nombre_plato exista en la tabla 'menu'
                cursor.execute("SELECT 1 FROM menu WHERE nombre = %s", (receta_actualizada.nombre_plato,))
                if not cursor.fetchone():
                    raise HTTPException(status_code=404, detail="Nuevo plato no encontrado en el menú.")
                cursor.execute("UPDATE recetas SET nombre_plato = %s WHERE id = %s", (receta_actualizada.nombre_plato, receta_id))
            
            if receta_actualizada.descripcion is not None:
                cursor.execute("UPDATE recetas SET descripcion = %s WHERE id = %s", (receta_actualizada.descripcion, receta_id))
            
            if receta_actualizada.instrucciones is not None:
                cursor.execute("UPDATE recetas SET instrucciones = %s WHERE id = %s", (receta_actualizada.instrucciones, receta_id))
            
            # Actualizar ingredientes: BORRAR TODOS Y REINSERTAR (simplificación)
            # Opcional: Implementar lógica de borrado/selección individual si se desea mayor precisión
            cursor.execute("DELETE FROM ingredientes_recetas WHERE receta_id = %s", (receta_id,))
            for ing in receta_actualizada.ingredientes:
                # Verificar que el ingrediente exista en la tabla 'inventario'
                cursor.execute("SELECT 1 FROM inventario WHERE id = %s", (ing.ingrediente_id,))
                if not cursor.fetchone():
                    conn.rollback() # Revertir si un ingrediente no existe
                    raise HTTPException(status_code=404, detail=f"Ingrediente con ID {ing.ingrediente_id} no encontrado en el inventario.")
                
                cursor.execute("""
                    INSERT INTO ingredientes_recetas (receta_id, ingrediente_id, cantidad_necesaria, unidad_medida_necesaria)
                    VALUES (%s, %s, %s, %s);
                """, (receta_id, ing.ingrediente_id, ing.cantidad_necesaria, ing.unidad_medida_necesaria))

            conn.commit()
            
            # Retornar la receta actualizada (opcional: llamar a obtener_receta_por_plato)
            nombre_para_retorno = receta_actualizada.nombre_plato if receta_actualizada.nombre_plato is not None else nombre_plato
            return obtener_receta_por_plato(nombre_para_retorno, conn)

    except HTTPException:
        # Re-raise HTTP exceptions (como 404)
        raise
    except Exception as e:
        print(f"Error en actualizar_receta: {e}")
        import traceback
        traceback.print_exc() # Imprime el traceback completo
        conn.rollback() # Revertir la transacción en caso de error inesperado
        raise HTTPException(status_code=500, detail="Error interno del servidor al actualizar la receta.")


@recetas_app.delete("/{nombre_plato}")
def eliminar_receta(nombre_plato: str, conn = Depends(get_db)):
    """
    Elimina una receta por el nombre del plato.
    """
    try:
        with conn.cursor() as cursor:
            # Verificar que la receta exista
            cursor.execute("SELECT id FROM recetas WHERE nombre_plato = %s", (nombre_plato,))
            receta_db = cursor.fetchone()
            if not receta_db:
                raise HTTPException(status_code=404, detail="Receta no encontrada.")
            
            # La FK con ON DELETE CASCADE hará el resto
            cursor.execute("DELETE FROM recetas WHERE nombre_plato = %s", (nombre_plato,))
            conn.commit()
            return {"status": "ok", "message": "Receta eliminada"}

    except HTTPException:
        # Re-raise HTTP exceptions (como 404)
        raise
    except Exception as e:
        print(f"Error en eliminar_receta: {e}")
        conn.rollback() # Revertir la transacción en caso de error inesperado
        raise HTTPException(status_code=500, detail="Error interno del servidor al eliminar la receta.")

# --- FIN ENDPOINTS PARA RECETAS ---